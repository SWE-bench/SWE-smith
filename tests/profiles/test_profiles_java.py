"""
Tests for Java profiles and log parsers.

This test suite follows the standard testing pattern established in other
language profile tests (Go, JavaScript, Python, Rust).
"""

import pytest
import subprocess
from unittest.mock import patch, mock_open
from swesmith.profiles.java import (
    JavaProfile,
    parse_log_maven_surefire,
    parse_log_gradle_junit_xml,
    Gsondd2fe59c,
    Eureka459fcf59,
)
from swebench.harness.constants import TestStatus as Status


# =============================================================================
# JavaProfile Base Class Tests
# =============================================================================


def make_dummy_java_profile():
    """Create a minimal concrete JavaProfile for testing"""

    class DummyJavaProfile(JavaProfile):
        owner = "dummy"
        repo = "dummyrepo"
        commit = "deadbeefcafebabe"

        @property
        def dockerfile(self):
            return "FROM ubuntu:22.04\nRUN echo hello"

        def log_parser(self, log: str) -> dict[str, str]:
            return {}

    return DummyJavaProfile()


def test_java_profile_defaults():
    """Test JavaProfile default file extensions"""
    profile = make_dummy_java_profile()
    assert profile.exts == [".java"]


def test_java_profile_inheritance():
    """Test that JavaProfile properly inherits from RepoProfile"""
    profile = make_dummy_java_profile()
    assert hasattr(profile, "owner")
    assert hasattr(profile, "repo")
    assert hasattr(profile, "commit")
    assert hasattr(profile, "exts")


# =============================================================================
# Maven Surefire Parser Tests
# =============================================================================


def test_maven_parser_basic():
    """Test parse_log_maven_surefire with basic PASSED/FAILED tests"""
    log = """
[INFO] testPass -- Time elapsed: 0.001 s
[ERROR] testFail -- Time elapsed: 0.002 s <<< FAILURE!
[INFO] testPass2 -- Time elapsed: 0.003 s
"""
    result = parse_log_maven_surefire(log)
    assert result["testPass"] == Status.PASSED.value
    assert result["testFail"] == Status.FAILED.value
    assert result["testPass2"] == Status.PASSED.value


def test_maven_parser_handles_failures():
    """Test Maven parser with <<< FAILURE! markers"""
    log = """[INFO] Running org.example.TestClass
[INFO] testMethodOne -- Time elapsed: 0.001 s
[ERROR] testMethodTwo -- Time elapsed: 0.002 s <<< FAILURE!
[INFO] testMethodThree -- Time elapsed: 0.001 s
"""
    result = parse_log_maven_surefire(log)
    assert result["testMethodOne"] == Status.PASSED.value
    assert result["testMethodTwo"] == Status.FAILED.value
    assert result["testMethodThree"] == Status.PASSED.value


def test_maven_parser_empty_log():
    """Test Maven parser with empty input"""
    result = parse_log_maven_surefire("")
    assert result == {}


def test_maven_parser_no_tests():
    """Test Maven parser with log containing no test output"""
    log = "[INFO] Building project\n[INFO] Compilation successful"
    result = parse_log_maven_surefire(log)
    assert result == {}


def test_maven_parser_alternative_format():
    """Test Maven parser with className(methodName) format"""
    log = """
testMethodOne(org.example.TestClass)  Time elapsed: 0.001 sec
testMethodTwo(org.example.TestClass)  Time elapsed: 0.002 sec
testMethodThree(org.example.AnotherTest)  Time elapsed: 0 sec
"""
    result = parse_log_maven_surefire(log)
    assert result["org.example.TestClass.testMethodOne"] == Status.PASSED.value
    assert result["org.example.TestClass.testMethodTwo"] == Status.PASSED.value
    assert result["org.example.AnotherTest.testMethodThree"] == Status.PASSED.value


def test_maven_parser_multiple_tests():
    """Test Maven parser with multiple tests"""
    log = """
[INFO] testHandler -- Time elapsed: 0.01 s
[INFO] testMiddleware -- Time elapsed: 0.02 s
[ERROR] testRouter -- Time elapsed: 0.03 s <<< FAILURE!
[INFO] testContext -- Time elapsed: 0.01 s
[ERROR] testEngine -- Time elapsed: 0.04 s <<< FAILURE!
"""
    result = parse_log_maven_surefire(log)
    assert len(result) == 5
    assert result["testHandler"] == Status.PASSED.value
    assert result["testMiddleware"] == Status.PASSED.value
    assert result["testRouter"] == Status.FAILED.value
    assert result["testContext"] == Status.PASSED.value
    assert result["testEngine"] == Status.FAILED.value


def test_maven_parser_edge_cases():
    """Test Maven parser with edge cases"""
    # Whitespace only
    assert parse_log_maven_surefire("   \n  \t  \n") == {}

    # Malformed lines (missing parts)
    log = """
[INFO] testIncomplete -- Time elapsed:
[ERROR] testMalformed
[INFO] testGood -- Time elapsed: 0.001 s
"""
    result = parse_log_maven_surefire(log)
    assert "testGood" in result
    assert result["testGood"] == Status.PASSED.value


# =============================================================================
# Gradle JUnit XML Parser Tests
# =============================================================================


def test_gradle_parser_basic():
    """Test parse_log_gradle_junit_xml with basic XML"""
    log = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.example.TestClass" tests="2" skipped="0" failures="0" errors="0">
  <testcase name="testPass" classname="com.example.TestClass" time="0.001"/>
  <testcase name="testPass2" classname="com.example.TestClass" time="0.001"/>
</testsuite>"""
    result = parse_log_gradle_junit_xml(log)
    assert result["com.example.TestClass.testPass"] == Status.PASSED.value
    assert result["com.example.TestClass.testPass2"] == Status.PASSED.value


def test_gradle_parser_handles_failures():
    """Test Gradle parser with failure elements"""
    log = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.example.TestClass" tests="3" skipped="0" failures="1" errors="0">
  <testcase name="testPass" classname="com.example.TestClass" time="0.001"/>
  <testcase name="testFail" classname="com.example.TestClass" time="0.002">
    <failure message="assertion failed"/>
  </testcase>
  <testcase name="testPass2" classname="com.example.TestClass" time="0.001"/>
</testsuite>"""
    result = parse_log_gradle_junit_xml(log)
    assert result["com.example.TestClass.testPass"] == Status.PASSED.value
    assert result["com.example.TestClass.testFail"] == Status.FAILED.value
    assert result["com.example.TestClass.testPass2"] == Status.PASSED.value


def test_gradle_parser_handles_skipped():
    """Test Gradle parser with skipped elements"""
    log = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.example.TestClass" tests="2" skipped="1" failures="0" errors="0">
  <testcase name="testPass" classname="com.example.TestClass" time="0.001"/>
  <testcase name="testSkipped" classname="com.example.TestClass" time="0.000">
    <skipped/>
  </testcase>
</testsuite>"""
    result = parse_log_gradle_junit_xml(log)
    assert result["com.example.TestClass.testPass"] == Status.PASSED.value
    assert result["com.example.TestClass.testSkipped"] == Status.SKIPPED.value


def test_gradle_parser_handles_error():
    """Test Gradle parser with error elements"""
    log = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.example.TestClass" tests="2" skipped="0" failures="0" errors="1">
  <testcase name="testPass" classname="com.example.TestClass" time="0.001"/>
  <testcase name="testError" classname="com.example.TestClass" time="0.002">
    <error message="NullPointerException"/>
  </testcase>
</testsuite>"""
    result = parse_log_gradle_junit_xml(log)
    assert result["com.example.TestClass.testPass"] == Status.PASSED.value
    assert result["com.example.TestClass.testError"] == Status.FAILED.value


def test_gradle_parser_empty_log():
    """Test Gradle parser with empty input"""
    result = parse_log_gradle_junit_xml("")
    assert result == {}


def test_gradle_parser_malformed_xml():
    """Test Gradle parser handles malformed XML gracefully"""
    log = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.example.TestClass" tests="1">
  <testcase name="testMalformed" classname="com.example.TestClass"
"""
    result = parse_log_gradle_junit_xml(log)
    # Should return empty dict, not crash
    assert result == {}


def test_gradle_parser_multiple_testsuites():
    """Test parsing multiple XML testsuites in one log"""
    log = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.example.TestClass1" tests="2">
  <testcase name="test1" classname="com.example.TestClass1" time="0.001"/>
  <testcase name="test2" classname="com.example.TestClass1" time="0.001"/>
</testsuite>
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.example.TestClass2" tests="2">
  <testcase name="test3" classname="com.example.TestClass2" time="0.001">
    <failure message="failed"/>
  </testcase>
  <testcase name="test4" classname="com.example.TestClass2" time="0.001"/>
</testsuite>"""
    result = parse_log_gradle_junit_xml(log)
    assert len(result) == 4
    assert result["com.example.TestClass1.test1"] == Status.PASSED.value
    assert result["com.example.TestClass1.test2"] == Status.PASSED.value
    assert result["com.example.TestClass2.test3"] == Status.FAILED.value
    assert result["com.example.TestClass2.test4"] == Status.PASSED.value


def test_gradle_parser_no_matches():
    """Test Gradle parser with log containing no XML"""
    log = """
Some random text
No test results here
Building project...
"""
    result = parse_log_gradle_junit_xml(log)
    assert result == {}


# =============================================================================
# Specific Profile Instance Tests
# =============================================================================


def test_gson_profile_properties():
    """Test Gsondd2fe59c profile properties"""
    profile = Gsondd2fe59c()
    assert profile.owner == "google"
    assert profile.repo == "gson"
    assert profile.commit == "dd2fe59c0d3390b2ad3dd365ed6938a5c15844cb"
    assert "mvn test" in profile.test_cmd
    assert "-Dsurefire.useFile=false" in profile.test_cmd
    assert "-Dsurefire.printSummary=true" in profile.test_cmd
    assert "-Dsurefire.reportFormat=plain" in profile.test_cmd


def test_gson_profile_dockerfile():
    """Test Gsondd2fe59c Dockerfile content"""
    profile = Gsondd2fe59c()
    dockerfile = profile.dockerfile
    assert "FROM ubuntu:22.04" in dockerfile
    assert f"git clone https://github.com/{profile.mirror_name}" in dockerfile
    assert "/testbed" in dockerfile
    assert "mvn clean install" in dockerfile


def test_gson_profile_log_parser():
    """Test Gsondd2fe59c uses Maven Surefire parser"""
    profile = Gsondd2fe59c()
    log = """
[INFO] testExample -- Time elapsed: 0.001 s
[ERROR] testFailure -- Time elapsed: 0.002 s <<< FAILURE!
"""
    result = profile.log_parser(log)
    assert result["testExample"] == Status.PASSED.value
    assert result["testFailure"] == Status.FAILED.value


def test_eureka_profile_properties():
    """Test Eureka459fcf59 profile uses Gradle"""
    profile = Eureka459fcf59()
    assert profile.owner == "Netflix"
    assert profile.repo == "eureka"
    assert profile.commit == "459fcf59866b1a950f6e88530a0b1b870fa5212f"
    assert "./gradlew test" in profile.test_cmd
    assert "--rerun-tasks" in profile.test_cmd
    assert "--continue" in profile.test_cmd
    assert "find . -type f -name 'TEST-*.xml'" in profile.test_cmd


def test_eureka_profile_dockerfile():
    """Test Eureka459fcf59 Dockerfile content"""
    profile = Eureka459fcf59()
    dockerfile = profile.dockerfile
    assert "FROM eclipse-temurin:8-jdk" in dockerfile
    assert f"git clone https://github.com/{profile.mirror_name}" in dockerfile
    assert "/testbed" in dockerfile
    assert "./gradlew build" in dockerfile


def test_eureka_profile_log_parser():
    """Test Eureka459fcf59 uses Gradle JUnit XML parser"""
    profile = Eureka459fcf59()
    log = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.netflix.eureka.TestClass" tests="2">
  <testcase name="testMethod" classname="com.netflix.eureka.TestClass" time="0.001"/>
  <testcase name="testMethod2" classname="com.netflix.eureka.TestClass" time="0.001">
    <failure message="test failed"/>
  </testcase>
</testsuite>"""
    result = profile.log_parser(log)
    assert result["com.netflix.eureka.TestClass.testMethod"] == Status.PASSED.value
    assert result["com.netflix.eureka.TestClass.testMethod2"] == Status.FAILED.value


def test_java_profile_inheritance_in_concrete_profiles():
    """Test that concrete Java profiles properly inherit from JavaProfile"""
    profiles_to_test = [Gsondd2fe59c, Eureka459fcf59]

    for profile_class in profiles_to_test:
        profile = profile_class()
        assert isinstance(profile, JavaProfile)
        assert hasattr(profile, "exts")
        assert profile.exts == [".java"]
        assert hasattr(profile, "owner")
        assert hasattr(profile, "repo")
        assert hasattr(profile, "commit")
        assert hasattr(profile, "test_cmd")
        assert hasattr(profile, "dockerfile")
        assert hasattr(profile, "log_parser")


# =============================================================================
# Build Image Tests (with mocks)
# =============================================================================


def test_java_profile_build_image():
    """Test JavaProfile.build_image writes Dockerfile and runs docker"""
    profile = Gsondd2fe59c()

    with (
        patch("pathlib.Path.mkdir") as mock_mkdir,
        patch("builtins.open", mock_open()) as mock_file,
        patch("subprocess.run") as mock_run,
    ):
        profile.build_image()

        # Verify directory creation
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Verify file operations
        mock_file.assert_called()

        # Verify docker build was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "docker build" in call_args[0][0]
        assert profile.image_name in call_args[0][0]


def test_java_profile_build_image_error_handling():
    """Test build_image error handling"""
    profile = Gsondd2fe59c()

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


def test_java_profile_build_image_checks_exit_code():
    """Test build_image checks subprocess exit code"""
    profile = Gsondd2fe59c()

    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open", mock_open()),
        patch("subprocess.run") as mock_run,
    ):
        profile.build_image()
        assert mock_run.call_args.kwargs["check"] is True


def test_java_profile_build_image_file_operations():
    """Test build_image creates Dockerfile and build log"""
    profile = Gsondd2fe59c()

    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open", mock_open()) as mock_file,
        patch("subprocess.run"),
    ):
        profile.build_image()

        file_calls = mock_file.call_args_list
        assert len(file_calls) >= 2  # Dockerfile and build log

        # Check for Dockerfile creation
        dockerfile_calls = [call for call in file_calls if "Dockerfile" in str(call)]
        assert len(dockerfile_calls) > 0

        # Check for build log creation
        log_calls = [call for call in file_calls if "build_image.log" in str(call)]
        assert len(log_calls) > 0


def test_java_profile_build_image_subprocess_parameters():
    """Test build_image subprocess parameters"""
    profile = Gsondd2fe59c()

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
