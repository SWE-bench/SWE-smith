"""
Purpose: Given a task instance, attached a fixed problem statement to the issue text.

python swesmith/issue_gen/get_fixed.py logs/experiments/*.json
"""

import argparse
import json
import random
from typing import Set

from pathlib import Path
from swebench.harness.constants import FAIL_TO_PASS, KEY_INSTANCE_ID
from swesmith.bug_gen.procedural import MAP_EXT_TO_MODIFIERS
from tqdm.auto import tqdm
from unidiff import PatchSet

BUG_TYPE_TO_PROMPT = {
    x.name: x.explanation
    for modifiers in MAP_EXT_TO_MODIFIERS.values()
    for x in modifiers
}

# MARK: Basic says-nothing prompt
PROMPT_BASIC = (
    """There is a bug in this codebase. Please look into it and resolve the issue."""
)

# MARK: Prompts that mention file names
PROMPT_FILES = """There are bug(s) in this codebase, likely located in the following file(s):
{gold_files}

Please look into them and fix any bugs that you find."""

# MARK: Prompts that mention file + function names
PROMPT_FILES_FUNCS = """There are bug(s) in this codebase, likely located in the following file(s).
{gold_files}

I think these function(s) are relevant to the bug:
{gold_funcs}

Please look into them and fix any bugs that you find."""

# MARK: Prompts that mention test cases
PROMPT_TESTS_BASIC = (
    """Several tests in the codebase are breaking. Please find the bugs and fix them."""
)
PROMPT_TESTS_F2P = """Several tests in the codebase are breaking.

The tests that are failing are:
{f2p_list}

Please fix the codebase such that the tests pass."""

# MARK: Prompts that mention the type of bug
PROMPT_BUG_TYPE_BASIC = """There is a bug in this codebase. {bug_type}Please look into it and resolve the issue."""
PROMPT_BUG_TYPE_FILES = """There is a bug in this codebase. {bug_type}It seems to be related to the following files:" \
{gold_files}
Please look into these files and resolve the issue."""
PROMPT_BUG_TYPE_FILES_TESTS = """There is a bug in this codebase. {bug_type}It seems to be related to the following files:
{gold_files}

Please look into these files and resolve the issue. I believe a test case is also failing because of this bug:
{f2p_single}"""
PROMPT_BUG_TYPE_FILES_FUNCS_TESTS = """There is a bug in this codebase. {bug_type}It seems to be related to the following files:
{gold_files}

I think these function(s) are relevant to the bug:
{gold_funcs}

Please look into this and resolve the issue. I believe a test case is also failing because of this bug:
{f2p_single}"""

PROMPT_POOL = [
    (PROMPT_BASIC, 0.05),
    (PROMPT_FILES, 0.1),
    (PROMPT_FILES_FUNCS, 0.15),
    (PROMPT_TESTS_BASIC, 0.1),
    (PROMPT_TESTS_F2P, 0.1),
    (PROMPT_BUG_TYPE_BASIC, 0.05),
    (PROMPT_BUG_TYPE_FILES, 0.15),
    (PROMPT_BUG_TYPE_FILES_TESTS, 0.15),
    (PROMPT_BUG_TYPE_FILES_FUNCS_TESTS, 0.15),
]

random.seed(24)


def print_list(x):
    return "- " + "\n- ".join(x)


def get_bug_exp(instance) -> str:
    inst_id = instance[KEY_INSTANCE_ID]
    for bug_type, prompt in BUG_TYPE_TO_PROMPT.items():
        if bug_type in inst_id:
            return prompt
    return ""


def get_changed_functions(patch_text) -> Set[str]:
    patch = PatchSet(patch_text.splitlines())
    changed_funcs = set()

    for file in patch:
        for hunk in file:
            for line in hunk:
                if line.is_added or line.is_removed:
                    # Extract function context
                    function_name = hunk.section_header
                    if function_name:
                        changed_funcs.add(function_name.strip())

    return changed_funcs


def main(dataset_path: str | Path) -> None:
    dataset_path = Path(dataset_path)
    dataset = []
    if dataset_path.name.endswith(".json"):
        with open(dataset_path, "r") as f:
            dataset = json.load(f)
    elif dataset_path.name.endswith(".jsonl"):
        with open(dataset_path, "r") as f:
            dataset = [json.loads(x) for x in f]
    else:
        raise ValueError(
            f"Unsupported file format (must be .json, .jsonl): {dataset_path}"
        )
    dataset_path = Path(dataset_path)
    print(f"Found {len(dataset)} task instances to generate instructions for")

    prompt_pool = [x[0] for x in PROMPT_POOL]
    prompt_weights = [x[1] for x in PROMPT_POOL]
    for instance in tqdm(dataset):
        instance["bug_type"] = get_bug_exp(instance)
        instance["f2p_single"] = random.choice(instance[FAIL_TO_PASS])
        instance["f2p_list"] = print_list(instance[FAIL_TO_PASS])
        instance["gold_files"] = print_list(
            [x.path for x in PatchSet(instance["patch"])]
        )
        instance["gold_funcs"] = print_list(get_changed_functions(instance["patch"]))

        prompt = random.choices(prompt_pool, weights=prompt_weights, k=1)[0]
        instance["problem_statement"] = prompt.format(**instance)
    out_path = dataset_path.parent / f"{dataset_path.stem}__ig_static.json"
    with open(out_path, "w") as f:
        json.dump(dataset, f, indent=2)
        print(f"Wrote dataset with static instructions to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_path", type=str, help="Path to the dataset file")
    args = parser.parse_args()
    main(**vars(args))
