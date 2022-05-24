import platform
import subprocess
import sys

import click
from click_didyoumean import DYMGroup
from django.core.management.utils import get_random_secret_key


@click.group(cls=DYMGroup)
def heroku():
    """Shortcuts for common Heroku operations"""
    pass


@heroku.command()
@click.option("--postgres-tier", default="hobby-dev")
@click.option("--redis-tier", default="hobby-dev")
@click.option("--team", default="")
@click.argument("heroku_app_name")
@click.pass_context
def create(ctx, heroku_app_name, postgres_tier, redis_tier, team):
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
