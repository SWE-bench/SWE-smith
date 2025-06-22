from swesmith.constants import ORG_NAME_GH
from swesmith.profiles import global_registry, RepoProfile
from swesmith.profiles.utils import INSTALL_CMAKE, INSTALL_BAZEL
from unittest.mock import patch
import subprocess
import pytest


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


def test_registry_register_profile():
    """Test Registry.register_profile method"""
    from swesmith.profiles.base import Registry

    registry = Registry()

    # Test registering a valid profile class
    class TestProfile(RepoProfile):
        owner = "test"
        repo = "test-repo"
        commit = "1234567890abcdef"

        def build_image(self):
            pass

        def log_parser(self, log: str) -> dict[str, str]:
            return {}

    registry.register_profile(TestProfile)
    assert "test__test-repo.12345678" in registry.keys()

    # Test that abstract base class cannot be registered
    registry.register_profile(RepoProfile)
    assert (
        "test__test-repo.12345678" in registry.keys()
    )  # Only the valid one should be there


def test_registry_get_from_inst():
    """Test Registry.get_from_inst method"""
    from swesmith.profiles.base import Registry
    from swebench.harness.constants import KEY_INSTANCE_ID

    registry = Registry()

    class TestProfile(RepoProfile):
        owner = "test"
        repo = "test-repo"
        commit = "1234567890abcdef"

        def build_image(self):
            pass

        def log_parser(self, log: str) -> dict[str, str]:
            return {}

    registry.register_profile(TestProfile)

    # Test getting profile from instance
    instance = {KEY_INSTANCE_ID: "test__test-repo.12345678.some_suffix"}
    profile = registry.get_from_inst(instance)
    assert isinstance(profile, TestProfile)
    assert profile.owner == "test"
    assert profile.repo == "test-repo"


def test_registry_values():
    """Test Registry.values method"""
    from swesmith.profiles.base import Registry

    registry = Registry()

    class TestProfile1(RepoProfile):
        owner = "test1"
        repo = "test-repo1"
        commit = "1234567890abcdef"

        def build_image(self):
            pass

        def log_parser(self, log: str) -> dict[str, str]:
            return {}

    class TestProfile2(RepoProfile):
        owner = "test2"
        repo = "test-repo2"
        commit = "abcdef1234567890"

        def build_image(self):
            pass

        def log_parser(self, log: str) -> dict[str, str]:
            return {}

    registry.register_profile(TestProfile1)
    registry.register_profile(TestProfile2)

    values = registry.values()
    assert len(values) == 2
    assert all(isinstance(v, RepoProfile) for v in values)
    assert any(v.owner == "test1" for v in values)
    assert any(v.owner == "test2" for v in values)


def test_mirror_exists():
    """Test _mirror_exists method"""
    repo_profile = global_registry.get("mewwts__addict.75284f95")

    # Mock the GitHub API response
    mock_repos = [
        {"name": "mewwts__addict.75284f95"},
        {"name": "other_repo"},
    ]

    with patch("swesmith.profiles.base.api") as mock_api:
        mock_api.repos.list_for_org.return_value = mock_repos
        assert repo_profile._mirror_exists() is True

    # Test when mirror doesn't exist
    mock_repos_no_match = [
        {"name": "other_repo1"},
        {"name": "other_repo2"},
    ]

    with patch("swesmith.profiles.base.api") as mock_api:
        mock_api.repos.list_for_org.return_value = mock_repos_no_match
        assert repo_profile._mirror_exists() is False


def test_create_mirror():
    """Test create_mirror method"""
    repo_profile = global_registry.get("mewwts__addict.75284f95")

    with (
        patch.object(repo_profile, "_mirror_exists", return_value=True),
        patch("os.listdir", return_value=[]),
        patch("shutil.rmtree"),
        patch("swesmith.profiles.base.api") as mock_api,
        patch("subprocess.run") as mock_run,
    ):
        repo_profile.create_mirror()

        # Should not create mirror if it already exists
        mock_api.repos.create_in_org.assert_not_called()
        mock_run.assert_not_called()

    # Test creating new mirror
    with (
        patch.object(repo_profile, "_mirror_exists", return_value=False),
        patch("os.listdir", return_value=[repo_profile.repo_name]),
        patch("shutil.rmtree"),
        patch("swesmith.profiles.base.api") as mock_api,
        patch("subprocess.run") as mock_run,
    ):
        repo_profile.create_mirror()

        # Should create mirror and run git commands
        mock_api.repos.create_in_org.assert_called_once()
        assert mock_run.call_count == 3  # Three git commands


def test_repo_profile_properties():
    """Test RepoProfile properties"""
    repo_profile = global_registry.get("mewwts__addict.75284f95")

    # Test repo_name property
    expected_repo_name = (
        f"{repo_profile.owner}__{repo_profile.repo}.{repo_profile.commit[:8]}"
    )
    assert repo_profile.repo_name == expected_repo_name

    # Test mirror_name property
    expected_mirror_name = f"{repo_profile.org_gh}/{repo_profile.repo_name}"
    assert repo_profile.mirror_name == expected_mirror_name

    # Test image_name property
    image_name = repo_profile.image_name
    assert repo_profile.org_dh in image_name
    assert "swesmith" in image_name
    assert repo_profile.arch in image_name
    assert repo_profile.owner in image_name
    assert repo_profile.repo in image_name
    assert repo_profile.commit[:8] in image_name


def test_repo_profile_platform_detection():
    """Test platform detection in RepoProfile"""
    repo_profile = global_registry.get("mewwts__addict.75284f95")

    # Test that arch and pltf are set based on platform
    assert repo_profile.arch in ["x86_64", "arm64"]
    assert repo_profile.pltf in ["linux/x86_64", "linux/arm64/v8"]

    # Test that they are consistent
    if repo_profile.arch == "x86_64":
        assert repo_profile.pltf == "linux/x86_64"
    else:
        assert repo_profile.pltf == "linux/arm64/v8"


def test_clone_mirror_not_exists():
    """Test clone method when mirror doesn't exist"""
    repo_profile = global_registry.get("mewwts__addict.75284f95")

    with patch.object(repo_profile, "_mirror_exists", return_value=False):
        with pytest.raises(ValueError, match="Mirror clone repo must be created first"):
            repo_profile.clone()


def test_clone_subprocess_error():
    """Test clone method when subprocess fails"""
    repo_profile = global_registry.get("mewwts__addict.75284f95")

    with (
        patch.object(repo_profile, "_mirror_exists", return_value=True),
        patch("os.path.exists", return_value=False),
        patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, "git clone")
        ),
    ):
        with pytest.raises(subprocess.CalledProcessError):
            repo_profile.clone()
