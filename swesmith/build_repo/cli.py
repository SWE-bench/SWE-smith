"""
Build repository management commands.
"""

import sys
from swesmith.cli_utils import dispatch_sub_cli


def main(args: list[str] | None = None):
    command_mapping = {
        "download_images": (
            "swesmith.build_repo.download_images::run_from_cli",
            "Download all SWEFT Docker images",
        ),
        "create_images": (
            "swesmith.build_repo.create_images::run_from_cli",
            "Build Docker images for repository profiles",
        ),
        "try_install_py": (
            "swesmith.build_repo.try_install_py::run_from_cli",
            "Test installation commands for Python repositories",
        ),
    }

    dispatch_sub_cli(
        args=args,
        command_mapping=command_mapping,
        prog_name="swesmith build_repo",
        module_doc=__doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
