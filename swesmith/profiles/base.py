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
from swesmith.constants import ORG_NAME_DH, ORG_NAME_GH
from swesmith.utils import repo_exists, get_arch_and_platform
from typing import Dict, List


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
    install_cmds: List[str] = None
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

    def get_image_name(self, arch: str | None = None) -> str:
        arch, _ = get_arch_and_platform()
        return f"{self.org_dh}/swesmith.{arch}.{self.get_mirror_name()}"

    @abstractmethod
    def log_parser(self, log: str) -> Dict[str, str]:
        """Parse test output logs and extract relevant information."""
        pass

    def get_mirror_name(self):
        return f"{self.owner}_1776_{self.repo}.{self.commit[:8]}"

    def create_mirror_repo(self):
        """
        Create a mirror of this repository at the specified commit.
        """
        api = GhApi(token=GITHUB_TOKEN)
        repo_full_name = f"{self.owner}/{self.repo}"

        if repo_exists(self.get_mirror_name()):
            return
        if self.get_mirror_name() in os.listdir():
            shutil.rmtree(self.get_mirror_name())
        api.repos.create_in_org(self.org, self.get_mirror_name())
        for cmd in [
            f"git clone git@github.com:{repo_full_name}.git {self.get_mirror_name()}",
            (
                f"cd {self.get_mirror_name()}; "
                f"git checkout {self.commit}; "
                "rm -rf .git; "
                "git init; "
                'git config user.name "swesmith"; '
                'git config user.email "swesmith@anon.com"; '
                "rm -rf .github/workflows; "
                "git add .; "
                "git commit -m 'Initial commit'; "
                "git branch -M main; "
                f"git remote add origin git@github.com:{self.org}/{self.get_mirror_name()}.git; "
                "git push -u origin main",
            ),
            f"rm -rf {self.get_mirror_name()}",
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
    """Simple registry for mapping strings to profile classes."""

    def __init__(self, profile_class: type = None, module_globals: dict = None):
        self.profile_class = profile_class
        self.module_globals = module_globals
        self._cache = {}

    def register_from_module(self, profile_class: type, module_globals: dict):
        """Register profiles from a specific module."""
        for name, obj in module_globals.items():
            if (
                isinstance(obj, type)
                and issubclass(obj, profile_class)
                and obj != profile_class
            ):
                key = f"{obj.owner}/{obj.repo}"
                self._cache[key] = obj

    def register_profile(self, profile_class: type):
        """Register a single profile class."""
        if (
            isinstance(profile_class, type)
            and issubclass(profile_class, RepoProfile)
            and profile_class != RepoProfile
        ):
            key = f"{profile_class.owner}/{profile_class.repo}"
            self._cache[key] = profile_class

    def _build_cache(self):
        if self.profile_class and self.module_globals and not self._cache:
            self.register_from_module(self.profile_class, self.module_globals)

    def get(self, key: str):
        """Get a profile class by 'owner/repo' string."""
        self._build_cache()
        return self._cache.get(key)

    def keys(self):
        """Get all available profile keys."""
        self._build_cache()
        return list(self._cache.keys())

    def values(self):
        """Get all profile classes."""
        self._build_cache()
        return list(self._cache.values())


# Global registry instance that can be shared across modules
global_registry = Registry()
