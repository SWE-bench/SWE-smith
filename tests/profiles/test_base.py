import subprocess
import pytest
import os
import shutil
from dataclasses import dataclass

from swebench.harness.constants import FAIL_TO_PASS, KEY_INSTANCE_ID
from swesmith.bug_gen.mirror.generate import INSTANCE_REF
from swesmith.constants import KEY_PATCH
from swesmith.constants import ORG_NAME_GH
from swesmith.profiles import global_registry, RepoProfile
from swesmith.profiles.utils import INSTALL_CMAKE, INSTALL_BAZEL
from unittest.mock import patch


@pytest.fixture(autouse=True)
def clear_singleton_cache():
    """Clear singleton cache between tests to prevent interference."""
    from swesmith.profiles.base import SingletonMeta

    SingletonMeta._instances.clear()
    yield


@pytest.fixture(autouse=True)
def clear_test_paths_cache():
    RepoProfile._test_paths_cache.clear()


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
        result, cloned = repo_profile.clone()
        mock_exists.assert_called_once_with(expected_dest)
        mock_run.assert_called_once_with(
            expected_cmd,
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        assert result == expected_dest
        assert cloned == True

    # Test with custom dest specified
    custom_dest = "some_dir"
    expected_cmd_with_dest = (
        f"git clone git@github.com:{repo_profile.mirror_name}.git {custom_dest}"
    )

    with (
        patch("os.path.exists", return_value=False) as mock_exists,
        patch("subprocess.run") as mock_run,
    ):
        result, cloned = repo_profile.clone(custom_dest)
        mock_exists.assert_called_once_with(custom_dest)
        mock_run.assert_called_once_with(
            expected_cmd_with_dest,
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        assert result == custom_dest
        assert cloned == True

    # Test when repo already exists
    with (
        patch("os.path.exists", return_value=True) as mock_exists,
        patch("subprocess.run") as mock_run,
    ):
        result, cloned = repo_profile.clone(custom_dest)
        mock_exists.assert_called_once_with(custom_dest)
        mock_run.assert_not_called()
        assert result == custom_dest
        assert cloned == False


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
    @dataclass
    class TestProfile(RepoProfile):
        owner: str = "test"
        repo: str = "test-repo"
        commit: str = "1234567890abcdef"

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

    @dataclass
    class TestProfile(RepoProfile):
        owner: str = "test"
        repo: str = "test-repo"
        commit: str = "1234567890abcdef"

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

    @dataclass
    class TestProfile1(RepoProfile):
        owner: str = "test1"
        repo: str = "test-repo1"
        commit: str = "1234567890abcdef"

        def build_image(self):
            pass

        def log_parser(self, log: str) -> dict[str, str]:
            return {}

    @dataclass
    class TestProfile2(RepoProfile):
        owner: str = "test2"
        repo: str = "test-repo2"
        commit: str = "abcdef1234567890"

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

    # Test when mirror exists (api.repos.get does not raise)
    with patch("swesmith.profiles.base.api.repos.get", return_value=None) as mock_get:
        assert repo_profile._mirror_exists() is True
        mock_get.assert_called_once_with(
            owner=repo_profile.org_gh, repo=repo_profile.repo_name
        )

    # Test when mirror does not exist (api.repos.get raises Exception)
    with patch(
        "swesmith.profiles.base.api.repos.get", side_effect=Exception("not found")
    ) as mock_get:
        assert repo_profile._mirror_exists() is False
        mock_get.assert_called_once_with(
            owner=repo_profile.org_gh, repo=repo_profile.repo_name
        )


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


class MockRepoProfile(RepoProfile):
    """Mock RepoProfile for testing that uses a local directory instead of cloning."""

    def __init__(self, test_dir: str):
        super().__init__()  # Call parent __init__ to create the lock
        self.owner = "test"
        self.repo = "test_repo"
        self.commit = "test12345678"
        self.test_cmd = "pytest"
        self.min_testing = True
        self._test_dir = test_dir

    def build_image(self):
        pass

    def log_parser(self, log: str) -> dict[str, str]:
        return {}

    def clone(self, dest: str | None = None) -> tuple[str, bool]:
        """Override clone to use the test directory instead of git clone."""
        dest = self.repo_name if not dest else dest
        if not os.path.exists(dest):
            # Copy the test directory to the expected repo name
            shutil.copytree(self._test_dir, dest)
            return dest, True
        else:
            return dest, False


def test_get_cached_test_paths(tmp_path):
    """Test the _get_cached_test_paths method."""
    # Create directory structure
    (tmp_path / "tests").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "specs").mkdir()
    # Test files
    test_files = [
        tmp_path / "tests" / "test_foo.py",
        tmp_path / "tests" / "foo_test.py",
        tmp_path / "specs" / "bar_test.py",
        tmp_path / "src" / "test_bar.py",
        tmp_path / "src" / "baz_test.py",
    ]
    # Non-test files
    non_test_files = [
        tmp_path / "src" / "foo.py",
        tmp_path / "src" / "bar.txt",
        tmp_path / "src" / "gin.py",
    ]
    for f in test_files + non_test_files:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# test file" if f in test_files else "# not a test file")

    # Create mock RepoProfile
    mock_rp = MockRepoProfile(str(tmp_path))

    # Call _get_cached_test_paths
    result = mock_rp._get_cached_test_paths()
    result_set = set(str(p) for p in result)
    # Expected: all test_files, relative to tmp_path
    expected = set(str(f.relative_to(tmp_path)) for f in test_files)
    assert result_set == expected


def test_get_test_cmd_basic():
    """Test get_test_cmd with basic instance (no patch, no eval)."""
    mock_rp = MockRepoProfile("dummy_dir")
    mock_rp.test_cmd = "pytest"

    instance = {KEY_INSTANCE_ID: "test__test_repo.test1234.suffix"}

    test_command, test_files = mock_rp.get_test_cmd(instance)
    assert test_command == "pytest"
    assert test_files == []


def test_get_test_cmd_min_testing():
    """Test get_test_cmd when min_testing is enabled."""
    mock_rp = MockRepoProfile("dummy_dir")
    mock_rp.test_cmd = "pytest"
    mock_rp.min_testing = False

    instance = {
        KEY_INSTANCE_ID: "test__test_repo.test1234.suffix",
        KEY_PATCH: "dummy patch content",
    }

    test_command, test_files = mock_rp.get_test_cmd(instance)
    assert test_command == "pytest"
    assert test_files == []


def test_get_test_cmd_no_patch():
    """Test get_test_cmd when no patch is provided."""
    mock_rp = MockRepoProfile("dummy_dir")
    mock_rp.test_cmd = "pytest"

    instance = {
        KEY_INSTANCE_ID: "test__test_repo.test1234.suffix"
        # No KEY_PATCH
    }

    test_command, test_files = mock_rp.get_test_cmd(instance)
    assert test_command == "pytest"
    assert test_files == []


def test_get_test_cmd_with_test_patch(tmp_path):
    """Test get_test_cmd with test patch from INSTANCE_REF."""
    # Create test directory structure
    (tmp_path / "tests").mkdir()
    test_file = tmp_path / "tests" / "test_example.py"
    test_file.write_text("# test file")

    mock_rp = MockRepoProfile(str(tmp_path))
    mock_rp.test_cmd = "pytest"

    # Create a test patch that references the test file
    test_patch = """diff --git a/tests/test_example.py b/tests/test_example.py
index 1234567..abcdefg 100644
--- a/tests/test_example.py
+++ b/tests/test_example.py
@@ -1,1 +1,1 @@
-# test file
+# updated test file
"""

    instance = {
        KEY_INSTANCE_ID: "test__test_repo.test1234.suffix",
        KEY_PATCH: "dummy patch content",
        INSTANCE_REF: {"test_patch": test_patch},
    }

    test_command, test_files = mock_rp.get_test_cmd(instance)
    assert "tests/test_example.py" in test_command
    assert len(test_files) > 0


def test_get_test_cmd_with_code_patch(tmp_path):
    """Test get_test_cmd with code patch that should match test files."""
    # Create test directory structure
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()

    # Create source file
    src_file = tmp_path / "src" / "example.py"
    src_file.write_text("# source file")

    # Create corresponding test file
    test_file = tmp_path / "tests" / "test_example.py"
    test_file.write_text("# test file")

    mock_rp = MockRepoProfile(str(tmp_path))
    mock_rp.test_cmd = "pytest"

    # Create a patch that modifies the source file
    code_patch = """diff --git a/src/example.py b/src/example.py
index 1234567..abcdefg 100644
--- a/src/example.py
+++ b/src/example.py
@@ -1,1 +1,1 @@
-# source file
+# updated source file
"""

    instance = {
        KEY_INSTANCE_ID: "test__test_repo.test1234.suffix",
        KEY_PATCH: code_patch,
    }

    test_command, test_files = mock_rp.get_test_cmd(instance)
    assert "tests/test_example.py" in test_command
    assert len(test_files) > 0


def test_get_test_cmd_instance_id_mismatch():
    """Test get_test_cmd with mismatched instance ID."""
    mock_rp = MockRepoProfile("dummy_dir")
    mock_rp.test_cmd = "pytest"

    instance = {KEY_INSTANCE_ID: "different__repo.12345678.suffix"}

    with pytest.raises(
        AssertionError,
        match="WARNING: different__repo.12345678.suffix not from test__test_repo.test1234",
    ):
        mock_rp.get_test_cmd(instance)


def test_get_test_cmd_non_pytest_eval():
    """Test get_test_cmd in eval mode with non-pytest command."""
    mock_rp = MockRepoProfile("dummy_dir")
    mock_rp.test_cmd = "go test"

    instance = {
        KEY_INSTANCE_ID: "test__test_repo.test1234.suffix",
        FAIL_TO_PASS: ["test_file.go::test_function"],
    }

    test_command, test_files = mock_rp.get_test_cmd(instance)
    assert test_command == "go test"
    assert test_files == []


def test_extract_entities_simple(tmp_path):
    # Create a simple Python file with a class and a function
    py_file = tmp_path / "foo.py"
    py_file.write_text(
        """
class MyClass:
    def method(self):
        pass

def my_function(x, y):
    return x + y
"""
    )

    # Create a mock profile pointing to the temp directory
    mock_rp = MockRepoProfile(str(tmp_path))
    # Extract entities
    entities = mock_rp.extract_entities(exclude_tests=False)
    # Should find MyClass and my_function
    names = {e.name for e in entities}
    assert "MyClass" in names
    assert "my_function" in names
    print([e.file_path == str(py_file) for e in entities])
    print([e.file_path for e in entities])
    print(str(py_file))
    expected_path = f"{mock_rp.repo_name}/foo.py"
    assert all([e.file_path == expected_path for e in entities])
    # All entities should have ext == 'py'
    assert all(e.ext == "py" for e in entities)
    # Check that at least one is a class and one is a function
    assert any(getattr(e, "is_class", False) for e in entities)
    assert any(getattr(e, "is_function", False) for e in entities)
