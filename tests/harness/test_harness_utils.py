from swesmith.harness.utils import *
from swesmith.profiles import RepoProfile
import os


class MockRepoProfile(RepoProfile):
    """Mock RepoProfile for testing that uses a local directory instead of cloning."""

    def __init__(self, test_dir: str):
        self.owner = "test"
        self.repo = "test_repo"
        self.commit = "test12345678"
        self._test_dir = test_dir

    def build_image(self):
        pass

    def log_parser(self, log: str) -> dict[str, str]:
        return {}

    def clone(self, dest: str | None = None) -> str | None:
        """Override clone to use the test directory instead of git clone."""
        dest = self.repo_name if not dest else dest
        if not os.path.exists(dest):
            # Copy the test directory to the expected repo name
            import shutil

            shutil.copytree(self._test_dir, dest)
            return dest
        return None


def test_get_cached_test_paths(tmp_path):
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

    # Call get_cached_test_paths
    result = get_cached_test_paths(mock_rp)
    result_set = set(str(p) for p in result)
    # Expected: all test_files, relative to tmp_path
    expected = set(str(f.relative_to(tmp_path)) for f in test_files)
    assert result_set == expected
