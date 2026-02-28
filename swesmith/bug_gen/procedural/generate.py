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
import time

from pathlib import Path
from rich import print
from swesmith.bug_gen.utils import (
    generate_patch_fast,
    get_bug_directory,
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

from swesmith.bug_gen.procedural import MAP_EXT_TO_MODIFIERS
from swesmith.bug_gen.procedural.base import ProceduralModifier


def _process_candidate(
    candidate: CodeEntity, pm: ProceduralModifier, log_dir: Path, repo: str
):
    """
    Process a candidate by applying a given procedural modification to it.

    Uses fast difflib-based patch generation instead of git subprocess calls.
    """
    # Get modified function
    bug: BugRewrite | None = pm.modify(candidate)
    if not bug:
        return False

    # Generate patch using fast difflib-based method (no git subprocess calls)
    patch = generate_patch_fast(candidate, bug, repo)
    if not patch:
        return False

    # Create artifacts
    bug_dir = get_bug_directory(log_dir, candidate)
    bug_dir.mkdir(parents=True, exist_ok=True)
    uuid_str = f"{pm.name}__{bug.get_hash()}"
    metadata_path = f"{PREFIX_METADATA}__{uuid_str}.json"
    bug_path = f"{PREFIX_BUG}__{uuid_str}.diff"

    with open(bug_dir / metadata_path, "w") as f:
        json.dump(bug.to_dict(), f, indent=2)
    with open(bug_dir / bug_path, "w") as f:
        f.write(patch)
    return True


def main(
    repo: str,
    max_bugs: int,
    seed: int,
    interleave: bool = False,
    max_entities: int = -1,
    max_candidates: int = -1,
    timeout_seconds: int | None = None,
):
    random.seed(seed)
    total = 0
    start_time = time.time() if timeout_seconds is not None else None
    rp = registry.get(repo)
    rp.clone()
    entities = rp.extract_entities()

    def check_timeout():
        """Check if timeout has been reached. Returns True if should stop."""
        if start_time is None:
            return False
        elapsed = time.time() - start_time
        if elapsed >= timeout_seconds:
            print(
                f"\n[{repo}] TIMEOUT: Reached {timeout_seconds}s limit after {elapsed:.1f}s, stopping generation..."
            )
            return True
        return False

    # Apply entity sampling if limit is set and exceeded
    original_count = len(entities)
    if max_entities > 0 and original_count > max_entities:
        random.shuffle(entities)
        entities = entities[:max_entities]
        print(
            f"Found {original_count} entities in {repo}, sampled down to {max_entities} for efficiency."
        )
    else:
        print(f"Found {len(entities)} entities in {repo}.")

    log_dir = LOG_DIR_BUG_GEN / repo
    log_dir.mkdir(parents=True, exist_ok=True)
    print(f"Logging bugs to {log_dir}")

    def process_with_timeout():
        """Process candidates with timeout checking. Returns total bugs processed."""
        local_total = 0

        if interleave:
            # Build all (candidate, modifier) pairs upfront
            pairs = []
            for ext, pm_list in MAP_EXT_TO_MODIFIERS.items():
                for pm in pm_list:
                    candidates = [
                        x
                        for x in entities
                        if Path(x.file_path).suffix == ext and pm.can_change(x)
                    ]
                    if not candidates:
                        continue
                    print(f"[{repo}] Found {len(candidates)} candidates for {pm.name}.")

                    if max_bugs > 0 and len(candidates) > max_bugs:
                        candidates = random.sample(candidates, max_bugs)

                    # Add all pairs for this modifier
                    for candidate in candidates:
                        pairs.append((candidate, pm))

            # Shuffle all pairs to interleave modifiers
            random.shuffle(pairs)

            # Apply max_candidates limit if set
            original_pairs_len = len(pairs)
            if max_candidates > 0 and original_pairs_len > max_candidates:
                pairs = pairs[:max_candidates]
                print(
                    f"[{repo}] Processing {len(pairs)} (candidate, modifier) pairs (limited from {original_pairs_len})."
                )
            else:
                print(
                    f"[{repo}] Processing {len(pairs)} (candidate, modifier) pairs in randomized order."
                )

            # Process in randomized order
            for candidate, pm in tqdm(pairs):
                local_total += _process_candidate(candidate, pm, log_dir, repo)
                if check_timeout():
                    return local_total
        else:
            # Sequential processing (original behavior)
            for ext, pm_list in MAP_EXT_TO_MODIFIERS.items():
                for pm in pm_list:
                    candidates = [
                        x
                        for x in entities
                        if Path(x.file_path).suffix == ext and pm.can_change(x)
                    ]
                    if not candidates:
                        continue
                    print(f"[{repo}] Found {len(candidates)} candidates for {pm.name}.")

                    if max_bugs > 0 and len(candidates) > max_bugs:
                        candidates = random.sample(candidates, max_bugs)

                    # Apply max_candidates limit across all processed pairs
                    processed = 0
                    for candidate in tqdm(candidates):
                        if max_candidates > 0 and processed >= max_candidates:
                            return local_total
                        local_total += _process_candidate(candidate, pm, log_dir, repo)
                        processed += 1
                        if check_timeout():
                            return local_total
        return local_total

    total = process_with_timeout()

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
        "-s",
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
        "-i",
        "--interleave",
        action="store_true",
        help="Randomize and interleave modifiers instead of processing sequentially.",
    )
    parser.add_argument(
        "--max_entities",
        type=int,
        default=-1,
        help="Maximum number of entities to sample from the repository. Set to -1 to disable sampling.",
    )
    parser.add_argument(
        "--max_candidates",
        type=int,
        default=-1,
        help="Maximum number of (candidate, modifier) pairs to process. Set to -1 to process all.",
    )
    parser.add_argument(
        "-t",
        "--timeout_seconds",
        type=int,
        default=None,
        help="Maximum number of seconds to run generation. Set to None to disable timeout.",
    )

    args = parser.parse_args()
    main(**vars(args))
