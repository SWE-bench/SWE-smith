"""
Purpose: Given a run_evaluation log, repair task instances with flaky tests. Specifically, given a log
generated with:

python swesmith/harness/eval.py -d logs/task_insts/*.json -p gold --run_id <run_id>

This script will take the `logs/run_evaluation/<run_id>` artifact and, for each task instance,
make edits to the following:
* `logs/run_validation/<repo>/<instance_id>`
* `logs/task_insts/*.json`

Specifically, the logic for each instance that will be carried out is as follows:

Tests that are found under
* report["tests_status"]["FAIL_TO_PASS"]["failure"]
* report["tests_status"]["PASS_TO_PASS"]["failure"]
will be remove from the "FAIL_TO_PASS" and "PASS_TO_PASS" fields correspond to the `instance_id` assets
under the aforementioned folders.

If the removal of these tests leads to a instance having an empty FAIL_TO_PASS field, then the instance should
be deleted all together. This implies:
* `rm -r logs/run_validation/<repo>/<instance_id>`
* removal of item from `logs/task_insts/*.json`
"""

import argparse
import json
import subprocess
from pathlib import Path
from swebench.harness.constants import (
    FAIL_TO_PASS,
    PASS_TO_PASS,
    KEY_INSTANCE_ID,
    LOG_REPORT,
)
from swesmith.constants import KEY_TIMED_OUT, LOG_DIR_RUN_VALIDATION, LOG_DIR_TASKS
from swesmith.profiles import global_registry
from tqdm.auto import tqdm


def _remove_task_instance(
    repo: str,
    inst_id: str,
    validation_path: Path,
    task_insts_file,
    task_insts_cache: dict,
) -> bool:
    """
    Remove a task instance from both logs/run_validation and logs/task_insts.
    This is a helper function to avoid code duplication.
    """
    removed_valid, removed_task, removed_branch = False, False, False
    # 1. Remove from logs/run_validation
    if validation_path.exists():
        subprocess.run(["rm", "-rf", str(validation_path)], check=True)
        removed_valid = True
    # 2. Remove from logs/task_insts
    if repo not in task_insts_cache:
        with open(task_insts_file, "r") as f:
            task_insts_cache[repo] = {x[KEY_INSTANCE_ID]: x for x in json.load(f)}
    if inst_id in task_insts_cache[repo]:
        del task_insts_cache[repo][inst_id]
        removed_task = True
    # 3. Optionally, delete branch from remote if exists
    rp = global_registry.get_from_repo(repo)
    try:
        subprocess.run(
            f"git push --delete origin {inst_id}",
            cwd=rp.repo_name,
            shell=True,
            check=True,
        )
        removed_branch = True
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Warning: Failed to delete branch {inst_id} from remote: {e}")
    return removed_valid, removed_task, removed_branch


def main(
    eval_logs: list[str],
    logs_validation: Path,
    logs_task_insts: Path,
    dry_run: bool = False,
):
    task_insts_cache = {}
    total_deleted_timeout, total_deleted, total_modified, total_kept = 0, 0, 0, 0

    if dry_run:
        print(
            "🔍 DRY RUN MODE: No changes will be made, only showing what would happen"
        )
    cloned_repos = set()
    for eval_log in eval_logs:
        with open(Path(eval_log) / LOG_REPORT, "r") as f:
            eval_report = json.load(f)
        unresolved = eval_report["ids_unresolved"]
        print(f"Found {len(unresolved)} unresolved instances in {eval_log}")

        if not dry_run:
            print(
                f"⚠️ This will modify logs under {logs_validation} and {logs_task_insts}"
            )
            if input("Continue? [y/N] ") != "y":
                print("Aborting.")
                return

        for inst_id in tqdm(unresolved):
            repo = inst_id.rsplit(".", 1)[0]
            validation_path = logs_validation / repo / inst_id
            task_insts_file = logs_task_insts / f"{repo}.json"
            rp = global_registry.get_from_repo(repo)
            _, cloned = rp.clone()
            if cloned:
                cloned_repos.add(repo)

            with open(Path(eval_log) / inst_id / LOG_REPORT, "r") as f:
                report = json.load(f)

            if report.get(KEY_TIMED_OUT, False):
                if not dry_run:
                    removed_valid, removed_task, removed_branch = _remove_task_instance(
                        repo,
                        inst_id,
                        validation_path,
                        task_insts_file,
                        task_insts_cache,
                    )
                    if removed_valid or removed_task or removed_branch:
                        total_deleted_timeout += 1
                else:
                    # In dry run, count all timeout instances as would-be-deleted
                    total_deleted_timeout += 1
                continue

            f2p_fails = report["tests_status"][FAIL_TO_PASS]["failure"]
            p2p_fails = report["tests_status"][PASS_TO_PASS]["failure"]
            f2p_passes = report["tests_status"][FAIL_TO_PASS]["success"]

            if len(f2p_fails) == 0 and len(p2p_fails) == 0:
                # Nothing to do for this instance
                total_kept += 1
                continue

            if len(f2p_passes) == 0:
                # This instance is irreparably broken, remove it
                if not dry_run:
                    removed_valid, removed_task, removed_branch = _remove_task_instance(
                        repo,
                        inst_id,
                        validation_path,
                        task_insts_file,
                        task_insts_cache,
                    )
                    if removed_valid or removed_task or removed_branch:
                        total_deleted += 1
                else:
                    # In dry run, count as would-be-deleted and load cache for simulation
                    total_deleted += 1
                    if repo not in task_insts_cache:
                        try:
                            with open(task_insts_file, "r") as f:
                                task_insts_cache[repo] = {
                                    x[KEY_INSTANCE_ID]: x for x in json.load(f)
                                }
                        except FileNotFoundError:
                            print(
                                f"⚠️ Warning: Task insts file not found: {task_insts_file}"
                            )
                            task_insts_cache[repo] = {}
                continue

            # Keep instance, but remove the failing tests
            # 1. Update logs/run_validation
            if not validation_path.exists():
                print(
                    f"⚠️ Warning: Validation path does not exist for {inst_id}: {validation_path}"
                )
                total_kept += 1
                continue

            with open(validation_path / LOG_REPORT, "r") as f:
                val_report = json.load(f)
            new_f2p = [x for x in val_report[FAIL_TO_PASS] if x not in f2p_fails]
            assert len(new_f2p) > 0, (
                f"Instance {inst_id} should have some FAIL_TO_PASS tests after removing failures"
            )
            new_p2p = [x for x in val_report[PASS_TO_PASS] if x not in p2p_fails]

            if not dry_run:
                if (
                    val_report[FAIL_TO_PASS] == new_f2p
                    and val_report[PASS_TO_PASS] == new_p2p
                ):
                    # No changes needed
                    total_kept += 1
                    continue
                val_report[FAIL_TO_PASS] = new_f2p
                val_report[PASS_TO_PASS] = new_p2p
                with open(validation_path / LOG_REPORT, "w") as f:
                    json.dump(val_report, f, indent=2)
                # 2. Update logs/task_insts
                if repo not in task_insts_cache:
                    with open(task_insts_file, "r") as f:
                        task_insts_cache[repo] = {
                            x[KEY_INSTANCE_ID]: x for x in json.load(f)
                        }
                if inst_id in task_insts_cache[repo]:
                    inst = task_insts_cache[repo][inst_id]
                    inst[FAIL_TO_PASS] = new_f2p
                    inst[PASS_TO_PASS] = new_p2p
                    task_insts_cache[repo][inst_id] = inst
                total_modified += 1
            else:
                # Dry run: Load cache for simulation and count as modified
                if repo not in task_insts_cache:
                    try:
                        with open(task_insts_file, "r") as f:
                            task_insts_cache[repo] = {
                                x[KEY_INSTANCE_ID]: x for x in json.load(f)
                            }
                    except FileNotFoundError:
                        print(
                            f"⚠️ Warning: Task insts file not found: {task_insts_file}"
                        )
                        task_insts_cache[repo] = {}
                total_modified += 1

    # Write all updated task instances back to files
    if not dry_run:
        for repo, insts_dict in task_insts_cache.items():
            task_insts_file = logs_task_insts / f"{repo}.json"
            with open(task_insts_file, "w") as f:
                json.dump(list(insts_dict.values()), f, indent=2)
    else:
        print(f"\n[DRY RUN] Would write updates to {len(task_insts_cache)} repo files:")
        for repo in task_insts_cache.keys():
            task_insts_file = logs_task_insts / f"{repo}.json"
            print(f"[DRY RUN] - {task_insts_file}")

    print("\n=== SUMMARY ===")
    if dry_run:
        print("🔍 DRY RUN MODE - No actual changes were made")
    print(
        f"Total instances processed: {total_deleted_timeout + total_deleted + total_modified + total_kept}\n"
        f"- {'Would delete (Timeout)' if dry_run else 'Deleted'} (timeout): {total_deleted_timeout}\n"
        f"- {'Would delete (No F2P)' if dry_run else 'Deleted'} (no F2P passes): {total_deleted}\n"
        f"- {'Would modify' if dry_run else 'Modified'}: {total_modified}\n"
        f"- Kept unchanged: {total_kept}"
    )

    # Cleanup cloned repos
    for repo in cloned_repos:
        subprocess.run(["rm", "-rf", repo], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Repair task instances with flaky tests using run_evaluation logs."
    )
    parser.add_argument(
        "eval_logs",
        type=str,
        nargs="+",
        help="Path(s) to run_evaluation log files (JSON).",
    )
    parser.add_argument("--logs_validation", type=Path, default=LOG_DIR_RUN_VALIDATION)
    parser.add_argument("--logs_task_insts", type=Path, default=LOG_DIR_TASKS)
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Show what would be done without making any changes",
    )
    args = parser.parse_args()
    # Convert dry-run to dry_run for function call
    main(
        eval_logs=args.eval_logs,
        logs_validation=args.logs_validation,
        logs_task_insts=args.logs_task_insts,
        dry_run=args.dry_run,
    )
