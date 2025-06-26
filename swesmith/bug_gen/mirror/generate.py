"""
Purpose: Given a pull request, mirror the bug in the current form of the repository.

Usage: python -m swesmith.bug_gen.mirror.main \
    /path/to/swe-bench-task-instances.json
"""

import argparse
import json
import litellm
import logging
import os
import re
import shutil
import uuid
import traceback
import signal

from concurrent.futures import ProcessPoolExecutor, as_completed
from dotenv import load_dotenv
from litellm import completion, completion_cost
from multiprocessing import current_process
from swebench.harness.constants import KEY_INSTANCE_ID
from swesmith.bug_gen.utils import (
    apply_patches,
    get_patch,
)
from swesmith.bug_gen.mirror.prompts import (
    DEMO_PROMPT,
    RECOVERY_PROMPT,
    TASK_PROMPT,
)
from swesmith.constants import (
    LOG_DIR_BUG_GEN,
    KEY_PATCH,
    PREFIX_BUG,
    PREFIX_METADATA,
    INSTANCE_REF,
)
from swesmith.profiles import global_registry, RepoProfile
from tqdm.auto import tqdm
from unidiff import PatchSet

load_dotenv()
litellm.drop_params = True

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logging.getLogger("LiteLLM").setLevel(logging.WARNING)
litellm.suppress_debug_info = True

MIRROR_PR = "pr_mirror"
KEY_COST = "cost"
KEY_PULL_NUM = "pull_number"
KEY_RECOVER_STATUS = "recover_status"
KEY_REWRITES = "rewrites"
KEY_SKIP_REASON = "skip_reason"
RECOVER_FAIL = "failed"
RECOVER_SKIPPED = "skipped"
RECOVER_SUCCESS = "success"


def get_metadata_file_name(pr_num):
    return f"{PREFIX_METADATA}__pr_{pr_num}.json"


worker_tempdirs = {}


def should_attempt_recovery(inst, repo):
    """
    Attempt if the following criteria are met:
    * Fewer than 8 files are changed
    * Fewer than 500 lines are changed
    * No changed file is >1000 lines
    """
    patch = PatchSet(inst[KEY_PATCH])
    num_py_edited = len([x for x in patch if x.path.endswith(".py")])
    if num_py_edited == 0:
        return False, "No Python files changed"
    if num_py_edited > 8:
        return False, "Too many files changed (>8 files)"
    lines_changed = 0
    for file_diff in patch:
        if file_diff.is_binary_file:
            return False, "Contains binary file"
        file_path = os.path.join(repo, file_diff.path)
        if not os.path.exists(file_path):
            # Skip over edits to files that don't exist
            continue
        file_content = open(file_path).read()
        if len(file_content.splitlines()) > 1000:
            return False, "Changed file is too long (>1000 lines)"
        lines_changed += file_diff.added + file_diff.removed
    if lines_changed == 0:
        return False, "No lines changed (no changed file exists)"
    if lines_changed > 500:
        return False, "Too many lines changed"
    return True, None


def recover_sweb_inst(inst, repo, model, api_key=None, log_path=None):
    """
    Given a pull request, mirror the bug in the current form of the repository.

    Args:
        inst: The instance to mirror.
        repo: The repository to mirror the bug in.
        model: The model to use for bug generation.
    Returns:
        A list of patch files.
    """
    patch_files = []
    patch = PatchSet(inst[KEY_PATCH])

    def extract_output(output):
        code_block_pat = re.compile(r"^```python\s*\n([\s\S]*)^```\s*$", re.MULTILINE)
        if code_block_pat.search(output):
            output = output.split("```python", 1)[1]
            output = output.rsplit("```", 1)[0]
            output = output.strip()
            output = code_block_pat.sub("", output)
        return output

    metadata = {KEY_COST: 0, KEY_REWRITES: {}, KEY_RECOVER_STATUS: RECOVER_SUCCESS}
    for idx, file_diff in enumerate(patch):
        file_path = os.path.join(repo, file_diff.path)

        if file_diff.is_added_file and os.path.exists(file_path):
            os.remove(file_path)
            patch = get_patch(repo, reset_changes=True)
            if patch:
                patch_path = f"{inst[KEY_INSTANCE_ID]}_{idx}.diff"
                with open(patch_path, "w") as f:
                    f.write(patch)
                patch_files.append(patch_path)
            continue
        elif file_diff.is_removed_file:
            if not os.path.exists(os.path.dirname(file_path)):
                # Skip over re-adding removed file if the parent directory doesn't exist
                continue
            with open(file_path, "w") as f:
                # Write the removed lines to the file
                f.write(
                    "".join(
                        line.value
                        for hunk in file_diff
                        for line in hunk
                        if line.is_removed
                    )
                )
            patch = get_patch(repo, reset_changes=True)
            if patch:
                patch_path = f"{inst[KEY_INSTANCE_ID]}_{idx}.diff"
                with open(patch_path, "w") as f:
                    f.write(patch)
                patch_files.append(patch_path)
            continue

        if not os.path.exists(file_path) or not file_path.endswith(".py"):
            # Skip over edits to files that don't exist or are not Python files
            continue
        file_content = open(file_path).read()

        # Call llm generation
        response = completion(
            model=model,
            messages=[
                {"role": "user", "content": RECOVERY_PROMPT},
                {"role": "user", "content": DEMO_PROMPT},
                {
                    "role": "user",
                    "content": TASK_PROMPT.format(file_content, str(file_diff)),
                },
            ],
            n=1,
            temperature=0,
            api_key=api_key,
        )

        # Perform rewrite
        cost = completion_cost(completion_response=response)
        metadata[KEY_COST] += cost
        metadata[INSTANCE_REF] = inst
        output = response.choices[0].message.content.strip()  # type: ignore
        output_extracted = extract_output(output)
        metadata[KEY_REWRITES][file_path] = {
            "output": output,
            "output_extracted": output_extracted,
            KEY_COST: cost,
        }
        with open(file_path, "w") as f:
            f.write(output_extracted)

        # Get patch from codebase
        try:
            patch = get_patch(repo, reset_changes=True)
            if not patch:
                raise ValueError("Patch is empty")
            patch_path = f"{inst[KEY_INSTANCE_ID]}_{idx}.diff"
            with open(patch_path, "w") as f:
                f.write(patch)
            patch_files.append(patch_path)
        except Exception as e:
            logger.error(f"Failed to get patch: {e}")
            continue

    # Save logs
    if log_path is None:
        log_path = LOG_DIR_BUG_GEN / repo / MIRROR_PR / inst[KEY_INSTANCE_ID]
    metadata_file = log_path / get_metadata_file_name(inst[KEY_PULL_NUM])
    ref_patch_file = log_path / f"ref__pr_{inst[KEY_PULL_NUM]}.diff"
    with open(metadata_file, "w") as f:
        if len(patch_files) == 0:
            metadata[KEY_RECOVER_STATUS] = RECOVER_FAIL
        json.dump(metadata, f, indent=4)
    with open(ref_patch_file, "w") as f:
        f.write(inst[KEY_PATCH])

    return patch_files


def should_process_instance(inst, repo, redo_existing, redo_skipped):
    """
    Determine if an instance should be processed based on existing metadata.
    """
    log_path = LOG_DIR_BUG_GEN / repo / MIRROR_PR / inst[KEY_INSTANCE_ID]
    metadata_file = log_path / get_metadata_file_name(inst[KEY_PULL_NUM])

    if not os.path.exists(metadata_file):
        return True, None

    metadata = json.load(open(metadata_file))
    recover_status = metadata[KEY_RECOVER_STATUS]

    if redo_existing and redo_skipped:
        return True, recover_status
    elif redo_existing and recover_status != RECOVER_SKIPPED:
        return True, recover_status
    elif redo_skipped and recover_status == RECOVER_SKIPPED:
        return True, recover_status

    return False, recover_status


def process_single_instance(inst, repo, model, api_key=None):
    """Process a single instance with its own working directory."""
    global this_worker_id
    temp_dir = worker_tempdirs[this_worker_id]
    original_dir = os.getcwd()
    try:
        log_path = (
            (LOG_DIR_BUG_GEN / repo / MIRROR_PR / inst[KEY_INSTANCE_ID])
            .resolve()
            .absolute()
        )
        metadata_file = log_path / get_metadata_file_name(inst[KEY_PULL_NUM])
        os.makedirs(log_path, exist_ok=True)

        os.chdir(temp_dir)
        global_registry.get(repo).clone()

        # Check if we should attempt recovery
        attempt_recovery, reason = should_attempt_recovery(inst, repo)
        if not attempt_recovery:
            with open(metadata_file, "w") as f:
                json.dump(
                    {
                        KEY_RECOVER_STATUS: RECOVER_SKIPPED,
                        KEY_SKIP_REASON: reason,
                    },
                    f,
                    indent=4,
                )
            return "skipped"

        # Attempt to apply patch directly to repo
        bug_file = log_path / f"{PREFIX_BUG}__pr_{inst[KEY_PULL_NUM]}.diff"
        direct_patch = f"{inst[KEY_INSTANCE_ID]}.diff"
        with open(direct_patch, "w") as f:
            f.write(inst[KEY_PATCH])
        if apply_patches(repo, [direct_patch]):
            with open(bug_file, "w") as f:
                f.write(inst[KEY_PATCH])
            with open(metadata_file, "w") as f:
                json.dump(
                    {
                        KEY_RECOVER_STATUS: RECOVER_SUCCESS,
                        KEY_COST: 0,
                        KEY_REWRITES: {},
                        "direct_patch": True,
                        INSTANCE_REF: inst,
                    },
                    f,
                    indent=4,
                )
            os.remove(direct_patch)
            return "recover_success"
        else:
            os.remove(direct_patch)

        # Attempt to perform recovery
        patch_files = recover_sweb_inst(
            inst, repo, model, api_key=api_key, log_path=log_path
        )

        if len(patch_files) == 0:
            return {"status": "recover_fail"}
        else:
            patch_merged = apply_patches(repo, patch_files)
            if patch_merged:
                with open(bug_file, "w") as f:
                    f.write(patch_merged)
                for patch_file in patch_files:
                    os.remove(patch_file)
                return "recover_success"
            else:
                return "recover_fail"
    except Exception as e:
        logger.error(f"Error processing instance {inst[KEY_INSTANCE_ID]}: {e}")
        logger.error(traceback.format_exc())
        return "recover_fail"
    finally:
        os.chdir(original_dir)


def init_worker():
    """
    When ProcessPoolExecutor workers are initialized, we
    """
    global this_worker_id, worker_tempdirs
    this_worker_id = int(current_process().name.split("-")[-1])
    worker_tempdirs[this_worker_id] = f"mirror_tmps/{str(uuid.uuid4())[:8]}"
    print(
        f"Initialized worker {this_worker_id} with temp dir {worker_tempdirs[this_worker_id]} (PID: {os.getpid()})"
    )
    os.makedirs(worker_tempdirs[this_worker_id], exist_ok=True)


def sweb_inst_to_rp(inst: dict) -> RepoProfile:
    owner, repo = inst["repo"].split("/")
    rps = [x for x in global_registry.values() if x.owner == owner and x.repo == repo]
    if len(rps) == 0:
        raise ValueError(
            f"{repo} not found in SWE-smith registry, create profile for repo under swesmith/profiles"
        )
    elif len(rps) > 1:
        print(f"Multiple profiles for {owner}/{repo} found")
        for i, rp in enumerate(rps):
            print(f"{i + 1}. {rp.commit}")
        idx = int(input("Enter index of RepoProfile to use: "))
        return rps[idx]
    return rps[0]


def main(
    sweb_insts_files: list,
    model: str,
    redo_existing: bool,
    redo_skipped: bool,
    api_key: str | None = None,
    num_processes: int = 1,
):
    global worker_tempdirs, this_worker_id

    assert not (redo_existing and redo_skipped), (
        "Cannot redo existing and skipped at the same time"
    )

    all_instances = []
    seen_repo_inst_ids = set()

    for sweb_insts_file in sweb_insts_files:
        if any([sweb_insts_file.endswith(ext) for ext in [".jsonl", ".jsonl.all"]]):
            file_instances = [json.loads(line) for line in open(sweb_insts_file)]
        elif sweb_insts_file.endswith(".json"):
            file_instances = json.load(open(sweb_insts_file))
        else:
            raise ValueError(
                f"Invalid file format for {sweb_insts_file}. Must be .json or .jsonl"
            )
        for inst in file_instances:
            inst[MIRROR_PR] = sweb_inst_to_rp(inst).repo_name
            repo_inst_id = (inst[MIRROR_PR], inst[KEY_INSTANCE_ID])
            if repo_inst_id in seen_repo_inst_ids:
                raise ValueError(f"Duplicate instance ID: {inst[KEY_INSTANCE_ID]}")
            seen_repo_inst_ids.add(repo_inst_id)
            all_instances.append(inst)
    print(f"Found {len(all_instances)} instances across {len(sweb_insts_files)} files")

    to_process = []
    already_completed = {RECOVER_SUCCESS: [], RECOVER_FAIL: [], RECOVER_SKIPPED: []}
    all_repos = set()
    repos_to_process = set()
    for inst in all_instances:
        should_process, status = should_process_instance(
            inst, inst[MIRROR_PR], redo_existing, redo_skipped
        )
        if should_process:
            to_process.append(inst)
        elif status:
            already_completed[status].append(inst)
        all_repos.add(inst[MIRROR_PR])
        if should_process:
            repos_to_process.add(inst[MIRROR_PR])
    print("Pre-processing report:")
    print(f"- Repos to process: {len(repos_to_process)}")
    print(f"- Instances to process: {len(to_process)}")
    print(
        f"- Already completed instances: {sum(len(v) for v in already_completed.values())}"
    )
    print(f"- All repos: {len(all_repos)}")
    print(f"  - Success: {len(already_completed[RECOVER_SUCCESS])}")
    print(f"  - Failed: {len(already_completed[RECOVER_FAIL])}")
    print(f"  - Skipped: {len(already_completed[RECOVER_SKIPPED])}")
    if not to_process:
        print("No instances to process. Exiting.")
        return

    num_processes = min(num_processes, len(to_process))
    print(f"Using {num_processes} processes")

    task_args = []
    for inst in to_process:
        task_args.append((inst, inst[MIRROR_PR], model, api_key))

    pbar = tqdm(total=len(task_args))

    results = {"skipped": 0, "recover_success": 0, "recover_fail": 0}
    if num_processes > 1:
        worker_pids = {}

        with ProcessPoolExecutor(
            max_workers=num_processes, initializer=init_worker
        ) as pool:
            try:
                futures = [
                    pool.submit(process_single_instance, *args) for args in task_args
                ]

                # Store worker process PIDs
                for executor in pool._processes.values():
                    worker_pids[executor.pid] = executor
                print(f"Worker PIDs: {list(worker_pids.keys())}")

                for future in as_completed(futures):
                    result = future.result()
                    if result in results:
                        results[result] += 1
                    else:
                        print(f"Unknown result: {result}")
                    pbar.update(1)
            except KeyboardInterrupt:
                print("\nKeyboard interrupt. Forcefully killing all workers...")
                print(f"Partial results: {results}")
                for pid in worker_pids:
                    try:
                        print(f"Sending SIGKILL to worker PID {pid}")
                        os.kill(pid, signal.SIGKILL)
                    except OSError as e:
                        print(f"Error killing process {pid}: {e}")
                pool.shutdown(wait=False)
                raise KeyboardInterrupt
            finally:
                for temp_dir in worker_tempdirs.values():
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
    else:
        # Single process mode
        worker_tempdirs = {0: f"tmp_{str(uuid.uuid4())[:8]}"}
        os.makedirs(worker_tempdirs[0], exist_ok=True)
        this_worker_id = 0
        for args in task_args:
            result = process_single_instance(*args)
            if result in results:
                results[result] += 1
            pbar.update(1)
        if os.path.exists(worker_tempdirs[0]):
            shutil.rmtree(worker_tempdirs[0])

    pbar.close()

    # Update results with already completed instances if needed
    if not redo_existing and not redo_skipped:
        results["skipped"] += len(already_completed[RECOVER_SKIPPED])
        results["recover_success"] += len(already_completed[RECOVER_SUCCESS])
        results["recover_fail"] += len(already_completed[RECOVER_FAIL])
    elif redo_existing and not redo_skipped:
        results["skipped"] += len(already_completed[RECOVER_SKIPPED])
    elif redo_skipped and not redo_existing:
        results["recover_success"] += len(already_completed[RECOVER_SUCCESS])
        results["recover_fail"] += len(already_completed[RECOVER_FAIL])

    print(f"\nFinal summary for ({len(all_instances)} instances)")
    print(f"- Skipped {results['skipped']}")
    print(f"- Recovery Success: {results['recover_success']}")
    print(f"- Recovery Fail: {results['recover_fail']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Given a pull request, mirror the bug in a repository."
    )
    parser.add_argument(
        "sweb_insts_files",
        type=str,
        nargs="+",
        help="Paths to one or more swe-bench-task-instances.json[l] files.",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Model to use for bug generation",
        default="openai/gpt-4o",
    )
    parser.add_argument(
        "--redo_existing",
        action="store_true",
        help="Whether to redo existing bugs",
        default=False,
    )
    parser.add_argument(
        "--redo_skipped",
        action="store_true",
        help="Whether to redo bugs skipped due to failing recovery criteria",
        default=False,
    )
    parser.add_argument(
        "--num_processes",
        type=int,
        default=1,
    )
    args = parser.parse_args()
    main(**vars(args))
