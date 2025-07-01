"""
Purpose: Determine the total cost of LLM generated bugs (bug__func*.json) for a given repository.

Usage: python -m swesmith.bug_gen.get_cost logs/bug_gen/<repo>
"""

import argparse
import json
import os


def main(repo_path: str, bug_type: str) -> tuple[float, int, float]:
    total_cost = 0.0
    total_bugs = 0
    prefix = "metadata__"
    if bug_type != "all":
        prefix += f"{bug_type}"
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.startswith(prefix) and file.endswith(".json"):
                with open(os.path.join(root, file), "r") as f:
                    data = json.load(f)
                    if "cost" in data:
                        total_cost += data["cost"]
                        total_bugs += 1
    per_instance = total_cost / total_bugs if total_bugs > 0 else 0
    return total_cost, total_bugs, per_instance


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Determine the total cost of generating bugs for a given repository."
    )
    parser.add_argument("repo_path", help="Path to the bug_gen logs.")
    parser.add_argument(
        "--type",
        dest="bug_type",
        type=str,
        help="Type of patches to collect. (default: all)",
        default="all",
    )
    args = parser.parse_args()
    print(main(**vars(args)))
