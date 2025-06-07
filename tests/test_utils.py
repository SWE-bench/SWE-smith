from swesmith.utils import *
from unittest.mock import patch


def test_get_repo_commit_from_image_name():
    image_name = "swesmith.x86_64.instagram__monkeytype.70c3acf6"
    repo, commit = get_repo_commit_from_image_name(image_name)
    assert repo == "Instagram/MonkeyType"
    assert commit == "70c3acf62950be5dfb28743c7a719bfdecebcd84"


def test_get_repo_name():
    repo = "Instagram/MonkeyType"
    commit = "70c3acf62950be5dfb28743c7a719bfdecebcd84"
    image_name = get_image_name(repo, commit)
    assert image_name == "swesmith.x86_64.instagram__monkeytype.70c3acf6"


def test_get_full_commit():
    repo = "Instagram/MonkeyType"
    partial_commit = "70c3acf6"
    full_commit = get_full_commit(repo, partial_commit)
    assert full_commit == "70c3acf62950be5dfb28743c7a719bfdecebcd84"


def test_clone_repo():
    repo = "TestRepo"
    dest = None
    org = "TestOrg"
    expected_cmd = f"git clone git@github.com:{org}/{repo}.git"
    with (
        patch("os.path.exists", return_value=False) as mock_exists,
        patch("subprocess.run") as mock_run,
    ):
        result = clone_repo(repo, dest, org)
        mock_exists.assert_called_once_with(repo)
        mock_run.assert_called_once_with(
            expected_cmd,
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        assert result == repo

    # Test with dest specified
    dest = "some_dir"
    expected_cmd = f"git clone git@github.com:{org}/{repo}.git {dest}"
    with (
        patch("os.path.exists", return_value=False) as mock_exists,
        patch("subprocess.run") as mock_run,
    ):
        result = clone_repo(repo, dest, org)
        mock_exists.assert_called_once_with(dest)
        mock_run.assert_called_once_with(
            expected_cmd,
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        assert result == dest

    # Test when repo already exists
    with (
        patch("os.path.exists", return_value=True) as mock_exists,
        patch("subprocess.run") as mock_run,
    ):
        result = clone_repo(repo, dest, org)
        mock_exists.assert_called_once_with(dest)
        mock_run.assert_not_called()
        assert result is None


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


def test_repo_exists():
    repo_name = "TestRepo"
    # Mock environment variable and GhApi
    with (
        patch("os.getenv", return_value="dummy_token") as mock_getenv,
        patch("swesmith.utils.GhApi") as mock_GhApi,
    ):
        mock_api_instance = mock_GhApi.return_value
        # Simulate repo exists in first page
        mock_api_instance.repos.list_for_org.side_effect = [
            [{"name": repo_name}],  # page 1
            [],  # page 2
        ]
        assert repo_exists(repo_name) is True
        # Simulate repo does not exist
        mock_api_instance.repos.list_for_org.side_effect = [[{"name": "OtherRepo"}], []]
        assert repo_exists(repo_name) is False
