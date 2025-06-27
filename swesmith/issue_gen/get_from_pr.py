"""
Purpose: Given a bug patch, retrieve the issue text from the PR that the bug was created from.

python swesmith/issue_gen/get_from_pr.py logs/experiments/*.json
"""

import argparse
import json

from pathlib import Path
from swesmith.constants import LOG_DIR_BUG_GEN
from swesmith.bug_gen.mirror.generate import INSTANCE_REF, MIRROR_PR
from tqdm.auto import tqdm


def transform_to_sweb_inst_id(inst):
    repo = inst["repo"].split("/", 1)[-1].rsplit(".", 1)[0]
    pr_num = inst["instance_id"].rsplit("_", 1)[-1]
    return f"{repo}-{pr_num}"


def get_original_ps_from_pr(instance, log_dir_bug_gen=LOG_DIR_BUG_GEN):
    log_dir_bug_gen = Path(log_dir_bug_gen)
    sweb_inst_id = transform_to_sweb_inst_id(instance)
    pr_num = sweb_inst_id.rsplit("-", 1)[-1]
    metadata_path = (
        log_dir_bug_gen
        / instance["repo"].split("/")[-1]
        / MIRROR_PR
        / sweb_inst_id
        / f"metadata__pr_{pr_num}.json"
    )
    if not metadata_path.exists():
        return ""
    metadata = json.load(open(metadata_path, "r"))
    if INSTANCE_REF not in metadata:
        return ""
    ps = metadata[INSTANCE_REF]["problem_statement"]
    return ps


def main(dataset_path: str):
    dataset_path = Path(dataset_path)

    # Load bug dataset
    dataset = json.load(open(dataset_path, "r"))
    print(f"Found {len(dataset)} task instances to generate instructions for")
    kept = []
    for instance in tqdm(dataset):
        ps = get_original_ps_from_pr(instance)
        if len(ps.strip()) > 0:
            instance["problem_statement"] = ps
            kept.append(instance)
    print(
        f"{len(kept)} instances have problem statements ({len(dataset) - len(kept)} missing)"
    )

    if len(kept) > 0:
        # Create .json version of the dataset
        output_path = dataset_path.parent / f"{dataset_path.stem}__ig_orig.json"
        with open(output_path, "w") as f:
            json.dump(kept, f, indent=2)
        print(f"Wrote dataset with original problem statements to {output_path}")
    else:
        print("No instances found with original problem statements.")


def get_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "dataset_path",
        type=str,
        help="Path to the dataset",
    )
    return parser


def run_from_cli(args: list[str] | None = None) -> None:
    cli_parser = get_cli_parser()
    cli_args = cli_parser.parse_args(args)
    main(**vars(cli_args))


if __name__ == "__main__":
    run_from_cli()
