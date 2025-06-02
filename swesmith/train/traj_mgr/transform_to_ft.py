"""
Given a folder of SWE-agent trajectories, extracts the trajectories
and transforms them into a fine-tuning compatible format, namely...

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
python -m swesmith.train.traj_mgr.transform_to_ft --traj_dir <path> \
    --eval_dir <path> \
    --resolved_only
"""

import argparse
import json
import os
from pathlib import Path

from swesmith.train.traj_mgr.utils import MAP_STYLE_TO_FUNC
from tqdm.auto import tqdm


def main(
    out_path: Path,
    traj_dir: Path,
    eval_dir: Path,
    style: str,
    only_resolved: bool = False,
):
    if style not in MAP_STYLE_TO_FUNC:
        raise ValueError(
            f"Style {style} not supported. Options: {list(MAP_STYLE_TO_FUNC.keys())}"
        )
    transform_traj = MAP_STYLE_TO_FUNC[style]

    folders = [x.name for x in traj_dir.iterdir() if x.is_dir()]
    print(f"Found {len(folders)} trajectory folders in {traj_dir}")

    if only_resolved and eval_dir.exists():
        print("Only keeping trajectories for resolved instances")

    num_trajs = 0
    with open(out_path, "w") as f:
        for folder in tqdm(folders):
            if not (eval_dir / folder).exists():
                continue
            if not (eval_dir / folder / "report.json").exists():
                continue

            if only_resolved:
                report_path = eval_dir / folder / "report.json"
                report = json.load(open(report_path, "r"))
                is_resolved = (
                    report.get("resolved", False)
                    if folder not in report
                    else report[folder].get("resolved", False)
                )
                if not is_resolved:
                    continue

            traj_path = traj_dir / folder / f"{folder}.traj"
            traj = transform_traj(json.load(open(traj_path, "r")))
            traj["instance_id"] = folder
            f.write(json.dumps(traj) + "\n")
            num_trajs += 1

    print(f"Found {num_trajs} valid trajectories")
    print(f"Wrote trajectories to {out_path}")


if __name__ == "__main__":
    user = os.getenv("USER")

    arg_parser = argparse.ArgumentParser(
        description="Transform SWE-agent trajectories to fine-tuning format"
    )
    arg_parser.add_argument(
        "--traj_dir",
        type=Path,
        required=False,
        help="Path to folder containing SWE-agent trajectories. Default: trajectories/{user}/",
        default=f"trajectories/{user}/",
    )
    arg_parser.add_argument(
        "--eval_dir",
        type=Path,
        required=False,
        default="logs/run_evaluation/",
        help="Path to folder containing evaluation results. Default: logs/run_evaluation/",
    )
    arg_parser.add_argument(
        "--style",
        type=str,
        required=False,
        default="xml",
        help="Style of the trajectories",
    )
    arg_parser.add_argument(
        "--only_resolved",
        action="store_true",
        required=False,
        help="Only keep trajectories for resolved instances",
    )
    arg_parser.add_argument(
        "--out_path",
        type=Path,
        required=False,
        default="trajectories_sft/",
        help="Path to output directory",
    )
    args = arg_parser.parse_args()
    main(**vars(args))

    args.out_path.mkdir(parents=True, exist_ok=True)

    USER = "john-b-yang"
    # TRAJS_EXP_PREFIX = "swesmith_gen_"

    for run_id in sorted(args.traj_dir.iterdir()):
        # if not run_id.startswith(TRAJS_EXP_PREFIX):
        #     continue
        traj_dir = args.traj_dir / run_id
        eval_dir = args.eval_dir / run_id
        out_path = args.out_path / f"ft_xml_{eval_dir.name}.jsonl"
        if out_path.exists():
            num = len(out_path.read_text().splitlines())
            print(f"Skipping {out_path} because it already exists ({num} trajs)")
            continue
        print("*" * 20)
        main(
            out_path=out_path,
            traj_dir=traj_dir,
            eval_dir=eval_dir,
            style="xml",
            only_resolved=True,
        )
