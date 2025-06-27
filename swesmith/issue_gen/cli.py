"""
Issue and problem statement generation commands.
"""

import sys
from swesmith.cli_utils import dispatch_sub_cli


def main(args: list[str] | None = None):
    command_mapping = {
        "get_from_tests": (
            "swesmith.issue_gen.get_from_tests::run_from_cli",
            "Generate issues from test cases",
        ),
        "get_from_pr": (
            "swesmith.issue_gen.get_from_pr::run_from_cli",
            "Get issue text from pull requests",
        ),
        "get_static": (
            "swesmith.issue_gen.get_static::run_from_cli",
            "Generate static problem statements",
        ),
        "generate": (
            "swesmith.issue_gen.generate::run_from_cli",
            "Generate issue text using language models",
        ),
    }

    dispatch_sub_cli(
        args=args,
        command_mapping=command_mapping,
        prog_name="swesmith issue_gen",
        module_doc=__doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
