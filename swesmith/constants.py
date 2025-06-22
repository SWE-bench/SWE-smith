"""
Purpose: Repo-wide constants
"""

from pathlib import Path

DEFAULT_PM_LIKELIHOOD = 0.2
ENV_NAME = "testbed"
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
SGLANG_API_KEY = "swesmith"
TEMP_PATCH = "_temp_patch_swesmith.diff"
TEST_OUTPUT_END = ">>>>> End Test Output"
TEST_OUTPUT_START = ">>>>> Start Test Output"
TIMEOUT = 120
TODO_REWRITE = "TODO: Implement this function"
UBUNTU_VERSION = "22.04"
VOLUME_NAME_DATASET = "datasets"
VOLUME_NAME_MODEL = "llm-weights"

GIT_APPLY_CMDS = [
    "git apply --verbose",
    "git apply --verbose --reject",
    "patch --batch --fuzz=5 -p1 -i",
]
