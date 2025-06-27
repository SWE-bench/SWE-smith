"""
Purpose: Combine multiple .jsonl files together and shuffle the lines, where the .jsonl files correspond to
SFT datasets of SWE-agent expert trajectories.

Usage: You should run this script in the root directory of the SWE-agent repository.

python -m swesmith.train.traj_mgr.combine_trajs
"""

import argparse
import json
import os
import random
import rich
import sys

from pathlib import Path
from sparklines import sparklines
from swebench.harness.constants import KEY_INSTANCE_ID


def merge_and_shuffle_jsonl(
    max_per_inst: int = 3,
    output_file: Path | None = None,
    seed: int = 24,
    sft_dir: Path = Path("trajectories_sft/"),
):
    """
    Merge multiple JSONL files containing SWE-agent expert trajectories and shuffle the combined data.

    Args:
        max_per_inst: Maximum number of trajectories to include per instance ID. If an instance
            has more trajectories than this limit, a random sample will be selected.
        output_file: Path to the output JSONL file. If None, user will be prompted to enter
            a filename.
        seed: Random seed for shuffling trajectories and sampling when max_per_inst is exceeded.
        sft_dir: Directory containing the SFT trajectory JSONL files to merge.
    """

    # List all .jsonl files in expert_trajs/
    try:
        all_trajs = sorted([f for f in os.listdir(sft_dir) if f.endswith(".jsonl")])
        print("Select 2+ files to merge:")
        print("Index | Filename | # Trajectories")
        for idx, file in enumerate(all_trajs):
            if file.endswith(".jsonl"):
                num_trajs = sum(1 for _ in open(sft_dir / file, "r", encoding="utf-8"))
                print(f"{idx}: {file} ({num_trajs})")
        selected_indices = input(
            "Enter the indices of the files to merge (specify indices or range of indices, e.g. `7 11-13`): "
        )
        process_idx = (
            lambda idx: list(range(int(idx.split("-")[0]), int(idx.split("-")[1]) + 1))
            if "-" in idx
            else [int(idx.strip())]
        )
        selected_indices = [
            idx for part in selected_indices.split() for idx in process_idx(part)
        ]
        files = [sft_dir / all_trajs[idx] for idx in selected_indices]

        if not output_file:
            filename = input("Name of output file (without extension): ") + ".jsonl"
            output_file = sft_dir / filename
    except KeyboardInterrupt:
        print("\nExiting...")
        return

    # Read all lines from the input JSONL files
    inst_to_trajs = {}
    for file in files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                for traj in f.readlines():
                    traj = json.loads(traj)
                    inst_id = traj[KEY_INSTANCE_ID]
                    if inst_id not in inst_to_trajs:
                        inst_to_trajs[inst_id] = []
                    inst_to_trajs[inst_id].append(traj)
        except FileNotFoundError:
            print(f"Warning: File not found - {file}", file=sys.stderr)
        except Exception as e:
            print(f"Error reading {file}: {e}", file=sys.stderr)

    all_trajs = []
    random.seed(seed)
    bug_types, repo_count = {}, {}
    for k, v in inst_to_trajs.items():
        s = min(len(v), max_per_inst)
        all_trajs.extend(random.sample(v, s))

        bug_type = k.rsplit(".", 1)[-1].rsplit("_", 1)[0]
        if bug_type.startswith("func_pm"):
            bug_type = "func_pm"
        if bug_type not in bug_types:
            bug_types[bug_type] = 0
        bug_types[bug_type] += s

        repo = k.rsplit(".", 1)[0]
        if repo not in repo_count:
            repo_count[repo] = 0
        repo_count[repo] += s
    random.shuffle(all_trajs)
    rich.print(bug_types)
    rich.print(sparklines(bug_types.values())[0])

    # Write to the output file
    with open(output_file, "w", encoding="utf-8") as f:
        for traj in all_trajs:
            f.write(json.dumps(traj) + "\n")

    print(
        f"Merged and shuffled content written to {output_file} ({len(all_trajs)} lines)"
    )

    metadata_file = output_file.parent / f"metadata__{output_file.stem}.json"
    print(f"Writing metadata to {metadata_file}")
    with open(metadata_file, "w") as f:
        json.dump(
            {
                "output_file": str(output_file),
                "num_files": len(files),
                "num_trajs": len(all_trajs),
                "max_per_inst": max_per_inst,
                "bug_types_dist": bug_types,
                "seed": seed,
                "files": [str(f) for f in files],
                "repo_count": [
                    f"{repo} | {count}"
                    for repo, count in sorted(
                        repo_count.items(), key=lambda x: x[1], reverse=True
                    )
                ],
            },
            f,
            indent=4,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge and shuffle multiple JSONL files."
    )
    parser.add_argument(
        "-m",
        "--max_per_inst",
        type=int,
        default=3,
        help="Max number of trajectories per instance.",
    )
    parser.add_argument(
        "-o", "--output_file", type=Path, help="Name of the output file."
    )
    parser.add_argument(
        "-s", "--seed", type=int, default=24, help="Random seed for shuffling."
    )
    parser.add_argument(
        "-d",
        "--sft_dir",
        type=Path,
        default=Path("trajectories_sft/"),
        help="Directory containing the SFT trajectory JSONL files to merge.",
    )

    args = parser.parse_args()
    merge_and_shuffle_jsonl(**vars(args))
