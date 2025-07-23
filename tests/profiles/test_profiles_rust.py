from swesmith.profiles.rust import RustProfile


def test_rust_profile_log_parser_basic():
    profile = RustProfile()
    log = """
test test_some_thing ... ok
test test_some_other_thing ... ok
test test_some_failure ... FAILED

test result: FAILED. 2 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s
"""
    result = profile.log_parser(log)
    assert len(result) == 3
    assert result["test_some_thing"] == "PASSED"
    assert result["test_some_other_thing"] == "PASSED"
    assert result["test_some_failure"] == "FAILED"


def test_rust_profile_log_parser_no_matches():
    profile = RustProfile()
    log = """
running 101 tests
Some random output
test result: ok. 101 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s
"""
    result = profile.log_parser(log)
    assert result == {}


def test_rust_profile_log_parser_multiple_test_files():
    profile = RustProfile()
    log = """
     Running `/testbed/some-binary`

running 3 tests
test test_some_thing ... ok
test test_some_other_thing ... ok
test test_some_failure ... FAILED

test result: FAILED. 2 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s

     Running `/testbed/some-other-binary`

running 2 tests
test test_another_thing ... ok
test test_one_more_thing ... ok

test result: PASSED. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s

   Doc-tests foo
test src/lib.rs - Bar (line 123) ... ok
test result: PASSED. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s
"""
    result = profile.log_parser(log)
    assert len(result) == 6
    assert result["test_some_thing"] == "PASSED"
    assert result["test_some_other_thing"] == "PASSED"
    assert result["test_some_failure"] == "FAILED"
    assert result["test_another_thing"] == "PASSED"
    assert result["test_one_more_thing"] == "PASSED"
    assert result["src/lib.rs - Bar (line 123)"] == "PASSED"
