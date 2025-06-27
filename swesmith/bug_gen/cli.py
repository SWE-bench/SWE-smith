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

import sys
from swesmith.cli_utils import dispatch_sub_cli


def main(args: list[str] | None = None):
    command_mapping = {
        "collect_patches": ("swesmith.bug_gen.collect_patches", "run_from_cli"),
        "get_cost": ("swesmith.bug_gen.get_cost", "run_from_cli"),
        "procedural": ("swesmith.bug_gen.procedural.cli", "main"),
        "mirror": ("swesmith.bug_gen.mirror.cli", "main"),
        "combine": ("swesmith.bug_gen.combine.cli", "main"),
        "llm": ("swesmith.bug_gen.llm.cli", "main"),
    }

    dispatch_sub_cli(
        args=args,
        command_mapping=command_mapping,
        prog_name="swesmith bug_gen",
        module_doc=__doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
