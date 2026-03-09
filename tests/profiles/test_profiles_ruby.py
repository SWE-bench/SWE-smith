import json

from swesmith.profiles.ruby import (
    RubyProfile,
    parse_log_rspec_json,
    parse_log_ruby_test,
)


def test_parse_log_ruby_test_minitest_verbose():
    log = """
Run options: --seed 12345

# Running:

TestFoo#test_something = 0.01 s = .
TestFoo#test_other = 0.02 s = F
TestBar#test_works = 0.00 s = .

2 runs, 2 assertions, 1 failures, 0 errors, 0 skips
"""
    result = parse_log_ruby_test(log)
    assert len(result) == 3
    assert result["TestFoo#test_something"] == "PASSED"
    assert result["TestFoo#test_other"] == "FAILED"
    assert result["TestBar#test_works"] == "PASSED"


def test_parse_log_ruby_test_minitest_error():
    log = "TestFoo#test_boom = 0.01 s = E\n"
    result = parse_log_ruby_test(log)
    assert result["TestFoo#test_boom"] == "ERROR"


def test_parse_log_ruby_test_test_unit_verbose():
    """test-unit verbose format as produced by Faker."""
    log = """
Loaded suite /usr/local/bundle/gems/rake-13.3.1/lib/rake/rake_test_loader
Started
TestArLocale:
  test_ar_address_methods:                              .: (0.000788)
  test_ar_app_methods:                                  .: (0.000122)
TestChileRut:
  test_check_digit:                                     .: (0.000058)
  test_full_rut:                                        F: (0.000042)
  test_rut_length:                                      E: (0.000035)
Finished in 4.715342625 seconds.
"""
    result = parse_log_ruby_test(log)
    assert len(result) == 5
    assert result["TestArLocale#test_ar_address_methods"] == "PASSED"
    assert result["TestArLocale#test_ar_app_methods"] == "PASSED"
    assert result["TestChileRut#test_check_digit"] == "PASSED"
    assert result["TestChileRut#test_full_rut"] == "FAILED"
    assert result["TestChileRut#test_rut_length"] == "ERROR"


def test_parse_log_rspec_json_passes_and_failures():
    rspec_output = json.dumps(
        {
            "version": "3.13.0",
            "examples": [
                {
                    "full_description": "Widget does something",
                    "status": "passed",
                },
                {
                    "full_description": "Widget handles edge case",
                    "status": "failed",
                },
                {
                    "full_description": "Widget pending feature",
                    "status": "pending",
                },
            ],
            "summary_line": "3 examples, 1 failure, 1 pending",
        }
    )
    result = parse_log_rspec_json(rspec_output)
    assert len(result) == 2
    assert result["Widget does something"] == "PASSED"
    assert result["Widget handles edge case"] == "FAILED"


def test_parse_log_rspec_json_embedded_in_other_output():
    log = (
        "Building...\nCompiling gems...\n"
        + json.dumps(
            {
                "examples": [
                    {"full_description": "Foo bar", "status": "passed"},
                ],
            }
        )
        + "\nDone.\n"
    )
    result = parse_log_rspec_json(log)
    assert len(result) == 1
    assert result["Foo bar"] == "PASSED"


def test_parse_log_rspec_json_no_json():
    result = parse_log_rspec_json("no json here\njust text\n")
    assert result == {}


def test_ruby_profile_log_parser_delegates_to_minitest():
    profile = RubyProfile()
    log = "TestFoo#test_something = 0.01 s = .\n"
    result = profile.log_parser(log)
    assert result["TestFoo#test_something"] == "PASSED"


def test_ruby_profile_log_parser_delegates_to_rspec_json():
    profile = RubyProfile()
    log = json.dumps(
        {
            "examples": [
                {"full_description": "works", "status": "passed"},
                {"full_description": "fails", "status": "failed"},
            ],
        }
    )
    result = profile.log_parser(log)
    assert len(result) == 2
    assert result["works"] == "PASSED"
    assert result["fails"] == "FAILED"


def test_ruby_profile_log_parser_no_matches():
    profile = RubyProfile()
    log = """
Some random build output
Compiling...
Done.
"""
    result = profile.log_parser(log)
    assert result == {}


def test_ruby_profile_eval_sets():
    """All Ruby repo profiles in SWE-bench_Multilingual should declare it."""
    from swesmith.profiles.ruby import (
        Faker9ef1ecae,
        Jekylld0cf1791,
        Rubocop519206df,
        Fluentd7906fda4,
        Fastlane0e18ea7c,
        Fpm5b1fe9af,
    )

    for profile_cls in [
        Faker9ef1ecae,
        Rubocop519206df,
        Jekylld0cf1791,
        Fluentd7906fda4,
        Fastlane0e18ea7c,
        Fpm5b1fe9af,
    ]:
        profile = profile_cls()
        assert "SWE-bench/SWE-bench_Multilingual" in profile.eval_sets, (
            f"{profile_cls.__name__} missing SWE-bench_Multilingual eval set"
        )


def test_parse_log_rspec_json_malformed_json():
    """Exercises the JSONDecodeError path when JSON is invalid."""
    log = '{"version": "3.13.0", "examples": [{"full_description": "works"}'
    result = parse_log_rspec_json(log)
    assert result == {}


def test_parse_log_rspec_json_no_closing_brace():
    """Exercises the rfind("}") < start path."""
    log = '{"examples": no closing brace here'
    result = parse_log_rspec_json(log)
    assert result == {}


def test_parse_log_rspec_json_empty_description():
    """Examples with empty full_description are skipped."""
    rspec_output = json.dumps(
        {
            "examples": [
                {"full_description": "", "status": "passed"},
                {"full_description": "   ", "status": "passed"},
                {"full_description": "Real test", "status": "passed"},
            ],
        }
    )
    result = parse_log_rspec_json(rspec_output)
    assert len(result) == 1
    assert result["Real test"] == "PASSED"


def test_ruby_profile_is_test_path_rspec():
    """RubyProfile._is_test_path detects RSpec spec/ dirs and _spec.rb files."""
    profile = RubyProfile()
    # Standard RSpec directory
    assert profile._is_test_path("/repo/spec/models", "user_spec.rb")
    assert profile._is_test_path("/repo/spec", "helper_spec.rb")
    # _spec.rb suffix outside spec/ dir
    assert profile._is_test_path("/repo/lib", "widget_spec.rb")
    # Base class paths still work
    assert profile._is_test_path("/repo/test/unit", "test_foo.rb")
    assert profile._is_test_path("/repo/tests", "foo.rb")
    assert profile._is_test_path("/repo/specs", "foo.rb")
    # Non-test paths return False
    assert not profile._is_test_path("/repo/lib", "widget.rb")
    assert not profile._is_test_path("/repo/lib/specific", "handler.rb")
    # "spec" as substring in dir name should NOT match (only exact dir component)
    assert not profile._is_test_path("/repo/lib/inspector", "handler.rb")
