"""
Combine patches utilities.

Available commands:
    same_file    Combine multiple patches from the same file
    same_module  Combine patches from the same module
"""

import argparse
import sys

import rich


def get_cli():
    parser = argparse.ArgumentParser(
        add_help=False, prog="swesmith bug_gen combine", description=__doc__
    )
    parser.add_argument(
        "command",
        choices=[
            "same_file",
            "same_module",
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
    if command == "same_file":
        from swesmith.bug_gen.combine.same_file import run_from_cli as same_file_main

        same_file_main(remaining_args)
    elif command == "same_module":
        from swesmith.bug_gen.combine.same_module import (
            run_from_cli as same_module_main,
        )

        same_module_main(remaining_args)
    else:
        msg = f"Unknown command: {command}"
        raise ValueError(msg)


if __name__ == "__main__":
    sys.exit(main())
