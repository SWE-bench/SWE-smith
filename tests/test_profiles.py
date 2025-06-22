from swesmith.constants import ORG_NAME_GH
from swesmith.profiles import global_registry, RepoProfile
from swesmith.profiles.utils import INSTALL_CMAKE, INSTALL_BAZEL
from unittest.mock import patch
import subprocess


def test_registry_keys_and_lookup():
    # Should have many keys after importing profiles
    keys = global_registry.keys()
    assert len(keys) > 0
    # Pick a known profile
    key = "mewwts__addict.75284f95"
    repo_profile = global_registry.get(key)
    assert repo_profile is not None
    assert isinstance(repo_profile, RepoProfile)
    assert repo_profile.owner == "mewwts"
    assert repo_profile.repo == "addict"
    assert repo_profile.commit.startswith("75284f95")
    # Mirror name matches key
    assert repo_profile.mirror_name == f"{ORG_NAME_GH}/{key}"


def test_image_name():
    repo_profile = global_registry.get("mewwts__addict.75284f95")
    image_name = repo_profile.image_name
    assert "swesmith" in image_name
    assert repo_profile.owner in image_name
    assert repo_profile.repo in image_name
    assert repo_profile.commit[:8] in image_name


def test_repo_profile_clone():
    """Test the RepoProfile.clone method, adapted from the original clone_repo test."""
    repo_profile = global_registry.get("mewwts__addict.75284f95")

    # Test with default dest (should use repo_name)
    expected_dest = repo_profile.repo_name
    expected_cmd = f"git clone git@github.com:{repo_profile.mirror_name}.git {repo_profile.repo_name}"

    with (
        patch("os.path.exists", return_value=False) as mock_exists,
        patch("subprocess.run") as mock_run,
    ):
        result = repo_profile.clone()
        mock_exists.assert_called_once_with(expected_dest)
        mock_run.assert_called_once_with(
            expected_cmd,
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        assert result == expected_dest

    # Test with custom dest specified
    custom_dest = "some_dir"
    expected_cmd_with_dest = (
        f"git clone git@github.com:{repo_profile.mirror_name}.git {custom_dest}"
    )

    with (
        patch("os.path.exists", return_value=False) as mock_exists,
        patch("subprocess.run") as mock_run,
    ):
        result = repo_profile.clone(custom_dest)
        mock_exists.assert_called_once_with(custom_dest)
        mock_run.assert_called_once_with(
            expected_cmd_with_dest,
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        assert result == custom_dest

    # Test when repo already exists
    with (
        patch("os.path.exists", return_value=True) as mock_exists,
        patch("subprocess.run") as mock_run,
    ):
        result = repo_profile.clone(custom_dest)
        mock_exists.assert_called_once_with(custom_dest)
        mock_run.assert_not_called()
        assert result is None


def test_python_log_parser():
    # Use the default PythonProfile log_parser
    repo_profile = global_registry.get("mewwts__addict.75284f95")
    log = "test_foo.py PASSED\ntest_bar.py FAILED\ntest_baz.py SKIPPED"

    # Patch TestStatus for this test
    class DummyStatus:
        PASSED = type("T", (), {"value": "PASSED"})
        FAILED = type("T", (), {"value": "FAILED"})
        SKIPPED = type("T", (), {"value": "SKIPPED"})

    import swebench.harness.constants as harness_constants

    old = harness_constants.TestStatus
    harness_constants.TestStatus = [
        DummyStatus.PASSED,
        DummyStatus.FAILED,
        DummyStatus.SKIPPED,
    ]
    try:
        result = repo_profile.log_parser(log)
        assert result["test_foo.py"] == "PASSED"
        assert result["test_bar.py"] == "FAILED"
        assert result["test_baz.py"] == "SKIPPED"
    finally:
        harness_constants.TestStatus = old


def test_golang_log_parser():
    # Use Gin3c12d2a8 Go profile
    key = "gin-gonic__gin.3c12d2a8"
    repo_profile = global_registry.get(key)
    log = """
--- PASS: TestFoo (0.01s)
--- FAIL: TestBar (0.02s)
--- SKIP: TestBaz (0.00s)
"""

    class DummyStatus:
        PASSED = type("T", (), {"value": "PASSED"})
        FAILED = type("T", (), {"value": "FAILED"})
        SKIPPED = type("T", (), {"value": "SKIPPED"})

    import swebench.harness.constants as harness_constants

    old = harness_constants.TestStatus
    harness_constants.TestStatus = DummyStatus
    try:
        result = repo_profile.log_parser(log)
        assert result["TestFoo"] == "PASSED"
        assert result["TestBar"] == "FAILED"
        assert result["TestBaz"] == "SKIPPED"
    finally:
        harness_constants.TestStatus = old


def test_utils_install_constants():
    assert isinstance(INSTALL_CMAKE, list)
    assert any("cmake" in cmd for cmd in INSTALL_CMAKE)
    assert isinstance(INSTALL_BAZEL, list)
    assert any("bazel" in cmd for cmd in INSTALL_BAZEL)
