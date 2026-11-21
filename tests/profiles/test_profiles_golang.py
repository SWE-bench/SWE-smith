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
    assert profile.test_cmd == "go test -json ./..."
    assert "go test" in profile.test_cmd
    assert "-json" in profile.test_cmd
    assert "./..." in profile.test_cmd


def test_gin_profile_dockerfile_content():
    # This test is Gin-specific and checks the Gin profile's Dockerfile
    profile = Gin3c12d2a8()
    dockerfile = profile.dockerfile
    assert "FROM golang:1.24" in dockerfile
    assert f"git clone https://github.com/{profile.mirror_name}" in dockerfile
    assert "WORKDIR /testbed" in dockerfile
    assert "go mod tidy" in dockerfile


def test_package_qualified_results_and_legacy_lookup():
    profile = make_dummy_go_profile()
    log = """
{"Action":"fail","Package":"example.com/m/config","Test":"TestParse"}
{"Action":"pass","Package":"example.com/m/version","Test":"TestParse"}
{"Action":"skip","Package":"example.com/m/version","Test":"TestUnique"}
{"Action":"fail","Package":"example.com/m/config"}
"""
    instance = {"FAIL_TO_PASS": ["TestParse"], "PASS_TO_PASS": ["TestUnique"]}
    parsed = profile.log_parser(log)
    assert parsed == {
        "example.com/m/config::TestParse": "FAILED",
        "example.com/m/version::TestParse": "PASSED",
        "example.com/m/version::TestUnique": "SKIPPED",
        "example.com/m/config": "FAILED",
    }
    assert profile.eval_log_parser(log, instance) == {**parsed, "TestUnique": "SKIPPED"}


def test_go_test_file_lookup_handles_qualified_subtests():
    profile = make_dummy_go_profile()
    profile._test_name_to_files_cache = {"TestParse": {"config/parse_test.go"}}
    instance = {
        "FAIL_TO_PASS": ["example.com/m/config::TestParse/missing"],
        "PASS_TO_PASS": ["TestParse"],
    }
    assert profile.get_test_files(instance) == (
        ["config/parse_test.go"],
        ["config/parse_test.go"],
    )


def test_archived_go_log_keeps_colliding_names_apart():
    profile = make_dummy_go_profile()
    log = (
        "--- FAIL: TestParse (0.01s)\n"
        "FAIL\texample.com/m/config\t0.02s\n"
        "--- PASS: TestParse (0.01s)\n"
        "--- PASS: TestUnique (0.00s)\n"
        "ok\texample.com/m/version\t0.03s\n"
    )
    assert profile.log_parser(log) == {
        "example.com/m/config": "FAILED",
        "example.com/m/config::TestParse": "FAILED",
        "example.com/m/version::TestParse": "PASSED",
        "TestUnique": "PASSED",
    }


def test_failed_build_suppresses_unproven_legacy_alias():
    profile = make_dummy_go_profile()
    log = """
{"Action":"start","Package":"example.com/m/config"}
{"Action":"fail","Package":"example.com/m/config","FailedBuild":"example.com/m/config"}
{"Action":"start","Package":"example.com/m/version"}
{"Action":"pass","Package":"example.com/m/version","Test":"TestParse"}
{"Action":"pass","Package":"example.com/m/version"}
"""
    instance = {"FAIL_TO_PASS": ["TestParse"], "PASS_TO_PASS": []}
    assert profile.eval_log_parser(log, instance) == {
        "example.com/m/config": "FAILED",
        "example.com/m/version::TestParse": "PASSED",
    }


def test_go_f2p_only_grades_tests_in_selected_packages():
    profile = Gin3c12d2a8()
    instance = {
        "instance_id": f"{profile.repo_name}.fixture",
        "FAIL_TO_PASS": ["example.com/m/config::TestParse"],
        "PASS_TO_PASS": [
            "example.com/m/config::TestDefault",
            "example.com/m/version::TestParse",
        ],
    }
    assert profile.get_test_cmd(instance, f2p_only=True) == ("go test -json ./...", [])
    selected = profile.select_f2p_tests(instance)
    assert selected["FAIL_TO_PASS"] == instance["FAIL_TO_PASS"]
    assert selected["PASS_TO_PASS"] == ["example.com/m/config::TestDefault"]
    assert len(instance["PASS_TO_PASS"]) == 2


def test_go_cached_verbose_baseline_matches_json_results(tmp_path):
    from swesmith.constants import TEST_OUTPUT_END, TEST_OUTPUT_START
    from swesmith.harness.grading import get_valid_report

    profile = Gin3c12d2a8()
    archive = tmp_path / "cached.log"
    new_run = tmp_path / "new.log"

    def save(path, output):
        path.write_text(f"+ : '{TEST_OUTPUT_START}'\n{output}\n+ : '{TEST_OUTPUT_END}'\n")

    save(
        archive,
        "--- PASS: TestUnique (0.01s)\n"
        "ok\tgithub.com/gin-gonic/gin\t0.02s",
    )
    save(
        new_run,
        '{"Action":"fail","Package":"github.com/gin-gonic/gin","Test":"TestUnique"}',
    )
    report = get_valid_report(str(new_run), str(archive), {"repo": profile.repo_name})
    assert report["FAIL_TO_PASS"] == ["github.com/gin-gonic/gin::TestUnique"]
