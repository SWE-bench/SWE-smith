import docker
import fnmatch
import threading
import traceback

from concurrent.futures import ThreadPoolExecutor, as_completed
from docker.models.containers import Container
from logging import Logger
from pathlib import Path
from swebench.harness.constants import (
    APPLY_PATCH_FAIL,
    APPLY_PATCH_PASS,
    DOCKER_PATCH,
    DOCKER_USER,
    DOCKER_WORKDIR,
    KEY_INSTANCE_ID,
    LOG_INSTANCE,
    LOG_TEST_OUTPUT,
    RUN_EVALUATION_LOG_DIR,
    TESTS_TIMEOUT,
    UTF8,
)
from swebench.harness.docker_build import setup_logger
from swebench.harness.docker_utils import (
    cleanup_container,
    copy_to_container,
    exec_run_with_timeout,
)
from swebench.harness.utils import EvaluationError
from swesmith.constants import (
    GIT_APPLY_CMDS,
    LOG_DIR_RUN_VALIDATION,
    TEST_OUTPUT_END,
    TEST_OUTPUT_START,
)
from swesmith.profiles import registry
from swesmith.profiles.base import _find_ssh_key
from unidiff import PatchSet


_ssh_copy_lock = threading.Lock()


def matches_instance_filter(instance_id: str, instance_ids: list[str] | None) -> bool:
    """
    Check if an instance_id matches the filtering criteria.

    Args:
        instance_id: The instance ID to check
        instance_ids: List of instance IDs or patterns to match against

    Returns:
        True if the instance should be included, False otherwise
    """
    if instance_ids is None:
        return True

    for filter_item in instance_ids:
        # Check for exact match first
        if instance_id == filter_item:
            return True

        # Check for pattern match (supports * and ? wildcards)
        if fnmatch.fnmatch(instance_id, filter_item):
            return True

    return False


def _apply_patch(
    instance_id: str, container: Container, logger: Logger, is_gold: bool = False
):
    """
    Apply a patch to a container's codebase
    """
    apply_succeeded = False
    for git_apply_cmd in GIT_APPLY_CMDS:
        # Because gold patches = bug patches, so fix = revert
        git_apply_cmd = (
            f"{git_apply_cmd} {DOCKER_PATCH}"
            if not is_gold
            else f"{git_apply_cmd} --reverse {DOCKER_PATCH}"
        )
        val = container.exec_run(
            git_apply_cmd, workdir=DOCKER_WORKDIR, user=DOCKER_USER
        )
        if val.exit_code == 0:
            apply_succeeded = True
            logger.info(f"{APPLY_PATCH_PASS}:\n{val.output.decode(UTF8)}")
            break
        logger.info(
            f"Failed to apply patch to container with {git_apply_cmd}.\n"
            + f"Error Message: {val.output.decode(UTF8)}\nTrying again..."
        )
    if not apply_succeeded:
        apply_failed_msg = f"{APPLY_PATCH_FAIL}:\n{val.output.decode(UTF8)}"
        logger.info(apply_failed_msg)
        raise EvaluationError(instance_id, apply_failed_msg, logger)


def run_patch_in_container(
    instance: dict,
    run_id: str,
    log_dir: Path,
    timeout: int,
    patch: str | None = None,
    commit: str | None = None,
    f2p_only: bool = False,
    is_gold: bool = False,
) -> tuple[Logger, bool] | None:
    """
    Run a patch in a container. The general logical flow is as follows:
    1. Setup logging directory
    2. Start docker container
    3. Copy patch to container, if provided
        a. Apply patch to codebase
    4. Copy eval script to container
    5. Run eval script, write outputs to logs

    Returns:
        tuple[Logger, bool]: logger and whether the container timed out or None if an error occurred
    """
    container = None
    client = docker.from_env()
    instance_id = instance[KEY_INSTANCE_ID]
    rp = registry.get_from_inst(instance)
    is_eval = log_dir == RUN_EVALUATION_LOG_DIR
    try:
        container_type = None
        if is_eval:
            container_type = "eval"
        elif log_dir == LOG_DIR_RUN_VALIDATION:
            container_type = "val"

        # Setup logging directory
        log_dir = log_dir / run_id / instance_id
        log_dir.mkdir(parents=True, exist_ok=True)
        container_name = f"swesmith.{container_type}.{run_id}.{instance_id}"
        log_file = log_dir / LOG_INSTANCE
        logger = setup_logger(container_name, log_file)

        # Start docker container
        rp.pull_image()
        container = client.containers.create(
            image=rp.image_name,
            name=container_name,
            user=DOCKER_USER,
            detach=True,
            command="tail -f /dev/null",
            platform="linux/x86_64",
            mem_limit="10g",
        )
        container.start()

        # For private repos, copy SSH key into container
        ssh_env = {}
        if rp._is_repo_private():
            key_file = _find_ssh_key()
            if key_file is None:
                raise ValueError(
                    "Repo is private but no SSH key found. "
                    "Set GITHUB_USER_SSH_KEY or add a key to ~/.ssh/"
                )

            # Prevent race condition
            with _ssh_copy_lock:
                copy_to_container(container, key_file, Path("/github_key"))
            container.exec_run("chmod 600 /github_key", user=DOCKER_USER)
            ssh_env = {
                "GIT_SSH_COMMAND": "ssh -i /github_key -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes"
            }

        # If provided, checkout commit in container
        if commit is not None:
            logger.info(f"Checking out commit {commit}")
            fetch_val = container.exec_run(
                "git fetch",
                workdir=DOCKER_WORKDIR,
                user=DOCKER_USER,
                environment=ssh_env,
            )
            if fetch_val.exit_code != 0:
                logger.info(
                    f"GIT FETCH FAILED (exit={fetch_val.exit_code}): {fetch_val.output.decode(UTF8)}"
                )
            val = container.exec_run(
                f"git checkout {commit}", workdir=DOCKER_WORKDIR, user=DOCKER_USER
            )
            if val.exit_code != 0:
                logger.info(f"CHECKOUT FAILED: {val.output.decode(UTF8)}")
                return logger, False
            if is_eval:
                # NOTE: Key assumption we make is that each branch has two commits
                # 1. Bug commit
                # 2. F2P Test File(s) removal commit (on top of 1).
                # The `HEAD~1` corresponds to reverting the branch to (1), which
                # effectively brings the tests back into the codebase.
                val = container.exec_run(
                    "git checkout HEAD~1", workdir=DOCKER_WORKDIR, user=DOCKER_USER
                )
                if val.exit_code != 0:
                    logger.info(
                        f"CHECKOUT TO BUG STAGE FAILED: {val.output.decode(UTF8)}"
                    )
                    return logger, False

        # If provided, copy patch to container and apply it to codebase
        if patch is not None and len(patch) >= 1:
            logger.info("Applying patch to container...")

            # Revert any changes to those files in the container to ensure a clean state
            changed_files = " ".join([x.path for x in PatchSet(patch)])
            container.exec_run(
                f"git checkout -- {changed_files}",
                workdir=DOCKER_WORKDIR,
                user=DOCKER_USER,
            )

            # Apply the patch inside the container
            patch_file = Path(log_dir / "patch.diff")
            patch_file.write_text(patch)
            logger.info(f"Patch written to {patch_file}, now applying to container...")
            copy_to_container(container, patch_file, Path(DOCKER_PATCH))
            _apply_patch(instance_id, container, logger, is_gold)

            if is_eval:
                # For evaluation, removes any changes to test related files.
                f2p_files, p2p_files = rp.get_test_files(instance)
                test_files = " ".join(f2p_files + p2p_files)
                if test_files:
                    container.exec_run(
                        f"git checkout -- {test_files}",
                        workdir=DOCKER_WORKDIR,
                        user=DOCKER_USER,
                    )
                    logger.info(
                        f"Reverted changes to test files in container: {test_files}"
                    )

        # Copy eval script to container
        eval_file = Path(log_dir / "eval.sh")
        test_command, _ = rp.get_test_cmd(instance, f2p_only=f2p_only)
        eval_file.write_text(
            "\n".join(
                [
                    "#!/bin/bash",
                    "set -uxo pipefail",
                    f"cd {DOCKER_WORKDIR}",
                    f": '{TEST_OUTPUT_START}'",
                    test_command,
                    f": '{TEST_OUTPUT_END}'",
                ]
            )
            + "\n"
        )
        copy_to_container(container, eval_file, Path("/eval.sh"))

        # Run eval script, write outputs to logs
        test_output, timed_out, total_runtime = exec_run_with_timeout(
            container, "/bin/bash /eval.sh", timeout=timeout
        )
        test_output_path = log_dir / LOG_TEST_OUTPUT
        logger.info(f"Test Runtime: {total_runtime:_.2f} seconds")
        with open(test_output_path, "w") as f:
            f.write(test_output)
            if timed_out:
                timeout_error = f"{TESTS_TIMEOUT}: {timeout} seconds exceeded"
                f.write(f"\n\n{timeout_error}")

        logger.info(f"Test output for {instance_id} written to {test_output_path}")
        cleanup_container(client, container, logger)
        return logger, timed_out
    except Exception as e:
        error_msg = (
            f"Error validating {instance_id}: {e}\n"
            f"{traceback.format_exc()}\n"
            f"Check ({logger.log_file}) for more information."
        )
        logger.info(error_msg)
        print(f"Error validating {instance_id}: {e}")

        # Remove instance container + image, close logger
        cleanup_container(client, container, logger)
        return logger, False


def run_threadpool(func, payloads, max_workers):
    """
    Run a function with a list of payloads using ThreadPoolExecutor.

    Args:
        func: Function to run for each payload
        payloads: List of payloads to process
        max_workers: Maximum number of worker threads

    Returns:
        tuple: (succeeded, failed) lists of payloads
    """
    if max_workers <= 0:
        return run_sequential(func, payloads)

    succeeded, failed = [], []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a future for running each instance
        futures = {executor.submit(func, *payload): payload for payload in payloads}
        # Wait for each future to complete
        for future in as_completed(futures):
            try:
                # Check if instance ran successfully
                future.result()
                succeeded.append(futures[future])
            except Exception as e:
                print(f"{type(e)}: {e}")
                traceback.print_exc()
                failed.append(futures[future])

    return succeeded, failed


def run_sequential(func, payloads):
    """
    Run a function with a list of payloads sequentially.

    Args:
        func: Function to run for each payload
        payloads: List of payloads to process

    Returns:
        tuple: (succeeded, failed) lists of payloads
    """
    succeeded, failed = [], []
    for payload in payloads:
        try:
            func(*payload)
            succeeded.append(payload)
        except Exception:
            traceback.print_exc()
            failed.append(payload)

    return succeeded, failed
