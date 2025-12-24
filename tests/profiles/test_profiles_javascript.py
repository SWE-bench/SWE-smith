from swesmith.profiles.javascript import parse_log_karma, parse_log_jasmine
from swebench.harness.constants import TestStatus


def test_parse_log_karma_basic():
    log = """
Chrome Headless 137.0.0.0 (Linux x86_64): Executed 108 of 108 SUCCESS (0.234 secs / 0.215 secs)
"""
    result = parse_log_karma(log)
    assert len(result) == 108
    assert result["karma_unit_test_1"] == TestStatus.PASSED.value
    assert result["karma_unit_test_108"] == TestStatus.PASSED.value


def test_parse_log_karma_with_failures():
    log = "Chrome Headless 137.0.0.0 (Linux x86_64): Executed 95 of 100 SUCCESS (0.5 secs / 0.45 secs)\nChrome Headless 137.0.0.0 (Linux x86_64): Executed 100 of 100 (5 FAILED) (0.5 secs / 0.45 secs)"
    result = parse_log_karma(log)
    passed_count = sum(1 for v in result.values() if v == TestStatus.PASSED.value)
    failed_count = sum(1 for v in result.values() if v == TestStatus.FAILED.value)
    assert passed_count == 95
    assert failed_count == 5


def test_parse_log_karma_no_matches():
    log = """
Some random text
No test results here
"""
    result = parse_log_karma(log)
    assert result == {}


def test_parse_log_jasmine_basic():
    log = "426 specs, 0 failures"
    result = parse_log_jasmine(log)
    assert len(result) == 426
    assert result["jasmine_spec_1"] == TestStatus.PASSED.value
    assert result["jasmine_spec_426"] == TestStatus.PASSED.value


def test_parse_log_jasmine_with_failures():
    log = "100 specs, 5 failures"
    result = parse_log_jasmine(log)
    passed_count = sum(1 for v in result.values() if v == TestStatus.PASSED.value)
    failed_count = sum(1 for v in result.values() if v == TestStatus.FAILED.value)
    assert passed_count == 95
    assert failed_count == 5


def test_parse_log_jasmine_with_pending():
    log = """
100 specs, 2 failures, 3 pending specs
"""
    result = parse_log_jasmine(log)
    passed_count = sum(1 for v in result.values() if v == TestStatus.PASSED.value)
    failed_count = sum(1 for v in result.values() if v == TestStatus.FAILED.value)
    skipped_count = sum(1 for v in result.values() if v == TestStatus.SKIPPED.value)
    assert passed_count == 95
    assert failed_count == 2
    assert skipped_count == 3


def test_parse_log_jasmine_no_matches():
    log = """
Some random text
No test results here
"""
    result = parse_log_jasmine(log)
    assert result == {}
