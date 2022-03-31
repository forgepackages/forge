import glob
import os
import shutil
import subprocess
import sys

import click
import dj_database_url
from dotenv import dotenv_values, load_dotenv
from honcho.manager import Manager as HonchoManager

from . import Forge


@click.group()
def cli():
    pass


@cli.command("format")  # format is a keyword
@click.option("--check", is_flag=True)
def format_cmd(check):
    forge = Forge()
    forge.venv_cmd("black", "--exclude", "migrations", forge.app_dir, check=check)
    forge.venv_cmd("isort", "--skip", "migrations", forge.app_dir, check=check)


@cli.command(
    context_settings=dict(
        ignore_unknown_options=True,
    )
)
@click.argument("pytest_args", nargs=-1, type=click.UNPROCESSED)
def test(pytest_args):
    forge = Forge()
    load_dotenv()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    result = forge.venv_cmd(
        "pytest",
        *pytest_args,
        env={
            "PYTHONPATH": forge.app_dir,
        },
    )
    sys.exit(result.returncode)


@cli.command("pre-deploy")
def pre_deploy():
    forge = Forge()

    click.secho("Running Django system checks", bold=True)
    forge.manage_cmd("check", "--deploy", "--fail-level", "WARNING", check=True)

    click.secho("Running Django migrations", bold=True)
    forge.manage_cmd("migrate", check=True)


@cli.command()
def serve():
    """Run a production server using gunicorn (should be used for Heroku process)"""
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
    if install:
        forge = Forge()

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

        """#!/bin/sh -e

        BOLD="\033[1m"
        NORMAL="\033[0m"

        echo "${BOLD}Checking formatting${NORMAL}"
        ./scripts/format --check

        echo ""
        echo "${BOLD}Checking database connection${NORMAL}"
        if ! ./scripts/manage dbconnected; then
            echo ""
            echo "${BOLD}Running Django checks (without database)${NORMAL}"
            ./scripts/manage check
        else
            echo ""
            echo "${BOLD}Running Django checks${NORMAL}"
            ./scripts/manage check --database default

            echo ""
            echo "${BOLD}Checking Django migrations${NORMAL}"
            ./scripts/manage migrate --check
        fi

        echo ""
        echo "${BOLD}Running tests${NORMAL}"
        ./scripts/test"""

        click.secho("Checking formatting", bold=True)
        ctx.invoke(format_cmd, check=True)


@cli.command(
    context_settings=dict(
        ignore_unknown_options=True,
    )
)
@click.argument("managepy_args", nargs=-1, type=click.UNPROCESSED)
def django(managepy_args):
    result = Forge().manage_cmd(*managepy_args)
    sys.exit(result.returncode)


@cli.command()
def work():
    # TODO check docker is available first

    forge = Forge()

    repo_root = forge.repo_root
    if not repo_root:
        click.secho("Not in a git repository", fg="red")
        sys.exit(1)

    project_slug = os.path.basename(repo_root)

    managepy = forge.user_or_forge_path("manage.py")

    dotenv = dotenv_values(os.path.join(repo_root, ".env"))

    postgres_version = dotenv.get("POSTGRES_VERSION", "10.4")
    postgres_port = dj_database_url.parse(dotenv.get("DATABASE_URL"))["PORT"]
    runserver_port = dotenv.get("RUNSERVER_PORT", "8000")

    manage_cmd = f"python {managepy}"

    manager = HonchoManager()
    manager.add_process(
        "postgres",
        f"docker run --name {project_slug}-postgres --rm -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -v {repo_root}/.forge/pgdata:/var/lib/postgresql/data -p {postgres_port}:5432 postgres:{postgres_version} || docker attach {project_slug}-postgres",
    )
    manager.add_process(
        "django",
        f"{manage_cmd} dbwait && {manage_cmd} migrate && {manage_cmd} runserver {runserver_port}",
        env={
            **os.environ,
            "PYTHONPATH": forge.app_dir,
            "PYTHONUNBUFFERED": "true",
        },
    )
    manager.add_process("tailwind", "npm run watch")

    if "NGROK_SUBDOMAIN" in dotenv:
        manager.add_process(
            "ngrok",
            "ngrok http {runserver_port} --subdomain {dotenv['NGROK_SUBDOMAIN']}",
        )

    manager.loop()

    sys.exit(manager.returncode)


@cli.command()
@click.pass_context
def init(ctx):
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
    template_path = os.path.join(os.path.dirname(__file__), "scaffold", "template")

    # Copy .env manually for now (not in basic glob)
    shutil.copy(os.path.join(template_path, ".env"), destination)

    for f in glob.glob(os.path.join(template_path, "*")):
        if os.path.isfile(f):
            shutil.copy(f, destination)
        else:
            shutil.copytree(f, os.path.join(destination, os.path.basename(f)))

    # package.json comes with template, not quickstart
    event("Installing npm dependencies")
    subprocess.check_call(["npm", "install"])

    event("Installing pre-commit hook")
    ctx.invoke(pre_commit, install=True)

    # technically this will give an error code because db isn't running
    event("Creating default team and user migrations")
    Forge().manage_cmd("makemigrations", stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    cli()
