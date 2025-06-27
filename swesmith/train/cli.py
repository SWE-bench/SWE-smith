"""
Training and trajectory management commands.

Available commands:
    difficulty_rater   Difficulty rating utilities
    traj_mgr          Trajectory management utilities

For nested commands, use:
    swesmith train difficulty_rater <subcommand>
    swesmith train traj_mgr <subcommand>
"""

import sys
from swesmith.cli_utils import dispatch_sub_cli


def main(args: list[str] | None = None):
    command_mapping = {
        "difficulty_rater": ("swesmith.train.difficulty_rater.cli", "main"),
        "traj_mgr": ("swesmith.train.traj_mgr.cli", "main"),
    }

    dispatch_sub_cli(
        args=args,
        command_mapping=command_mapping,
        prog_name="swesmith train",
        module_doc=__doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
