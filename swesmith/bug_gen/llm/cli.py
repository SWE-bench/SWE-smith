"""
Language model bug generation utilities.
"""

import sys
from swesmith.cli_utils import dispatch_sub_cli


def main(args: list[str] | None = None):
    command_mapping = {
        "rewrite": (
            "swesmith.bug_gen.llm.rewrite::run_from_cli",
            "Generate bug patches by rewriting functions/classes",
        ),
        "modify": (
            "swesmith.bug_gen.llm.modify::run_from_cli",
            "Generate bugs using language model modifications",
        ),
    }

    dispatch_sub_cli(
        args=args,
        command_mapping=command_mapping,
        prog_name="swesmith bug_gen llm",
        module_doc=__doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
