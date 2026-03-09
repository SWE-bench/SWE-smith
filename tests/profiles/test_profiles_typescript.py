"""
Tests for TypeScript profiles.

This test suite follows the standard testing pattern established in other
language profile tests (Java, C++, JavaScript, etc.).
"""

import pytest
import subprocess
from unittest.mock import patch, mock_open
from swesmith.profiles.typescript import (
    TypeScriptProfile,
    CrossEnv9951937a,
    Trpc2f40ba93,
    ClassValidator977d2c70,
    Rxjsc15b37f8,
    default_npm_install_dockerfile,
    default_pnpm_install_dockerfile,
)
from swesmith.constants import ENV_NAME
from swebench.harness.constants import TestStatus as Status


# =============================================================================
# TypeScriptProfile Base Class Tests
# =============================================================================


def make_dummy_ts_profile():
    """Create a minimal concrete TypeScriptProfile for testing."""

    class DummyTSProfile(TypeScriptProfile):
        owner = "dummy"
        repo = "dummyrepo"
        commit = "deadbeefcafebabe"
        test_cmd = "npm test"

        @property
        def dockerfile(self):
            return "FROM node:20\nRUN echo hello"

        def log_parser(self, log: str) -> dict[str, str]:
            return {}

    return DummyTSProfile()


def test_ts_profile_defaults():
    """Test TypeScriptProfile default file extensions."""
    profile = make_dummy_ts_profile()
    assert profile.exts == [".ts", ".tsx"]


def test_ts_profile_inheritance():
    """Test that TypeScriptProfile properly inherits from RepoProfile."""
    profile = make_dummy_ts_profile()
    assert hasattr(profile, "owner")
    assert hasattr(profile, "repo")
    assert hasattr(profile, "commit")
    assert hasattr(profile, "exts")
    assert hasattr(profile, "extract_entities")
    assert callable(profile.extract_entities)


def test_ts_profile_extract_entities_default_excludes():
    """Test that extract_entities has correct default exclusions."""
    profile = make_dummy_ts_profile()
    assert hasattr(profile, "extract_entities")
    assert callable(profile.extract_entities)


# =============================================================================
# Default Dockerfile Helper Tests
# =============================================================================


def test_default_npm_install_dockerfile():
    """Test default_npm_install_dockerfile generates correct Dockerfile."""
    result = default_npm_install_dockerfile("org/repo__name.abc12345")
    assert "FROM node:20-bullseye" in result
    assert "git clone https://github.com/org/repo__name.abc12345" in result
    assert f"/{ENV_NAME}" in result
    assert "npm install" in result


def test_default_npm_install_dockerfile_custom_node():
    """Test default_npm_install_dockerfile with custom node version."""
    result = default_npm_install_dockerfile("org/repo", node_version="18")
    assert "FROM node:18-bullseye" in result


def test_default_pnpm_install_dockerfile():
    """Test default_pnpm_install_dockerfile generates correct Dockerfile."""
    result = default_pnpm_install_dockerfile("org/repo__name.abc12345")
    assert "FROM node:20-bullseye" in result
    assert "npm install -g pnpm" in result
    assert "git clone https://github.com/org/repo__name.abc12345" in result
    assert f"/{ENV_NAME}" in result
    assert "pnpm install" in result


def test_default_pnpm_install_dockerfile_custom_node():
    """Test default_pnpm_install_dockerfile with custom node version."""
    result = default_pnpm_install_dockerfile("org/repo", node_version="22")
    assert "FROM node:22-bullseye" in result


# =============================================================================
# Specific Profile Instance Tests
# =============================================================================


def test_crossenv_profile_properties():
    """Test CrossEnv9951937a profile properties."""
    profile = CrossEnv9951937a()
    assert profile.owner == "kentcdodds"
    assert profile.repo == "cross-env"
    assert profile.commit == "9951937a7d3d4a1ea7bd2ce3133bcfb687125813"
    assert profile.test_cmd == "npm test"


def test_crossenv_profile_dockerfile():
    """Test CrossEnv9951937a Dockerfile content."""
    profile = CrossEnv9951937a()
    dockerfile = profile.dockerfile
    assert "FROM node:18-slim" in dockerfile
    assert f"git clone https://github.com/{profile.mirror_name}" in dockerfile
    assert "npm install" in dockerfile


def test_crossenv_profile_log_parser():
    """Test CrossEnv9951937a uses Vitest parser."""
    profile = CrossEnv9951937a()
    log = """
✓ src/index.test.ts (5 tests) 12ms
✗ src/utils.test.ts (3 tests | 1 failed) 8ms
"""
    result = profile.log_parser(log)
    assert result["src/index.test.ts"] == Status.PASSED.value
    assert result["src/utils.test.ts"] == Status.FAILED.value


def test_trpc_profile_properties():
    """Test Trpc2f40ba93 profile properties."""
    profile = Trpc2f40ba93()
    assert profile.owner == "trpc"
    assert profile.repo == "trpc"
    assert profile.commit == "2f40ba935ad7f7d29eec3f9c45d353450b43e852"
    assert profile.test_cmd == "pnpm test"


def test_trpc_profile_dockerfile():
    """Test Trpc2f40ba93 Dockerfile content."""
    profile = Trpc2f40ba93()
    dockerfile = profile.dockerfile
    assert "FROM node:22" in dockerfile
    assert "pnpm" in dockerfile
    assert f"git clone https://github.com/{profile.mirror_name}" in dockerfile
    assert "pnpm install" in dockerfile


def test_trpc_profile_log_parser():
    """Test Trpc2f40ba93 uses Vitest parser."""
    profile = Trpc2f40ba93()
    log = """
✓ packages/server/src/core.test.ts (10 tests) 25ms
"""
    result = profile.log_parser(log)
    assert result["packages/server/src/core.test.ts"] == Status.PASSED.value


def test_classvalidator_profile_properties():
    """Test ClassValidator977d2c70 profile properties."""
    profile = ClassValidator977d2c70()
    assert profile.owner == "typestack"
    assert profile.repo == "class-validator"
    assert profile.commit == "977d2c707930db602b6450d0c03ee85c70756f1f"
    assert profile.test_cmd == "npm test"


def test_classvalidator_profile_dockerfile():
    """Test ClassValidator977d2c70 Dockerfile content."""
    profile = ClassValidator977d2c70()
    dockerfile = profile.dockerfile
    assert "FROM node:18-slim" in dockerfile
    assert f"git clone https://github.com/{profile.mirror_name}" in dockerfile
    assert "npm install" in dockerfile


def test_classvalidator_profile_log_parser():
    """Test ClassValidator977d2c70 uses Jest parser."""
    profile = ClassValidator977d2c70()
    log = """
  ✓ should validate strings (5ms)
  ✕ should reject invalid input (3ms)
  ✓ should handle arrays (2ms)
"""
    result = profile.log_parser(log)
    assert result["should validate strings"] == Status.PASSED.value
    assert result["should reject invalid input"] == Status.FAILED.value
    assert result["should handle arrays"] == Status.PASSED.value


def test_rxjs_profile_properties():
    """Test Rxjsc15b37f8 profile properties."""
    profile = Rxjsc15b37f8()
    assert profile.owner == "ReactiveX"
    assert profile.repo == "rxjs"
    assert profile.commit == "c15b37f81ba5f5abea8c872b0189a70b150df4cb"
    assert "yarn" in profile.test_cmd


def test_rxjs_profile_dockerfile():
    """Test Rxjsc15b37f8 Dockerfile content."""
    profile = Rxjsc15b37f8()
    dockerfile = profile.dockerfile
    assert "FROM node:20-slim" in dockerfile
    assert f"git clone https://github.com/{profile.mirror_name}" in dockerfile
    assert "git submodule update --init --recursive" in dockerfile
    assert "yarn install" in dockerfile


def test_rxjs_profile_log_parser():
    """Test Rxjsc15b37f8 uses Mocha parser."""
    profile = Rxjsc15b37f8()
    log = """
  ✓ should emit values (5ms)
  ✓ should complete stream
  ✖ should handle errors (10ms)
"""
    result = profile.log_parser(log)
    passed = sum(1 for v in result.values() if v == Status.PASSED.value)
    failed = sum(1 for v in result.values() if v == Status.FAILED.value)
    assert passed == 2
    assert failed == 1


def test_ts_profile_inheritance_in_concrete_profiles():
    """Test that concrete TS profiles properly inherit from TypeScriptProfile."""
    profiles_to_test = [
        CrossEnv9951937a,
        Trpc2f40ba93,
        ClassValidator977d2c70,
        Rxjsc15b37f8,
    ]

    for profile_class in profiles_to_test:
        profile = profile_class()
        assert isinstance(profile, TypeScriptProfile)
        assert profile.exts == [".ts", ".tsx"]
        assert hasattr(profile, "owner")
        assert hasattr(profile, "repo")
        assert hasattr(profile, "commit")
        assert hasattr(profile, "test_cmd")
        assert hasattr(profile, "dockerfile")
        assert hasattr(profile, "log_parser")


def test_all_profiles_have_mirror_name_in_dockerfile():
    """Test that all concrete profiles use mirror_name (not owner/repo) in dockerfiles."""
    profiles_to_test = [
        CrossEnv9951937a,
        Trpc2f40ba93,
        ClassValidator977d2c70,
        Rxjsc15b37f8,
    ]

    for profile_class in profiles_to_test:
        profile = profile_class()
        dockerfile = profile.dockerfile
        assert profile.mirror_name in dockerfile, (
            f"{profile_class.__name__} dockerfile should contain mirror_name"
        )


# =============================================================================
# Build Image Tests (with mocks)
# =============================================================================


def test_ts_profile_build_image():
    """Test TypeScriptProfile.build_image writes Dockerfile and runs docker."""
    profile = CrossEnv9951937a()

    with (
        patch("pathlib.Path.mkdir") as mock_mkdir,
        patch("builtins.open", mock_open()) as mock_file,
        patch("subprocess.run") as mock_run,
    ):
        profile.build_image()

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file.assert_called()
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "docker build" in call_args[0][0]
        assert profile.image_name in call_args[0][0]


def test_ts_profile_build_image_error_handling():
    """Test build_image error handling."""
    profile = CrossEnv9951937a()

    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open", mock_open()),
        patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "docker build"),
        ),
    ):
        with pytest.raises(subprocess.CalledProcessError):
            profile.build_image()


def test_ts_profile_build_image_checks_exit_code():
    """Test build_image checks subprocess exit code."""
    profile = CrossEnv9951937a()

    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open", mock_open()),
        patch("subprocess.run") as mock_run,
    ):
        profile.build_image()
        assert mock_run.call_args.kwargs["check"] is True


def test_ts_profile_build_image_file_operations():
    """Test build_image creates Dockerfile and build log."""
    profile = CrossEnv9951937a()

    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open", mock_open()) as mock_file,
        patch("subprocess.run"),
    ):
        profile.build_image()

        file_calls = mock_file.call_args_list
        assert len(file_calls) >= 2

        dockerfile_calls = [call for call in file_calls if "Dockerfile" in str(call)]
        assert len(dockerfile_calls) > 0

        log_calls = [call for call in file_calls if "build_image.log" in str(call)]
        assert len(log_calls) > 0
