"""
Build repository management commands.

Available commands:
    download_images    Download all SWEFT Docker images
    create_images      Build Docker images for repository profiles
    try_install_py     Test installation commands for Python repositories
"""

import argparse
import sys

import rich


def get_cli():
    parser = argparse.ArgumentParser(
        add_help=False, prog="swesmith build_repo", description=__doc__
    )
    parser.add_argument(
        "command",
        choices=[
            "download_images",
            "create_images",
            "try_install_py",
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
    if command == "download_images":
        from swesmith.build_repo.download_images import (
            run_from_cli as download_images_main,
        )

        download_images_main(remaining_args)
    elif command == "create_images":
        from swesmith.build_repo.create_images import run_from_cli as create_images_main

        create_images_main(remaining_args)
    elif command == "try_install_py":
        from swesmith.build_repo.try_install_py import (
            run_from_cli as try_install_py_main,
        )

        try_install_py_main(remaining_args)
    else:
        msg = f"Unknown command: {command}"
        raise ValueError(msg)


if __name__ == "__main__":
    sys.exit(main())
