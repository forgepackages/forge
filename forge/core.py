import os
import subprocess


class Forge:
    def __init__(self, target_path=os.getcwd()):
        self.target_path = target_path

        try:
            self.repo_root = (
                subprocess.check_output(
                    ["git", "rev-parse", "--show-toplevel"], cwd=self.target_path
                )
                .decode("utf-8")
                .strip()
            )
        except subprocess.CalledProcessError:
            # On Heroku, there won't be a repo, so we can't require that necessarily
            # (helps with some other scenarios too)
            self.repo_root = None

        if self.repo_root == self.target_path:
            # If we're at the root of the repo, then presume the app is in "app"
            self.app_dir = os.path.join(self.repo_root, "app")
        else:
            # Otherwise consider the app to be the current directory (app dir can be "tests", or something else)
            self.app_dir = self.target_path

    def venv_cmd(self, executable, *args, **kwargs):
        return subprocess.run(
            [executable] + list(args),
            env={
                **os.environ,
                "PYTHONPATH": self.app_dir,
                "PATH": os.environ["PATH"] + ":.venv/bin",
            },
            check=kwargs.pop("check", False),
            cwd=kwargs.pop("cwd", None),
            **kwargs,
        )

    def manage_cmd(self, *args, **kwargs):
        return self.venv_cmd(
            "python", self.user_or_forge_path("manage.py"), *args, **kwargs
        )

    def user_file_exists(self, filename):
        return os.path.exists(os.path.join(self.app_dir, filename))

    def user_or_forge_path(self, filename):
        if os.path.exists(os.path.join(self.app_dir, filename)):
            return os.path.join(self.app_dir, filename)
        return os.path.join(os.path.dirname(__file__), "default_files", filename)
