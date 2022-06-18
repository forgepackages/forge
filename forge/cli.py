import importlib
import os
import subprocess
import sys

import click
from forgecore import Forge
from forgeheroku.cli import pre_deploy, serve


class NamespaceGroup(click.Group):
    COMMAND_PREFIX = "forge-"

    def list_commands(self, ctx):
        bin_dir = os.path.dirname(sys.executable)
        rv = []
        for filename in os.listdir(bin_dir):
            if filename.startswith(self.COMMAND_PREFIX):
                rv.append(filename[len(self.COMMAND_PREFIX) :])

        rv.sort()
        return rv

    def get_command(self, ctx, name):
        # Remove hyphens and prepend w/ "forge"
        # so "pre-commit" becomes "forgeprecommit" as an import
        import_name = "forge" + name.replace("-", "")
        try:
            i = importlib.import_module(import_name)
            return i.cli
        except ImportError as e:
            # Built-in commands will appear here, but so would failed imports of new ones
            pass
        except AttributeError as e:
            click.secho(f'Error importing "{import_name}":\n  {e}\n', fg="red")


@click.group()
def cli():
    pass


# Deprecated - moved to heroku serve and heroku pre-deploy
# (buildpack Procfile needs to support both for now?)
cli.add_command(serve)
cli.add_command(pre_deploy)


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

    # Turn deprecation warnings into errors
    if "-W" not in pytest_args:
        pytest_args = list(pytest_args)  # Make sure it's a list instead of tuple
        pytest_args.append("-W")
        pytest_args.append("error::DeprecationWarning")

    result = forge.venv_cmd(
        "pytest",
        *pytest_args,
        env={
            "PYTHONPATH": forge.project_dir,
        },
    )
    if result.returncode:
        # Can be invoked by pre-commit, so only exit if it fails
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
        try:
            from forgeformat import cli as format_cmd

            click.secho("Checking formatting", bold=True)
            ctx.invoke(format_cmd, check=True)
            click.echo()
        except ImportError:
            pass

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


cli = click.CommandCollection(sources=[NamespaceGroup(), cli])


if __name__ == "__main__":
    cli()
