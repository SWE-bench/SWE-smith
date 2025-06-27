"""
Evaluation and validation harness commands.

Available commands:
    eval     Evaluate predictions on SWEFT bugs
    valid    Run validation on bug patches
    gather   Convert validation logs to SWE-bench style dataset
"""

import argparse
import sys

import rich


def get_cli():
    parser = argparse.ArgumentParser(
        add_help=False, prog="swesmith harness", description=__doc__
    )
    parser.add_argument(
        "command",
        choices=[
            "eval",
            "valid",
            "gather",
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
    if command == "eval":
        from swesmith.harness.eval import run_from_cli as eval_main

        eval_main(remaining_args)
    elif command == "valid":
        from swesmith.harness.valid import run_from_cli as valid_main

        valid_main(remaining_args)
    elif command == "gather":
        from swesmith.harness.gather import run_from_cli as gather_main

        gather_main(remaining_args)
    else:
        msg = f"Unknown command: {command}"
        raise ValueError(msg)


if __name__ == "__main__":
    sys.exit(main())
