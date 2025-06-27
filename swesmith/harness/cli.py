"""
Evaluation and validation harness commands.
"""

import sys
from swesmith.cli_utils import dispatch_sub_cli


def main(args: list[str] | None = None):
    command_mapping = {
        "eval": (
            "swesmith.harness.eval::run_from_cli",
            "Evaluate predictions on SWE-smith bugs",
        ),
        "valid": (
            "swesmith.harness.valid::run_from_cli",
            "Run validation on bug patches",
        ),
        "gather": (
            "swesmith.harness.gather::run_from_cli",
            "Convert validation logs to SWE-bench style dataset",
        ),
    }

    dispatch_sub_cli(
        args=args,
        command_mapping=command_mapping,
        prog_name="swesmith harness",
        module_doc=__doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
