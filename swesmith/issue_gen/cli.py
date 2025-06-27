"""
Issue and problem statement generation commands.

Available commands:
    get_from_tests  Generate issues from test cases
    get_from_pr     Get issue text from pull requests
    get_static      Generate static problem statements
    generate        Generate issue text using language models
"""

import argparse
import sys

import rich


def get_cli():
    parser = argparse.ArgumentParser(
        add_help=False, prog="swesmith issue_gen", description=__doc__
    )
    parser.add_argument(
        "command",
        choices=[
            "get_from_tests",
            "get_from_pr",
            "get_static",
            "generate",
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
    if command == "get_from_tests":
        from swesmith.issue_gen.get_from_tests import (
            run_from_cli as get_from_tests_main,
        )

        get_from_tests_main(remaining_args)
    elif command == "get_from_pr":
        from swesmith.issue_gen.get_from_pr import run_from_cli as get_from_pr_main

        get_from_pr_main(remaining_args)
    elif command == "get_static":
        from swesmith.issue_gen.get_static import run_from_cli as get_static_main

        get_static_main(remaining_args)
    elif command == "generate":
        from swesmith.issue_gen.generate import run_from_cli as generate_main

        generate_main(remaining_args)
    else:
        msg = f"Unknown command: {command}"
        raise ValueError(msg)


if __name__ == "__main__":
    sys.exit(main())
