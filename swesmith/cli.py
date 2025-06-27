"""
SWE-smith: A toolkit for generating software engineering bugs and benchmarks.

Usage:
    swesmith <command> [<args>...]

Commands:
    build_repo    Build and manage repository environments
    train         Training and trajectory management utilities
    issue_gen     Issue and problem statement generation
    harness       Evaluation and validation harness
    bug_gen       Bug generation utilities
    calculate_cost Calculate costs for bug generation

For help on a specific command, use:
    swesmith <command> --help
"""

import sys
from swesmith.cli_utils import dispatch_sub_cli


def main(args: list[str] | None = None):
    command_mapping = {
        "build_repo": ("swesmith.build_repo.cli", "main"),
        "train": ("swesmith.train.cli", "main"),
        "issue_gen": ("swesmith.issue_gen.cli", "main"),
        "harness": ("swesmith.harness.cli", "main"),
        "bug_gen": ("swesmith.bug_gen.cli", "main"),
        "calculate_cost": ("scripts.calculate_cost", "run_from_cli"),
    }

    dispatch_sub_cli(
        args=args,
        command_mapping=command_mapping,
        prog_name="swesmith",
        module_doc=__doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
