"""
Bug generation utilities.

Available commands:
    collect_patches  Collect all patches into a single JSON file
    get_cost        Determine the total cost of LLM generated bugs
    procedural      Procedural bug generation utilities
    mirror          Mirror bug generation utilities
    combine         Combine patches utilities
    llm             Language model bug generation utilities

For nested commands, use:
    swesmith bug_gen procedural <subcommand>
    swesmith bug_gen mirror <subcommand>
    swesmith bug_gen combine <subcommand>
    swesmith bug_gen llm <subcommand>
"""

import argparse
import sys

import rich


def get_cli():
    parser = argparse.ArgumentParser(
        add_help=False, prog="swesmith bug_gen", description=__doc__
    )
    parser.add_argument(
        "command",
        choices=[
            "collect_patches",
            "get_cost",
            "procedural",
            "mirror",
            "combine",
            "llm",
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

    # Handle direct commands
    if command == "collect_patches":
        from swesmith.bug_gen.collect_patches import (
            run_from_cli as collect_patches_main,
        )

        collect_patches_main(remaining_args)
    elif command == "get_cost":
        from swesmith.bug_gen.get_cost import run_from_cli as get_cost_main

        get_cost_main(remaining_args)
    # Handle nested commands
    elif command == "procedural":
        from swesmith.bug_gen.procedural.cli import main as procedural_main

        procedural_main(remaining_args)
    elif command == "mirror":
        from swesmith.bug_gen.mirror.cli import main as mirror_main

        mirror_main(remaining_args)
    elif command == "combine":
        from swesmith.bug_gen.combine.cli import main as combine_main

        combine_main(remaining_args)
    elif command == "llm":
        from swesmith.bug_gen.llm.cli import main as llm_main

        llm_main(remaining_args)
    else:
        msg = f"Unknown command: {command}"
        raise ValueError(msg)


if __name__ == "__main__":
    sys.exit(main())
