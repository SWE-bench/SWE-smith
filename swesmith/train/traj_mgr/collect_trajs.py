"""
Given a folder of SWE-agent trajectories, extracts the trajectories
and transforms them into a fine-tuning compatible jsonl format, namely...

[
  {
    "messages": [
      {
        "role": "system",
        "content": "system prompt (optional)"
      },
      {
        "role": "user",
        "content": "human instruction"
      },
      {
        "role": "assistant",
        "content": "model response"
      }
    ]
  },
  ...
]

Usage: (from SWE-agent directory)
python -m swesmith.train.traj_mgr.collect_trajs --traj_dir <path> \
    --eval_dir <path> \
"""

import argparse
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from swebench.harness.constants import KEY_INSTANCE_ID, LOG_REPORT
from swesmith.constants import generate_hash
from swesmith.train.traj_mgr.utils import MAP_STYLE_TO_FUNC
from tqdm.auto import tqdm
from typing import Optional, Tuple


def process_single_trajectory(
    folder: str,
    traj_dir: Path,
    eval_dir: Path,
    transform_traj,
) -> Optional[Tuple[str, dict]]:
    """Process a single trajectory folder and return the result."""
    if not (eval_dir / folder).exists():
        return None
    if not (eval_dir / folder / LOG_REPORT).exists():
        return None

    try:
        report_path = eval_dir / folder / LOG_REPORT
        report = json.loads(report_path.read_text())
        is_resolved = (
            report.get("resolved", False)
            if folder not in report
            else report[folder].get("resolved", False)
        )

        pred_path = traj_dir / folder / f"{folder}.patch"
        traj_path = traj_dir / folder / f"{folder}.traj"
        traj_orig = json.loads(traj_path.read_text())
        traj = transform_traj(traj_orig)
        traj[KEY_INSTANCE_ID] = folder
        traj["resolved"] = is_resolved
        if "replay_config" in traj_orig:
            traj["model"] = json.loads(traj_orig["replay_config"])["agent"]["model"][
                "name"
            ]
        traj["traj_id"] = f"{folder}.{generate_hash(str(traj_dir))}"
        traj["patch"] = pred_path.read_text() if pred_path.exists() else ""

        return (folder, traj)
    except Exception as e:
        print(f"Error processing folder {folder}: {e}")
        return None


def main(
    out_dir: Path,
    traj_dir: Path,
    eval_dir: Path,
    style: str,
    workers: int,
):
    if style not in MAP_STYLE_TO_FUNC:
        raise ValueError(
            f"Style {style} not supported. Options: {list(MAP_STYLE_TO_FUNC.keys())}"
        )
    transform_traj = MAP_STYLE_TO_FUNC[style]

    folders = [x.name for x in traj_dir.iterdir() if x.is_dir()]
    print(f"Found {len(folders)} trajectory folders in {traj_dir}")

    out_path = out_dir / f"{eval_dir.name}.{style}.jsonl"

    # Process trajectories in parallel
    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all tasks
        future_to_folder = {
            executor.submit(
                process_single_trajectory, folder, traj_dir, eval_dir, transform_traj
            ): folder
            for folder in folders
        }

        # Collect results as they complete
        for future in tqdm(
            as_completed(future_to_folder),
            total=len(folders),
            desc="Processing trajectories",
        ):
            result = future.result()
            if result is not None:
                results.append(result)

    # Write results to file
    num_trajs = 0
    with open(out_path, "w") as f:
        for _, traj in results:
            f.write(json.dumps(traj) + "\n")
            num_trajs += 1

    print(f"Wrote {num_trajs} valid trajectories to {out_path.absolute()}")


if __name__ == "__main__":
    user = os.getenv("USER")

    arg_parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    arg_parser.add_argument(
        "-t",
        "--traj_dir",
        type=Path,
        required=False,
        help="Path to folder containing SWE-agent trajectories. Default: trajectories/{user}/",
        default=f"trajectories/{user}/",
    )
    arg_parser.add_argument(
        "-e",
        "--eval_dir",
        type=Path,
        required=False,
        default="logs/run_evaluation/",
        help="Path to folder containing evaluation results. Default: logs/run_evaluation/",
    )
    arg_parser.add_argument(
        "-s",
        "--style",
        type=str,
        required=False,
        default="xml",
        choices=list(MAP_STYLE_TO_FUNC.keys()),
        help="Style of the trajectories",
    )
    arg_parser.add_argument(
        "-o",
        "--out_dir",
        type=Path,
        required=False,
        default=".",
        help="Path to output directory",
    )
    arg_parser.add_argument(
        "-w",
        "--workers",
        type=int,
        required=False,
        default=min(32, os.cpu_count() + 4),
        help="Maximum number of worker threads. Default: min(32, os.cpu_count() + 4)",
    )
    args = arg_parser.parse_args()
    main(**vars(args))
