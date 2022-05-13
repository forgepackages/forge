import glob
import json
import os
import platform
import shutil
import subprocess
import sys

import click
import requests
from django.core.management.utils import get_random_secret_key
from dotenv import set_key as dotenv_set_key
from honcho.manager import Manager as HonchoManager

from . import Forge
from .tailwind import Tailwind


@click.group()
def cli():
    pass


@cli.command("format")  # format is a keyword
@click.option("--check", is_flag=True)
def format_cmd(check):
    forge = Forge()

    # Make relative for nicer output
    target = os.path.relpath(forge.app_dir)

    black_args = ["--extend-exclude", "migrations"]
    if check:
        black_args.append("--check")
    black_args.append(target)
    forge.venv_cmd(
        "black",
        *black_args,
        check=True,
    )

    # Include --src so internal imports are recognized correctly
    isort_args = ["--extend-skip", "migrations", "--profile", "black", "--src", target]
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

        click.secho("Checking database connection", bold=True)
        if forge.manage_cmd("dbconnected").returncode:
            click.secho("Running Django checks (without database)", bold=True)
            forge.manage_cmd("check", check=True)
        else:
            click.secho("Running Django checks", bold=True)
            forge.manage_cmd("check", "--database", "default", check=True)

            click.secho("Checking Django migrations", bold=True)
            forge.manage_cmd("migrate", "--check", check=True)

        click.secho("Running tests", bold=True)
        ctx.invoke(test)


@cli.command(
    context_settings=dict(
        ignore_unknown_options=True,
    )
)
@click.argument("managepy_args", nargs=-1, type=click.UNPROCESSED)
def django(managepy_args):
    result = Forge().manage_cmd(*managepy_args)
    if result.returncode:
        sys.exit(result.returncode)


@cli.command()
@click.option("--heroku", is_flag=True)
def shell(heroku):
    """Open a Python shell"""
    if heroku:
        subprocess.run(["heroku", "run", "python app/manage.py shell"])
    else:
        Forge().manage_cmd("shell")


@cli.command()
def work():
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


@cli.group()
def db():
    pass


@db.command("start")
@click.option("--logs", is_flag=True)
def db_start(logs):
    forge = Forge()
    forge.db_container.start()

    if logs:
        forge.db_container.logs()


@db.command("stop")
def db_stop():
    forge = Forge()
    forge.db_container.stop()
    click.secho("Database stopped", fg="green")


@db.command("reset")
def db_reset():
    forge = Forge()
    forge.db_container.reset(create=True)
    click.secho("Local development database reset", fg="green")


@db.command("pull")
@click.option("--backup", is_flag=True)
@click.option(
    "--anonymize",
    type=bool,
    default=None,
    help="Anonymize data during import, enabled by default if anonymize installed",
)
@click.pass_context
def db_pull(ctx, backup, anonymize):
    forge = Forge()

    # Make sure Django works first
    if forge.manage_cmd("check").returncode:
        click.secho("Django check failed!", fg="red")
        sys.exit(1)

    anonymize_installed = (
        forge.manage_cmd(
            "anonymizedump",
            "--help",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )
    if anonymize and not anonymize_installed:
        raise Exception("Anonymize is not installed")

    if anonymize_installed and anonymize is None:
        click.secho("Enabling anonymize by default", fg="yellow")
        anonymize = True

    if not anonymize and not click.confirm(
        "Anonymization is not enabled. Are you sure you want to download production data?"
    ):
        return

    if backup:
        click.secho("Creating a backup using heroku pg:backups:capture", bold=True)
        subprocess.check_call(["heroku", "pg:backups:capture"])

    backup_lines = (
        subprocess.check_output(["heroku", "pg:backups"]).decode().splitlines()[1:4]
    )
    if backup_lines[-1].startswith("No backups"):
        click.Abort("No backups found. Run with --backup to make a new backup now.")

    click.secho("Using latest Heroku backup", bold=True)
    for line in backup_lines:
        click.echo(line)
    click.echo()

    forge.db_container.start()

    heroku_app_name = json.loads(
        subprocess.check_output(["heroku", "apps:info", "--json"]).decode().strip()
    )["app"]["name"]

    # TODO way to check if container ready?

    backup_name = backup_lines[-1].split()[0]

    backup_url = (
        subprocess.check_output(["heroku", "pg:backups:url", backup_name])
        .decode()
        .strip()
    )

    if not anonymize:
        dump_path = os.path.join(forge.forge_tmp_dir, f"{heroku_app_name}.dump")
        dump_compressed = True
        click.secho(
            f"Downloading Heroku backup to {os.path.relpath(dump_path)}", bold=True
        )
        subprocess.check_call(["curl", "-o", dump_path, backup_url])
    else:
        dump_path = os.path.join(
            forge.forge_tmp_dir, f"{heroku_app_name}.anonymized.dump"
        )
        dump_compressed = False
        click.secho(
            f"Anonymizing Heroku backup and saving to {os.path.relpath(dump_path)}",
            bold=True,
        )
        with requests.get(backup_url, stream=True) as r:
            r.raise_for_status()

            p = subprocess.Popen(
                [
                    "python",
                    forge.user_or_forge_path("manage.py"),
                    "anonymizedump",
                    "--output",
                    dump_path,
                ],
                env={**os.environ, "PYTHONPATH": forge.app_dir},
                stdin=subprocess.PIPE,
            )
            for chunk in r.iter_content(2048):
                p.stdin.write(chunk)
            _, stderr = p.communicate()
            if stderr:
                print(stderr)

            if p.returncode != 0:
                click.secho("Failed to anonymize Heroku backup", fg="red")
                exit(p.returncode)

    click.secho("Importing database from Heroku backup", bold=True)
    forge.db_container.restore_dump(dump_path, compressed=dump_compressed)

    # TODO run migrations afterwards too?

    click.secho("Database imported!", fg="green")


@cli.group()
def quickstart():
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
    template_path = os.path.join(os.path.dirname(__file__), "scaffold", "template")

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
    event("Creating default team and user migrations")
    Forge().manage_cmd("makemigrations", stderr=subprocess.DEVNULL)


@quickstart.command()
@click.option("--postgres-tier", default="hobby-dev")
@click.option("--redis-tier", default="hobby-dev")
@click.option("--team", default="")
@click.argument("heroku_app_name")
@click.pass_context
def heroku(ctx, heroku_app_name, postgres_tier, redis_tier, team):
    if (
        subprocess.call(
            ["git", "remote", "show", "heroku"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        == 0
    ):
        click.secho("heroku remote already exists", fg="red", err=True)
        sys.exit(1)

    if team:
        click.secho(f"Creating Heroku app on {team}", bold=True)
        subprocess.check_call(
            ["heroku", "apps:create", heroku_app_name, "--team", team]
        )
    else:
        click.secho("Creating Heroku app", bold=True)
        subprocess.check_call(["heroku", "apps:create", heroku_app_name])

    click.secho("Setting Heroku buildpacks", bold=True)
    subprocess.check_call(["heroku", "buildpacks:clear"])
    subprocess.check_call(
        [
            "heroku",
            "buildpacks:add",
            "https://github.com/django-forge/heroku-buildpack-forge.git",
        ]
    )
    subprocess.check_call(
        [
            "heroku",
            "buildpacks:add",
            "https://github.com/moneymeets/python-poetry-buildpack.git",
        ]
    )
    subprocess.check_call(["heroku", "buildpacks:add", "heroku/python"])

    click.secho("Adding Postgres and Redis", bold=True)
    subprocess.check_call(
        ["heroku", "addons:create", f"heroku-postgresql:{postgres_tier}"]
    )
    subprocess.check_call(["heroku", "addons:create", f"heroku-redis:{redis_tier}"])

    click.secho("Setting PYTHON_RUNTIME_VERSION, SECRET_KEY, and BASE_URL", bold=True)
    python_version = platform.python_version()
    secret_key = get_random_secret_key()
    # TODO --domain option?
    base_url = f"https://{heroku_app_name}.herokuapp.com"
    subprocess.check_call(
        [
            "heroku",
            "config:set",
            f"PYTHON_RUNTIME_VERSION={python_version}",
            f"SECRET_KEY={secret_key}",
            f"BASE_URL={base_url}",
        ]
    )

    click.secho("Enabling runtime-dyno-metadata", bold=True)
    subprocess.check_call(["heroku", "labs:enable", "runtime-dyno-metadata"])

    click.secho(
        f"You're all set! Connect your GitHub repo to the Heroku app at:\n\n  https://dashboard.heroku.com/apps/{heroku_app_name}/deploy/github",
        fg="green",
    )


@cli.group()
def tailwind():
    pass


@tailwind.command("compile")
@click.option("--watch", is_flag=True)
@click.option("--minify", is_flag=True)
def tailwind_compile(watch, minify):
    forge = Forge()
    tailwind = Tailwind(forge.forge_tmp_dir)

    if not tailwind.is_installed() or tailwind.needs_update():
        version_to_install = tailwind.get_version_from_config()
        if version_to_install:
            click.secho(
                f"Installing Tailwind standalone {version_to_install}...", bold=True
            )
            version = tailwind.install(version_to_install)
        else:
            click.secho("Installing Tailwind standalone...", bold=True)
            version = tailwind.install()
        click.secho(f"Tailwind {version} installed", fg="green")

    args = [tailwind.standalone_path]

    args.append("-i")
    args.append(os.path.join(forge.app_dir, "static", "src", "tailwind.css"))

    args.append("-o")
    args.append(os.path.join(forge.app_dir, "static", "dist", "tailwind.css"))

    # These paths should actually work on Windows too
    # https://github.com/mrmlnc/fast-glob#how-to-write-patterns-on-windows
    args.append("--content")
    args.append(
        ",".join(
            [
                "./app/**/*.{html,js}",
                "./{.venv,.heroku/python}/lib/python*/site-packages/forge*/**/*.{html,js}",
            ]
        )
    )

    if watch:
        args.append("--watch")

    if minify:
        args.append("--minify")

    subprocess.check_call(args, cwd=os.path.dirname(forge.app_dir))


@tailwind.command("update")
def tailwind_update():
    forge = Forge()
    tailwind = Tailwind(forge.forge_tmp_dir)
    click.secho("Installing Tailwind standalone...", bold=True)
    version = tailwind.install()
    click.secho(f"Tailwind {version} installed", fg="green")


if __name__ == "__main__":
    cli()
