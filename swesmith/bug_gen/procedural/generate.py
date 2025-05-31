"""
Purpose: Given a repository, procedurally generate a variety of bugs for functions/classes/objects in the repository.

Usage: python -m swesmith.bug_gen.procedural.generate \
    --repo <repo> \
    --commit <commit>
"""

import argparse
import json
import libcst
import random
import shutil

from pathlib import Path
from rich import print
from swesmith.bug_gen.utils import (
    apply_code_change,
    extract_entities_from_directory,
    get_patch,
)
from swesmith.constants import (
    LOG_DIR_BUG_GEN,
    ORG_NAME,
    PREFIX_BUG,
    PREFIX_METADATA,
)
from swesmith.utils import (
    BugRewrite,
    CodeEntity,
    clone_repo,
    repo_exists,
)
from tqdm.auto import tqdm

from swesmith.bug_gen.procedural import BaseProceduralModifier
from swesmith.bug_gen.procedural.classes import (
    ClassRemoveBasesModifier,
    ClassRemoveFuncsModifier,
    ClassShuffleMethodsModifier,
)
from swesmith.bug_gen.procedural.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
)
from swesmith.bug_gen.procedural.operations import (
    OperationBreakChainsModifier,
    OperationChangeConstantsModifier,
    OperationChangeModifier,
    OperationSwapOperandsModifier,
)
from swesmith.bug_gen.procedural.remove import (
    RemoveAssignModifier,
    RemoveConditionalModifier,
    RemoveLoopModifier,
    RemoveWrapperModifier,
)

PM_TECHNIQUES = [
    ClassRemoveBasesModifier(likelihood=0.25),
    ClassRemoveFuncsModifier(likelihood=0.15),
    ClassShuffleMethodsModifier(likelihood=0.25),
    ControlIfElseInvertModifier(likelihood=0.25),
    ControlShuffleLinesModifier(likelihood=0.25),
    RemoveAssignModifier(likelihood=0.25),
    RemoveConditionalModifier(likelihood=0.25),
    RemoveLoopModifier(likelihood=0.25),
    RemoveWrapperModifier(likelihood=0.25),
    OperationBreakChainsModifier(likelihood=0.4),
    OperationChangeConstantsModifier(likelihood=0.4),
    OperationChangeModifier(likelihood=0.4),
    OperationSwapOperandsModifier(likelihood=0.4),
]


def _process_candidate(
    candidate: CodeEntity, pm: BaseProceduralModifier, log_dir: Path, repo: str
):
    """
    Process a candidate by applying a given procedural modification to it.
    """
    # Apply transformation
    try:
        module = libcst.parse_module(candidate.src_code)
    except Exception:
        # Failed to parse code
        return False

    changed = False
    try:
        for _ in range(5):
            modified = module.visit(pm)
            if module.code != modified.code:
                changed = True
                break
    except Exception:
        return False

    if not changed:
        return False

    # Get modified function
    bug = BugRewrite(
        rewrite=modified.code,
        explanation=pm.explanation,
        cost=0.0,
        strategy=pm.name,
    )

    # Create artifacts
    bug_dir = log_dir / candidate.file_path.replace("/", "__") / candidate.name
    bug_dir.mkdir(parents=True, exist_ok=True)
    uuid_str = f"{pm.name}__{bug.get_hash()}"
    metadata_path = f"{PREFIX_METADATA}__{uuid_str}.json"
    bug_path = f"{PREFIX_BUG}__{uuid_str}.diff"

    with open(bug_dir / metadata_path, "w") as f:
        json.dump(bug.to_dict(), f, indent=2)
    apply_code_change(candidate, bug)
    patch = get_patch(repo, reset_changes=True)
    if patch:
        with open(bug_dir / bug_path, "w") as f:
            f.write(patch)
        return True
    return False


def main(
    repo: str,
    max_bugs: int,
    seed: int,
):
    assert repo_exists(repo), f"Repository {repo} does not exist in {ORG_NAME}."
    random.seed(seed)

    total = 0
    clone_repo(repo)
    print(f"Cloned {repo} repository.")
    entities = extract_entities_from_directory(repo)
    print(f"Found {len(entities)} entities in {repo}.")
    for pm in PM_TECHNIQUES:
        print(f"Generating [bold blue]{pm.name}[/bold blue] bugs in {repo}...")
        candidates = [x for x in entities if all(c(x) for c in pm.conditions)]
        if not candidates:
            print(f"No candidates found in {repo}.")
            continue
        print(f"Found {len(candidates)} candidates in {repo}.")

        log_dir = LOG_DIR_BUG_GEN / repo
        log_dir.mkdir(parents=True, exist_ok=True)
        print(f"Logging bugs to {log_dir}")

        if max_bugs > 0 and len(candidates) > max_bugs:
            candidates = random.sample(candidates, max_bugs)

        for candidate in tqdm(candidates):
            total += _process_candidate(candidate, pm, log_dir, repo)

    shutil.rmtree(repo)
    print(f"Generated {total} bugs for {repo}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate bugs for a given repository and commit."
    )
    parser.add_argument(
        "repo",
        type=str,
        help="Name of a SWE-smith repository to generate bugs for.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=24,
        help="Seed for random number generator.",
    )
    parser.add_argument(
        "--max_bugs",
        type=int,
        default=-1,
        help="Maximum number of bugs to generate.",
    )

    args = parser.parse_args()
    main(**vars(args))
