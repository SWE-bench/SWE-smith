import docker
import traceback

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
from swesmith.profiles import global_registry


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
