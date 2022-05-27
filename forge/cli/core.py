import glob
import json
import os
import shutil
import subprocess
import sys

import click
from click_didyoumean import DYMGroup
from dotenv import set_key as dotenv_set_key
from honcho.manager import Manager as HonchoManager

from .. import Forge
from .db import db
from .heroku import heroku
from .tailwind import tailwind


@click.group(cls=DYMGroup)
def cli():
    pass


cli.add_command(heroku)
cli.add_command(db)
cli.add_command(tailwind)


@cli.command("format")  # format is a keyword
@click.option("--check", is_flag=True)
@click.option("--black", is_flag=True, default=True)
@click.option("--isort", is_flag=True, default=True)
def format_cmd(check, black, isort):
    """Format Python code with black and isort"""
    forge = Forge()

    # Make relative for nicer output
    target = os.path.relpath(forge.app_dir)

    if black:
        click.secho("Formatting with black", bold=True)
        black_args = ["--extend-exclude", "migrations"]
        if check:
            black_args.append("--check")
        black_args.append(target)
        forge.venv_cmd(
            "black",
            *black_args,
            check=True,
        )

    if black and isort:
        click.echo()

    if isort:
        click.secho("Formatting with isort", bold=True)
        isort_config_root = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "forge_isort.cfg"
        )

        # Include --src so internal imports are recognized correctly
        isort_args = ["--settings-file", isort_config_root, "--src", target]
        if check:
            isort_args.append("--check")
        isort_args.append(target)
        forge.venv_cmd("isort", *isort_args, check=True)


@cli.command(
    context_settings=dict(
        ignore_unknown_options=True,
    )
)
@click.argument("pytest_args", nargs=-1, type=click.UNPROCESSED)
def test(pytest_args):
    """Run tests with pytest"""
    forge = Forge()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    result = forge.venv_cmd(
        "pytest",
        *pytest_args,
        env={
            "PYTHONPATH": forge.app_dir,
        },
    )
    if result.returncode:
        # Can be invoked by pre-commit, so only exit if it fails
        sys.exit(result.returncode)


@cli.command("pre-deploy")
def pre_deploy():
    """Pre-deploy checks for release process"""
    forge = Forge()

    click.secho("Running Django system checks", bold=True)
    forge.manage_cmd("check", "--deploy", "--fail-level", "WARNING", check=True)

    click.echo()

    click.secho("Running Django migrations", bold=True)
    forge.manage_cmd("migrate", check=True)


@cli.command()
def serve():
    """Run a production server using gunicorn (Heroku)"""
    forge = Forge()
    wsgi = "wsgi" if forge.user_file_exists("wsgi.py") else "forge.default_files.wsgi"
    result = forge.venv_cmd(
        "gunicorn",
        f"{wsgi}:application",
        "--log-file",
        "-",
        env={
            "PYTHONPATH": forge.app_dir,
        },
    )
    sys.exit(result.returncode)


@cli.command()
@click.option("--install", is_flag=True)
@click.pass_context
def pre_commit(ctx, install):
    """Git pre-commit checks"""
    forge = Forge()

    if install:
        if not forge.repo_root:
            click.secho("Not in a git repository", fg="red")
            sys.exit(1)

        hook_path = os.path.join(forge.repo_root, ".git", "hooks", "pre-commit")
        if os.path.exists(hook_path):
            print("pre-commit hook already exists")
        else:
            with open(hook_path, "w") as f:
                f.write(
                    f"""#!/bin/sh
forge pre-commit"""
                )
            os.chmod(hook_path, 0o755)
            print("pre-commit hook installed")
    else:
        click.secho("Checking formatting", bold=True)
        ctx.invoke(format_cmd, check=True)

        click.echo()
        click.secho("Checking database connection", bold=True)
        if forge.manage_cmd("dbconnected").returncode:
            click.echo()
            click.secho("Running Django checks (without database)", bold=True)
            forge.manage_cmd("check", check=True)
        else:
            click.echo()
            click.secho("Running Django checks", bold=True)
            forge.manage_cmd("check", "--database", "default", check=True)

            click.echo()
            click.secho("Checking Django migrations", bold=True)
            forge.manage_cmd("migrate", "--check", check=True)

        click.echo()
        click.secho("Running tests", bold=True)
        ctx.invoke(test)


@cli.command(
    context_settings=dict(
        ignore_unknown_options=True,
    )
)
@click.argument("managepy_args", nargs=-1, type=click.UNPROCESSED)
def django(managepy_args):
    """Pass commands to Django manage.py"""
    result = Forge().manage_cmd(*managepy_args)
    if result.returncode:
        sys.exit(result.returncode)


@cli.command()
@click.option("--heroku", is_flag=True)
def shell(heroku):
    """Open a Python/Django shell"""
    if heroku:
        subprocess.run(["heroku", "run", "python app/manage.py shell"])
    else:
        Forge().manage_cmd("shell")


@cli.command()
def work():
    """Start local development"""
    # TODO check docker is available first

    forge = Forge()

    repo_root = forge.repo_root
    if not repo_root:
        click.secho("Not in a git repository", fg="red")
        sys.exit(1)

    dotenv_path = os.path.join(repo_root, ".env")

    django_env = {
        "PYTHONPATH": forge.app_dir,
        "PYTHONUNBUFFERED": "true",
    }
    if (
        "STRIPE_WEBHOOK_PATH" in os.environ
        and "STRIPE_WEBHOOK_SECRET" not in os.environ
    ):
        # TODO check stripe command available, need to do the same with docker
        stripe_webhook_secret = (
            subprocess.check_output(["stripe", "listen", "--print-secret"])
            .decode()
            .strip()
        )
        click.secho("Adding automatic STRIPE_WEBHOOK_SECRET to .env", fg="green")
        dotenv_set_key(
            dotenv_path,
            "STRIPE_WEBHOOK_SECRET",
            stripe_webhook_secret,
            quote_mode="auto",
        )
        os.environ["STRIPE_WEBHOOK_SECRET"] = stripe_webhook_secret

    if forge.manage_cmd("check", env=django_env).returncode:
        click.secho("Django check failed!", fg="red")
        sys.exit(1)

    managepy = forge.user_or_forge_path("manage.py")

    runserver_port = os.environ.get("RUNSERVER_PORT", "8000")

    manage_cmd = f"python {managepy}"

    manager = HonchoManager()

    # Meant to work with Forge Pro, but doesn't necessarily have to
    if "STRIPE_WEBHOOK_PATH" in os.environ:
        manager.add_process(
            "stripe",
            f"stripe listen --forward-to localhost:{runserver_port}{os.environ['STRIPE_WEBHOOK_PATH']}",
        )

    # So this can work in development too...
    forge_executable = os.path.join(os.path.dirname(sys.executable), "forge")

    manager.add_process("postgres", f"{forge_executable} db start --logs")

    manager.add_process(
        "django",
        f"{manage_cmd} dbwait && {manage_cmd} migrate && {manage_cmd} runserver {runserver_port}",
        env={
            **os.environ,
            **django_env,
        },
    )

    manager.add_process("tailwind", f"{forge_executable} tailwind compile --watch")

    if "NGROK_SUBDOMAIN" in os.environ:
        manager.add_process(
            "ngrok",
            f"ngrok http {runserver_port} --log stdout --subdomain {os.environ['NGROK_SUBDOMAIN']}",
        )

    # Run package.json "watch" script automatically
    package_json = os.path.join(repo_root, "package.json")
    if os.path.exists(package_json):
        with open(package_json) as f:
            package_json_data = json.load(f)
        if "watch" in package_json_data.get("scripts", {}):
            manager.add_process(
                "npm watch",
                "npm run watch",
            )

    manager.loop()

    sys.exit(manager.returncode)


@cli.group(cls=DYMGroup)
def quickstart():
    """Quickstart commands"""
    pass


@quickstart.command()
@click.pass_context
def template(ctx):
    """Forge is already installed, and presumably in a git repo."""

    # Matches the format in quickstart.py
    def event(text, *args, **kwargs):
        print("\033[1m--> " + text + "\033[0m", *args, **kwargs)

    # Do a basic sanity check for whether we should continue
    if os.path.exists("app"):
        click.secho("app directory already exists", fg="red", err=True)
        sys.exit(1)

    event("Creating project files")
    destination = os.getcwd()
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "scaffold", "template"
    )

    # Copy .env manually for now (not in basic glob)
    shutil.copy(os.path.join(template_path, ".env"), destination)

    for f in glob.glob(os.path.join(template_path, "*")):
        if os.path.isfile(f):
            shutil.copy(f, destination)
        else:
            shutil.copytree(f, os.path.join(destination, os.path.basename(f)))

    event("Installing pre-commit hook")
    ctx.invoke(pre_commit, install=True)

    # technically this will give an error code because db isn't running
    event("Creating default team and user migrations\n")
    Forge().manage_cmd("makemigrations", "--no-input", stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    cli()
