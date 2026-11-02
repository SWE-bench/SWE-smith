"""Tests for the evaluation steps of swesmith.harness.utils.run_patch_in_container."""

from unittest.mock import MagicMock, patch

import pytest
from swebench.harness.constants import RUN_EVALUATION_LOG_DIR

from swesmith.constants import TEST_OUTPUT_START
from swesmith.harness.utils import run_patch_in_container


def make_container(tip_subject: str) -> MagicMock:
    """A fake container whose branch tip has the given commit subject."""

    def exec_run(cmd, **kwargs):
        if cmd.startswith("git log -1"):
            return MagicMock(exit_code=0, output=f"{tip_subject}\n".encode())
        return MagicMock(exit_code=0, output=b"ok")

    container = MagicMock()
    container.exec_run.side_effect = exec_run
    return container


@pytest.fixture
def run_eval(tmp_path, monkeypatch):
    """Run run_patch_in_container in eval mode against a fake container."""
    monkeypatch.chdir(tmp_path)

    def _run(container, build_cmd=""):
        profile = MagicMock()
        profile._is_repo_private.return_value = False
        profile.build_cmd = build_cmd
        profile.build_timeout = 600
        profile.get_test_cmd.return_value = ("make test", [])
        client = MagicMock()
        client.containers.create.return_value = container
        with (
            patch("swesmith.harness.utils.docker") as mock_docker,
            patch("swesmith.harness.utils.registry") as mock_registry,
            patch("swesmith.harness.utils.setup_logger", return_value=MagicMock()),
            patch("swesmith.harness.utils.copy_to_container"),
            patch(
                "swesmith.harness.utils.exec_run_with_timeout",
                return_value=("output", False, 1.0),
            ) as mock_exec,
            patch("swesmith.harness.utils.cleanup_container"),
        ):
            mock_docker.from_env.return_value = client
            mock_registry.get_from_inst.return_value = profile
            run_patch_in_container(
                instance={"instance_id": "repo.abc.bug"},
                run_id="run1",
                log_dir=RUN_EVALUATION_LOG_DIR,
                timeout=60,
                commit="repo.abc.bug",
            )
            return mock_exec

    return _run


def commands(container: MagicMock) -> list[str]:
    return [c.args[0] for c in container.exec_run.call_args_list]


def eval_script(tmp_path):
    return tmp_path / RUN_EVALUATION_LOG_DIR / "run1" / "repo.abc.bug" / "eval.sh"


def test_eval_steps_back_over_test_removal_commit(run_eval):
    container = make_container("Remove F2P Tests")
    run_eval(container)
    assert "git checkout HEAD~1" in commands(container)


def test_eval_stays_on_bug_commit_without_test_removal_commit(run_eval):
    # Branches without F2P test files end in "Bug Patch"; HEAD~1 would be the
    # original, bug-free code.
    container = make_container("Bug Patch")
    run_eval(container)
    assert "git checkout repo.abc.bug" in commands(container)
    assert "git checkout HEAD~1" not in commands(container)


def test_eval_rejects_unexpected_branch_tip(run_eval, tmp_path):
    container = make_container("Some other commit")
    run_eval(container)
    assert "git checkout HEAD~1" not in commands(container)
    assert not eval_script(tmp_path).exists()


def test_eval_script_builds_before_tests(run_eval, tmp_path):
    mock_exec = run_eval(make_container("Bug Patch"), build_cmd="cmake --build build")
    lines = eval_script(tmp_path).read_text().splitlines()
    build = lines.index("cmake --build build || exit 1")
    assert build < lines.index(f": '{TEST_OUTPUT_START}'") < lines.index("make test")
    assert mock_exec.call_args.kwargs["timeout"] == 60 + 600


def test_eval_script_without_build_cmd(run_eval, tmp_path):
    mock_exec = run_eval(make_container("Bug Patch"))
    lines = eval_script(tmp_path).read_text().splitlines()
    assert not any("exit 1" in line for line in lines)
    assert lines.index(f": '{TEST_OUTPUT_START}'") == lines.index("make test") - 1
    assert mock_exec.call_args.kwargs["timeout"] == 60
