import json
import os
import subprocess
import sys

import click
import requests
from click_didyoumean import DYMGroup

from .. import Forge


@click.group(cls=DYMGroup)
def db():
    """Start, stop, and manage the local Postgres database"""
    pass


@db.command()
@click.option("--logs", is_flag=True)
def start(logs):
    forge = Forge()
    forge.db_container.start()

    if logs:
        forge.db_container.logs()


@db.command()
def stop():
    forge = Forge()
    forge.db_container.stop()
    click.secho("Database stopped", fg="green")


@db.command()
def reset():
    forge = Forge()
    forge.db_container.reset(create=True)
    click.secho("Local development database reset", fg="green")


@db.command()
@click.option("--backup", is_flag=True)
@click.option(
    "--anonymize",
    type=bool,
    default=None,
    help="Anonymize data during import, enabled by default if anonymize installed",
)
@click.pass_context
def pull(ctx, backup, anonymize):
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
