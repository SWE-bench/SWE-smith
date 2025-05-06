"""
Purpose: Calculate the cost of generating bugs across all repositories

Usage: python scripts/calculate_cost.py <bug_type (e.g. "lm_rewrite")>
"""

import argparse
import os

from swesmith.bug_gen.get_cost import main as get_cost
from swesmith.constants import LOG_DIR_BUG_GEN


def main(bug_gen_folder: str, bug_type: str) -> None:
    if bug_gen_folder == LOG_DIR_BUG_GEN:
        folders = [
            os.path.join(LOG_DIR_BUG_GEN, x)
            for x in os.listdir(LOG_DIR_BUG_GEN)
            if os.path.isdir(os.path.join(LOG_DIR_BUG_GEN, x))
        ]
    elif bug_gen_folder.startswith(str(LOG_DIR_BUG_GEN)):
        assert os.path.isdir(bug_gen_folder), (
            f"{bug_gen_folder} should point to a folder"
        )
        folders = [bug_gen_folder]
    total_cost, total_bugs = 0, 0
    print("Repo | Cost | Bugs | Cost/Instance")
    for folder in folders:
        cost, bugs, per_instance = get_cost(folder, bug_type)
        if cost == 0:
            continue
        repo = folder.rsplit("/", 1)[-1]
        print(f"{repo} | ${round(cost, 2)} | {bugs} | ${round(per_instance, 4)}")
        total_cost += cost
        total_bugs += bugs
    print(
        f"Total | ${round(total_cost, 2)} | {total_bugs} | ${round(total_cost / total_bugs, 6)}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Determine the total cost of generating bugs across all repositories"
    )
    parser.add_argument(
        "--folder",
        dest="bug_gen_folder",
        type=str,
        help="Folder under `{LOG_DIR_BUG_GEN}`",
        default=LOG_DIR_BUG_GEN,
    )
    parser.add_argument(
        "--type",
        dest="bug_type",
        type=str,
        help="Type of patches to collect. (default: all)",
        default="all",
    )
    args = parser.parse_args()
    main(**vars(args))
