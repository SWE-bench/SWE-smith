import pytest
import subprocess

from swesmith.profiles.golang import GoProfile, Gin3c12d2a8
from unittest.mock import patch, mock_open


# Minimal concrete GoProfile for generic tests
def make_dummy_go_profile():
    class DummyGoProfile(GoProfile):
        owner = "dummy"
        repo = "dummyrepo"
        commit = "deadbeefcafebabe"

        @property
        def dockerfile(self):
            return "FROM golang:1.20\nRUN echo hello"

    return DummyGoProfile()


def test_go_profile_log_parser_basic():
    profile = make_dummy_go_profile()
    log = """
=== RUN   TestFoo
--- PASS: TestFoo (0.01s)
=== RUN   TestBar
--- FAIL: TestBar (0.02s)
=== RUN   TestBaz
--- SKIP: TestBaz (0.00s)
PASS
ok      github.com/dummy/dummyrepo    0.030s
"""
    result = profile.log_parser(log)
    assert result["TestFoo"] == "PASSED"
    assert result["TestBar"] == "FAILED"
    assert result["TestBaz"] == "SKIPPED"


def test_go_profile_log_parser_no_matches():
    profile = make_dummy_go_profile()
    log = """
=== RUN   TestFoo
Some random output
PASS
ok      github.com/dummy/dummyrepo    0.030s
"""
    result = profile.log_parser(log)
    assert result == {}


def test_go_profile_log_parser_edge_cases():
    profile = make_dummy_go_profile()
    # Empty log
    assert profile.log_parser("") == {}
    # Whitespace only
    assert profile.log_parser("   \n  \t  \n") == {}
    # Malformed lines
    log = """
--- PASS: TestFoo
--- FAIL: TestBar (0.02s
--- SKIP: TestBaz (0.00s)
"""
    result = profile.log_parser(log)
    assert "TestBar" in result
    assert "TestBaz" in result


def test_go_profile_log_parser_multiple_tests():
    profile = make_dummy_go_profile()
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


def test_go_profile_build_image_writes_dockerfile_and_runs_docker():
    profile = make_dummy_go_profile()
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


def test_go_profile_build_image_error_handling():
    profile = make_dummy_go_profile()
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


def test_go_profile_build_image_checks_exit_code():
    profile = make_dummy_go_profile()
    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open", mock_open()),
        patch(
            "subprocess.run",
        ) as mock_run,
    ):
        profile.build_image()
        assert mock_run.call_args.kwargs["check"] is True


def test_go_profile_build_image_file_operations():
    profile = make_dummy_go_profile()
    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open", mock_open()) as mock_file,
        patch("subprocess.run"),
    ):
        profile.build_image()
        file_calls = mock_file.call_args_list
        assert len(file_calls) >= 2  # Dockerfile and build log
        dockerfile_calls = [call for call in file_calls if "Dockerfile" in str(call)]
        assert len(dockerfile_calls) > 0
        log_calls = [call for call in file_calls if "build_image.log" in str(call)]
        assert len(log_calls) > 0


def test_go_profile_build_image_subprocess_parameters():
    profile = make_dummy_go_profile()
    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open", mock_open()),
        patch("subprocess.run") as mock_run,
    ):
        profile.build_image()
        call_args = mock_run.call_args
        assert call_args[1]["shell"] is True
        assert call_args[1]["stdout"] is not None
        assert call_args[1]["stderr"] == subprocess.STDOUT


def test_go_profile_go_test_command():
    profile = make_dummy_go_profile()
    assert profile.test_cmd == "go test -v ./..."
    assert "go test" in profile.test_cmd
    assert "-v" in profile.test_cmd
    assert "./..." in profile.test_cmd


def test_gin_profile_dockerfile_content():
    # This test is Gin-specific and checks the Gin profile's Dockerfile
    profile = Gin3c12d2a8()
    dockerfile = profile.dockerfile
    assert "FROM golang:1.24" in dockerfile
    assert f"git clone https://github.com/{profile.mirror_name}" in dockerfile
    assert "WORKDIR /testbed" in dockerfile
    assert "go mod tidy" in dockerfile
