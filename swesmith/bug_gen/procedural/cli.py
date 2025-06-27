"""
Procedural bug generation utilities.

Available commands:
    generate  Generate bugs procedurally for a repository
"""

import sys
from swesmith.cli_utils import dispatch_sub_cli


def main(args: list[str] | None = None):
    command_mapping = {
        "generate": ("swesmith.bug_gen.procedural.generate", "run_from_cli"),
    }

    dispatch_sub_cli(
        args=args,
        command_mapping=command_mapping,
        prog_name="swesmith bug_gen procedural",
        module_doc=__doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
