"""
Purpose: Given the validation logs, create a SWE-bench-style dataset + set of repositories
that can be run with SWE-agent. Each instances is of the form:

{
    "instance_id":
    "repo":
    "base_commit":
    "patch":
    "problem_statement":
    "FAIL_TO_PASS":
    "PASS_TO_PASS":
    "created_at":
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

from datetime import datetime
from dotenv import load_dotenv
from ghapi.all import GhApi
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
    REF_SUFFIX,
)
from swesmith.profiles import global_registry
from tqdm.auto import tqdm

load_dotenv()
api = GhApi(token=os.getenv("GITHUB_TOKEN"))

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


def skip_print(reason, pbar, stats, verbose):
    stats["skipped"] += 1
    pbar.set_postfix(stats)
    if verbose:
        print(f"[SKIP] {reason}")
    pbar.update()
    return stats


def check_if_branch_exists(api, rp, subfolder, main_branch, override_branch, verbose):
    branch_exists = None
    branch_commit = None
    try:
        api.repos.get_branch(rp.org_gh, rp.repo_name, subfolder)
        subprocess.run(
            f"cd {rp.repo_name}; git checkout {subfolder}", **SUBPROCESS_ARGS
        )
        if override_branch:
            # Delete the branch remotely
            subprocess.run(
                f"cd {rp.repo_name}; git push --delete origin {subfolder}",
                **SUBPROCESS_ARGS,
            )
            if verbose:
                print(f"[{subfolder}] Overriding existing branch")
            branch_exists = False
        else:
            branch_commit = (
                subprocess.run(
                    f"cd {rp.repo_name}; git rev-parse HEAD",
                    capture_output=True,
                    **SUBPROCESS_ARGS,
                )
                .stdout.decode()
                .strip()
            )
            branch_exists = True
        subprocess.run(
            f"cd {rp.repo_name}; git checkout {main_branch}", **SUBPROCESS_ARGS
        )
        subprocess.run(
            f"cd {rp.repo_name}; git branch -D {subfolder}", **SUBPROCESS_ARGS
        )
    except Exception:
        branch_exists = False
        pass
    return branch_exists, branch_commit


def _main(
    validation_logs_path: str | Path,
    *,
    debug_subprocess: bool = False,
    override_branch: bool = False,
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
        Path("logs/run_validation").resolve()
    ), "Validation logs should be in logs/run_validation"
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
    if os.path.exists(task_instances_path):
        task_instances = [
            x
            for x in json.load(open(task_instances_path))
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

        results = json.load(open(path_results))
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

        task_instance = {
            KEY_INSTANCE_ID: subfolder,
            KEY_PATCH: open(path_patch).read(),
            FAIL_TO_PASS: results[FAIL_TO_PASS],
            PASS_TO_PASS: results[PASS_TO_PASS],
            "created_at": datetime.now().isoformat(),
        }
        rp = global_registry.get_from_inst(task_instance)
        task_instance[KEY_IMAGE_NAME] = rp.image_name
        task_instance["repo"] = rp.mirror_name

        # Clone repository
        if rp.clone():
            created_repos.add(rp.repo_name)
        main_branch = (
            subprocess.run(
                f"cd {rp.repo_name}; git rev-parse --abbrev-ref HEAD",
                capture_output=True,
                shell=True,
                check=True,
            )
            .stdout.decode()
            .strip()
        )

        # Check if branch already created for this problem
        branch_exists, branch_commit = check_if_branch_exists(
            api, rp.repo_name, subfolder, main_branch, override_branch, verbose
        )
        if branch_exists:
            task_instance["base_commit"] = branch_commit
            task_instances.append(task_instance)
            stats = skip_print(
                f"{subfolder}: Already exists @ branch `{subfolder}` {branch_commit[:8]}",
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
                f"cd {rp.repo_name}; {git_apply} ../{path_patch}",
                capture_output=True,
                shell=True,
            )
            if output.returncode == 0:
                applied = True
                break
            else:
                # Remove any artifacts
                subprocess.run(
                    f"cd {rp.repo_name}; git reset --hard", **SUBPROCESS_ARGS
                )
        if not applied:
            raise Exception(f"[{subfolder}] Failed to apply patch to {rp.repo_name}")
        if verbose:
            print(f"[{subfolder}] Bug patch applied successfully")

        # Create a branch, check it out, commit, push the branch, and cleanup
        cmds = [
            f"cd {rp.repo_name}; git config user.email 'swesmith@swesmith.ai'",
            f"cd {rp.repo_name}; git config user.name 'swesmith'",
            f"cd {rp.repo_name}; git config commit.gpgsign false",
            f"cd {rp.repo_name}; git checkout -b {subfolder}",
            f"cd {rp.repo_name}; git add .",
            f"cd {rp.repo_name}; git commit --no-gpg-sign -m 'Bug Patch'",
            f"cd {rp.repo_name}; git push origin {subfolder}",
            f"cd {rp.repo_name}; git rev-parse HEAD",
            f"cd {rp.repo_name}; git checkout {main_branch}",
            f"cd {rp.repo_name}; git reset --hard",
            f"cd {rp.repo_name}; git branch -D {subfolder}",
        ]
        bug_commit = None
        for cmd in cmds:
            if debug_subprocess:
                print(f"[{subfolder}] Running: {cmd}")
            if cmd.endswith("git rev-parse HEAD"):
                bug_commit = (
                    subprocess.run(cmd, capture_output=True, shell=True, check=True)
                    .stdout.decode()
                    .strip()
                )
            else:
                subprocess.run(cmd, **SUBPROCESS_ARGS)
        if verbose:
            print(f"[{subfolder}] Bug @ branch `{subfolder}` {bug_commit[:8]}")

        task_instance["base_commit"] = bug_commit
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
            print(f"Removed {repo}")

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
        "--override_branch",
        action="store_true",
        help="Override existing branches",
    )
    parser.add_argument(
        "--debug_subprocess",
        action="store_true",
        help="Debug mode (output subprocess output)",
    )
    args = parser.parse_args()

    main(**vars(args))
