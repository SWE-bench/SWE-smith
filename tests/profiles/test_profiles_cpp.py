from swesmith.profiles.cpp import (
    CppProfile,
    parse_log_ctest,
    parse_log_gtest,
    parse_log_catch2,
)


# ========== CTest Parser Tests ==========


def test_ctest_parser_basic():
    """Test basic CTest output parsing with passed and failed tests."""
    log = """
Test project /build
      Start  1: test_addition
 1/10 Test  #1: test_addition ....................   Passed    0.01 sec
      Start  2: test_subtraction
 2/10 Test  #2: test_subtraction .................   Passed    0.02 sec
      Start  3: test_multiplication
 3/10 Test  #3: test_multiplication ..............   Failed    0.03 sec
      Start  4: test_division
 4/10 Test  #4: test_division ....................   Passed    0.01 sec
"""
    result = parse_log_ctest(log)
    assert len(result) == 4
    assert result["test_addition"] == "PASSED"
    assert result["test_subtraction"] == "PASSED"
    assert result["test_multiplication"] == "FAILED"
    assert result["test_division"] == "PASSED"


def test_ctest_parser_with_failed_section():
    """Test CTest parser with 'The following tests FAILED:' section."""
    log = """
The following tests FAILED:
	  3 - test_parser (Failed)
	  7 - test_lexer (Failed)
	 15 - test_analyzer (Failed)
Errors while running CTest
"""
    result = parse_log_ctest(log)
    assert len(result) == 3
    assert result["test_parser"] == "FAILED"
    assert result["test_lexer"] == "FAILED"
    assert result["test_analyzer"] == "FAILED"


def test_ctest_parser_summary_fallback():
    """Test CTest parser fallback to summary when no individual tests found."""
    log = """
100% tests passed, 0 tests failed out of 42
"""
    result = parse_log_ctest(log)
    assert len(result) == 42
    # All should be passes
    for key, value in result.items():
        assert value == "PASSED"
        assert key.startswith("synthetic_pass_")


def test_ctest_parser_summary_with_failures():
    """Test CTest parser with summary showing failures."""
    log = """
95% tests passed, 2 tests failed out of 40
"""
    result = parse_log_ctest(log)
    assert len(result) == 40
    passed = [k for k, v in result.items() if v == "PASSED"]
    failed = [k for k, v in result.items() if v == "FAILED"]
    assert len(passed) == 38
    assert len(failed) == 2


def test_ctest_parser_case_insensitive():
    """Test that CTest parser handles case variations."""
    log = """
 1/2 Test  #1: test_one .........................   passed    0.01 sec
 2/2 Test  #2: test_two .........................   FAILED    0.02 sec
"""
    result = parse_log_ctest(log)
    assert result["test_one"] == "PASSED"
    assert result["test_two"] == "FAILED"


def test_ctest_parser_with_hyphens_and_slashes():
    """Test CTest parser with test names containing hyphens and slashes."""
    log = """
 47/70 Test #47: brpc_load_balancer_unittest .....   Passed  173.42 sec
 48/70 Test #48: io/file-reader-test ..............   Failed    2.15 sec
"""
    result = parse_log_ctest(log)
    assert result["brpc_load_balancer_unittest"] == "PASSED"
    assert result["io/file-reader-test"] == "FAILED"


def test_ctest_parser_empty_log():
    """Test CTest parser with empty log."""
    result = parse_log_ctest("")
    assert result == {}


def test_ctest_parser_no_matches():
    """Test CTest parser with no matching patterns."""
    log = """
Some random output
Building project...
Compilation successful
"""
    result = parse_log_ctest(log)
    assert result == {}


# ========== Google Test Parser Tests ==========


def test_gtest_parser_basic():
    """Test basic Google Test output parsing."""
    log = """
[==========] Running 4 tests from 2 test suites.
[----------] Global test environment set-up.
[----------] 2 tests from TestSuite1
[ RUN      ] TestSuite1.TestCase1
[       OK ] TestSuite1.TestCase1 (0 ms)
[ RUN      ] TestSuite1.TestCase2
[  FAILED  ] TestSuite1.TestCase2 (1 ms)
[----------] 2 tests from TestSuite2
[ RUN      ] TestSuite2.TestCase1
[       OK ] TestSuite2.TestCase1 (0 ms)
[ RUN      ] TestSuite2.TestCase2
[  SKIPPED ] TestSuite2.TestCase2 (0 ms)
[==========] 4 tests from 2 test suites ran. (1 ms total)
[  PASSED  ] 2 tests.
[  FAILED  ] 1 test.
[  SKIPPED ] 1 test.
"""
    result = parse_log_gtest(log)
    assert len(result) == 4
    assert result["TestSuite1.TestCase1"] == "PASSED"
    assert result["TestSuite1.TestCase2"] == "FAILED"
    assert result["TestSuite2.TestCase1"] == "PASSED"
    assert result["TestSuite2.TestCase2"] == "SKIPPED"


def test_gtest_parser_with_colons():
    """Test Google Test parser with test names containing colons."""
    log = """
[ RUN      ] Namespace::Class::Method
[       OK ] Namespace::Class::Method (5 ms)
[ RUN      ] Another::Test::Case
[  FAILED  ] Another::Test::Case (10 ms)
"""
    result = parse_log_gtest(log)
    assert result["Namespace::Class::Method"] == "PASSED"
    assert result["Another::Test::Case"] == "FAILED"


def test_gtest_parser_summary_fallback():
    """Test Google Test parser fallback to summary when no individual tests found."""
    log = """
[==========] 150 tests from 25 test suites ran.
[  PASSED  ] 149 tests.
[  FAILED  ] 1 test, listed below:
"""
    result = parse_log_gtest(log)
    # Should create synthetic tests from summary since no individual tests were parsed
    assert len(result) == 150
    passed = [k for k, v in result.items() if v == "PASSED"]
    failed = [k for k, v in result.items() if v == "FAILED"]
    assert len(passed) == 149
    assert len(failed) == 1


def test_gtest_parser_skips_summary_lines():
    """Test that Google Test parser skips summary lines properly."""
    log = """
[       OK ] TestSuite.TestCase1 (0 ms)
[  PASSED  ] 150 tests.
[  FAILED  ] 2 tests, listed below:
"""
    result = parse_log_gtest(log)
    # Should only have TestCase1, not the summary lines
    assert len(result) == 1
    assert result["TestSuite.TestCase1"] == "PASSED"


def test_gtest_parser_disabled_tests():
    """Test Google Test parser with DISABLED tests."""
    log = """
[ RUN      ] TestSuite.NormalTest
[       OK ] TestSuite.NormalTest (0 ms)
[ RUN      ] TestSuite.DISABLED_SkippedTest
[ DISABLED ] TestSuite.DISABLED_SkippedTest (0 ms)
"""
    result = parse_log_gtest(log)
    assert result["TestSuite.NormalTest"] == "PASSED"
    assert result["TestSuite.DISABLED_SkippedTest"] == "SKIPPED"


def test_gtest_parser_with_slashes():
    """Test Google Test parser with test names containing slashes."""
    log = """
[ RUN      ] Path/To/Test.Case1
[       OK ] Path/To/Test.Case1 (0 ms)
[ RUN      ] Another/Path.Case2
[  FAILED  ] Another/Path.Case2 (1 ms)
"""
    result = parse_log_gtest(log)
    assert result["Path/To/Test.Case1"] == "PASSED"
    assert result["Another/Path.Case2"] == "FAILED"


def test_gtest_parser_empty_log():
    """Test Google Test parser with empty log."""
    result = parse_log_gtest("")
    assert result == {}


def test_gtest_parser_no_matches():
    """Test Google Test parser with no matching patterns."""
    log = """
Building tests...
Compilation successful
Some other output
"""
    result = parse_log_gtest(log)
    assert result == {}


def test_gtest_parser_passed_alternative():
    """Test Google Test parser with PASSED instead of OK."""
    log = """
[ RUN      ] TestSuite.TestCase1
[  PASSED  ] TestSuite.TestCase1 (0 ms)
"""
    result = parse_log_gtest(log)
    assert result["TestSuite.TestCase1"] == "PASSED"


# ========== Catch2 Parser Tests ==========


def test_catch2_parser_xml_format():
    """Test Catch2 parser with XML output format."""
    log = """
<?xml version="1.0" encoding="UTF-8"?>
<TestCase name="Test Addition" filename="test.cpp" line="10">
    <OverallResult success="true"/>
</TestCase>
<TestCase name="Test Subtraction" filename="test.cpp" line="20">
    <OverallResult success="true"/>
</TestCase>
<TestCase name="Test Division" filename="test.cpp" line="30">
    <OverallResult success="false"/>
</TestCase>
"""
    result = parse_log_catch2(log)
    assert len(result) == 3
    assert result["Test Addition"] == "PASSED"
    assert result["Test Subtraction"] == "PASSED"
    assert result["Test Division"] == "FAILED"


def test_catch2_parser_text_format():
    """Test Catch2 parser with text output format."""
    log = """
All tests passed (42 assertions in 10 test cases)

Filters: *
Randomness seeded to: 1234567890

Test Addition ... PASSED
Test Subtraction ... PASSED
Test Multiplication ... PASSED
Test Division ... FAILED
"""
    result = parse_log_catch2(log)
    assert len(result) == 4
    assert result["Test Addition"] == "PASSED"
    assert result["Test Subtraction"] == "PASSED"
    assert result["Test Multiplication"] == "PASSED"
    assert result["Test Division"] == "FAILED"


def test_catch2_parser_summary_format():
    """Test Catch2 parser with summary line."""
    log = """
test cases: 150 | 149 passed | 1 failed
assertions: 1234 | 1233 passed | 1 failed
"""
    result = parse_log_catch2(log)
    assert len(result) == 150
    passed = [k for k, v in result.items() if v == "PASSED"]
    failed = [k for k, v in result.items() if v == "FAILED"]
    assert len(passed) == 149
    assert len(failed) == 1


def test_catch2_parser_all_tests_passed():
    """Test Catch2 parser with 'All tests passed' format."""
    log = """
All tests passed (1234 assertions in 42 test cases)
"""
    result = parse_log_catch2(log)
    assert len(result) == 42
    for key, value in result.items():
        assert value == "PASSED"
        assert key.startswith("test_passed_")


def test_catch2_parser_all_tests_passed_single():
    """Test Catch2 parser with 'All tests passed' single test case."""
    log = """
All tests passed (10 assertions in 1 test case)
"""
    result = parse_log_catch2(log)
    assert len(result) == 1
    assert result["test_passed_1"] == "PASSED"


def test_catch2_parser_avoids_ctest_format():
    """Test that Catch2 parser doesn't match CTest output."""
    log = """
 1/10 Test  #1: test_addition ....................   Passed    0.01 sec
"""
    result = parse_log_catch2(log)
    # Should not match CTest format (has numeric prefix and brackets)
    assert result == {}


def test_catch2_parser_xml_multiline():
    """Test Catch2 parser with multiline XML content between tags."""
    log = """
<TestCase name="Complex Test" filename="test.cpp" line="50">
    <Expression success="true" type="REQUIRE" filename="test.cpp" line="52">
        <Original>x == 42</Original>
        <Expanded>42 == 42</Expanded>
    </Expression>
    <OverallResult success="true"/>
</TestCase>
"""
    result = parse_log_catch2(log)
    assert len(result) == 1
    assert result["Complex Test"] == "PASSED"


def test_catch2_parser_empty_log():
    """Test Catch2 parser with empty log."""
    result = parse_log_catch2("")
    assert result == {}


def test_catch2_parser_no_matches():
    """Test Catch2 parser with no matching patterns."""
    log = """
Building tests...
Compilation successful
Some other output
"""
    result = parse_log_catch2(log)
    assert result == {}


def test_catch2_parser_case_insensitive():
    """Test Catch2 parser handles case variations in text format."""
    log = """
Test One ... passed
Test Two ... PASSED
Test Three ... failed
Test Four ... FAILED
"""
    result = parse_log_catch2(log)
    assert result["Test One"] == "PASSED"
    assert result["Test Two"] == "PASSED"
    assert result["Test Three"] == "FAILED"
    assert result["Test Four"] == "FAILED"


# ========== CppProfile Integration Tests ==========


def make_dummy_cpp_profile():
    """Create a minimal concrete CppProfile for testing."""

    class DummyCppProfile(CppProfile):
        owner = "dummy"
        repo = "dummyrepo"
        commit = "deadbeefcafebabe"

        @property
        def dockerfile(self):
            return "FROM gcc:12\nRUN echo hello"

        def log_parser(self, log: str) -> dict[str, str]:
            return parse_log_gtest(log)

    return DummyCppProfile()


def test_cpp_profile_extensions():
    """Test that CppProfile has correct file extensions."""
    profile = make_dummy_cpp_profile()
    assert set(profile.exts) == {".cpp", ".cc", ".cxx", ".h", ".hpp"}


def test_cpp_profile_bug_gen_dirs_exclude():
    """Test that CppProfile has default excluded directories."""
    profile = make_dummy_cpp_profile()
    assert "/doc" in profile.bug_gen_dirs_exclude
    assert "/docs" in profile.bug_gen_dirs_exclude
    assert "/examples" in profile.bug_gen_dirs_exclude
    assert "/cmake" in profile.bug_gen_dirs_exclude
    assert "/scripts" in profile.bug_gen_dirs_exclude


def test_cpp_profile_extract_entities_merges_excludes():
    """Test that extract_entities merges custom and default excludes."""
    profile = make_dummy_cpp_profile()
    # We can't easily test the internal behavior without mocking,
    # but we can at least verify the method exists and accepts the right parameters
    # This would require more complex mocking to test fully
    assert hasattr(profile, "extract_entities")
    assert callable(profile.extract_entities)
