"""
Utilities for command lines
"""

import argparse
import sys
from typing import Dict, Tuple
import importlib

import rich
from rich.table import Table


def dispatch_sub_cli(
    args: list[str] | None,
    command_mapping: Dict[str, Tuple[str, str]],
    prog_name: str,
    module_doc: str | None = None,
) -> None:
    """
    Dispatch to subcommands based on a command mapping.

    Args:
        args: Command line arguments (if None, use sys.argv[1:])
        command_mapping: Dict mapping command names to (import_path, description) tuples,
            where import_path is a string of the form "module_path::function_name"
        prog_name: Program name for the parser
        module_doc: Module docstring for help text (can be None)
    """
    if args is None:
        args = sys.argv[1:]

    if module_doc is None:
        module_doc = f"Command line interface for {prog_name}"

    # Create parser
    parser = argparse.ArgumentParser(add_help=False, prog=prog_name)
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
            # Show main help with rich formatting
            _print_main_help(prog_name, command_mapping, module_doc.lstrip())
            sys.exit(0)
        else:
            # Add to remaining_args
            remaining_args.append("--help")
    elif not command:
        _print_main_help(prog_name, command_mapping, module_doc.lstrip())
        sys.exit(2)

    # Dispatch to command
    import_path, _ = command_mapping[command]

    # Parse import path and function name
    if "::" in import_path:
        module_path, function_name = import_path.split("::", 1)
    else:
        module_path = import_path
        function_name = "main"  # default function name

    # Dynamic import and call
    module = importlib.import_module(module_path)
    func = getattr(module, function_name)

    func(remaining_args)


def _print_main_help(
    prog_name: str, command_mapping: Dict[str, Tuple[str, str]], module_doc: str | None
) -> None:
    """Print nicely formatted help using rich."""
    # Header
    rich.print(
        f"[cyan][bold]{module_doc or f'Command line interface for {prog_name}'}[/bold][/cyan]\n"
    )

    # Usage section
    rich.print("[cyan][bold]=== USAGE ===[/bold][/cyan]\n")
    rich.print(f"[green]{prog_name} <command> [options][/green]")
    rich.print(f"[green]{prog_name} <command> [bold]--help[/bold][/green]\n")

    # Commands section
    rich.print("[cyan][bold]=== AVAILABLE COMMANDS ===[/bold][/cyan]\n")

    # Create and populate table
    table = Table(
        show_header=False, show_lines=False, show_edge=False, pad_edge=False, box=None
    )
    table.add_column("Command", style="bold green", width=20)
    table.add_column("Description", style="white")

    for cmd, (_, description) in command_mapping.items():
        table.add_row(cmd, description)

    rich.print(table)
