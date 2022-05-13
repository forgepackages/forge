import os
import re
import subprocess

import dj_database_url
from dotenv import load_dotenv


class Forge:
    def __init__(self, target_path=os.getcwd()):
        # Where local psql data goes, tailwind
        self.forge_tmp_dir = os.path.join(target_path, ".forge")

        try:
            self.repo_root = (
                subprocess.check_output(
                    ["git", "rev-parse", "--show-toplevel"],
                    cwd=target_path,
                    stderr=subprocess.DEVNULL,
                )
                .decode("utf-8")
                .strip()
            )
            self.forge_tmp_dir = os.path.join(self.repo_root, ".forge")
        except subprocess.CalledProcessError:
            # On Heroku, there won't be a repo, so we can't require that necessarily
            # (helps with some other scenarios too)
            self.repo_root = None

        # Load a .env if one exists in the repo root
        if self.repo_root and os.path.exists(os.path.join(self.repo_root, ".env")):
            load_dotenv(os.path.join(self.repo_root, ".env"))

        # If there's a directory named "app" right here,
        # assume that's the Django project.
        if os.path.exists(os.path.join(target_path, "app")):
            self.app_dir = os.path.join(target_path, "app")
        else:
            self.app_dir = target_path

        # Make sure the tmp dir exists
        if not os.path.exists(self.forge_tmp_dir):
            os.mkdir(self.forge_tmp_dir)

        if self.repo_root:
            self.db_container = DBContainer(
                name=os.path.basename(self.repo_root) + "-postgres",
                tmp_dir=self.forge_tmp_dir,
            )
        else:
            self.db_container = None

    def venv_cmd(self, executable, *args, **kwargs):
        # implement our own check without a stacktrace
        check = kwargs.pop("check", False)

        result = subprocess.run(
            [executable] + list(args),
            env={
                **os.environ,
                **kwargs.pop("env", {}),
            },
            check=False,
            cwd=kwargs.pop("cwd", None),
            **kwargs,
        )

        if check and result.returncode != 0:
            exit(result.returncode)

        return result

    def manage_cmd(self, *args, **kwargs):
        # Make sure our app is in the PYTHONPATH
        # when running manage.py commands
        kwargs["env"] = {"PYTHONPATH": self.app_dir}

        return self.venv_cmd(
            "python", self.user_or_forge_path("manage.py"), *args, **kwargs
        )

    def user_file_exists(self, filename):
        return os.path.exists(os.path.join(self.app_dir, filename))

    def user_or_forge_path(self, filename):
        if os.path.exists(os.path.join(self.app_dir, filename)):
            return os.path.join(self.app_dir, filename)
        return os.path.join(os.path.dirname(__file__), "default_files", filename)


class DBContainer:
    def __init__(self, name, tmp_dir):
        self.name = name
        self.tmp_dir = os.path.abspath(tmp_dir)
        self.postgres_version = os.environ.get("POSTGRES_VERSION", "13")
        parsed_db_url = dj_database_url.parse(os.environ.get("DATABASE_URL"))
        self.postgres_port = parsed_db_url.get("PORT", "5432")
        self.postgres_db = parsed_db_url.get("NAME", "postgres")
        self.postgres_user = parsed_db_url.get("USER", "postgres")
        self.postgres_password = parsed_db_url.get("PASSWORD", "postgres")

    def start(self):
        try:
            subprocess.check_output(
                [
                    "docker",
                    "run",
                    "--detach",
                    "--name",
                    self.name,
                    "--rm",
                    "-e",
                    f"POSTGRES_USER={self.postgres_user}",
                    "-e",
                    f"POSTGRES_PASSWORD={self.postgres_password}",
                    "-v",
                    f"{self.tmp_dir}/pgdata:/var/lib/postgresql/data",
                    "-p",
                    f"{self.postgres_port}:5432",
                    f"postgres:{self.postgres_version}",
                ],
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            if "already in use" not in e.stderr.decode():
                raise

    def stop(self):
        try:
            subprocess.check_output(
                [
                    "docker",
                    "stop",
                    self.name,
                ],
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            if "No such container" not in e.stderr.decode():
                raise

    def logs(self):
        subprocess.check_call(
            [
                "docker",
                "logs",
                "--follow",
                self.name,
            ],
        )

    def execute(self, command, *args, **kwargs):
        docker_flags = kwargs.pop("docker_flags", "-it")
        return subprocess.run(
            [
                "docker",
                "exec",
                docker_flags,
                self.name,
                *command.split(),
            ]
            + list(args),
            check=True,
            **kwargs,
        )

    def reset(self, create=False):
        try:
            self.execute(
                f"dropdb {self.postgres_db} --force -U {self.postgres_user}",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            if "does not exist" not in e.stdout.decode():
                raise

        if create:
            self.execute(
                f"createdb {self.postgres_db} -U {self.postgres_user}",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def restore_dump(self, dump_path, compressed=False):
        """Imports a dump into {name}_import, then renames to {name} to prevent Django connections during process"""
        maintenance_db = "template1"
        import_db = f"{self.postgres_db}_import"

        self.execute(
            f"dropdb {import_db} --if-exists -U {self.postgres_user}",
            stdout=subprocess.DEVNULL,
        )
        self.execute(
            f"createdb {import_db} -U {self.postgres_user}", stdout=subprocess.DEVNULL
        )

        if compressed:
            restore_command = (
                f"pg_restore --no-owner --dbname {import_db} -U {self.postgres_user}"
            )
        else:
            # Text format can to straight in (has already gone through pg_restore to get text format)
            restore_command = f"psql {import_db} -U {self.postgres_user}"

        result = self.execute(
            restore_command,
            stdin=open(dump_path),
            docker_flags="-i",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        if result.stderr:
            # Print errors except for role does not exist (can't ignore this in psql-style import)
            role_error_re = re.compile(r"^ERROR:  role \".+\" does not exist")
            for line in result.stderr.decode().splitlines():
                if not role_error_re.match(line):
                    print(line)

        # Get rid of the main database
        self.reset(create=False)

        # Connect to template1 (which should exist as "maintenance db") so we can rename the others
        self.execute(
            f"psql -U {self.postgres_user} {maintenance_db} -c",
            f"ALTER DATABASE {import_db} RENAME TO {self.postgres_user}",
            stdout=subprocess.DEVNULL,
        )
