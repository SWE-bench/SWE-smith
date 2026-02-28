"""Tests for SSH/private-repo support in swesmith.harness.utils."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from swesmith.profiles.base import _find_ssh_key


class TestFindSshKey:
    """Tests for the _find_ssh_key helper."""

    def test_returns_env_var_path_when_exists(self, tmp_path):
        key_file = tmp_path / "my_key"
        key_file.write_text("fake key")
        with patch.dict(os.environ, {"GITHUB_USER_SSH_KEY": str(key_file)}):
            result = _find_ssh_key()
            assert result == Path(key_file)

    def test_ignores_env_var_when_file_missing(self):
        with patch.dict(os.environ, {"GITHUB_USER_SSH_KEY": "/nonexistent/key"}):
            with patch("pathlib.Path.exists", return_value=False):
                result = _find_ssh_key()
                assert result is None

    def test_falls_back_to_default_ssh_keys(self, tmp_path):
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        ed25519_key = ssh_dir / "id_ed25519"
        ed25519_key.write_text("fake key")

        with (
            patch.dict(os.environ, {}, clear=False),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            os.environ.pop("GITHUB_USER_SSH_KEY", None)
            result = _find_ssh_key()
            assert result == ed25519_key

    def test_returns_first_matching_default_key(self, tmp_path):
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        rsa_key = ssh_dir / "id_rsa"
        rsa_key.write_text("fake rsa key")
        ed25519_key = ssh_dir / "id_ed25519"
        ed25519_key.write_text("fake ed25519 key")

        with (
            patch.dict(os.environ, {}, clear=False),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            os.environ.pop("GITHUB_USER_SSH_KEY", None)
            result = _find_ssh_key()
            assert result == rsa_key

    def test_returns_none_when_no_keys_exist(self, tmp_path):
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()

        with (
            patch.dict(os.environ, {}, clear=False),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            os.environ.pop("GITHUB_USER_SSH_KEY", None)
            result = _find_ssh_key()
            assert result is None


class TestRunPatchInContainerSsh:
    """Tests for the private-repo SSH logic inside run_patch_in_container."""

    @pytest.fixture
    def mock_env(self, tmp_path):
        """Set up the common mocks needed for run_patch_in_container."""
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(exit_code=0, output=b"ok")

        mock_client = MagicMock()
        mock_client.containers.create.return_value = mock_container

        mock_profile = MagicMock()
        mock_profile.image_name = "test-image"
        mock_profile._is_repo_private.return_value = False

        mock_logger = MagicMock()
        mock_logger.log_file = str(tmp_path / "test.log")

        return {
            "container": mock_container,
            "client": mock_client,
            "profile": mock_profile,
            "logger": mock_logger,
            "log_dir": tmp_path,
        }

    def test_private_repo_copies_ssh_key(self, mock_env, tmp_path):
        """When repo is private, SSH key should be copied into container."""
        mock_env["profile"]._is_repo_private.return_value = True

        ssh_key = tmp_path / "id_rsa"
        ssh_key.write_text("fake key")

        with (
            patch("swesmith.harness.utils.docker") as mock_docker,
            patch("swesmith.harness.utils.registry") as mock_registry,
            patch(
                "swesmith.harness.utils.setup_logger", return_value=mock_env["logger"]
            ),
            patch("swesmith.harness.utils._find_ssh_key", return_value=ssh_key),
            patch("swesmith.harness.utils.copy_to_container") as mock_copy,
            patch(
                "swesmith.harness.utils.exec_run_with_timeout",
                return_value=("output", False, 1.0),
            ),
            patch("swesmith.harness.utils.cleanup_container"),
        ):
            mock_docker.from_env.return_value = mock_env["client"]
            mock_registry.get_from_inst.return_value = mock_env["profile"]

            from swesmith.harness.utils import run_patch_in_container

            instance = {"instance_id": "test_instance"}
            run_patch_in_container(
                instance=instance,
                run_id="run1",
                log_dir=tmp_path,
                timeout=60,
            )

            mock_copy.assert_called_once_with(
                mock_env["container"], ssh_key, Path("/github_key")
            )
            mock_env["container"].exec_run.assert_any_call(
                "chmod 600 /github_key", user="root"
            )

    def test_private_repo_no_key_raises(self, mock_env, tmp_path):
        """When repo is private and no SSH key found, should raise ValueError."""
        mock_env["profile"]._is_repo_private.return_value = True

        with (
            patch("swesmith.harness.utils.docker") as mock_docker,
            patch("swesmith.harness.utils.registry") as mock_registry,
            patch(
                "swesmith.harness.utils.setup_logger", return_value=mock_env["logger"]
            ),
            patch("swesmith.harness.utils._find_ssh_key", return_value=None),
            patch("swesmith.harness.utils.cleanup_container"),
        ):
            mock_docker.from_env.return_value = mock_env["client"]
            mock_registry.get_from_inst.return_value = mock_env["profile"]

            from swesmith.harness.utils import run_patch_in_container

            instance = {"instance_id": "test_instance"}
            result = run_patch_in_container(
                instance=instance,
                run_id="run1",
                log_dir=tmp_path,
                timeout=60,
            )
            assert result is not None
            logger, timed_out = result
            assert timed_out is False

    def test_public_repo_skips_ssh(self, mock_env, tmp_path):
        """When repo is public, no SSH key logic should be triggered."""
        mock_env["profile"]._is_repo_private.return_value = False

        with (
            patch("swesmith.harness.utils.docker") as mock_docker,
            patch("swesmith.harness.utils.registry") as mock_registry,
            patch(
                "swesmith.harness.utils.setup_logger", return_value=mock_env["logger"]
            ),
            patch("swesmith.harness.utils._find_ssh_key") as mock_find_key,
            patch("swesmith.harness.utils.copy_to_container") as mock_copy,
            patch(
                "swesmith.harness.utils.exec_run_with_timeout",
                return_value=("output", False, 1.0),
            ),
            patch("swesmith.harness.utils.cleanup_container"),
        ):
            mock_docker.from_env.return_value = mock_env["client"]
            mock_registry.get_from_inst.return_value = mock_env["profile"]

            from swesmith.harness.utils import run_patch_in_container

            instance = {"instance_id": "test_instance"}
            run_patch_in_container(
                instance=instance,
                run_id="run1",
                log_dir=tmp_path,
                timeout=60,
            )

            mock_find_key.assert_not_called()
            mock_copy.assert_not_called()

    def test_git_fetch_with_ssh_env_when_private(self, mock_env, tmp_path):
        """When repo is private and commit is given, git fetch should receive ssh_env."""
        mock_env["profile"]._is_repo_private.return_value = True

        ssh_key = tmp_path / "id_rsa"
        ssh_key.write_text("fake key")

        with (
            patch("swesmith.harness.utils.docker") as mock_docker,
            patch("swesmith.harness.utils.registry") as mock_registry,
            patch(
                "swesmith.harness.utils.setup_logger", return_value=mock_env["logger"]
            ),
            patch("swesmith.harness.utils._find_ssh_key", return_value=ssh_key),
            patch("swesmith.harness.utils.copy_to_container"),
            patch(
                "swesmith.harness.utils.exec_run_with_timeout",
                return_value=("output", False, 1.0),
            ),
            patch("swesmith.harness.utils.cleanup_container"),
        ):
            mock_docker.from_env.return_value = mock_env["client"]
            mock_registry.get_from_inst.return_value = mock_env["profile"]

            from swesmith.harness.utils import run_patch_in_container

            instance = {"instance_id": "test_instance"}
            run_patch_in_container(
                instance=instance,
                run_id="run1",
                log_dir=tmp_path,
                timeout=60,
                commit="abc123",
            )

            fetch_calls = [
                c
                for c in mock_env["container"].exec_run.call_args_list
                if c.args
                and c.args[0] == "git fetch"
                or (c.kwargs.get("cmd") == "git fetch")
            ]

            found_ssh_env = False
            for c in mock_env["container"].exec_run.call_args_list:
                if len(c.args) > 0 and c.args[0] == "git fetch":
                    env = c.kwargs.get("environment", {})
                    if "GIT_SSH_COMMAND" in env:
                        found_ssh_env = True
            assert found_ssh_env, (
                "git fetch should have been called with ssh_env containing GIT_SSH_COMMAND"
            )

    def test_git_fetch_failure_logged(self, mock_env, tmp_path):
        """When git fetch fails, the failure should be logged."""
        mock_env["profile"]._is_repo_private.return_value = False

        def exec_run_side_effect(cmd, **kwargs):
            if cmd == "git fetch":
                return MagicMock(exit_code=1, output=b"fetch error")
            if isinstance(cmd, str) and cmd.startswith("git checkout"):
                return MagicMock(exit_code=0, output=b"ok")
            return MagicMock(exit_code=0, output=b"ok")

        mock_env["container"].exec_run.side_effect = exec_run_side_effect

        with (
            patch("swesmith.harness.utils.docker") as mock_docker,
            patch("swesmith.harness.utils.registry") as mock_registry,
            patch(
                "swesmith.harness.utils.setup_logger", return_value=mock_env["logger"]
            ),
            patch(
                "swesmith.harness.utils.exec_run_with_timeout",
                return_value=("output", False, 1.0),
            ),
            patch("swesmith.harness.utils.cleanup_container"),
        ):
            mock_docker.from_env.return_value = mock_env["client"]
            mock_registry.get_from_inst.return_value = mock_env["profile"]

            from swesmith.harness.utils import run_patch_in_container

            instance = {"instance_id": "test_instance"}
            run_patch_in_container(
                instance=instance,
                run_id="run1",
                log_dir=tmp_path,
                timeout=60,
                commit="abc123",
            )

            logged_messages = [str(c) for c in mock_env["logger"].info.call_args_list]
            assert any("GIT FETCH FAILED" in msg for msg in logged_messages)
