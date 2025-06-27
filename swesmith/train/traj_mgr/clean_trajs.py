"""
Remove unnecessary files from the trajectories directory.

Usage: python swesmith/
"""

import argparse
import os


def main(traj_dir):
    assert traj_dir.startswith("trajectories"), (
        "This script can only be run on SWE-agent trajectories."
    )
    for folder in sorted(
        [x for x in os.listdir(traj_dir) if os.path.isdir(os.path.join(traj_dir, x))]
    ):
        folder = os.path.join(traj_dir, folder)
        removed = 0
        for root, _, files in os.walk(folder):
            for file in files:
                if any(
                    [
                        file.endswith(ext)
                        for ext in [
                            ".config.yaml",
                            ".debug.log",
                            ".info.log",
                            ".trace.log",
                        ]
                    ]
                ):
                    if file == "run_batch.config.yaml":
                        continue
                    # Delete this file
                    os.remove(os.path.join(root, file))
                    removed += 1
        print(f"{folder}: Removed {removed} files.")


def get_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "traj_dir",
        type=str,
        help="Path to the directory containing the trajectories.",
    )
    return parser


def run_from_cli(args: list[str] | None = None) -> None:
    cli_parser = get_cli_parser()
    cli_args = cli_parser.parse_args(args)
    main(**vars(cli_args))


if __name__ == "__main__":
    run_from_cli()
