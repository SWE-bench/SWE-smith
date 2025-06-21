import docker
import os
import re
import shutil
import traceback

from docker.models.containers import Container
from functools import lru_cache
from logging import Logger
from multiprocessing import Lock
from pathlib import Path
from swebench.harness.constants import (
    APPLY_PATCH_FAIL,
    APPLY_PATCH_PASS,
    DOCKER_PATCH,
    DOCKER_USER,
    DOCKER_WORKDIR,
    FAIL_TO_PASS,
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
from swesmith.bug_gen.mirror.generate import INSTANCE_REF
from swesmith.constants import (
    ENV_NAME,
    GIT_APPLY_CMDS,
    KEY_PATCH,
    LOG_DIR_RUN_VALIDATION,
    TEST_OUTPUT_END,
    TEST_OUTPUT_START,
    TIMEOUT,
)
from swesmith.profiles import global_registry
from swesmith.utils import clone_repo
from unidiff import PatchSet


repo_lock = Lock()


def get_test_paths(dir_path: str, ext: str = ".py") -> list[Path]:
    """
    Get all testing file paths relative to the given directory.
    """
    return [
        Path(os.path.relpath(os.path.join(root, file), dir_path))
        for root, _, files in os.walk(Path(dir_path).resolve())
        for file in files
        if (
            (
                any([x in root.split("/") for x in ["tests", "test", "specs"]])
                or file.lower().startswith("test")
                or file.rsplit(".", 1)[0].endswith("test")
            )
            and (ext is None or file.endswith(ext))
        )
    ]


@lru_cache(maxsize=None)
def get_cached_test_paths(repo_name):
    with repo_lock:  # Only one process enters this block at a time
        if not os.path.exists(repo_name):
            clone_repo(repo_name)

        test_paths = get_test_paths(repo_name)

        if os.path.exists(repo_name):
            shutil.rmtree(repo_name)

    return test_paths


def get_test_command_mypy(instance: dict):
    rp = global_registry.get_from_inst(instance)
    pattern = r"\[case ([^\]]+)\]"
    if FAIL_TO_PASS in instance:
        test_keys = " or ".join([x.rsplit("::", 1)[-1] for x in instance[FAIL_TO_PASS]])
    elif INSTANCE_REF in instance and "test_patch" in instance[INSTANCE_REF]:
        test_keys = " or ".join(
            re.findall(pattern, instance[INSTANCE_REF]["test_patch"])
        )
    return f'{rp.test_cmd} "{test_keys}"'


MAP_REPO_TO_TEST_CMD = {
    "python/mypy": get_test_command_mypy,
}


def get_test_command(instance: dict):
    """
    Given a repo/commit pair and a (gold) patch, return the test command to run
    """
    rp = global_registry.get_from_inst(instance)
    test_command = rp.test_cmd
    _r = f"{rp.owner}/{rp.repo}"

    if FAIL_TO_PASS in instance and "pytest" in rp.test_cmd:
        # NOTE: Using F2P key as indicator that this is eval instance, not validation
        if _r in MAP_REPO_TO_TEST_CMD:
            return MAP_REPO_TO_TEST_CMD[_r](instance), []
        f2p_files = list(set([x.split("::", 1)[0] for x in instance[FAIL_TO_PASS]]))
        test_command += f" {' '.join(f2p_files)}"
        return test_command, f2p_files

    if rp.min_testing or KEY_PATCH not in instance:
        # If min testing is not enabled or there's no patch
        # return test command as is (usually = run whole test suite)
        return test_command, []

    # Get all testing related file paths in the repo
    test_paths = get_cached_test_paths(rp.repo_name)

    if (
        INSTANCE_REF in instance
        and len(instance[INSTANCE_REF]["test_patch"].strip()) > 0
    ):
        test_patch = instance[INSTANCE_REF]["test_patch"]
        # For PR Mirroring (SWE-bench style) instances,
        # if test patch is available, use that information
        if _r in MAP_REPO_TO_TEST_CMD:
            return MAP_REPO_TO_TEST_CMD[_r](instance), []
        rv = []
        for x in PatchSet(test_patch):
            for test_path in test_paths:
                if str(test_path).endswith(x.path) or str(test_path).endswith(
                    Path(x.path).name
                ):
                    rv.append(str(test_path))
        if len(rv) > 0:
            test_command += f" {' '.join(rv)}"
            return test_command, rv

    # Identify relevant test files based on the patch
    patch_paths = [Path(f.path) for f in PatchSet(instance[KEY_PATCH])]
    rv = []
    for patch_path in patch_paths:
        file_name = patch_path.name.strip(".py")
        parent_dir = patch_path.parent.name
        for test_path in test_paths:
            # Check for common test file naming conventions first
            # If found, add to list and break
            common_test_names = [
                f"test_{file_name}.py",
                f"test{file_name}.py",
                f"{file_name}_test.py",
                f"{file_name}test.py",
            ]
            if any(
                [
                    str(test_path).endswith(f"{parent_dir}/{name}")
                    or str(test_path).endswith(name)
                    for name in common_test_names
                ]
            ):
                rv.append(str(test_path))
                break
        else:
            for test_path in test_paths:
                if parent_dir == test_path.parent.name:
                    # If similar testing folder found, add to list and break
                    rv.append(str(test_path.parent))
                    break
                elif any(
                    [
                        x.format(parent_dir) == test_path.name
                        for x in ["test_{}.py", "test{}.py", "{}_test.py", "{}test.py"]
                    ]
                ):
                    rv.append(str(test_path))

    if len(rv) > 0:
        # Remove duplicates
        test_files = [x for x in rv if x.endswith(".py")]
        final = [x for x in rv if not x.endswith(".py")]
        for test_file in test_files:
            if os.path.dirname(test_file) not in final:
                final.append(test_file)
        test_command += f" {' '.join(set(final))}"

    return test_command, rv


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
    patch: str | None = None,
    commit: str | None = None,
    is_gold: bool = False,
    timeout: int = TIMEOUT,
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
    rp = global_registry.get_from_inst(instance)
    try:
        container_type = None
        if log_dir == RUN_EVALUATION_LOG_DIR:
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

        # If provided, checkout commit in container
        if commit is not None:
            logger.info(f"Checking out commit {commit}")
            container.exec_run("git fetch", workdir=DOCKER_WORKDIR, user=DOCKER_USER)
            val = container.exec_run(
                f"git checkout {commit}", workdir=DOCKER_WORKDIR, user=DOCKER_USER
            )
            if val.exit_code != 0:
                logger.info(f"CHECKOUT FAILED: {val.output.decode(UTF8)}")
                return logger, False

        # If provided, copy patch to container and apply it to codebase
        if patch is not None:
            patch_file = Path(log_dir / "patch.diff")
            patch_file.write_text(patch)
            logger.info(f"Patch written to {patch_file}, now applying to container...")
            copy_to_container(container, patch_file, Path(DOCKER_PATCH))
            _apply_patch(instance_id, container, logger, is_gold)

        # Copy eval script to container
        eval_file = Path(log_dir / "eval.sh")
        test_command, _ = get_test_command(instance)
        eval_file.write_text(
            "\n".join(
                [
                    "#!/bin/bash",
                    "set -uxo pipefail",
                    "source /opt/miniconda3/bin/activate",
                    f"conda activate {ENV_NAME}",
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
