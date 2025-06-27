"""
Trajectory management utilities.

Available commands:
    transform_to_ft_list  Transform a list of trajectories to fine-tuning format
    clean_trajs          Remove unnecessary files from trajectories directory
    transform_to_ft      Transform trajectories to fine-tuning format
    combine_trajs        Combine multiple trajectory files and shuffle
"""

import argparse
import sys

import rich


def get_cli():
    parser = argparse.ArgumentParser(
        add_help=False, prog="swesmith train traj_mgr", description=__doc__
    )
    parser.add_argument(
        "command",
        choices=[
            "transform_to_ft_list",
            "clean_trajs",
            "transform_to_ft",
            "combine_trajs",
        ],
        nargs="?",
    )
    parser.add_argument(
        "-h", "--help", action="store_true", help="Show this help message and exit"
    )
    return parser


def main(args: list[str] | None = None):
    if args is None:
        args = sys.argv[1:]
    cli = get_cli()
    parsed_args, remaining_args = cli.parse_known_args(args)  # type: ignore
    command = parsed_args.command
    show_help = parsed_args.help

    if show_help:
        if not command:
            # Show main help
            rich.print(__doc__)
            sys.exit(0)
        else:
            # Add to remaining_args
            remaining_args.append("--help")
    elif not command:
        cli.print_help()
        sys.exit(2)

    # Defer imports to avoid unnecessary long loading times
    if command == "transform_to_ft_list":
        from swesmith.train.traj_mgr.transform_to_ft_list import (
            run_from_cli as transform_to_ft_list_main,
        )

        transform_to_ft_list_main(remaining_args)
    elif command == "clean_trajs":
        from swesmith.train.traj_mgr.clean_trajs import run_from_cli as clean_trajs_main

        clean_trajs_main(remaining_args)
    elif command == "transform_to_ft":
        from swesmith.train.traj_mgr.transform_to_ft import (
            run_from_cli as transform_to_ft_main,
        )

        transform_to_ft_main(remaining_args)
    elif command == "combine_trajs":
        from swesmith.train.traj_mgr.combine_trajs import (
            run_from_cli as combine_trajs_main,
        )

        combine_trajs_main(remaining_args)
    else:
        msg = f"Unknown command: {command}"
        raise ValueError(msg)


if __name__ == "__main__":
    sys.exit(main())
