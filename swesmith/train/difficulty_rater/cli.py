"""
Difficulty rating utilities.

Available commands:
    test_rater        Test the difficulty rater model
    get_difficulties  Get difficulty ratings for different bugs
"""

import argparse
import sys

import rich


def get_cli():
    parser = argparse.ArgumentParser(
        add_help=False, prog="swesmith train difficulty_rater", description=__doc__
    )
    parser.add_argument(
        "command",
        choices=[
            "test_rater",
            "get_difficulties",
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
    if command == "test_rater":
        from swesmith.train.difficulty_rater.test_rater import (
            run_from_cli as test_rater_main,
        )

        test_rater_main(remaining_args)
    elif command == "get_difficulties":
        from swesmith.train.difficulty_rater.get_difficulties import (
            run_from_cli as get_difficulties_main,
        )

        get_difficulties_main(remaining_args)
    else:
        msg = f"Unknown command: {command}"
        raise ValueError(msg)


if __name__ == "__main__":
    sys.exit(main())
