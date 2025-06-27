"""
Utilities for CLI command dispatching.
"""

import argparse
import sys
from typing import Dict, Tuple
import importlib

import rich


def dispatch_sub_cli(
    args: list[str] | None,
    command_mapping: Dict[str, Tuple[str, str]],
    prog_name: str,
    module_doc: str | None,
) -> None:
    """
    Dispatch to subcommands based on a command mapping.

    Args:
        args: Command line arguments (None for sys.argv[1:])
        command_mapping: Dict mapping command names to (import_path, function_name) tuples
        prog_name: Program name for the parser
        module_doc: Module docstring for help text (can be None)
    """
    if args is None:
        args = sys.argv[1:]

    # Create parser
    parser = argparse.ArgumentParser(
        add_help=False, prog=prog_name, description=module_doc
    )
    parser.add_argument(
        "command",
        choices=list(command_mapping.keys()),
        nargs="?",
    )
    parser.add_argument(
        "-h", "--help", action="store_true", help="Show this help message and exit"
    )

    # Parse arguments
    parsed_args, remaining_args = parser.parse_known_args(args)
    command = parsed_args.command
    show_help = parsed_args.help

    # Handle help
    if show_help:
        if not command:
            # Show main help
            rich.print(module_doc or "")
            sys.exit(0)
        else:
            # Add to remaining_args
            remaining_args.append("--help")
    elif not command:
        parser.print_help()
        sys.exit(2)

    # Dispatch to command
    import_path, function_name = command_mapping[command]

    # Dynamic import and call
    if "." in import_path:
        module_path, module_name = import_path.rsplit(".", 1)
        module = importlib.import_module(import_path)
        func = getattr(module, function_name)
    else:
        # Simple import for nested CLI modules
        module = importlib.import_module(import_path)
        func = getattr(module, function_name)

    func(remaining_args)
