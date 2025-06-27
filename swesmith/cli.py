"""
SWE-smith: A toolkit for generating software engineering bugs and benchmarks.

Usage:
    swesmith <command> [<args>...]

Commands:
    build_repo    Build and manage repository environments
    train         Training and trajectory management utilities
    issue_gen     Issue and problem statement generation
    harness       Evaluation and validation harness
    bug_gen       Bug generation utilities
    calculate_cost Calculate costs for bug generation

For help on a specific command, use:
    swesmith <command> --help
"""

import argparse
import sys

import rich


def get_cli():
    parser = argparse.ArgumentParser(
        add_help=False, prog="swesmith", description=__doc__
    )
    parser.add_argument(
        "command",
        choices=[
            "build_repo",
            "train",
            "issue_gen",
            "harness",
            "bug_gen",
            "calculate_cost",
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
    if command == "build_repo":
        from swesmith.build_repo.cli import main as build_repo_main

        build_repo_main(remaining_args)
    elif command == "train":
        from swesmith.train.cli import main as train_main

        train_main(remaining_args)
    elif command == "issue_gen":
        from swesmith.issue_gen.cli import main as issue_gen_main

        issue_gen_main(remaining_args)
    elif command == "harness":
        from swesmith.harness.cli import main as harness_main

        harness_main(remaining_args)
    elif command == "bug_gen":
        from swesmith.bug_gen.cli import main as bug_gen_main

        bug_gen_main(remaining_args)
    elif command == "calculate_cost":
        from scripts.calculate_cost import run_from_cli as calculate_cost_main

        calculate_cost_main(remaining_args)
    else:
        msg = f"Unknown command: {command}"
        raise ValueError(msg)


if __name__ == "__main__":
    sys.exit(main())
