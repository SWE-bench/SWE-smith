"""
Base repository profile class.

This module defines the abstract base class for repository profiles that specify
installation and testing configurations for different repositories.
"""

import os
import platform
import shutil
import subprocess

from abc import ABC, abstractmethod, ABCMeta
from collections import UserDict
from dataclasses import dataclass, field
from dotenv import load_dotenv
from ghapi.all import GhApi
from multiprocessing import Lock
from pathlib import Path
from swebench.harness.constants import FAIL_TO_PASS, KEY_INSTANCE_ID
from swesmith.constants import (
    KEY_PATCH,
    LOG_DIR_ENV,
    ORG_NAME_DH,
    ORG_NAME_GH,
    INSTANCE_REF,
)
from unidiff import PatchSet


load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
api = GhApi(token=GITHUB_TOKEN)


class SingletonMeta(ABCMeta):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


@dataclass
class RepoProfile(ABC, metaclass=SingletonMeta):
    """
    Base class for repository profiles that define installation and testing specifications.

    This class provides a language-agnostic interface for repository configuration,
    allowing different languages (Python, Go, Rust, etc.) to have their own
    installation and testing patterns while maintaining a consistent API.
    """

    owner: str = ""
    repo: str = ""
    commit: str = ""
    org_dh: str = ORG_NAME_DH
    org_gh: str = ORG_NAME_GH
    arch: str = "x86_64" if platform.machine() not in {"aarch64", "arm64"} else "arm64"
    pltf: str = "linux/x86_64" if arch == "x86_64" else "linux/arm64/v8"

    # Install + Test specifications
    install_cmds: list[str] = field(default_factory=list)
    test_cmd: str = ""
    test_exts: list[str] = field(
        default_factory=lambda: [".py", ".go", ".rb", ".php", ".java"]
    )

    # `min_testing`: If set, then subset of tests (not all) are run for post-bug validation
    # Affects get_test_cmd, get_valid_report
    min_testing: bool = False

    # `min_pregold`: If set, then for pre-bug validation, individual runs are
    # performed instead of running the entire test suite
    # Affects valid.py
    min_pregold: bool = False

    # The lock is to prevent concurrent clones of the same repository.
    # In this repo, all subclasses of RepoProfile are meant to be Singletons (only one instance
    # of the class will ever be created). If this changes for some reason in the future,
    # this design may have to be updated.
    _lock: Lock = field(default_factory=Lock, init=False, repr=False, compare=False)

    # Class-level cache for test paths, keyed by repo_name
    _test_paths_cache = {}

    @abstractmethod
    def log_parser(self, log: str) -> dict[str, str]:
        """Parse test output logs and extract relevant information."""
        pass

    @property
    def image_name(self) -> str:
        return f"{self.org_dh}/swesmith.{self.arch}.{self.owner}_1776_{self.repo}.{self.commit[:8]}".lower()

    @property
    def mirror_name(self):
        return f"{self.org_gh}/{self.repo_name}"

    @property
    def repo_name(self):
        return f"{self.owner}__{self.repo}.{self.commit[:8]}"

    def _mirror_exists(self):
        """Check if mirror repository exists under organization"""
        return self.repo_name in [
            x["name"]
            for page in range(1, 3)  # TODO: Need to update over time
            for x in api.repos.list_for_org(self.org_gh, per_page=100, page=page)
        ]

    def build_image(self):
        """Build a Docker image (execution environment) for this repository profile."""
        env_dir = LOG_DIR_ENV / self.repo_name
        env_dir.mkdir(parents=True, exist_ok=True)
        dockerfile_path = env_dir / "Dockerfile"
        with open(dockerfile_path, "w") as f:
            f.write(self.dockerfile)
        with open(env_dir / "build_image.log", "w") as log_file:
            subprocess.run(
                f"docker build -f {dockerfile_path} -t {self.image_name} .",
                shell=True,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )

    def clone(self, dest: str | None = None) -> str:
        """Clone repository locally"""
        if not self._mirror_exists():
            raise ValueError(
                "Mirror clone repo must be created first (call .create_mirror)"
            )
        dest = self.repo_name if not dest else dest
        if not os.path.exists(dest):
            clone_cmd = (
                f"git clone git@github.com:{self.mirror_name}.git"
                if dest is None
                else f"git clone git@github.com:{self.mirror_name}.git {dest}"
            )
            subprocess.run(
                clone_cmd,
                check=True,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return dest

    def create_mirror(self):
        """Create a mirror of this repository at the specified commit."""
        if self._mirror_exists():
            return
        if self.repo_name in os.listdir():
            shutil.rmtree(self.repo_name)
        api.repos.create_in_org(self.org_gh, self.repo_name)
        for cmd in [
            f"git clone git@github.com:{self.owner}/{self.repo}.git {self.repo_name}",
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

    def _get_cached_test_paths(self) -> list[Path]:
        """Clone the repo, get all testing file paths relative to the repo directory, then clean up."""
        # Use repo_name as cache key since it's unique per repository profile
        cache_key = self.repo_name

        if cache_key not in self._test_paths_cache:
            with self._lock:  # Only one process enters this block at a time
                self.clone()
                test_paths = [
                    Path(os.path.relpath(os.path.join(root, file), self.repo_name))
                    for root, _, files in os.walk(Path(self.repo_name).resolve())
                    for file in files
                    if (
                        (
                            any(
                                [
                                    x in root.split("/")
                                    for x in ["tests", "test", "specs"]
                                ]
                            )
                            or file.lower().startswith("test")
                            or file.rsplit(".", 1)[0].endswith("test")
                        )
                        and (
                            len(self.test_exts) == 0
                            or any([file.endswith(ext) for ext in self.test_exts])
                        )
                    )
                ]
                if os.path.exists(self.repo_name):
                    shutil.rmtree(self.repo_name)
                self._test_paths_cache[cache_key] = test_paths

        return self._test_paths_cache[cache_key]

    def get_test_cmd(self, instance: dict):
        assert instance[KEY_INSTANCE_ID].rsplit(".", 1)[0] == self.repo_name, (
            f"WARNING: {instance[KEY_INSTANCE_ID]} not from {self.repo_name}"
        )
        test_command = self.test_cmd

        if FAIL_TO_PASS in instance and "pytest" in test_command:
            # NOTE: Using F2P key as indicator that this is eval instance, not validation
            f2p_files = sorted(
                list(set([x.split("::", 1)[0] for x in instance[FAIL_TO_PASS]]))
            )
            test_command += f" {' '.join(f2p_files)}"
            return test_command, f2p_files

        if self.min_testing or KEY_PATCH not in instance:
            # If min testing is not enabled or there's no patch
            # return test command as is (usually = run whole test suite)
            return test_command, []

        # Get all testing related file paths in the repo
        test_paths = self._get_cached_test_paths()

        # For PR Mirroring (SWE-bench style) instances
        if (
            INSTANCE_REF in instance
            and len(instance[INSTANCE_REF]["test_patch"].strip()) > 0
        ):
            # if test patch is available, use that information
            test_patch = instance[INSTANCE_REF]["test_patch"]
            rv = []
            for x in PatchSet(test_patch):
                for test_path in test_paths:
                    if str(test_path).endswith(x.path) or str(test_path).endswith(
                        Path(x.path).name
                    ):
                        rv.append(str(test_path))
            if len(rv) > 0:
                test_command += f" {' '.join(rv)}"
                return test_command, rv

        # Identify relevant test files based on the patch
        patch_paths = [Path(f.path) for f in PatchSet(instance[KEY_PATCH])]
        rv = []
        for patch_path in patch_paths:
            file_name = patch_path.name.strip(".py")
            parent_dir = patch_path.parent.name
            for test_path in test_paths:
                # Check for common test file naming conventions first
                # If found, add to list and break
                common_test_names = [
                    f"test_{file_name}.py",
                    f"test{file_name}.py",
                    f"{file_name}_test.py",
                    f"{file_name}test.py",
                ]
                if any(
                    [
                        str(test_path).endswith(f"{parent_dir}/{name}")
                        or str(test_path).endswith(name)
                        for name in common_test_names
                    ]
                ):
                    rv.append(str(test_path))
                    break
            else:
                for test_path in test_paths:
                    if parent_dir == test_path.parent.name:
                        # If similar testing folder found, add to list and break
                        rv.append(str(test_path.parent))
                        break
                    elif any(
                        [
                            x.format(parent_dir) == test_path.name
                            for x in [
                                "test_{}.py",
                                "test{}.py",
                                "{}_test.py",
                                "{}test.py",
                            ]
                        ]
                    ):
                        rv.append(str(test_path))

        if len(rv) > 0:
            # Remove duplicates
            test_files = [x for x in rv if x.endswith(".py")]
            final = [x for x in rv if not x.endswith(".py")]
            for test_file in test_files:
                if os.path.dirname(test_file) not in final:
                    final.append(test_file)
            test_command += f" {' '.join(set(final))}"

        return test_command, rv


### MARK: Profile Registry ###


class Registry(UserDict):
    """A registry mapping repo/mirror names to RepoProfile subclasses."""

    def register_profile(self, profile_class: type):
        """Register a RepoProfile subclass (except base types)."""
        # Skip base types
        if profile_class.__name__ in {
            "RepoProfile",
            "PythonProfile",
            "GoProfile",
            "RustProfile",
        }:
            # TODO: Update for new languages
            return
        # Create temporary instance to get properties
        p = profile_class()
        self.data[p.repo_name] = profile_class
        self.data[p.mirror_name] = profile_class

    def get(self, key: str) -> RepoProfile:
        """Get a profile class by mirror name or repo name."""
        cls = self.data.get(key)
        if cls is None:
            raise KeyError(f"No profile registered for key: {key}")
        return cls()

    def get_from_inst(self, instance: dict) -> RepoProfile:
        """Get a profile class by a SWE-smith instance dict."""
        key = instance[KEY_INSTANCE_ID].rsplit(".", 1)[0]
        return self.get(key)

    def keys(self):
        return self.data.keys()

    def values(self):
        return [cls() for cls in self.data.values()]


# Global registry instance that can be shared across modules
global_registry = Registry()
