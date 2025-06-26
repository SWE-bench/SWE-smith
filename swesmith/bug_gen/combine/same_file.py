"""
Purpose: Combine multiple patches from the same file into a single patch.

Usage: python swesmith/bug_gen/combine/same_file.py \
    --bug_gen_dir <path to bug_gen dir> \
    --num_patches <number of patches to merge> \
    --limit_per_file <limit per file> \
    --max_combos <max combos to try> \
    --include_invalid_patches

NOTE: The logic in this file assumes that validation logs are available (under logs/run_validation/<repo>)
"""

import argparse
import json
import os
import subprocess

from pathlib import Path
from swebench.harness.constants import KEY_INSTANCE_ID
from swesmith.bug_gen.utils import apply_patches, get_combos
from swesmith.constants import (
    LOG_DIR_BUG_GEN,
    LOG_DIR_TASKS,
    PREFIX_BUG,
    PREFIX_METADATA,
    generate_hash,
)
from swesmith.profiles import global_registry
from tqdm.auto import tqdm

COMBINE_FILE = "combine_file"
EXCLUDED_BUG_TYPES = ["func_basic", "combine_file", "combine_module", "pr_mirror"]


def main(
    bug_gen_dir: str,
    num_patches: int,
    limit_per_file: int,
    max_combos: int,
    include_invalid_patches: bool = False,
):
    assert bug_gen_dir.startswith(str(LOG_DIR_BUG_GEN)), (
        f"bug_gen_dir must be of form {str(LOG_DIR_BUG_GEN)}/<repo name>"
    )
    repo = bug_gen_dir.strip("/").split("/")[-1]
    bug_gen_dir = Path(bug_gen_dir)
    global_registry.get(repo).clone()
    folders = [
        x
        for x in os.listdir(bug_gen_dir)
        if x not in EXCLUDED_BUG_TYPES and os.path.isdir(bug_gen_dir / x)
    ]

    validated_inst_ids = []
    if not include_invalid_patches:
        validated_inst_ids = [
            x[KEY_INSTANCE_ID].split(".")[-1]
            for x in json.load(open(os.path.join(LOG_DIR_TASKS, f"{repo}.json")))
        ]

    print(f"[{repo}]: Processing {len(folders)} folders...")
    total_success, total_fails = 0, 0
    for folder in tqdm(folders):
        # Get all patch file paths for this source file
        folder_path = bug_gen_dir / folder
        patch_files = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.startswith(f"{PREFIX_BUG}__combine") or not file.endswith(
                    ".diff"
                ):
                    continue
                inst_id = file.split(f"{PREFIX_BUG}__")[-1].split(".diff")[0]
                if not include_invalid_patches and inst_id not in validated_inst_ids:
                    continue
                patch_files.append(os.path.join(root, file))

        if len(patch_files) <= 1:
            # Ignore if there is only one patch
            continue

        # Try out all combinations of patches
        combos = get_combos(patch_files, num_patches, max_combos)
        i, success, fails = 0, 0, 0
        while i < len(combos):
            combo = combos[i]
            patch = apply_patches(repo, combo)

            if patch is not None:
                success += 1
                file_name = f"{COMBINE_FILE}__{generate_hash(patch)}"
                with open(folder_path / f"{PREFIX_BUG}__{file_name}.diff", "w") as f:
                    f.write(patch)
                with open(
                    folder_path / f"{PREFIX_METADATA}__{file_name}.json", "w"
                ) as f:
                    json.dump(
                        {
                            "patch_files": [
                                Path(f).name.rsplit(".", 1)[0] for f in combo
                            ],
                            "num_patch_files": len(combo),
                        },
                        f,
                        indent=4,
                    )

                if limit_per_file != -1 and success >= limit_per_file:
                    break

                # Remove any remaining lists in `combos` that contain any file in combo
                used_files = set(combo)
                combos = [c for c in combos if not any(f in used_files for f in c)]
                i = 0
            else:
                fails += 1
                i += 1

        total_success += success
        total_fails += fails

    print(
        f"[{repo}]: Combinations that succeeded: {total_success}, failed: {total_fails}"
    )
    subprocess.run(["rm", "-rf", repo], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge multiple function-level patches from the same file into a single patch."
    )
    parser.add_argument(
        "bug_gen_dir", help="Path to the bug_gen directory for a specific repository."
    )
    parser.add_argument(
        "--num_patches",
        type=int,
        help="Number of patches to merge.",
        default=2,
    )
    parser.add_argument(
        "--limit_per_file",
        type=int,
        help="Maximum number of merged patches to keep per file (default no limit).",
        default=-1,
    )
    parser.add_argument(
        "--max_combos",
        type=int,
        help="Maximum number of combinations to try (-1 for no limit).",
        default=100,
    )
    parser.add_argument(
        "--include_invalid_patches",
        action="store_true",
        help="Include invalid patches.",
    )
    args = parser.parse_args()
    main(**vars(args))
