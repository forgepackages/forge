import os
import subprocess
import sys

DEFAULT_FORGE_SOURCE = "forge1"  # TODO change this when name changes
GITIGNORE_CONTENTS = """# Local development files
/.env
/.forge

# Bundled assets
/app/static/dist

# Collected staticfiles
/app/staticfiles

# Python
/.venv
__pycache__/
*.py[cod]
*$py.class

# JS
/node_modules

# OS files
.DS_Store
"""

POETRY_NOTICE = """This quickstart uses Poetry! It doesn't look like you have `poetry` installed (or it isn't in your PATH).

You can install Poetry with a one-line command found here:

  https://python-poetry.org/docs/#installation"

When you're ready, try running this command again."""


def event(text, *args, **kwargs):
    print("\033[1m--> " + text + "\033[0m", *args, **kwargs)


def main(project_name, forge_source):
    try:
        subprocess.check_output(["poetry", "--version"])
    except FileNotFoundError:
        print(POETRY_NOTICE)
        sys.exit(1)

    if os.path.exists(project_name):
        print(f"{project_name} already exists")
        sys.exit(1)

    event(f"Creating new project: {project_name}")
    os.mkdir(project_name)

    event("Running git init")
    subprocess.check_call(["git", "init"], cwd=project_name)

    event("Creating .gitignore")
    with open(os.path.join(project_name, ".gitignore"), "w") as f:
        f.write(GITIGNORE_CONTENTS)

    event("Running poetry init")
    subprocess.check_call(
        [
            "poetry",
            "init",
            "--no-interaction",
            "--name",
            project_name,
            "--dependency",
            forge_source,
        ],
        cwd=project_name,
    )

    event("Installing poetry dependencies")
    subprocess.check_call(
        ["poetry", "install"],
        cwd=project_name,
        env={**os.environ, "POETRY_VIRTUALENVS_IN_PROJECT": "true"},
    )

    print()
    subprocess.check_call(
        ["poetry", "run", "forge", "init"],
        cwd=project_name,
    )

    print(
        f"""
\033[32mYou're ready to go! First, go to your project directory with:\033[0m

  \033[1;32mcd {project_name}\033[0m

\033[32mTo do local development run:\033[0m

  \033[1;32mforge work\033[0m

\033[32mOnce that's up and running, you can make a new window or tab and create a superadmin user with:\033[0m

  \033[1;32mforge django createsuperuser\033[0m

\033[32mCheck the documentation for more details:\033[0m

  \033[1;32mhttps://www.djangoforge.dev/docs/\033[0m
"""
    )


if __name__ == "__main__":
    if len(sys.argv) < 2 or not sys.argv[1]:
        print("A package name is required as the argument")
        sys.exit(1)

    if "--source" in sys.argv:
        forge_source = sys.argv[sys.argv.index("--source") + 1]
        sys.argv.remove("--source")
        sys.argv.remove(forge_source)
    else:
        forge_source = DEFAULT_FORGE_SOURCE

    project_name = sys.argv[1]

    main(project_name, forge_source)
