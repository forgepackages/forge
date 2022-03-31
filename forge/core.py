import os
import subprocess


class Forge:
    def __init__(self, target_path=os.getcwd()):
        self.target_path = target_path

        self.repo_root = (
            subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], cwd=self.target_path
            )
            .decode("utf-8")
            .strip()
        )
        self.venv_bin = os.path.join(self.repo_root, ".venv", "bin")
        self.project_slug = os.path.basename(self.repo_root)

        if self.repo_root == self.target_path:
            # If we're at the root of the repo, then presume the app is in "app"
            self.app_dir = os.path.join(self.repo_root, "app")
        else:
            # Otherwise consider the app to be the current directory (app dir can be "tests", or something else)
            self.app_dir = self.target_path

    def venv_cmd(self, executable, *args, **kwargs):
        return subprocess.run(
            [f"{self.venv_bin}/{executable}"] + list(args),
            env={**os.environ, "PYTHONPATH": self.app_dir},
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
