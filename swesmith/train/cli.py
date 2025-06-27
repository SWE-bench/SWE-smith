"""
Training and trajectory management commands.
"""

import sys
from swesmith.cli_utils import dispatch_sub_cli


def main(args: list[str] | None = None):
    command_mapping = {
        "difficulty_rater": (
            "swesmith.train.difficulty_rater.cli::main",
            "Difficulty rating utilities",
        ),
        "traj_mgr": (
            "swesmith.train.traj_mgr.cli::main",
            "Trajectory management utilities",
        ),
    }

    dispatch_sub_cli(
        args=args,
        command_mapping=command_mapping,
        prog_name="swesmith train",
        module_doc=__doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
