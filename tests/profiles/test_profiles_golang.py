import pytest
from unittest.mock import patch, mock_open
import subprocess
import re

from swesmith.profiles.golang import Gin3c12d2a8
from swesmith.profiles import global_registry


def test_gin_profile_attributes():
    """Test Gin3c12d2a8 profile attributes"""
    profile = Gin3c12d2a8()

    assert profile.owner == "gin-gonic"
    assert profile.repo == "gin"
    assert profile.commit == "3c12d2a80e40930632fc4a4a4e1a45140f33fb12"
    assert profile.test_cmd == "go test -v ./..."


def test_gin_profile_build_image():
    """Test Gin3c12d2a8.build_image method"""
    profile = Gin3c12d2a8()

    with (
        patch("pathlib.Path.mkdir") as mock_mkdir,
        patch("builtins.open", mock_open()) as mock_file,
        patch("subprocess.run") as mock_run,
    ):
        profile.build_image()

        # Verify directory was created
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Verify Dockerfile was written
        mock_file.assert_called()

        # Verify subprocess.run was called for docker build
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "docker build" in call_args[0][0]
        assert profile.image_name in call_args[0][0]


def test_gin_profile_build_image_dockerfile_content():
    """Test that the generated Dockerfile has correct content"""
    profile = Gin3c12d2a8()

    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open", mock_open()) as mock_file,
        patch("subprocess.run"),
    ):
        profile.build_image()

        # Get the written content
        written_content = mock_file().write.call_args[0][0]

        # Check Dockerfile content
        assert "FROM golang:1.24" in written_content
        assert f"git clone https://github.com/{profile.mirror_name}" in written_content
        assert "WORKDIR /testbed" in written_content
        assert "go mod tidy" in written_content
        assert "go test ./..." in written_content


def test_gin_profile_log_parser():
    """Test Gin3c12d2a8.log_parser method"""
    profile = Gin3c12d2a8()

    log = """
=== RUN   TestFoo
--- PASS: TestFoo (0.01s)
=== RUN   TestBar
--- FAIL: TestBar (0.02s)
=== RUN   TestBaz
--- SKIP: TestBaz (0.00s)
PASS
ok      github.com/gin-gonic/gin    0.030s
"""

    result = profile.log_parser(log)

    assert result["TestFoo"] == "PASSED"
    assert result["TestBar"] == "FAILED"
    assert result["TestBaz"] == "SKIPPED"


def test_gin_profile_log_parser_no_matches():
    """Test Gin3c12d2a8.log_parser with no matching lines"""
    profile = Gin3c12d2a8()

    log = """
=== RUN   TestFoo
Some random output
PASS
ok      github.com/gin-gonic/gin    0.030s
"""

    result = profile.log_parser(log)
    assert result == {}


def test_gin_profile_log_parser_edge_cases():
    """Test Gin3c12d2a8.log_parser with edge cases"""
    profile = Gin3c12d2a8()

    # Test empty log
    result = profile.log_parser("")
    assert result == {}

    # Test log with only whitespace
    result = profile.log_parser("   \n  \t  \n")
    assert result == {}

    # Test log with malformed lines
    log = """
--- PASS: TestFoo
--- FAIL: TestBar (0.02s
--- SKIP: TestBaz (0.00s)
"""
    result = profile.log_parser(log)
    # Only the properly formatted line should be parsed
    assert "TestBar" not in result  # Malformed line
    assert "TestBaz" in result  # Properly formatted line


def test_gin_profile_log_parser_multiple_tests():
    """Test Gin3c12d2a8.log_parser with multiple test results"""
    profile = Gin3c12d2a8()

    log = """
--- PASS: TestHandler (0.01s)
--- PASS: TestMiddleware (0.02s)
--- FAIL: TestRouter (0.03s)
--- SKIP: TestContext (0.00s)
--- PASS: TestEngine (0.04s)
--- FAIL: TestBinding (0.05s)
"""

    result = profile.log_parser(log)

    assert len(result) == 6
    assert result["TestHandler"] == "PASSED"
    assert result["TestMiddleware"] == "PASSED"
    assert result["TestRouter"] == "FAILED"
    assert result["TestContext"] == "SKIPPED"
    assert result["TestEngine"] == "PASSED"
    assert result["TestBinding"] == "FAILED"


def test_gin_profile_registry_integration():
    """Test that Gin3c12d2a8 is properly registered in global registry"""
    key = "gin-gonic__gin.3c12d2a8"
    profile = global_registry.get(key)

    assert profile is not None
    assert isinstance(profile, Gin3c12d2a8)
    assert profile.owner == "gin-gonic"
    assert profile.repo == "gin"


def test_gin_profile_build_image_error_handling():
    """Test Gin3c12d2a8.build_image error handling"""
    profile = Gin3c12d2a8()

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


def test_gin_profile_build_image_file_operations():
    """Test file operations in Gin3c12d2a8.build_image"""
    profile = Gin3c12d2a8()

    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open", mock_open()) as mock_file,
        patch("subprocess.run"),
    ):
        profile.build_image()

        # Verify files were opened for writing
        file_calls = mock_file.call_args_list
        assert len(file_calls) >= 2  # Dockerfile and build log

        # Check that Dockerfile was written
        dockerfile_calls = [call for call in file_calls if "Dockerfile" in str(call)]
        assert len(dockerfile_calls) > 0

        # Check that build log was written
        log_calls = [call for call in file_calls if "build_image.log" in str(call)]
        assert len(log_calls) > 0


def test_gin_profile_inheritance():
    """Test that Gin3c12d2a8 properly inherits from RepoProfile"""
    profile = Gin3c12d2a8()

    from swesmith.profiles.base import RepoProfile

    assert isinstance(profile, RepoProfile)

    # Test that it has required abstract methods
    assert hasattr(profile, "build_image")
    assert hasattr(profile, "log_parser")

    # Test that it has RepoProfile properties
    assert hasattr(profile, "owner")
    assert hasattr(profile, "repo")
    assert hasattr(profile, "commit")
    assert hasattr(profile, "image_name")
    assert hasattr(profile, "mirror_name")
    assert hasattr(profile, "repo_name")


def test_gin_profile_log_parser_regex_pattern():
    """Test the regex pattern used in Gin3c12d2a8.log_parser"""
    profile = Gin3c12d2a8()

    # Test the regex pattern directly
    pattern = r"^--- (PASS|FAIL|SKIP): (.+) \((.+)\)$"

    # Valid test result lines
    valid_lines = [
        "--- PASS: TestFoo (0.01s)",
        "--- FAIL: TestBar (0.02s)",
        "--- SKIP: TestBaz (0.00s)",
    ]

    for line in valid_lines:
        match = re.match(pattern, line.strip())
        assert match is not None
        status, test_name, duration = match.groups()
        assert status in ["PASS", "FAIL", "SKIP"]
        assert test_name is not None
        assert duration is not None

    # Invalid test result lines
    invalid_lines = [
        "--- PASS: TestFoo",
        "--- FAIL: TestBar",
        "TestFoo PASSED",
        "TestBar FAILED",
    ]

    for line in invalid_lines:
        match = re.match(pattern, line.strip())
        assert match is None


def test_gin_profile_build_image_subprocess_parameters():
    """Test subprocess parameters in Gin3c12d2a8.build_image"""
    profile = Gin3c12d2a8()

    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open", mock_open()),
        patch("subprocess.run") as mock_run,
    ):
        profile.build_image()

        # Verify subprocess.run was called with correct parameters
        call_args = mock_run.call_args
        assert call_args[1]["shell"] is True
        assert call_args[1]["stdout"] is not None  # Should be a file object
        assert call_args[1]["stderr"] == subprocess.STDOUT


def test_gin_profile_go_test_command():
    """Test that the go test command is correctly specified"""
    profile = Gin3c12d2a8()

    assert profile.test_cmd == "go test -v ./..."

    # This is the standard Go test command format
    assert "go test" in profile.test_cmd
    assert "-v" in profile.test_cmd  # Verbose output
    assert "./..." in profile.test_cmd  # Test all packages recursively


def test_gin_profile_log_parser_with_real_gotest_output(test_output_gotest):
    """Test Gin3c12d2a8.log_parser method with real gotest output"""
    profile = Gin3c12d2a8()

    # Read the actual gotest output file
    log_content = test_output_gotest.read_text()

    # Parse the log using the profile's log_parser method
    result = profile.log_parser(log_content)

    # Verify the result is a dictionary with string keys and values
    assert isinstance(result, dict)
    assert all(
        isinstance(key, str) and isinstance(value, str) for key, value in result.items()
    )

    # Test specific test results that we know should be in the output
    expected_results = [
        ("TestRouteStaticNoListing", "FAILED"),
        ("TestBasicAuth", "PASSED"),
        ("TestContextGetInt8", "PASSED"),
        (
            "TestContextInitQueryCache/queryCache_should_remain_unchanged_if_already_not_nil",
            "PASSED",
        ),
    ]

    for test_name, expected_status in expected_results:
        assert test_name in result, f"Test {test_name} not found in parsed results"
        assert result[test_name] == expected_status, (
            f"Expected {test_name} to be {expected_status}, got {result[test_name]}"
        )

    # Verify that we have a reasonable number of test results
    # The actual file contains many more tests, so we should have a substantial number
    assert len(result) > 100, f"Expected many test results, got {len(result)}"

    # Verify that all status values are valid
    valid_statuses = {"PASSED", "FAILED", "SKIPPED"}
    for status in result.values():
        assert status in valid_statuses, f"Invalid status: {status}"
