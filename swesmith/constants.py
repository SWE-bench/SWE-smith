"""
Purpose: Repo-wide constants
"""

import hashlib
import random
import string

from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

DEFAULT_PM_LIKELIHOOD = 0.2
ENV_NAME = "testbed"
HF_DATASET = "SWE-bench/SWE-smith"
INSTANCE_REF = "instance_ref"
KEY_IMAGE_NAME = "image_name"
KEY_PATCH = "patch"
KEY_TIMED_OUT = "timed_out"
LOG_DIR_BUG_GEN = Path("logs/bug_gen")
LOG_DIR_ENV = Path("logs/build_images/env")
LOG_DIR_ISSUE_GEN = Path("logs/issue_gen")
LOG_DIR_RUN_VALIDATION = Path("logs/run_validation")
LOG_DIR_TASKS = Path("logs/task_insts")
LOG_TEST_OUTPUT_PRE_GOLD = "test_output_pre_gold.txt"
MAX_INPUT_TOKENS = 128000
ORG_NAME_DH = "jyangballin"
ORG_NAME_GH = "swesmith"
PREFIX_BUG = "bug"
PREFIX_METADATA = "metadata"
REF_SUFFIX = ".ref"
TEMP_PATCH = "_temp_patch_swesmith.diff"
TEST_OUTPUT_END = ">>>>> End Test Output"
TEST_OUTPUT_START = ">>>>> Start Test Output"
TODO_REWRITE = "TODO: Implement this function"
UBUNTU_VERSION = "22.04"

GIT_APPLY_CMDS = [
    "git apply --verbose",
    "git apply --verbose --reject",
    "patch --batch --fuzz=5 -p1 -i",
]


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


def generate_hash(s):
    return "".join(
        random.Random(int(hashlib.sha256(s.encode()).hexdigest(), 16)).choices(
            string.ascii_lowercase + string.digits, k=8
        )
    )
