"""
Purpose: Given the validation logs, create a SWE-bench-style dataset + set of repositories
that can be run with SWE-agent. Each instances is of the form:

{
    "instance_id":
    "repo":
    "patch":
    "test_patch":
    "problem_statement":
    "FAIL_TO_PASS":
    "PASS_TO_PASS":
    "version":
}

This script will clone the repository, apply the patches and push them to new branches.

IMPORTANT: Make sure you run authenticated git, because else you'll get rate limit issues.

Note: It cannot be strictly SWE-bench. Using SWE-bench styles + infra would be difficult because the
installation specifications are fundamentally different. Therefore, the construction of this
dataset aims for two goals:
* To be runnable in SWE-agent
* To be easy to evaluate with our custom scripts.

Usage: python -m swesmith.harness.gather logs/run_validation/<run_id>
"""

import argparse
import json
import os
import shutil
import subprocess

from pathlib import Path
from swebench.harness.constants import (
    FAIL_TO_PASS,
    PASS_TO_PASS,
    KEY_INSTANCE_ID,
    LOG_REPORT,
)
from swesmith.constants import (
    GIT_APPLY_CMDS,
    KEY_IMAGE_NAME,
    KEY_PATCH,
    KEY_TIMED_OUT,
    LOG_DIR_TASKS,
    LOG_DIR_RUN_VALIDATION,
    REF_SUFFIX,
)
from swesmith.profiles import global_registry
from tqdm.auto import tqdm

FAILURE_TIPS = """
IMPORTANT

1. If this script fails, you might have to remove the repo & reclone it or remove all branches. 
   Else you might get issues during git checkout -o . 
   Because some branches exist locally but not pushed to the remote on GitHub.

2. Make sure you run authenticated git, because else you'll get rate limit issues that are 
   interpreted as non-existent branches. Causing issues similar to 1.
"""

SUBPROCESS_ARGS = {
    "check": True,
    "shell": True,
}


def main(*args, **kwargs):
    """
    Main entry point for the script.
    """
    try:
        _main(*args, **kwargs)
    except Exception:
        print("=" * 80)
        print("=" * 80)
        print(FAILURE_TIPS)
        print("=" * 80)
        print("=" * 80)
        raise


def skip_print(reason: str, pbar: tqdm, stats: dict, verbose: bool):
    stats["skipped"] += 1
    pbar.set_postfix(stats)
    if verbose:
        print(f"[SKIP] {reason}")
    pbar.update()
    return stats


def check_if_branch_exists(
    repo_name: str,
    subfolder: str,
    main_branch: str,
    override_branch: bool,
    verbose: bool,
):
    branch_exists = None
    try:
        subprocess.run(f"git checkout {subfolder}", cwd=repo_name, **SUBPROCESS_ARGS)
        if override_branch:
            # Delete the branch remotely
            subprocess.run(
                f"git push --delete origin {subfolder}",
                cwd=repo_name,
                **SUBPROCESS_ARGS,
            )
            if verbose:
                print(f"[{subfolder}] Overriding existing branch")
            branch_exists = False
        else:
            branch_exists = True
        subprocess.run(f"git checkout {main_branch}", cwd=repo_name, **SUBPROCESS_ARGS)
        subprocess.run(f"git branch -D {subfolder}", cwd=repo_name, **SUBPROCESS_ARGS)
    except Exception:
        branch_exists = False
        pass
    return branch_exists


def _main(
    validation_logs_path: str | Path,
    *,
    debug_subprocess: bool = False,
    override_branch: bool = False,
    repush_image: bool = False,
    verbose: bool = False,
):
    """
    Create a SWE-bench-style dataset from the validation logs.

    Args:
        validation_logs_path: Path to the validation logs
        debug_subprocess: Whether to output subprocess output
    """
    if not debug_subprocess:
        SUBPROCESS_ARGS["stdout"] = subprocess.DEVNULL
        SUBPROCESS_ARGS["stderr"] = subprocess.DEVNULL

    validation_logs_path = Path(validation_logs_path)
    assert validation_logs_path.resolve().is_relative_to(
        LOG_DIR_RUN_VALIDATION.resolve()
    ), f"Validation logs should be in {LOG_DIR_RUN_VALIDATION}"
    assert validation_logs_path.exists(), (
        f"Validation logs path {validation_logs_path} does not exist"
    )
    assert validation_logs_path.is_dir(), (
        f"Validation logs path {validation_logs_path} is not a directory"
    )

    run_id = validation_logs_path.name
    print(f"{run_id=}")
    task_instances_path = LOG_DIR_TASKS / f"{run_id}.json"
    print(f"Out Path: {task_instances_path}")
    task_instances = []
    created_repos = set()

    completed_ids = []
    subfolders = os.listdir(validation_logs_path)
    if not override_branch and os.path.exists(task_instances_path):
        with open(task_instances_path) as f:
            task_instances = [
                x
                for x in json.load(f)
                if x[KEY_INSTANCE_ID] in subfolders  # Omits removed bugs
            ]
        completed_ids = [x[KEY_INSTANCE_ID] for x in task_instances]
        print(f"Found {len(task_instances)} existing task instances")
        subfolders = [x for x in subfolders if x not in completed_ids]

    stats = {"new_tasks": 0, "skipped": 0}
    print(f"Will process {len(subfolders)} instances")
    pbar = tqdm(subfolders, desc="Conversion", disable=verbose)
    for subfolder in sorted(subfolders):
        if subfolder.endswith(REF_SUFFIX) or subfolder in completed_ids:
            # Skip reference run or instances that have been completed
            stats = skip_print(f"{subfolder}: Reference", pbar, stats, verbose)
            continue

        path_results = os.path.join(validation_logs_path, subfolder, LOG_REPORT)
        path_patch = os.path.join(validation_logs_path, subfolder, "patch.diff")

        if not os.path.exists(path_results):
            stats = skip_print(f"{subfolder}: No results", pbar, stats, verbose)
            continue

        with open(path_results) as f:
            results = json.load(f)
        if FAIL_TO_PASS not in results or PASS_TO_PASS not in results:
            stats = skip_print(
                f"{subfolder}: No validatable bugs", pbar, stats, verbose
            )
            continue

        n_f2p = len(results[FAIL_TO_PASS])
        n_p2p = len(results[PASS_TO_PASS])
        pr_exception = (
            ".pr_" in subfolder and n_p2p == 0 and n_f2p > 0
        )  # TODO: Better way to determine if it's a PR miror?
        if not pr_exception and (KEY_TIMED_OUT in results or n_f2p == 0 or n_p2p == 0):
            # Skip instances that timed out OR don't have F2P or P2P
            stats = skip_print(
                f"{subfolder}: No validatable bugs: {n_f2p=}, {n_p2p=}",
                pbar,
                stats,
                verbose,
            )
            continue

        with open(path_patch) as f:
            patch_content = f.read()
        task_instance = {
            KEY_INSTANCE_ID: subfolder,
            KEY_PATCH: patch_content,
            FAIL_TO_PASS: results[FAIL_TO_PASS],
            PASS_TO_PASS: results[PASS_TO_PASS],
        }
        rp = global_registry.get_from_inst(task_instance)
        task_instance[KEY_IMAGE_NAME] = rp.image_name
        task_instance["repo"] = rp.mirror_name

        # Clone repository
        _, cloned = rp.clone()
        if cloned:
            created_repos.add(rp.repo_name)
        main_branch = (
            subprocess.run(
                "git rev-parse --abbrev-ref HEAD",
                cwd=rp.repo_name,
                capture_output=True,
                shell=True,
                check=True,
            )
            .stdout.decode()
            .strip()
        )

        # Check if branch already created for this problem
        branch_exists = check_if_branch_exists(
            rp.repo_name, subfolder, main_branch, override_branch, verbose
        )
        if branch_exists:
            task_instances.append(task_instance)
            stats = skip_print(
                f"{subfolder}: Branch `{subfolder}` exists",
                pbar,
                stats,
                verbose,
            )
            continue
        elif verbose:
            print(f"[{subfolder}] Does not exist yet")

        # Apply patch
        applied = False
        for git_apply in GIT_APPLY_CMDS:
            output = subprocess.run(
                f"{git_apply} ../{path_patch}",
                cwd=rp.repo_name,
                capture_output=True,
                shell=True,
            )
            if output.returncode == 0:
                applied = True
                break
            else:
                # Remove any artifacts
                subprocess.run("git reset --hard", cwd=rp.repo_name, **SUBPROCESS_ARGS)
        if not applied:
            raise Exception(f"[{subfolder}] Failed to apply patch to {rp.repo_name}")
        if verbose:
            print(f"[{subfolder}] Bug patch applied successfully")

        # Create a branch, check it out, commit, push the branch, and cleanup
        cmds = [
            "git config user.email 'swesmith@swesmith.ai'",
            "git config user.name 'swesmith'",
            "git config commit.gpgsign false",
            f"git checkout -b {subfolder}",
            "git add .",
            "git commit --no-gpg-sign -m 'Bug Patch'",
        ]
        for cmd in cmds:
            if debug_subprocess:
                print(f"[{subfolder}] {cmd}")
            subprocess.run(cmd, cwd=rp.repo_name, **SUBPROCESS_ARGS)

        # Create test patch by removing F2P test files
        f2p_test_files, _ = rp.get_test_files(task_instance)
        if f2p_test_files:
            # Remove the test files
            for test_file in f2p_test_files:
                test_file_path = os.path.join(rp.repo_name, test_file)
                if os.path.exists(test_file_path):
                    os.remove(test_file_path)
                    if verbose:
                        print(f"[{subfolder}] Removed F2P test file: {test_file}")

            # Add and commit removal
            cmds = [
                "git add .",
                "git commit --no-gpg-sign -m 'Remove F2P Tests'",
            ]
            for cmd in cmds:
                if debug_subprocess:
                    print(f"[{subfolder}] {cmd}")
                subprocess.run(cmd, cwd=rp.repo_name, **SUBPROCESS_ARGS)
            if verbose:
                print(f"[{subfolder}] Commit F2P test file(s) removal")
        elif verbose:
            print(f"[{subfolder}] No test files to remove")

        cmds = [
            f"git push origin {subfolder}",
            f"git checkout {main_branch}",
            "git reset --hard",
            f"git branch -D {subfolder}",
        ]
        for cmd in cmds:
            if debug_subprocess:
                print(f"[{subfolder}] {cmd}")
            subprocess.run(cmd, cwd=rp.repo_name, **SUBPROCESS_ARGS)
        if verbose:
            print(f"[{subfolder}] Bug @ branch `{subfolder}`")

        task_instances.append(task_instance)
        if verbose:
            print(f"[{subfolder}] Created task instance")
        stats["new_tasks"] += 1
        pbar.update()

    pbar.close()
    if len(created_repos) > 0:
        print("Cleaning up...")
        for repo in created_repos:
            shutil.rmtree(repo)
            print(f"[{repo}] Removed local clone")
            if repush_image:
                print(f"[{repo}] Rebuilding + pushing image")
                global_registry.get(repo).push_image(rebuild_image=True)

    task_instances_path.parent.mkdir(parents=True, exist_ok=True)
    with open(task_instances_path, "w") as f:
        json.dump(task_instances, f, indent=4)
    print(f"Wrote {len(task_instances)} instances to {task_instances_path}")
    print(f"- {stats['skipped']} skipped")
    print(f"- {stats['new_tasks']} new instances")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert validation logs to SWE-bench style dataset"
    )
    parser.add_argument(
        "validation_logs_path", type=str, help="Path to the validation logs"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose mode",
    )
    # Override branch takes effect when
    # - A branch for the bug already exists
    # - But the local version of the bug (in logs/run_validation) has been modified (out of sync with the branch)
    # In this case, we delete the branch and recreate the bug.
    # This is useful for if you've regenerated a bug, it's validated, and you'd like to override the existing branch.
    parser.add_argument(
        "-o",
        "--override_branch",
        action="store_true",
        help="Override existing branches",
    )
    parser.add_argument(
        "-d",
        "--debug_subprocess",
        action="store_true",
        help="Debug mode (output subprocess output)",
    )
    parser.add_argument(
        "-p",
        "--repush_image",
        action="store_true",
        help="Rebuild and push Docker image for repos (such that latest branches are included)",
    )
    args = parser.parse_args()

    main(**vars(args))
