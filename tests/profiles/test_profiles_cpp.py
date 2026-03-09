from swesmith.profiles.cpp import (
    CppProfile,
    parse_log_ctest,
    parse_log_gtest,
    parse_log_catch2,
    parse_log_boost_test,
    parse_log_pytest,
    parse_log_qtest,
    parse_log_lit,
    parse_log_autotools,
    parse_log_bun,
    parse_log_pycdc,
    parse_log_jakttest,
    parse_log_kakoune,
    parse_log_pugixml,
    parse_log_coost,
    parse_log_python_unittest,
    parse_log_redis_tcl,
    parse_log_async_profiler,
    parse_log_i2pd,
    parse_log_fastllm,
    parse_log_libsass,
    parse_log_ugrep,
    parse_log_fswatch,
    parse_log_tippecanoe,
    parse_log_platformio,
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


# ========== Boost.Test Parser Tests ==========


def test_boost_test_parser_individual_tests():
    """Test Boost.Test parser with entering/leaving test cases."""
    log = """
Running 3 test cases...
Entering test case "test_addition"
Leaving test case "test_addition"
Entering test case "test_subtraction"
Leaving test case "test_subtraction"
Entering test case "test_division"
error in "test_division": check x == y has failed [1 != 2]
Leaving test case "test_division"

*** 1 failure detected in test suite "MathTests"
"""
    result = parse_log_boost_test(log)
    assert result["test_addition"] == "PASSED"
    assert result["test_subtraction"] == "PASSED"
    assert result["test_division"] == "FAILED"


def test_boost_test_parser_no_errors():
    """Test Boost.Test parser with 'No errors detected' summary."""
    log = "*** No errors detected\n"
    result = parse_log_boost_test(log)
    assert result["boost_test_suite"] == "PASSED"


def test_boost_test_parser_failure_summary():
    """Test Boost.Test parser with failure summary only."""
    log = '*** 3 failures detected in test suite "AllTests"\n'
    result = parse_log_boost_test(log)
    assert sum(1 for v in result.values() if v == "FAILED") == 3


def test_boost_test_parser_empty_log():
    """Test Boost.Test parser with empty log."""
    assert parse_log_boost_test("") == {}


# ========== Pytest Parser Tests ==========


def test_pytest_parser_basic():
    """Test pytest parser with verbose output."""
    log = """tests/test_foo.py::test_bar PASSED                  [ 33%]
tests/test_foo.py::test_baz FAILED                  [ 66%]
tests/test_foo.py::test_qux SKIPPED                 [100%]
"""
    result = parse_log_pytest(log)
    assert result["tests/test_foo.py::test_bar"] == "PASSED"
    assert result["tests/test_foo.py::test_baz"] == "FAILED"
    assert result["tests/test_foo.py::test_qux"] == "SKIPPED"


def test_pytest_parser_empty_log():
    """Test pytest parser with empty log."""
    assert parse_log_pytest("") == {}


# ========== QTest Parser Tests ==========


def test_qtest_parser_basic():
    """Test QTest parser with pass, fail, and skip."""
    log = """PASS   : TestClass::testMethod()
FAIL!  : TestClass::failMethod() Comparison failed
SKIP   : TestClass::skipMethod() Condition not met
"""
    result = parse_log_qtest(log)
    assert result["TestClass::testMethod"] == "PASSED"
    assert result["TestClass::failMethod()"] == "FAILED"
    assert result["TestClass::skipMethod()"] == "SKIPPED"


def test_qtest_parser_empty_log():
    """Test QTest parser with empty log."""
    assert parse_log_qtest("") == {}


# ========== LIT Parser Tests ==========


def test_lit_parser_summary():
    """Test LIT parser with expected passes and unexpected failures."""
    log = """Expected Passes    : 120
Unexpected Failures: 3
"""
    result = parse_log_lit(log)
    assert sum(1 for v in result.values() if v == "PASSED") == 120
    assert sum(1 for v in result.values() if v == "FAILED") == 3


def test_lit_parser_individual_fail():
    """Test LIT parser with individual FAIL lines."""
    log = """FAIL: TestSuite :: some/test_name (5 of 100)
Expected Passes    : 99
Unexpected Failures: 1
"""
    result = parse_log_lit(log)
    assert result["some/test_name"] == "FAILED"
    assert sum(1 for v in result.values() if v == "PASSED") == 99


def test_lit_parser_klee_format():
    """Test LIT parser with KLEE-style summary."""
    log = """Passed: 50
Failed: 2
"""
    result = parse_log_lit(log)
    assert sum(1 for v in result.values() if v == "PASSED") == 50
    assert sum(1 for v in result.values() if v == "FAILED") == 2


def test_lit_parser_empty_log():
    """Test LIT parser with empty log."""
    assert parse_log_lit("") == {}


# ========== Autotools Parser Tests ==========


def test_autotools_parser_basic():
    """Test autotools parser with PASS, FAIL, XFAIL, SKIP."""
    log = """PASS: test_basic
FAIL: test_broken
XFAIL: test_known_issue
SKIP: test_optional
ERROR: test_crash
"""
    result = parse_log_autotools(log)
    assert result["test_basic"] == "PASSED"
    assert result["test_broken"] == "FAILED"
    assert result["test_known_issue"] == "PASSED"
    assert result["test_optional"] == "SKIPPED"
    assert result["test_crash"] == "FAILED"


def test_autotools_parser_empty_log():
    """Test autotools parser with empty log."""
    assert parse_log_autotools("") == {}


# ========== Bun Parser Tests ==========


def test_bun_parser_basic():
    """Test bun parser with pass and fail lines."""
    log = """(pass) Suite > test addition [5ms]
(fail) Suite > test division
(pass) Suite > test subtraction [2ms]
"""
    result = parse_log_bun(log)
    assert result["Suite > test addition"] == "PASSED"
    assert result["Suite > test division"] == "FAILED"
    assert result["Suite > test subtraction"] == "PASSED"


def test_bun_parser_empty_log():
    """Test bun parser with empty log."""
    assert parse_log_bun("") == {}


# ========== Pycdc Parser Tests ==========


def test_pycdc_parser_basic():
    """Test pycdc parser with PASS, XFAIL, and FAIL."""
    log = """*** test_basic: PASS (1)
*** test_known: XFAIL (2)
*** test_broken: FAIL (3)
"""
    result = parse_log_pycdc(log)
    assert result["test_basic"] == "PASSED"
    assert result["test_known"] == "PASSED"
    assert result["test_broken"] == "FAILED"


def test_pycdc_parser_with_ansi():
    """Test pycdc parser strips ANSI codes."""
    log = "\x1b[32m*** test_color: PASS (1)\x1b[0m\n"
    result = parse_log_pycdc(log)
    assert result["test_color"] == "PASSED"


def test_pycdc_parser_empty_log():
    """Test pycdc parser with empty log."""
    assert parse_log_pycdc("") == {}


# ========== Jakttest Parser Tests ==========


def test_jakttest_parser_basic():
    """Test jakttest parser with FAIL, SKIP, and passed summary."""
    log = """[ FAIL ] test_broken
[ SKIP ] test_optional
42 passed
"""
    result = parse_log_jakttest(log)
    assert result["test_broken"] == "FAILED"
    assert result["test_optional"] == "SKIPPED"
    assert sum(1 for v in result.values() if v == "PASSED") == 42


def test_jakttest_parser_empty_log():
    """Test jakttest parser with empty log."""
    assert parse_log_jakttest("") == {}


# ========== Kakoune Parser Tests ==========


def test_kakoune_parser_basic():
    """Test kakoune parser with ANSI color codes."""
    log = "\x1b[32mtest_passed\x1b[0m\n\x1b[31mtest_failed\x1b[0m\n\x1b[33mtest_skipped\x1b[0m\n"
    result = parse_log_kakoune(log)
    assert result["test_passed"] == "PASSED"
    assert result["test_failed"] == "FAILED"
    assert result["test_skipped"] == "SKIPPED"


def test_kakoune_parser_empty_log():
    """Test kakoune parser with empty log."""
    assert parse_log_kakoune("") == {}


# ========== Pugixml Parser Tests ==========


def test_pugixml_parser_with_failures():
    """Test pugixml parser with failed tests and summary."""
    log = """Test xpath_large_node_set failed: doc.load_file is false
Test document_load_file failed: doc.load_file is false
FAILURE: 2 out of 977 tests failed.
"""
    result = parse_log_pugixml(log)
    assert result["xpath_large_node_set"] == "FAILED"
    assert result["document_load_file"] == "FAILED"
    assert sum(1 for v in result.values() if v == "PASSED") == 975


def test_pugixml_parser_all_pass():
    """Test pugixml parser with all tests passing."""
    log = "Success: 0 out of 500 tests failed.\n"
    result = parse_log_pugixml(log)
    assert sum(1 for v in result.values() if v == "PASSED") == 500
    assert sum(1 for v in result.values() if v == "FAILED") == 0


def test_pugixml_parser_success_passed_format():
    """Test pugixml parser with 'Success: N tests passed' format."""
    log = "Success: 300 tests passed.\n"
    result = parse_log_pugixml(log)
    assert sum(1 for v in result.values() if v == "PASSED") == 300
    assert sum(1 for v in result.values() if v == "FAILED") == 0


def test_pugixml_parser_empty_log():
    """Test pugixml parser with empty log."""
    assert parse_log_pugixml("") == {}


# ========== Coost Parser Tests ==========


def test_coost_parser_basic():
    """Test coost parser with test sections and cases."""
    log = """> begin test: alien
 case find_index:
  EXPECT_EQ(find_index(1u << 4), 0) passed
  EXPECT_EQ(find_index(1u << 5), 1) passed
> begin test: math
 case abs:
  EXPECT_EQ(abs(-1), 1) passed
Congratulations! All tests passed!
"""
    result = parse_log_coost(log)
    assert "alien::find_index" in result
    assert "math::abs" in result
    assert all(v == "PASSED" for v in result.values())


def test_coost_parser_with_failure():
    """Test coost parser with a failed expectation."""
    log = """> begin test: math
 case divide:
  EXPECT_EQ(divide(1, 0), 0) failed: got inf
"""
    result = parse_log_coost(log)
    assert result["math"] == "FAILED"


def test_coost_parser_empty_log():
    """Test coost parser with empty log."""
    assert parse_log_coost("") == {}


# ========== Python Unittest Parser Tests ==========


def test_python_unittest_parser_all_pass():
    """Test python unittest parser with all tests passing."""
    log = """Ran 169 tests in 0.089s

OK
"""
    result = parse_log_python_unittest(log)
    assert len(result) == 169
    assert all(v == "PASSED" for v in result.values())


def test_python_unittest_parser_with_failures():
    """Test python unittest parser with failures and errors."""
    log = """Ran 50 tests in 1.2s

FAILED (failures=3, errors=2)
"""
    result = parse_log_python_unittest(log)
    assert sum(1 for v in result.values() if v == "PASSED") == 45
    assert sum(1 for v in result.values() if v == "FAILED") == 5


def test_python_unittest_parser_empty_log():
    """Test python unittest parser with empty log."""
    assert parse_log_python_unittest("") == {}


# ========== Redis TCL Parser Tests ==========


def test_redis_tcl_parser_basic():
    """Test Redis TCL parser with ok and err lines."""
    log = """[ok]: SET and GET an item
[ok]: DEL all keys
[err]: AUTH requires password
[ok]: PING returns PONG
"""
    result = parse_log_redis_tcl(log)
    assert result["SET and GET an item"] == "PASSED"
    assert result["DEL all keys"] == "PASSED"
    assert result["AUTH requires password"] == "FAILED"
    assert result["PING returns PONG"] == "PASSED"


def test_redis_tcl_parser_empty_log():
    """Test Redis TCL parser with empty log."""
    assert parse_log_redis_tcl("") == {}


# ========== Async Profiler Parser Tests ==========


def test_async_profiler_parser_basic():
    """Test async-profiler parser with PASS and FAIL lines."""
    log = """PASS [1/125] BasicTests.agentLoad took 1234 ms
PASS [2/125] BasicTests.cpuProfiler took 567 ms
FAIL [3/125] BasicTests.wallClock took 890 ms
PASS [4/125] BasicTests.allocProfiler took 123 ms
"""
    result = parse_log_async_profiler(log)
    assert result["BasicTests.agentLoad"] == "PASSED"
    assert result["BasicTests.cpuProfiler"] == "PASSED"
    assert result["BasicTests.wallClock"] == "FAILED"
    assert result["BasicTests.allocProfiler"] == "PASSED"


def test_async_profiler_parser_empty_log():
    """Test async-profiler parser with empty log."""
    assert parse_log_async_profiler("") == {}


# ========== i2pd Parser Tests ==========


def test_i2pd_parser_basic():
    """Test i2pd parser with Running lines."""
    log = """Running test-http-merge_chunked
Running test-http-req
Running test-http-res
Running test-gost
Running test-aes
"""
    result = parse_log_i2pd(log)
    assert len(result) == 5
    assert result["test-http-merge_chunked"] == "PASSED"
    assert result["test-http-req"] == "PASSED"
    assert result["test-gost"] == "PASSED"
    assert result["test-aes"] == "PASSED"


def test_i2pd_parser_empty_log():
    """Test i2pd parser with empty log."""
    assert parse_log_i2pd("") == {}


# ========== FastLLM Parser Tests ==========


def test_fastllm_parser_basic():
    """Test fastllm parser with 'test X finished!' lines."""
    log = """testing BaseOp...
shape: 1 2
data: 3.000000 4.000000
test BaseOp finished!
testing LinearOp...
shape: 1 3
data: 11.000000 16.000000 21.000000
test LinearOp finished!
"""
    result = parse_log_fastllm(log)
    assert result["BaseOp"] == "PASSED"
    assert result["LinearOp"] == "PASSED"


def test_fastllm_parser_empty_log():
    """Test fastllm parser with empty log."""
    assert parse_log_fastllm("") == {}


# ========== Libsass Parser Tests ==========


def test_libsass_parser_basic():
    """Test libsass parser with passed/failed counts per test binary."""
    log = """build/test_shared_ptr: Passed: 11, failed: 0.
build/test_util_string: Passed: 16, failed: 3.
"""
    result = parse_log_libsass(log)
    passed = sum(1 for v in result.values() if v == "PASSED")
    failed = sum(1 for v in result.values() if v == "FAILED")
    assert passed == 27
    assert failed == 3


def test_libsass_parser_empty_log():
    """Test libsass parser with empty log."""
    assert parse_log_libsass("") == {}


# ========== Ugrep Parser Tests ==========


def test_ugrep_parser_sections():
    """Test ugrep parser with multiple test sections."""
    log = """*** SINGLE-THREADED TESTS ***
.......
ALL TESTS PASSED

*** MULTI-THREADED TESTS ***
.......
ALL TESTS PASSED
"""
    result = parse_log_ugrep(log)
    assert result["SINGLE-THREADED TESTS"] == "PASSED"
    assert result["MULTI-THREADED TESTS"] == "PASSED"


def test_ugrep_parser_simple():
    """Test ugrep parser with just ALL TESTS PASSED and no sections."""
    log = "ALL TESTS PASSED\n"
    result = parse_log_ugrep(log)
    assert result["all_tests"] == "PASSED"


def test_ugrep_parser_empty_log():
    """Test ugrep parser with empty log."""
    assert parse_log_ugrep("") == {}


# ========== Fswatch Parser Tests ==========


def test_fswatch_parser_basic():
    """Test fswatch parser with all passing."""
    log = "1 tests, 1 passing\n"
    result = parse_log_fswatch(log)
    assert len(result) == 1
    assert result["test_pass_1"] == "PASSED"


def test_fswatch_parser_with_failures():
    """Test fswatch parser with some failures."""
    log = "5 tests, 3 passing\n"
    result = parse_log_fswatch(log)
    assert sum(1 for v in result.values() if v == "PASSED") == 3
    assert sum(1 for v in result.values() if v == "FAILED") == 2


def test_fswatch_parser_empty_log():
    """Test fswatch parser with empty log."""
    assert parse_log_fswatch("") == {}


# ========== Tippecanoe Parser Tests ==========


def test_tippecanoe_parser_basic():
    """Test tippecanoe parser with cmp lines."""
    log = """cmp tests/accumulate/out/result.json.check.out tests/accumulate/out/result.json
cmp tests/border/out/borders.json.check.out tests/border/out/borders.json
"""
    result = parse_log_tippecanoe(log)
    assert all(v == "PASSED" for v in result.values())
    assert len(result) == 2


def test_tippecanoe_parser_with_make_error():
    """Test tippecanoe parser with make error marking last test as failed."""
    log = """cmp tests/first/out/a.json.check.out tests/first/out/a.json
cmp tests/second/out/b.json.check.out tests/second/out/b.json
make: *** [Makefile:116: parallel-test] Error 127
"""
    result = parse_log_tippecanoe(log)
    keys = list(result.keys())
    assert result[keys[0]] == "PASSED"
    assert result[keys[-1]] == "FAILED"


def test_tippecanoe_parser_empty_log():
    """Test tippecanoe parser with empty log."""
    assert parse_log_tippecanoe("") == {}


# ========== PlatformIO Parser Tests ==========


def test_platformio_parser_basic():
    """Test PlatformIO parser with SUCCESS and FAILED lines."""
    log = """Environment        Status    Duration
-----------------  --------  ------------
linux_native_test  SUCCESS   00:00:07.850
========================= 1 succeeded in 00:00:07.850 =========================
"""
    result = parse_log_platformio(log)
    assert result["linux_native_test"] == "PASSED"


def test_platformio_parser_failure():
    """Test PlatformIO parser with FAILED environment."""
    log = "test_env  FAILED   00:00:12.000\n"
    result = parse_log_platformio(log)
    assert result["test_env"] == "FAILED"


def test_platformio_parser_empty_log():
    """Test PlatformIO parser with empty log."""
    assert parse_log_platformio("") == {}
