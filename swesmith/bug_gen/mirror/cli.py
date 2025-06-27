"""
Mirror bug generation utilities.
"""

import sys
from swesmith.cli_utils import dispatch_sub_cli


def main(args: list[str] | None = None):
    command_mapping = {
        "generate": (
            "swesmith.bug_gen.mirror.generate::run_from_cli",
            "Mirror bugs from pull requests",
        ),
    }

    dispatch_sub_cli(
        args=args,
        command_mapping=command_mapping,
        prog_name="swesmith bug_gen mirror",
        module_doc=__doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
