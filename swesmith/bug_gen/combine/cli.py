"""
Combine patches utilities.
"""

import sys
from swesmith.cli_utils import dispatch_sub_cli


def main(args: list[str] | None = None):
    command_mapping = {
        "same_file": (
            "swesmith.bug_gen.combine.same_file::run_from_cli",
            "Combine multiple patches from the same file",
        ),
        "same_module": (
            "swesmith.bug_gen.combine.same_module::run_from_cli",
            "Combine patches from the same module",
        ),
    }

    dispatch_sub_cli(
        args=args,
        command_mapping=command_mapping,
        prog_name="swesmith bug_gen combine",
        module_doc=__doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
