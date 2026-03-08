"""
Tests for Java profiles and log parsers.

This test suite follows the standard testing pattern established in other
language profile tests (Go, JavaScript, Python, Rust).
"""

import os
import pytest
import subprocess
import tempfile
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


def _write_file(base, relpath, content):
    full = os.path.join(base, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(content)


def _make_profile_with_clone(tmp_path):
    profile = make_dummy_java_profile()

    def fake_clone(dest=None):
        return str(tmp_path), False

    profile.clone = fake_clone
    return profile


def _make_profile_with_cache(cache):
    profile = make_dummy_java_profile()
    profile._test_name_to_files_cache = cache
    return profile


def test_extract_test_class_name_fqn_with_parens():
    cls = JavaProfile._extract_test_class_name(
        "com.google.gson.functional.ArrayTest.testSerialization()"
    )
    assert cls == "ArrayTest"


def test_extract_test_class_name_fqn_no_parens():
    cls = JavaProfile._extract_test_class_name(
        "brut.androlib.BuildAndDecodeApkTest.valuesDrawablesTest"
    )
    assert cls == "BuildAndDecodeApkTest"


def test_extract_test_class_name_parameterized():
    cls = JavaProfile._extract_test_class_name(
        "com.codahale.metrics.ExponentiallyDecayingReservoirTest.spotFall[0: EXPONENTIALLY_DECAYING]"
    )
    assert cls == "ExponentiallyDecayingReservoirTest"


def test_extract_test_class_name_parameterized_with_signature():
    cls = JavaProfile._extract_test_class_name(
        "io.dropwizard.configuration.ConfigurationMetadataTest.isCollectionOfStringsShouldWork(String, boolean)[6]"
    )
    assert cls == "ConfigurationMetadataTest"


def test_extract_test_class_name_nested_class():
    cls = JavaProfile._extract_test_class_name(
        "power.PowerTests$PowerGraphTests.directConsumptionStopsWithNoPower()"
    )
    assert cls == "PowerTests"


def test_extract_test_class_name_nested_class_no_parens():
    cls = JavaProfile._extract_test_class_name(
        "software.coley.recaf.services.search.SearchServiceTest$Jvm.testMethodPath"
    )
    assert cls == "SearchServiceTest"


def test_extract_test_class_name_repetition():
    cls = JavaProfile._extract_test_class_name(
        "com.baomidou.mybatisplus.test.h2.H2UserTest.repetition 1 of 1000"
    )
    assert cls == "H2UserTest"


def test_extract_test_class_name_simple_no_package():
    cls = JavaProfile._extract_test_class_name("ApplicationTests.groundZero")
    assert cls == "ApplicationTests"


def test_extract_test_class_name_simple_with_parens():
    cls = JavaProfile._extract_test_class_name("ApplicationTests.saveLoad()")
    assert cls == "ApplicationTests"


def test_extract_test_class_name_indexed_display():
    cls = JavaProfile._extract_test_class_name(
        "org.jackhuang.hmcl.util.io.CompressingUtilsTest.[2] /testbed/file.zip, GB18030"
    )
    assert cls == "CompressingUtilsTest"


def test_extract_test_class_name_display_name_with_colon():
    cls = JavaProfile._extract_test_class_name(
        "org.apache.calcite.test.SqlOperatorUnparseTest.CoercionEnabled: true"
    )
    assert cls == "SqlOperatorUnparseTest"


def test_extract_test_class_name_jdk_suffix():
    cls = JavaProfile._extract_test_class_name(
        "org.apache.cassandra.service.StorageServiceTest.testScheduledExecutorsShutdownOnDrain-_jdk11"
    )
    assert cls == "StorageServiceTest"


def test_extract_test_class_name_nested_parameterized():
    cls = JavaProfile._extract_test_class_name(
        "software.coley.recaf.util.StringUtilTest$StringDecoding.[3] name=lorem-long-ru.txt"
    )
    assert cls == "StringUtilTest"


def test_build_test_name_to_files_map_basic(tmp_path):
    _write_file(
        tmp_path,
        "src/test/java/com/example/FooTest.java",
        "package com.example;\npublic class FooTest {}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "FooTest" in result
    assert "src/test/java/com/example/FooTest.java" in result["FooTest"]


def test_build_test_name_to_files_map_multiple_files(tmp_path):
    _write_file(tmp_path, "module-a/src/test/java/FooTest.java", "class FooTest {}\n")
    _write_file(tmp_path, "module-b/src/test/java/FooTest.java", "class FooTest {}\n")
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "FooTest" in result
    assert len(result["FooTest"]) == 2


def test_build_test_name_to_files_map_non_java_ignored(tmp_path):
    _write_file(tmp_path, "src/main/FooTest.py", "class FooTest:\n    pass\n")
    _write_file(tmp_path, "src/test/java/BarTest.java", "public class BarTest {}\n")
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "FooTest" not in result
    assert "BarTest" in result


def test_build_test_name_to_files_map_cleanup_on_fresh_clone(tmp_path):
    src_dir = tmp_path / "repo"
    src_dir.mkdir()
    _write_file(str(src_dir), "src/test/java/FooTest.java", "class FooTest {}\n")

    profile = make_dummy_java_profile()

    def fake_clone(dest=None):
        return str(src_dir), True

    profile.clone = fake_clone

    with patch("swesmith.profiles.java.shutil.rmtree") as mock_rm:
        profile._build_test_name_to_files_map()
        mock_rm.assert_called_once_with(str(src_dir))


def test_get_test_files_basic_f2p_p2p():
    cache = {
        "ArrayTest": {"src/test/java/com/example/ArrayTest.java"},
        "FormatterTest": {"src/test/java/com/example/FormatterTest.java"},
        "ErrorTest": {"src/test/java/com/example/ErrorTest.java"},
    }
    profile = _make_profile_with_cache(cache)
    instance = {
        "instance_id": "dummy__dummyrepo.deadbeef.1",
        "FAIL_TO_PASS": ["com.example.ArrayTest.testSerialization()"],
        "PASS_TO_PASS": [
            "com.example.FormatterTest.testFormat()",
            "com.example.ErrorTest.testHandle",
        ],
    }
    f2p, p2p = profile.get_test_files(instance)
    assert set(f2p) == {"src/test/java/com/example/ArrayTest.java"}
    assert set(p2p) == {
        "src/test/java/com/example/FormatterTest.java",
        "src/test/java/com/example/ErrorTest.java",
    }


def test_get_test_files_nested_class():
    cache = {"PowerTests": {"src/test/java/power/PowerTests.java"}}
    profile = _make_profile_with_cache(cache)
    instance = {
        "instance_id": "dummy__dummyrepo.deadbeef.1",
        "FAIL_TO_PASS": [
            "power.PowerTests$PowerGraphTests.directConsumptionStopsWithNoPower()"
        ],
        "PASS_TO_PASS": [],
    }
    f2p, _ = profile.get_test_files(instance)
    assert set(f2p) == {"src/test/java/power/PowerTests.java"}


def test_get_test_files_parameterized():
    cache = {
        "ExponentiallyDecayingReservoirTest": {
            "src/test/java/com/codahale/metrics/ExponentiallyDecayingReservoirTest.java"
        }
    }
    profile = _make_profile_with_cache(cache)
    instance = {
        "instance_id": "dummy__dummyrepo.deadbeef.1",
        "FAIL_TO_PASS": [
            "com.codahale.metrics.ExponentiallyDecayingReservoirTest.spotFall[0: EXPONENTIALLY_DECAYING]"
        ],
        "PASS_TO_PASS": [],
    }
    f2p, _ = profile.get_test_files(instance)
    assert set(f2p) == {
        "src/test/java/com/codahale/metrics/ExponentiallyDecayingReservoirTest.java"
    }


def test_get_test_files_missing_test_names():
    cache = {"ArrayTest": {"src/test/java/ArrayTest.java"}}
    profile = _make_profile_with_cache(cache)
    instance = {
        "instance_id": "dummy__dummyrepo.deadbeef.1",
        "FAIL_TO_PASS": ["com.example.NonexistentTest.testMissing()"],
        "PASS_TO_PASS": ["com.example.AlsoMissingTest.testNotFound"],
    }
    f2p, p2p = profile.get_test_files(instance)
    assert f2p == []
    assert p2p == []


def test_get_test_files_cache_reuse():
    profile = make_dummy_java_profile()
    clone_count = 0

    def counting_clone(dest=None):
        nonlocal clone_count
        clone_count += 1
        d = tempfile.mkdtemp()
        return d, True

    profile.clone = counting_clone

    instance = {
        "instance_id": "dummy__dummyrepo.deadbeef.1",
        "FAIL_TO_PASS": ["com.example.FooTest.testA()"],
        "PASS_TO_PASS": ["com.example.BarTest.testB()"],
    }
    profile.get_test_files(instance)
    profile.get_test_files(instance)
    assert clone_count == 1


def test_get_test_files_assertion_error_on_missing_keys():
    profile = _make_profile_with_cache({})
    with pytest.raises(AssertionError):
        profile.get_test_files({"instance_id": "dummy__dummyrepo.deadbeef.1"})
