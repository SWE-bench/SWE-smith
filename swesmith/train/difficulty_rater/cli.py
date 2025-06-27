"""
Difficulty rating utilities.
"""

import sys
from swesmith.cli_utils import dispatch_sub_cli


def main(args: list[str] | None = None):
    command_mapping = {
        "test_rater": (
            "swesmith.train.difficulty_rater.test_rater::run_from_cli",
            "Test the difficulty rater model",
        ),
        "get_difficulties": (
            "swesmith.train.difficulty_rater.get_difficulties::run_from_cli",
            "Get difficulty ratings for different bugs",
        ),
    }

    dispatch_sub_cli(
        args=args,
        command_mapping=command_mapping,
        prog_name="swesmith train difficulty_rater",
        module_doc=__doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
