from swesmith.utils import *
from unittest.mock import patch


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
