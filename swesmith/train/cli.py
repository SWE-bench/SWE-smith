"""
Training and trajectory management commands.

Available commands:
    difficulty_rater   Difficulty rating utilities
    traj_mgr          Trajectory management utilities

For nested commands, use:
    swesmith train difficulty_rater <subcommand>
    swesmith train traj_mgr <subcommand>
"""

import argparse
import sys

import rich


def get_cli():
    parser = argparse.ArgumentParser(
        add_help=False, prog="swesmith train", description=__doc__
    )
    parser.add_argument(
        "command",
        choices=[
            "difficulty_rater",
            "traj_mgr",
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

    # Handle nested commands
    if command == "difficulty_rater":
        from swesmith.train.difficulty_rater.cli import main as difficulty_rater_main

        difficulty_rater_main(remaining_args)
    elif command == "traj_mgr":
        from swesmith.train.traj_mgr.cli import main as traj_mgr_main

        traj_mgr_main(remaining_args)
    else:
        msg = f"Unknown command: {command}"
        raise ValueError(msg)


if __name__ == "__main__":
    sys.exit(main())
