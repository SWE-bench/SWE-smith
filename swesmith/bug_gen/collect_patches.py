"""
Purpose: Collect all the patches into a single json file that can be fed into swesmith.harness.valid

Usage: python -m swesmith.bug_gen.collect_patches logs/bug_gen/<repo>

NOTE: Must be with respect to a logs/bug_gen/<...>/ directory
"""

import argparse
import os
import json
from pathlib import Path

from swebench.harness.constants import KEY_INSTANCE_ID
from swesmith.constants import LOG_DIR_BUG_GEN, KEY_PATCH, PREFIX_BUG


def main(bug_gen_path: str | Path, bug_type: str = "all", num_bugs: int = -1):
    """
    Collect all the patches into a single json file that can be fed into swebench.harness.valid
    :param repo_path: Path to the bug_gen logs.
    :param bug_type: Type of patches to collect. (default: all)
    :param num_bugs: Number of bugs to collect. (default: all)
    """
    bug_gen_path = Path(bug_gen_path)
    if not bug_gen_path.resolve().is_relative_to((Path() / LOG_DIR_BUG_GEN).resolve()):
        print(
            f"Warning: {bug_gen_path} may not point to a bug_gen log directory (should be in {(Path() / LOG_DIR_BUG_GEN).resolve()})."
        )

    repo = bug_gen_path.name

    patches = []
    prefix = f"{PREFIX_BUG}__"
    if bug_type != "all":
        prefix += bug_type + "_"
    exit_loop = False
    for root, _, files in os.walk(bug_gen_path):
        for file in files:
            if file.startswith(prefix) and file.endswith(".diff"):
                bug_type_and_uuid = file.split(f"{PREFIX_BUG}__")[-1].split(".diff")[0]
                instance_id = f"{repo}.{bug_type_and_uuid}"
                patch = {}

                # Add metadata if it exists
                metadata_file = f"metadata__{bug_type_and_uuid}.json"
                if os.path.exists(os.path.join(root, metadata_file)):
                    patch.update(json.load(open(os.path.join(root, metadata_file))))

                # Add necessary bug patch information
                patch.update(
                    {
                        KEY_INSTANCE_ID: instance_id,
                        KEY_PATCH: open(os.path.join(root, file), "r").read(),
                        "repo": repo,
                    }
                )
                patches.append(patch)
                if num_bugs != -1 and len(patches) >= num_bugs:
                    exit_loop = True
                    break
        if exit_loop:
            break

    bug_patches_file = (
        bug_gen_path.parent / f"{bug_gen_path.name}_{bug_type}_patches.json"
    )
    if num_bugs != -1:
        bug_patches_file = bug_patches_file.with_name(
            bug_patches_file.stem + f"_n{num_bugs}" + bug_patches_file.suffix
        )
    if len(patches) > 0:
        with open(bug_patches_file, "w") as f:
            f.write(json.dumps(patches, indent=4))
        print(f"Saved {len(patches)} patches to {bug_patches_file}")
    else:
        print(f"No patches found for `{bug_type}` in {bug_gen_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Collect all the patches into a single json file that can be fed into swesmith.harness.valid"
    )
    parser.add_argument("bug_gen_path", help="Path to the bug_gen logs.")
    parser.add_argument(
        "--type",
        dest="bug_type",
        type=str,
        help="Type of patches to collect. (default: all)",
        default="all",
    )
    parser.add_argument(
        "-n",
        "--num_bugs",
        type=int,
        help="Number of bugs to collect. (default: all)",
        default=-1,
    )
    args = parser.parse_args()
    main(**vars(args))
