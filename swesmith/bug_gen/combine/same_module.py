"""
Purpose: Combine multiple patches from the same module into a single patch.

Usage: python swesmith/bug_gen/combine/same_module.py \
    --bug_gen_dir <path to bug_gen dir> \
"""

import argparse
import json
import os
import re
import subprocess

from pathlib import Path
from swebench.harness.constants import KEY_INSTANCE_ID
from swesmith.constants import (
    LOG_DIR_BUG_GEN,
    LOG_DIR_TASKS,
    PREFIX_BUG,
    PREFIX_METADATA,
    generate_hash,
)
from swesmith.bug_gen.utils import apply_patches, get_combos
from swesmith.profiles import global_registry
from tqdm.auto import tqdm
from unidiff import PatchSet

COMBINE_MODULE = "combine_module"
EXCLUDED_BUG_TYPES = ["func_basic", "combine_file", "combine_module", "pr_mirror"]


def convert_to_path(folder: str):
    DUNDER_PATTERN = r"____[a-zA-z\d]+__\.py$"
    path = "/".join(folder.split("__")[2:])  # Exclude <repo>__<commit>
    if re.search(DUNDER_PATTERN, folder):
        path = path.replace("//", "/__").replace("/.py", "__.py")
    return path


def get_patches_from_folder(folder_path, include_patches=None):
    """Get all patch file paths from a folder."""
    if include_patches is None:
        include_patches = []
    patch_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if not file.endswith(".diff"):
                continue
            if len(include_patches) > 0 and file not in include_patches:
                continue
            patch_files.append(os.path.join(root, file))
    return patch_files


def remove_paths(current, depth, bug_gen_dir):
    """Remove all paths that are less than depth."""
    if depth == 0:
        return
    keys = list(current.keys())
    for k in keys:
        if isinstance(current[k], dict):
            remove_paths(current[k], depth - 1, bug_gen_dir)
            if len(current[k]) == 0:
                del current[k]
        else:
            current[k] = get_patches_from_folder(bug_gen_dir / k)


def remove_empty_paths(current):
    """Remove all empty paths."""
    keys = list(current.keys())
    for k in keys:
        if isinstance(current[k], dict):
            remove_empty_paths(current[k])
            if len(current[k]) == 0:
                del current[k]
        else:
            if len(current[k]) == 0:
                del current[k]


def collapse_subdicts(current, depth, prefix=""):
    """
    Collapse keys up to a certain depth.
    - If i have {"foo": {"bar": {"baz": 1}}} and depth = 2
    => I want to get {"foo_bar": {"baz": 1}}
    - If i have {"foo": {"bar": {"baz": 1}}} and depth of 3
    => I want to get {"foo_bar_baz": 1}
    - If i have {"foo": {"bar": {"baz": 1, "blow": 2}}} and depth of 3
    => I want to get {"foo_bar_baz": 1, "foo_bar_blow": 2}
    """
    if depth == 0 or not isinstance(current, dict):
        return current
    new_dict = {}
    for k, v in current.items():
        new_key = prefix + k
        if isinstance(v, dict) and depth > 1:
            collapsed = collapse_subdicts(v, depth - 1, new_key + "/")
            if isinstance(collapsed, dict):
                new_dict.update(collapsed)
            else:
                new_dict[new_key] = collapsed
        else:
            new_dict[new_key] = v
    return new_dict


def convert_nested_dict_to_list(nested_dict):
    """Convert a nested dict to a list of values."""
    result = []
    for value in nested_dict.values():
        value = convert_nested_dict_to_list(value) if isinstance(value, dict) else value
        result.extend(value)
    return result


def main(
    bug_gen_dir: str,
    depth: int,
    num_patches: int,
    limit_per_module: int,
    max_combos: int,
    include_invalid_patches: bool = False,
):
    assert bug_gen_dir.startswith(str(LOG_DIR_BUG_GEN)), (
        f"bug_gen_dir must be of form {str(LOG_DIR_BUG_GEN)}/<repo name>"
    )
    repo = bug_gen_dir.strip("/").split("/")[-1]
    bug_gen_dir = Path(bug_gen_dir)
    folders = [
        x
        for x in os.listdir(bug_gen_dir)
        if x not in EXCLUDED_BUG_TYPES and os.path.isdir(bug_gen_dir / x)
    ]

    print(f"[{repo}] Extracting patch groups at depth {depth}")

    # Construct map_path_to_patches[path][to][file] = [patches]
    map_path_to_patches = {}
    for folder in folders:
        path = convert_to_path(folder).split("/")
        current = map_path_to_patches
        for p in path:
            if p not in current:
                if p.endswith(".py"):
                    current[p] = []
                    break
                current[p] = {}
            current = current[p]
        current[p] = get_patches_from_folder(bug_gen_dir / folder)

    # Get validated instance ids
    validated_inst_ids = []
    if not include_invalid_patches:
        validated_inst_ids = [
            x[KEY_INSTANCE_ID].split(".")[-1]
            for x in json.load(open(os.path.join(LOG_DIR_TASKS, f"{repo}.json")))
        ]

    # Given map_patch_to_patches[path][to][file] = [patches]...
    # * Remove all paths < depth
    # * Collapse all remaining subdicts into a single dict
    remove_paths(map_path_to_patches, depth, bug_gen_dir)
    remove_empty_paths(map_path_to_patches)
    map_path_to_patches = collapse_subdicts(map_path_to_patches, depth)
    for k in list(map_path_to_patches.keys()):
        map_path_to_patches[k] = [
            x
            for x in convert_nested_dict_to_list(map_path_to_patches[k])
            if not include_invalid_patches
            and x.split(f"{PREFIX_BUG}__")[-1].split(".diff")[0] in validated_inst_ids
        ]
        if k.endswith(".py") or len(map_path_to_patches[k]) == 0:
            del map_path_to_patches[k]

    if map_path_to_patches == {}:
        print(f"[{repo}] No modules at file depth {depth} with multiple patches found")
        return
    print(
        f"[{repo}] Found {len(map_path_to_patches)} modules at file depth {depth} with multiple patches"
    )

    # For each module
    global_registry.get(repo).clone()
    total_success, total_fails = 0, 0
    for path, patches in tqdm(map_path_to_patches.items()):
        combos = get_combos(patches, num_patches, max_combos)
        i, success = 0, 0
        while i < len(combos):
            combo = combos[i]
            patch = apply_patches(repo, combo)
            if patch is not None and len(PatchSet(patch)) > 1:
                success += 1
                file_name = f"{COMBINE_MODULE}__{generate_hash(patch)}"
                file_parent = bug_gen_dir / COMBINE_MODULE
                file_parent.mkdir(parents=True, exist_ok=True)
                with open(file_parent / f"{PREFIX_BUG}__{file_name}.diff", "w") as f:
                    f.write(patch)
                with open(
                    file_parent / f"{PREFIX_METADATA}__{file_name}.json", "w"
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
                if limit_per_module != -1 and success >= limit_per_module:
                    break
                # Regenerate combos from unused patches
                patches = [p for p in patches if p not in set(combo)]
                combos = get_combos(patches, num_patches, max_combos)
                i = 0
            else:
                total_fails += 1
                i += 1
        total_success += success

    print(f"{repo}: {total_success} successes, {total_fails} fails")
    subprocess.run(["rm", "-rf", repo], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Combine patches from the same module")
    parser.add_argument("bug_gen_dir", type=str, help="Path to the bug_gen dir")
    parser.add_argument(
        "--num_patches",
        type=int,
        help="Number of patches to merge.",
        default=2,
    )
    parser.add_argument(
        "--limit_per_module",
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
        "--include_invalid_patches", action="store_true", help="Include invalid patches"
    )
    parser.add_argument(
        "--depth",
        type=int,
        help="Depth of the module to combine patches from",
        default=3,
    )
    args = parser.parse_args()
    main(**vars(args))
