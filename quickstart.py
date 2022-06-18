import os
import shutil
import subprocess
import sys

DEFAULT_TEMPLATE_SOURCE = "https://github.com/forgepackages/starter-template"

POETRY_NOTICE = """This quickstart uses Poetry! It doesn't look like you have `poetry` installed (or it isn't in your PATH).

You can install Poetry with a one-line command found here:

  https://python-poetry.org/docs/#installation"

When you're ready, try running this command again."""


def event(text, *args, **kwargs):
    print("\033[1m" + text + "\033[0m", *args, **kwargs)


def main(project_name, template_source):
    try:
        subprocess.check_output(["poetry", "--version"])
    except FileNotFoundError:
        print(POETRY_NOTICE)
        sys.exit(1)

    if os.path.exists(project_name):
        print(f"{project_name} already exists")
        sys.exit(1)

    if os.path.exists(template_source):
        event(f"Copying local template ({template_source})")
        subprocess.check_call(["cp", "-r", template_source, project_name])
    else:
        event(f"Creating new repo from template ({template_source})")
        subprocess.check_call(
            ["git", "clone", "--depth", "1", template_source, project_name],
            stdout=subprocess.DEVNULL,
        )

    shutil.rmtree(os.path.join(project_name, ".git"))
    subprocess.check_call(["git", "init"], cwd=project_name, stdout=subprocess.DEVNULL)

    print()
    subprocess.check_call(["./scripts/install"], cwd=project_name)

    print(
        f"""
\033[32mYou're ready to go! First, go to your project directory with:\033[0m

  \033[1;32mcd {project_name}\033[0m

\033[32mTo do local development run:\033[0m

  \033[1;32mforge work\033[0m

\033[32mOnce that's up and running, you can make a new window or tab and create a superadmin user with:\033[0m

  \033[1;32mforge django createsuperuser\033[0m

\033[32mCheck the documentation for more details:\033[0m

  \033[1;32mhttps://www.forgepackages.com/docs/\033[0m
"""
    )

    if ".venv/bin" not in os.environ["PATH"]:
        print(
            """
\033[1;33m⚠️  Check your PATH!\033[0m \033[33mForge projects use a virtual environment at ".venv" in your repo.
To make the `forge` command readily available, you'll probably want to add ".venv/bin" to your PATH.

To do this, add the following to your .bashrc or .zshrc file:\033[0m

\033[1;33m  export PATH="./.venv/bin:$PATH"\033[0m
"""
        )


if __name__ == "__main__":
    if len(sys.argv) < 2 or not sys.argv[1]:
        print("A package name is required as the argument")
        sys.exit(1)

    if "--source" in sys.argv:
        template_source = sys.argv[sys.argv.index("--source") + 1]
        sys.argv.remove("--source")
        sys.argv.remove(template_source)
    else:
        template_source = DEFAULT_TEMPLATE_SOURCE

    project_name = sys.argv[1]

    main(project_name, template_source)
