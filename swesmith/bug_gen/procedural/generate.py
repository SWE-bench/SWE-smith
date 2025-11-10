"""
Purpose: Given a repository, procedurally generate a variety of bugs for functions/classes/objects in the repository.

Usage: python -m swesmith.bug_gen.procedural.generate \
    --repo <repo> \
    --commit <commit>
"""

import argparse
import json
import random
import shutil

from pathlib import Path
from rich import print
from swesmith.bug_gen.utils import (
    apply_code_change,
    get_bug_directory,
    get_patch,
)
from swesmith.constants import (
    LOG_DIR_BUG_GEN,
    PREFIX_BUG,
    PREFIX_METADATA,
    BugRewrite,
    CodeEntity,
)
from swesmith.profiles import registry
from tqdm.auto import tqdm

from swesmith.bug_gen.procedural import MAP_EXT_TO_MODIFIERS, MAP_EXT_TO_NEW_MODIFIERS
from swesmith.bug_gen.procedural.base import ProceduralModifier


def _process_candidate(
    candidate: CodeEntity, pm: ProceduralModifier, log_dir: Path, repo: str
):
    """
    Process a candidate by applying a given procedural modification to it.
    """
    # Get modified function
    bug: BugRewrite | None = pm.modify(candidate)
    if not bug:
        return False

    # Create artifacts
    bug_dir = get_bug_directory(log_dir, candidate)
    bug_dir.mkdir(parents=True, exist_ok=True)
    uuid_str = f"{pm.name}__{bug.get_hash()}"
    metadata_path = f"{PREFIX_METADATA}__{uuid_str}.json"
    bug_path = f"{PREFIX_BUG}__{uuid_str}.diff"

    with open(bug_dir / metadata_path, "w") as f:
        json.dump(bug.to_dict(), f, indent=2)
    apply_code_change(candidate, bug)

    # Make file_path relative to repo root (strip repo prefix if present)
    relative_file_path = candidate.file_path
    if relative_file_path.startswith(repo + "/"):
        relative_file_path = relative_file_path[len(repo) + 1 :]

    patch = get_patch(repo, reset_changes=True, file_path=relative_file_path)
    if patch:
        with open(bug_dir / bug_path, "w") as f:
            f.write(patch)
        return True
    return False


def main(
    repo: str,
    max_bugs: int,
    seed: int,
    new_only: bool = False,
):
    random.seed(seed)
    total = 0
    rp = registry.get(repo)
    rp.clone()
    repo_path = rp.repo_name  # Use actual cloned directory name
    entities = rp.extract_entities()
    print(f"Found {len(entities)} entities in {repo}.")

    # Select modifier map based on new_only flag
    if new_only:
        print("🆕 Running ONLY NEW modifiers...")
        modifier_map = MAP_EXT_TO_NEW_MODIFIERS
    else:
        modifier_map = MAP_EXT_TO_MODIFIERS

    for ext, pm_list in modifier_map.items():
        for pm in pm_list:
            candidates = [
                x
                for x in entities
                if Path(x.file_path).suffix == ext and pm.can_change(x)
            ]
            if not candidates:
                continue
            print(f"[{repo}] Found {len(candidates)} candidates for {pm.name}.")

            log_dir = LOG_DIR_BUG_GEN / repo
            log_dir.mkdir(parents=True, exist_ok=True)
            print(f"Logging bugs to {log_dir}")

            if max_bugs > 0 and len(candidates) > max_bugs:
                candidates = random.sample(candidates, max_bugs)

            for candidate in tqdm(candidates):
                total += _process_candidate(candidate, pm, log_dir, repo_path)

    shutil.rmtree(repo_path)
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
    parser.add_argument(
        "--new-only",
        action="store_true",
        help="Generate bugs using only NEW modifiers (for testing).",
    )

    args = parser.parse_args()
    main(**vars(args))
