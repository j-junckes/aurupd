from tempfile import TemporaryDirectory
import tempfile
import re
import os
import subprocess
from termcolor import colored

class AurPackage:
    name: str
    version: str | None
    description: str
    ssh_git_url: str
    https_git_url: str
    build_dir: TemporaryDirectory[str]
    new_version: str | None
    downloaded: bool
    used_ssh: bool

    def __init__(self, name: str, description: str):
        self.name = name
        self.version = None
        self.description = description
        self.ssh_git_url = f"ssh://aur@aur.archlinux.org/{name}.git"
        self.https_git_url = f"https://aur.archlinux.org/{name}.git"
        self.build_dir = tempfile.TemporaryDirectory()
        self.new_version = None
        self.downloaded = False
        self.used_ssh = False

    def needs_update(self):
        return self.version.strip() != self.new_version.strip()

    def __str__(self):
        return f"{self.name} - {self.version}"

    def __repr__(self):
        return f"{self.name} - {self.version}"

    def __del__(self):
        self.build_dir.cleanup()

    def get_version_from_pkgbuild(self) -> str:
        # read PKGBUILD file
        pkgbuild_file = None
        for file in os.listdir(self.build_dir.name):
            if file == "PKGBUILD":
                pkgbuild_file = file
                break

        if not pkgbuild_file:
            raise Exception("Error finding PKGBUILD file")

        pkgbuild_content = ""

        with open(os.path.join(self.build_dir.name, pkgbuild_file), "r") as f:
            pkgbuild_content = f.read()

        # search for pkgver
        pkgver_match = re.search(r"^pkgver=((?:[0-9]|\.|[A-z]|_)*)$", pkgbuild_content, flags=re.M)

        if not pkgver_match:
            raise Exception("Error finding pkgver in PKGBUILD")

        return pkgver_match.group(1)

    def check_package(self):
        # execute makepkg in the directory

        makepkg_result = subprocess.run(["makepkg", "-o"], cwd=self.build_dir.name, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)

        if makepkg_result.returncode != 0:
            raise Exception(f"Error building package {self.name}")

        self.new_version = self.get_version_from_pkgbuild()

    def download_package(self):
        if self.downloaded:
            return

        git_result = subprocess.run(["git", "clone", self.ssh_git_url, self.build_dir.name],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        self.used_ssh = True

        if git_result.returncode == 128:
            print(colored(f"\t\t- Package {self.name} is private, trying to clone with https. Please add your ssh key to ssh-agent", "yellow", attrs=["bold"]))
            git_result = subprocess.run(["git", "clone", self.https_git_url, self.build_dir.name],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.used_ssh = False

        if git_result.returncode != 0:
            raise Exception(f"Error cloning package {self.name}")

        self.version = self.get_version_from_pkgbuild()
        self.downloaded = True

    def init_package(self):
        self.download_package()
        self.check_package()

    def update_package(self, email: str | None, user: str | None, commit: bool | None):
        if not self.needs_update():
            print(colored(f"\t\t- {self.name} is up to date", "green"))
            return
        if not self.used_ssh:
            print(colored(f"\t\t- Unable to update {self.name} because it is a private package", "red"))
            return

        makepkg_result = subprocess.run(["makepkg", "-scC", "--noconfirm", "--noarchive"], cwd=self.build_dir.name, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)

        if makepkg_result.returncode != 0:
            raise Exception(f"Error updating package {self.name}")

        srcinfo = subprocess.run(["makepkg", "--printsrcinfo"], cwd=self.build_dir.name, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        if srcinfo.returncode != 0:
            raise Exception(f"Error updating package {self.name}")

        srcinfo_content = srcinfo.stdout.decode("utf-8")

        with open(os.path.join(self.build_dir.name, ".SRCINFO"), "w") as f:
            f.write(srcinfo_content)

        if email:
            git_setup = subprocess.run(["git", "config", "--local", "user.email", email], cwd=self.build_dir.name, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            if git_setup.returncode != 0:
                raise Exception(f"Error setting git email")

        if user:
            git_setup = subprocess.run(["git", "config", "--local", "user.name", user], cwd=self.build_dir.name, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            if git_setup.returncode != 0:
                raise Exception(f"Error setting git user")

        git_add = subprocess.run(["git", "add", "."], cwd=self.build_dir.name, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if git_add.returncode != 0:
            raise Exception(f"Error adding files to git")

        git_commit = subprocess.run(["git", "commit", "-m", commit], cwd=self.build_dir.name, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if git_commit.returncode != 0:
            raise Exception(f"Error committing changes")

        git_push = subprocess.run(["git", "push"], cwd=self.build_dir.name, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if git_push.returncode != 0:
            raise Exception(f"Error pushing changes")