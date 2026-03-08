import os
import pytest
import tempfile

from unittest.mock import patch
from swesmith.profiles.rust import RustProfile


def make_dummy_rust_profile():
    class DummyRustProfile(RustProfile):
        owner = "dummy"
        repo = "dummyrepo"
        commit = "deadbeefcafebabe"

        @property
        def dockerfile(self):
            return "FROM rust:1.88\nRUN echo hello"

    return DummyRustProfile()


def _write_file(base, relpath, content):
    full = os.path.join(base, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(content)


def _make_profile_with_clone(tmp_path):
    profile = make_dummy_rust_profile()

    def fake_clone(dest=None):
        return str(tmp_path), False

    profile.clone = fake_clone
    return profile


def _make_profile_with_cache(cache):
    profile = make_dummy_rust_profile()
    profile._test_name_to_files_cache = cache
    return profile


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


def test_extract_test_fn_name_bare_function():
    fn, path = RustProfile._extract_test_fn_name("test_apparent_size")
    assert fn == "test_apparent_size"
    assert path is None


def test_extract_test_fn_name_module_qualified():
    fn, path = RustProfile._extract_test_fn_name("flags::defs::test_search_zip")
    assert fn == "test_search_zip"
    assert path is None


def test_extract_test_fn_name_deeply_nested():
    fn, path = RustProfile._extract_test_fn_name("a::b::c::d::test_deep")
    assert fn == "test_deep"
    assert path is None


def test_extract_test_fn_name_doc_test():
    fn, path = RustProfile._extract_test_fn_name(
        "src/writer.rs - WriterBuilder::quote_style (line 338)"
    )
    assert fn == "src/writer.rs"
    assert path == "src/writer.rs"


def test_extract_test_fn_name_should_panic():
    fn, path = RustProfile._extract_test_fn_name(
        "action::count_with_num_args - should panic"
    )
    assert fn == "count_with_num_args"
    assert path is None


def test_extract_test_fn_name_should_panic_bare():
    fn, path = RustProfile._extract_test_fn_name("test_panics - should panic")
    assert fn == "test_panics"
    assert path is None


def test_extract_test_fn_name_single_module():
    fn, path = RustProfile._extract_test_fn_name("utils::test_helper")
    assert fn == "test_helper"
    assert path is None


def test_build_test_name_to_files_map_basic(tmp_path):
    _write_file(
        tmp_path,
        "src/lib.rs",
        "#[test]\nfn test_add() {\n    assert_eq!(1 + 1, 2);\n}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "test_add" in result
    assert "src/lib.rs" in result["test_add"]


def test_build_test_name_to_files_map_integration_tests(tmp_path):
    _write_file(
        tmp_path,
        "tests/integration.rs",
        "#[test]\nfn test_integration() {}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "test_integration" in result
    assert "tests/integration.rs" in result["test_integration"]


def test_build_test_name_to_files_map_pub_async_fn(tmp_path):
    _write_file(
        tmp_path,
        "src/async_tests.rs",
        "#[tokio::test]\npub async fn test_async_op() {\n    // async test\n}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "test_async_op" in result
    assert "src/async_tests.rs" in result["test_async_op"]


def test_build_test_name_to_files_map_attrs_between_test_and_fn(tmp_path):
    _write_file(
        tmp_path,
        "src/panic.rs",
        '#[test]\n#[should_panic]\nfn test_panics() {\n    panic!("boom");\n}\n',
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "test_panics" in result


def test_build_test_name_to_files_map_comments_between_test_and_fn(tmp_path):
    _write_file(
        tmp_path,
        "src/commented.rs",
        "#[test]\n// This is a comment\n#[ignore]\nfn test_ignored() {}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "test_ignored" in result


def test_build_test_name_to_files_map_non_test_functions_ignored(tmp_path):
    _write_file(
        tmp_path,
        "src/lib.rs",
        "fn helper() {}\n\npub fn public_helper() {}\n\n#[test]\nfn test_real() {}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "helper" not in result
    assert "public_helper" not in result
    assert "test_real" in result


def test_build_test_name_to_files_map_same_fn_multiple_files(tmp_path):
    _write_file(tmp_path, "src/a.rs", "#[test]\nfn test_common() {}\n")
    _write_file(tmp_path, "src/b.rs", "#[test]\nfn test_common() {}\n")
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "test_common" in result
    assert result["test_common"] == {"src/a.rs", "src/b.rs"}


def test_build_test_name_to_files_map_pub_crate_fn(tmp_path):
    _write_file(
        tmp_path,
        "src/vis.rs",
        "#[test]\npub(crate) fn test_visible() {}\n\n#[test]\npub(super) async fn test_super() {}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "test_visible" in result
    assert "test_super" in result


def test_build_test_name_to_files_map_unreadable_file_skipped(tmp_path):
    _write_file(tmp_path, "src/good.rs", "#[test]\nfn test_ok() {}\n")
    bad_path = os.path.join(tmp_path, "src", "bad.rs")
    with open(bad_path, "wb") as f:
        f.write(b"\x80\x81\x82\x83" * 100)

    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "test_ok" in result


def test_build_test_name_to_files_map_cleanup_on_fresh_clone(tmp_path):
    src_dir = tmp_path / "repo"
    src_dir.mkdir()
    _write_file(str(src_dir), "src/lib.rs", "#[test]\nfn test_x() {}\n")

    profile = make_dummy_rust_profile()

    def fake_clone(dest=None):
        return str(src_dir), True

    profile.clone = fake_clone

    with patch("swesmith.profiles.rust.shutil.rmtree") as mock_rm:
        profile._build_test_name_to_files_map()
        mock_rm.assert_called_once_with(str(src_dir))


def test_build_test_name_to_files_map_actix_rt_test(tmp_path):
    _write_file(
        tmp_path,
        "src/web.rs",
        "#[actix_rt::test]\nasync fn test_handler() {}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "test_handler" in result


def test_build_test_name_to_files_map_blank_line_between(tmp_path):
    _write_file(
        tmp_path,
        "src/spaced.rs",
        "#[test]\n\nfn test_spaced() {}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "test_spaced" in result


def test_get_test_files_basic_f2p_p2p():
    cache = {
        "test_add": {"src/math.rs"},
        "test_sub": {"src/math.rs"},
        "test_display": {"src/fmt.rs"},
    }
    profile = _make_profile_with_cache(cache)
    instance = {
        "instance_id": "dummy__dummyrepo.deadbeef.1",
        "FAIL_TO_PASS": ["math::test_add"],
        "PASS_TO_PASS": ["math::test_sub", "fmt::test_display"],
    }
    f2p, p2p = profile.get_test_files(instance)
    assert set(f2p) == {"src/math.rs"}
    assert set(p2p) == {"src/math.rs", "src/fmt.rs"}


def test_get_test_files_doc_test():
    profile = _make_profile_with_cache({})
    instance = {
        "instance_id": "dummy__dummyrepo.deadbeef.1",
        "FAIL_TO_PASS": ["src/writer.rs - WriterBuilder::quote_style (line 338)"],
        "PASS_TO_PASS": [],
    }
    f2p, p2p = profile.get_test_files(instance)
    assert f2p == ["src/writer.rs"]
    assert p2p == []


def test_get_test_files_missing_test_names():
    cache = {"test_exists": {"src/lib.rs"}}
    profile = _make_profile_with_cache(cache)
    instance = {
        "instance_id": "dummy__dummyrepo.deadbeef.1",
        "FAIL_TO_PASS": ["nonexistent::test_missing"],
        "PASS_TO_PASS": ["also::test_not_found"],
    }
    f2p, p2p = profile.get_test_files(instance)
    assert f2p == []
    assert p2p == []


def test_get_test_files_cache_reuse():
    profile = make_dummy_rust_profile()
    clone_count = 0

    def counting_clone(dest=None):
        nonlocal clone_count
        clone_count += 1
        d = tempfile.mkdtemp()
        return d, True

    profile.clone = counting_clone

    instance = {
        "instance_id": "dummy__dummyrepo.deadbeef.1",
        "FAIL_TO_PASS": ["test_a"],
        "PASS_TO_PASS": ["test_b"],
    }
    profile.get_test_files(instance)
    profile.get_test_files(instance)
    assert clone_count == 1


def test_get_test_files_assertion_error_on_missing_keys():
    profile = _make_profile_with_cache({})
    with pytest.raises(AssertionError):
        profile.get_test_files({"instance_id": "dummy__dummyrepo.deadbeef.1"})


def test_get_test_files_should_panic():
    cache = {"count_with_num_args": {"src/action.rs"}}
    profile = _make_profile_with_cache(cache)
    instance = {
        "instance_id": "dummy__dummyrepo.deadbeef.1",
        "FAIL_TO_PASS": ["action::count_with_num_args - should panic"],
        "PASS_TO_PASS": [],
    }
    f2p, _ = profile.get_test_files(instance)
    assert set(f2p) == {"src/action.rs"}


def test_get_test_files_bare_fn():
    cache = {"test_simple": {"src/simple.rs"}}
    profile = _make_profile_with_cache(cache)
    instance = {
        "instance_id": "dummy__dummyrepo.deadbeef.1",
        "FAIL_TO_PASS": ["test_simple"],
        "PASS_TO_PASS": [],
    }
    f2p, _ = profile.get_test_files(instance)
    assert set(f2p) == {"src/simple.rs"}
