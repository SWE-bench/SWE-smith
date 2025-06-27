"""
Trajectory management utilities.
"""

import sys
from swesmith.cli_utils import dispatch_sub_cli


def main(args: list[str] | None = None):
    command_mapping = {
        "transform_to_ft_list": (
            "swesmith.train.traj_mgr.transform_to_ft_list::run_from_cli",
            "Transform a list of trajectories to fine-tuning format",
        ),
        "clean_trajs": (
            "swesmith.train.traj_mgr.clean_trajs::run_from_cli",
            "Remove unnecessary files from trajectories directory",
        ),
        "transform_to_ft": (
            "swesmith.train.traj_mgr.transform_to_ft::run_from_cli",
            "Transform trajectories to fine-tuning format",
        ),
        "combine_trajs": (
            "swesmith.train.traj_mgr.combine_trajs::run_from_cli",
            "Combine multiple trajectory files and shuffle",
        ),
    }

    dispatch_sub_cli(
        args=args,
        command_mapping=command_mapping,
        prog_name="swesmith train traj_mgr",
        module_doc=__doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
