"""
Purpose: Transform a bunch of patches that cause bugs into a SWE-bench style dataset.

Usage: python -m swesmith.harness.valid logs/bug_gen/*_patches.json --workers #
"""

import argparse
import json
import os
import shutil

from collections import defaultdict
from pathlib import Path
from swebench.harness.constants import (
    KEY_INSTANCE_ID,
    KEY_PREDICTION,
    FAIL_TO_PASS,
    LOG_REPORT,
    LOG_TEST_OUTPUT,
)
from swebench.harness.docker_build import close_logger
from swebench.harness.utils import run_threadpool
from swesmith.constants import (
    KEY_PATCH,
    KEY_TIMED_OUT,
    LOG_TEST_OUTPUT_PRE_GOLD,
    REF_SUFFIX,
    LOG_DIR_RUN_VALIDATION,
)
from swesmith.harness.grading import get_valid_report
from swesmith.harness.utils import run_patch_in_container
from swesmith.profiles import global_registry


def print_report(log_dir: Path) -> None:
    time_outs, f2p_none, f2p_some, other = 0, 0, 0, 0
    for folder in os.listdir(log_dir):
        if LOG_REPORT in os.listdir(log_dir / folder):
            with open(log_dir / folder / LOG_REPORT, "r") as f:
                report = json.load(f)
            if KEY_TIMED_OUT in report:
                time_outs += 1
            elif len(report[FAIL_TO_PASS]) > 0:
                f2p_some += 1
            elif len(report[FAIL_TO_PASS]) == 0:
                f2p_none += 1
            else:
                other += 1
    print(f"Total instances: {len(os.listdir(log_dir))}")
    print(f"- Timed out: {time_outs}")
    print(f"- Fail to pass: 0 ({f2p_none}); 1+ ({f2p_some})")
    print(f"- Other: {other}")


def run_validation(instance: dict) -> None:
    """
    Run per-instance validation. Steps are generally:
    1. Run the patch on the instance.
    2. Get the report from the test output.
    """
    instance_id = instance[KEY_INSTANCE_ID]
    rp = global_registry.get_from_inst(instance)
    valid_folder = LOG_DIR_RUN_VALIDATION / instance["repo"]
    val_postgold_path = (
        valid_folder / f"{instance['repo']}{REF_SUFFIX}" / LOG_TEST_OUTPUT
    )
    report_path = valid_folder / instance_id / LOG_REPORT

    if rp.min_pregold:
        ref_inst_id = f"{instance[KEY_INSTANCE_ID]}{REF_SUFFIX}"
        logger, timed_out = run_patch_in_container(
            {**instance, KEY_INSTANCE_ID: ref_inst_id},
            instance["repo"],
            LOG_DIR_RUN_VALIDATION,
            rp.timeout,
        )
        close_logger(logger)
        if timed_out:
            logger.info(f"Timed out (pre-gold) for {instance_id}.")
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, "w") as f:
                f.write(
                    json.dumps({KEY_TIMED_OUT: True, "timeout": rp.timeout}, indent=4)
                )
            shutil.rmtree(valid_folder / ref_inst_id)
            return

        # Copy pre-gold test output to the post-gold folder and remove the pre-gold folder
        val_postgold_path = valid_folder / instance_id / LOG_TEST_OUTPUT_PRE_GOLD
        val_postgold_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(
            valid_folder / ref_inst_id / LOG_TEST_OUTPUT,
            val_postgold_path,
        )
        shutil.rmtree(valid_folder / ref_inst_id)

    logger, timed_out = run_patch_in_container(
        instance,
        instance["repo"],
        LOG_DIR_RUN_VALIDATION,
        rp.timeout,
        patch=instance[KEY_PATCH],
    )

    if timed_out:
        logger.info(f"Timed out for {instance_id}.")
        with open(report_path, "w") as f:
            f.write(json.dumps({KEY_TIMED_OUT: True, "timeout": rp.timeout}, indent=4))
        close_logger(logger)
        return

    val_pregold_path = valid_folder / instance_id / LOG_TEST_OUTPUT
    if not val_pregold_path.exists():
        logger.info(f"Pre-gold for {instance_id} failed to run. Exiting early.")
        with open(report_path, "w") as f:
            f.write(
                json.dumps(
                    {KEY_TIMED_OUT: True, "missing_pregold_output": True}, indent=4
                )
            )
        close_logger(logger)
        return

    # Get report from test output
    logger.info(f"Grading answer for {instance_id}...")
    report = get_valid_report(
        val_pregold_path=val_pregold_path,
        val_postgold_path=val_postgold_path,
        instance=instance,
    )
    logger.info(f"Report: {json.dumps(report)}")

    # Write report to report.json
    with open(report_path, "w") as f:
        f.write(json.dumps(report, indent=4))
    close_logger(logger)


def main(
    bug_patches: str,
    workers: int,
    redo_existing: bool = False,
) -> None:
    # Bug patch should be a dict that looks like this:
    # {
    #     "instance_id": <instance_id>,
    #     "patch" / "model_patch": <bug inducing patch>,
    #     "repo": <mirror repo name>,
    # }
    print(f"Running validation for {bug_patches}...")
    with open(bug_patches, "r") as f:
        bug_patches = json.load(f)
    bug_patches = [
        {
            **x,
            KEY_PATCH: x.get(KEY_PATCH, x.get(KEY_PREDICTION)),
        }
        for x in bug_patches
    ]
    print(f"Found {len(bug_patches)} candidate patches.")

    completed = []
    for repo in set([bp["repo"] for bp in bug_patches]):
        log_dir_parent = LOG_DIR_RUN_VALIDATION / repo
        log_dir_parent.mkdir(parents=True, exist_ok=True)
        if not redo_existing and log_dir_parent.exists():
            for folder in os.listdir(log_dir_parent):
                # Identify completed instances (does report.json exist)
                log_report_path = log_dir_parent / folder / LOG_REPORT
                if log_report_path.exists():
                    completed.append(folder)
    if len(completed) > 0:
        print(f"Skipping {len(completed)} instances... (--redo_existing to not skip)")
        bug_patches = [x for x in bug_patches if x[KEY_INSTANCE_ID] not in completed]

    # Group patches by image_name:
    repo_to_bug_patches = defaultdict(list)
    for bp in bug_patches:
        repo_to_bug_patches[bp["repo"]].append(bp)

    # Log
    if len(repo_to_bug_patches) == 0:
        print("No patches to run.")
        print_report(log_dir_parent)
        return
    print("Will run validation for these images:")
    for repo, patches in repo_to_bug_patches.items():
        print(f"- {repo}: {len(patches)} patches")

    # Run validation
    payloads = list()
    for repo, bug_patches in repo_to_bug_patches.items():
        rp = global_registry.get(repo)
        ref_inst = f"{rp.repo_name}{REF_SUFFIX}"
        ref_dir = LOG_DIR_RUN_VALIDATION / repo / ref_inst
        if not rp.min_pregold and not os.path.exists(ref_dir):
            # Run pytest for each repo/commit to get pre-gold behavior.
            print(f"Running pre-gold for {repo}...")
            logger, timed_out = run_patch_in_container(
                {KEY_INSTANCE_ID: ref_inst},
                repo,
                LOG_DIR_RUN_VALIDATION,
                rp.timeout_ref,
            )
            close_logger(logger)
            if timed_out:
                # If timed out, skip this repo/commit (remove log directory)
                print(
                    f"Timed out for {repo}, not running validation. (Increase --timeout?)"
                )
                shutil.rmtree(ref_dir)
                continue

        # Add payloads
        for bug_patch in bug_patches:
            payloads.append((bug_patch,))

    run_threadpool(run_validation, payloads, workers)
    print("All instances run.")
    print_report(log_dir_parent)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transform a bunch of patches that cause bugs into a SWE-bench style dataset."
    )
    parser.add_argument(
        "bug_patches",
        type=str,
        help="Json file containing bug patches.",
    )
    parser.add_argument(
        "-w", "--workers", type=int, default=4, help="Number of workers to use."
    )
    parser.add_argument(
        "--redo_existing",
        action="store_true",
        help="Redo completed validation instances.",
    )
    args = parser.parse_args()
    main(**vars(args))
