import hashlib
import os
import platform
import random
import string
import subprocess

from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from ghapi.all import GhApi
from pathlib import Path
from swesmith.constants import MAP_REPO_TO_SPECS, ORG_NAME, LOG_DIR_ENV_RECORDS
from typing import Any


class CodeProperty(Enum):
    # Core entity types
    IS_FUNCTION = "is_function"
    IS_CLASS = "is_class"

    # Control flow
    HAS_EXCEPTION = "has_exception"
    HAS_IF = "has_if"
    HAS_IF_ELSE = "has_if_else"
    HAS_LOOP = "has_loop"

    # Operations
    HAS_ARITHMETIC = "has_arithmetic"
    HAS_ASSIGNMENT = "has_assignment"
    HAS_DECORATOR = "has_decorator"
    HAS_FUNCTION_CALL = "has_function_call"
    HAS_IMPORT = "has_import"
    HAS_LAMBDA = "has_lambda"
    HAS_LIST_COMPREHENSION = "has_list_comprehension"
    HAS_LIST_INDEXING = "has_list_indexing"
    HAS_OFF_BY_ONE = "has_off_by_one"
    HAS_PARENT = "has_parent"
    HAS_RETURN = "has_return"
    HAS_WRAPPER = "has_wrapper"

    # Operations by type
    HAS_BINARY_OP = "has_binary_op"
    HAS_BOOL_OP = "has_bool_op"
    HAS_UNARY_OP = "has_unary_op"


class CodeEntityMeta(type):
    def __new__(mcs, name, bases, namespace):
        # Create properties for all enum values
        for prop in CodeProperty:
            namespace[prop.value] = property(lambda self, p=prop: p in self._tags)
        return super().__new__(mcs, name, bases, namespace)


@dataclass
class CodeEntity(metaclass=CodeEntityMeta):
    """Data class to hold information about a code entity (e.g. function, class)."""

    file_path: str
    indent_level: int
    indent_size: int
    line_end: int
    line_start: int
    node: Any
    src_code: Any

    def __post_init__(self):
        self._tags: set[CodeProperty] = set()
        self._analyze_properties()

    def _analyze_properties(self):
        """To be implemented by language-specific classes"""
        pass

    @property
    def complexity(self) -> int:
        """Get the complexity of the code entity."""
        return -1  # Default value = no notion of complexity implemented

    @property
    def ext(self) -> str:
        if isinstance(self.file_path, Path):
            self.file_path = str(self.file_path)
        return self.file_path.rsplit(".", 1)[-1].lower()

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the code entity."""
        pass

    @property
    @abstractmethod
    def signature(self) -> str:
        """Get the signature of the code entity."""
        pass

    @property
    @abstractmethod
    def stub(self) -> str:
        """Get stub (code with implementation removed) for the code entity."""
        pass


class BugRewrite:
    cost: float = 0
    explanation: str = ""
    output: str
    rewrite: str
    strategy: str

    def __init__(
        self,
        rewrite: str,
        explanation: str,
        strategy: str,
        cost: float = 0,
        output: str = "",
    ):
        self.rewrite = rewrite
        self.explanation = explanation
        self.cost = cost
        self.strategy = strategy
        self.output = output

    def get_hash(self) -> str:
        """Generates a hash for the bug rewrite."""
        return generate_hash(self.rewrite)

    def to_dict(self) -> dict[str, Any]:
        """Converts the bug rewrite to a dictionary."""
        return {
            "cost": self.cost,
            "explanation": self.explanation,
            "output": self.output,
            "rewrite": self.rewrite,
            "strategy": self.strategy,
        }


def get_arch_and_platform() -> tuple[str, str]:
    """
    Get the architecture and platform for the current machine.
    """
    arch = "x86_64" if platform.machine() not in {"aarch64", "arm64"} else "arm64"
    if arch == "x86_64":
        pltf = "linux/x86_64"
    elif arch == "arm64":
        pltf = "linux/arm64/v8"
    else:
        raise ValueError(f"Invalid architecture: {arch}")
    return arch, pltf


def get_image_name(repo: str, commit: str, arch: str | None = None) -> str:
    """
    Get the docker image ID for a repository at a specific commit.
    """
    arch = arch or get_arch_and_platform()[0]
    return f"swesmith.{arch}.{repo.replace('/', '__').lower()}.{commit[:8]}"


def get_repo_commit_from_image_name(image_name: str) -> tuple[str, str]:
    """
    Get the repository and commit from a docker image ID.
    """
    # Parsing supports repos with '.' in their name
    image_name = image_name.split(".", 2)[-1]
    repo = image_name.rsplit(".", 1)[0].replace("__", "/")
    partial_commit = image_name.rsplit(".", 1)[-1]
    for repo_name in MAP_REPO_TO_SPECS:
        # Hack because docker image_name must be lowercase
        if repo_name.lower() == repo:
            repo = repo_name
            break
    commit = get_full_commit(repo, partial_commit)
    return repo, commit


def get_env_yml_path(repo: str, commit: str) -> str:
    """
    Get the path to the environment.yml file for a repository at a specific commit.
    """
    if len(commit) != 40:
        raise ValueError(
            f"Must provide full commit hash, not partial commit ({commit})"
        )
    return f"{LOG_DIR_ENV_RECORDS}/sweenv_{repo.replace('/', '__')}_{commit}.yml"


def get_full_commit(repo, partial_commit) -> str:
    """
    Get the full commit hash for a repository at a specific commit.
    """
    for commit in MAP_REPO_TO_SPECS[repo]:
        if commit.startswith(partial_commit):
            return commit

    raise ValueError(f"Commit {partial_commit} not found for repository {repo}.")


def get_repo_name(repo, commit) -> str:
    """
    Get the SWE-smith GitHub repository name for a repository at a specific commit.
    """
    return f"{repo.replace('/', '__')}.{commit[:8]}"


def clone_repo(repo: str, dest: str | None = None, org: str = ORG_NAME) -> str | None:
    """Clone a repository from GitHub."""
    if not os.path.exists(dest or repo):
        clone_cmd = (
            f"git clone git@github.com:{org}/{repo}.git"
            if dest is None
            else f"git clone git@github.com:{org}/{repo}.git {dest}"
        )
        subprocess.run(
            clone_cmd,
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return repo if dest is None else dest
    return None


def generate_hash(s):
    return "".join(
        random.Random(int(hashlib.sha256(s.encode()).hexdigest(), 16)).choices(
            string.ascii_lowercase + string.digits, k=8
        )
    )


def get_test_paths(dir_path: str, ext: str = ".py") -> list[Path]:
    """
    Get all testing file paths relative to the given directory.
    """
    return [
        Path(os.path.relpath(os.path.join(root, file), dir_path))
        for root, _, files in os.walk(Path(dir_path).resolve())
        for file in files
        if (
            (
                any([x in root.split("/") for x in ["tests", "test", "specs"]])
                or file.lower().startswith("test")
                or file.rsplit(".", 1)[0].endswith("test")
            )
            and (ext is None or file.endswith(ext))
        )
    ]


def repo_exists(repo: str, org_name: str = ORG_NAME) -> bool:
    """
    Check if a repository exists in project organization.
    """
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    api = GhApi(token=GITHUB_TOKEN)
    org_repos = [
        x["name"]
        for page in range(1, 3)
        for x in api.repos.list_for_org(org_name, per_page=100, page=page)  # type: ignore
    ]
    return repo in org_repos
