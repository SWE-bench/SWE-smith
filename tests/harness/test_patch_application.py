import shlex
import subprocess

import pytest

from types import SimpleNamespace
from unittest.mock import Mock

from swesmith.harness import utils


@pytest.mark.parametrize("commit_setup", [False, True])
@pytest.mark.parametrize("already_applied", [False, True])
@pytest.mark.parametrize("is_gold", [False, True])
def test_patch_fallback_preserves_code_and_setup(
    tmp_path, commit_setup, already_applied, is_gold, monkeypatch
):
    """A config context mismatch must not cause the code fix to be reversed."""

    patch_version = subprocess.run(
        ["patch", "--version"], capture_output=True, text=True
    )
    if not patch_version.stdout.startswith("GNU patch"):
        pytest.skip("This regression requires GNU patch")

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True
        )

    git("init", "-q")
    git("config", "user.name", "Test")
    git("config", "user.email", "test@example.com")
    code = tmp_path / "code.py"
    config = tmp_path / "tox.ini"
    original_code = "def answer():\n    return 1  # bug\n"
    fixed_code = "def answer():\n    return 2  # fixed\n"
    original_config = "[tox]\nenvlist = py\n\n[testenv]\ncommands = pytest\n"
    code.write_text(original_code)
    config.write_text(original_config)
    git("add", ".")
    git("-c", "commit.gpgsign=false", "commit", "-qm", "base")

    code.write_text(fixed_code)
    config.write_text(original_config.replace("pytest", "pytest -x"))
    patch = tmp_path / "model.patch"
    patch.write_bytes(git("diff", *(["-R"] if is_gold else [])).stdout)
    git("checkout", "--", ".")

    # Environment preparation changes a context line, not the patch's target line.
    prepared_config = original_config.replace("envlist = py", "envlist = py311")
    config.write_text(prepared_config)
    if commit_setup:
        git("add", "tox.ini")
        git("-c", "commit.gpgsign=false", "commit", "-qm", "prepare environment")
    setup_file = tmp_path / "setup-marker"
    setup_file.write_text("keep environment artifacts\n")
    if already_applied:
        code.write_text(fixed_code)
        config.write_text(prepared_config.replace("pytest", "pytest -x"))

    def exec_run(command, **kwargs):
        result = subprocess.run(shlex.split(command), cwd=tmp_path, capture_output=True)
        return SimpleNamespace(
            exit_code=result.returncode, output=result.stdout + result.stderr
        )

    monkeypatch.setattr(utils, "DOCKER_PATCH", str(patch))
    container = SimpleNamespace(exec_run=exec_run)
    if already_applied:
        with pytest.raises(utils.EvaluationError):
            utils._apply_patch("test-instance", container, Mock(), is_gold=is_gold)
    else:
        utils._apply_patch("test-instance", container, Mock(), is_gold=is_gold)

    assert code.read_text() == fixed_code
    assert config.read_text() == prepared_config.replace("pytest", "pytest -x")
    assert setup_file.read_text() == "keep environment artifacts\n"
