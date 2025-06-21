"""
Base repository profile class.

This module defines the abstract base class for repository profiles that specify
installation and testing configurations for different repositories.
"""

import os
import shutil
import subprocess

from abc import ABC, abstractmethod
from dotenv import load_dotenv
from ghapi.all import GhApi
from swebench.harness.constants import KEY_INSTANCE_ID
from swesmith.constants import ORG_NAME_DH, ORG_NAME_GH
from swesmith.utils import repo_exists, get_arch_and_platform


load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


class RepoProfile(ABC):
    """
    Base class for repository profiles that define installation and testing specifications.

    This class provides a language-agnostic interface for repository configuration,
    allowing different languages (Python, Go, Rust, etc.) to have their own
    installation and testing patterns while maintaining a consistent API.
    """

    owner: str
    repo: str
    commit: str
    org_dh: str = ORG_NAME_DH
    org_gh: str = ORG_NAME_GH

    # Install + Test specifications
    install_cmds: list[str] = None
    test_cmd: str = None

    # `min_testing`: If set, then subset of tests (not all) are run for post-bug validation
    # Affects get_test_command, get_valid_report
    min_testing: bool = False

    # `min_pregold`: If set, then for pre-bug validation, individual runs are
    # performed instead of running the entire test suite
    # Affects valid.py
    min_pregold: bool = False

    @abstractmethod
    def build_image(self):
        """Build a Docker image (execution environment) for this repository profile."""
        pass

    @property
    def image_name(self, arch: str | None = None) -> str:
        arch, _ = get_arch_and_platform()
        return f"{self.org_dh}/swesmith.{arch}.{self.owner}_1776_{self.repo}.{self.commit[:8]}".lower()

    @abstractmethod
    def log_parser(self, log: str) -> dict[str, str]:
        """Parse test output logs and extract relevant information."""
        pass

    @property
    def mirror_name(self):
        return f"{self.org_gh}/{self.repo_name}"

    @property
    def repo_name(self):
        return f"{self.owner}__{self.repo}.{self.commit[:8]}"

    def create_mirror_repo(self):
        """
        Create a mirror of this repository at the specified commit.
        """
        api = GhApi(token=GITHUB_TOKEN)

        if repo_exists(self.repo_name, self.org_gh):
            return
        if self.repo_name in os.listdir():
            shutil.rmtree(self.repo_name)
        api.repos.create_in_org(self.org, self.repo_name)
        for cmd in [
            f"git clone git@github.com:{self.mirror_name}.git {self.repo_name}",
            (
                f"cd {self.repo_name}; "
                f"git checkout {self.commit}; "
                "rm -rf .git; "
                "git init; "
                'git config user.name "swesmith"; '
                'git config user.email "swesmith@anon.com"; '
                "rm -rf .github/workflows; "
                "git add .; "
                "git commit -m 'Initial commit'; "
                "git branch -M main; "
                f"git remote add origin git@github.com:{self.mirror_name}.git; "
                "git push -u origin main",
            ),
            f"rm -rf {self.repo_name}",
        ]:
            subprocess.run(
                cmd,
                shell=True,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


### MARK: Profile Registry ###


class Registry:
    """Simple registry for mapping mirror names to profile classes."""

    def __init__(self):
        self._profiles = {}

    def register_profile(self, profile_class: type):
        """Register a single profile class."""
        if (
            isinstance(profile_class, type)
            and issubclass(profile_class, RepoProfile)
            and profile_class != RepoProfile
        ):
            # Create an instance to get the mirror name
            p = profile_class()
            self._profiles[p.repo_name] = profile_class

    def get(self, key: str) -> RepoProfile:
        """Get a profile class by mirror name."""
        return self._profiles.get(key)()

    def get_from_inst(self, instance: dict) -> RepoProfile:
        """Get a profile class by a SWE-smith instance"""
        key = instance[KEY_INSTANCE_ID].rsplit(".", 1)[0]
        return self._profiles.get(key)()

    def keys(self) -> list[str]:
        """Get all available profile keys (mirror names)."""
        return list(self._profiles.keys())

    def values(self) -> list[RepoProfile]:
        """Get all profile classes."""
        return [p() for p in self._profiles.values()]


# Global registry instance that can be shared across modules
global_registry = Registry()
