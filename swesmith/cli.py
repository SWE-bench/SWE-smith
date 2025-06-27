"""
SWE-smith: A toolkit for generating software engineering bugs and benchmarks.
"""

import sys
from swesmith.cli_utils import dispatch_sub_cli


def main(args: list[str] | None = None):
    command_mapping = {
        "build_repo": (
            "swesmith.build_repo.cli::main",
            "Build and manage repository environments",
        ),
        "train": (
            "swesmith.train.cli::main",
            "Training and trajectory management utilities",
        ),
        "issue_gen": (
            "swesmith.issue_gen.cli::main",
            "Issue and problem statement generation",
        ),
        "harness": ("swesmith.harness.cli::main", "Evaluation and validation harness"),
        "bug_gen": ("swesmith.bug_gen.cli::main", "Bug generation utilities"),
        "calculate_cost": (
            "scripts.calculate_cost::run_from_cli",
            "Calculate costs for bug generation",
        ),
    }

    dispatch_sub_cli(
        args=args,
        command_mapping=command_mapping,
        prog_name="swesmith",
        module_doc=__doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
