from swesmith.harness.utils import *


def test_get_test_paths(tmp_path):
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

    # Call get_test_paths
    result = get_test_paths(str(tmp_path))
    result_set = set(str(p) for p in result)
    # Expected: all test_files, relative to tmp_path
    expected = set(str(f.relative_to(tmp_path)) for f in test_files)
    assert result_set == expected
