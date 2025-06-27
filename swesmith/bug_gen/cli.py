"""
Bug generation utilities.
"""

import sys
from swesmith.cli_utils import dispatch_sub_cli


def main(args: list[str] | None = None):
    command_mapping = {
        "collect_patches": (
            "swesmith.bug_gen.collect_patches::run_from_cli",
            "Collect all patches into a single JSON file",
        ),
        "get_cost": (
            "swesmith.bug_gen.get_cost::run_from_cli",
            "Determine the total cost of LLM generated bugs",
        ),
        "procedural": (
            "swesmith.bug_gen.procedural.cli::main",
            "Procedural bug generation utilities",
        ),
        "mirror": (
            "swesmith.bug_gen.mirror.cli::main",
            "Mirror bug generation utilities",
        ),
        "combine": ("swesmith.bug_gen.combine.cli::main", "Combine patches utilities"),
        "llm": (
            "swesmith.bug_gen.llm.cli::main",
            "Language model bug generation utilities",
        ),
    }

    dispatch_sub_cli(
        args=args,
        command_mapping=command_mapping,
        prog_name="swesmith bug_gen",
        module_doc=__doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
