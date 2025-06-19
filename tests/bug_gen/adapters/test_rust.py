import pytest
import re
import warnings

from swesmith.bug_gen.adapters.rust import (
    get_entities_from_file_rs,
)


@pytest.fixture
def entities(test_file_rust):
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)
    return entities


def test_get_entities_from_file_rs_count(entities):
    assert len(entities) == 19


def test_get_entities_from_file_rs_max(test_file_rust):
    entities = []
    get_entities_from_file_rs(entities, test_file_rust, 3)
    assert len(entities) == 3


def test_get_entities_from_file_rs_unreadable():
    with pytest.raises(IOError):
        get_entities_from_file_rs([], "non-existent-file")


def test_get_entities_from_file_rs_no_functions(tmp_path):
    no_functions_file = tmp_path / "no_functions.rs"
    no_functions_file.write_text("// there are no functions here")
    entities = []
    get_entities_from_file_rs(entities, no_functions_file)
    assert len(entities) == 0


def test_get_entities_from_file_rs_malformed(tmp_path):
    malformed_file = tmp_path / "malformed.rs"
    malformed_file.write_text("(malformed")
    entities = []
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        get_entities_from_file_rs(entities, malformed_file)
        assert any(
            [
                re.search(r"Error encountered parsing .*malformed.rs", str(w.message))
                for w in ws
            ]
        )


def test_get_entities_from_file_rs_test_function_ignored(tmp_path):
    test_function_file = tmp_path / "test_function.rs"
    test_function_file.write_text(
        """
#[test]
#[should_panic]
fn test_true() {
    assert!(true);
}
        """
    )
    entities = []
    get_entities_from_file_rs(entities, test_function_file)
    assert len(entities) == 0


def test_get_entities_from_file_rs_names(entities):
    names = [e.name for e in entities]
    expected_names = [
        "parse",
        "name",
        "value",
        "http_only",
        "secure",
        "same_site_lax",
        "same_site_strict",
        "path",
        "domain",
        "max_age",
        "expires",
        "fmt",
        "extract_response_cookie_headers",
        "extract_response_cookies",
        "fmt",
        "fmt",
        "add_cookie_str",
        "set_cookies",
        "cookies",
    ]
    assert names == expected_names


def test_get_entities_from_file_rs_line_ranges(entities):
    start_end = [(e.line_start, e.line_end) for e in entities]
    expected_ranges = [
        (37, 43),
        (46, 48),
        (51, 53),
        (56, 58),
        (61, 63),
        (66, 68),
        (71, 73),
        (76, 78),
        (81, 83),
        (86, 91),
        (94, 99),
        (103, 105),
        (108, 112),
        (114, 121),
        (127, 129),
        (133, 135),
        (158, 164),
        (168, 173),
        (175, 190),
    ]
    assert start_end == expected_ranges


def test_get_entities_from_file_rs_extensions(entities):
    assert all([e.ext == "rs" for e in entities]), (
        "All entities should have the extension 'rs'"
    )


def test_get_entities_from_file_rs_file_paths(entities, test_file_rust):
    assert all([e.file_path == test_file_rust for e in entities]), (
        "All entities should have the correct file path"
    )


def test_get_entities_from_file_rs_signatures(entities):
    signatures = [e.signature for e in entities]
    expected_signatures = [
        "fn parse(value: &'a HeaderValue) -> Result<Cookie<'a>, CookieParseError>",
        "pub fn name(&self) -> &str",
        "pub fn value(&self) -> &str",
        "pub fn http_only(&self) -> bool",
        "pub fn secure(&self) -> bool",
        "pub fn same_site_lax(&self) -> bool",
        "pub fn same_site_strict(&self) -> bool",
        "pub fn path(&self) -> Option<&str>",
        "pub fn domain(&self) -> Option<&str>",
        "pub fn max_age(&self) -> Option<std::time::Duration>",
        "pub fn expires(&self) -> Option<SystemTime>",
        "fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result",
        "pub(crate) fn extract_response_cookie_headers<'a>(headers: &'a hyper::HeaderMap) -> impl Iterator<Item = &'a HeaderValue> + 'a",
        "pub(crate) fn extract_response_cookies<'a>(headers: &'a hyper::HeaderMap) -> impl Iterator<Item = Result<Cookie<'a>, CookieParseError>> + 'a",
        "fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result",
        "fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result",
        "pub fn add_cookie_str(&self, cookie: &str, url: &url::Url)",
        "fn set_cookies(&self, cookie_headers: &mut dyn Iterator<Item = &HeaderValue>, url: &url::Url)",
        "fn cookies(&self, url: &url::Url) -> Option<HeaderValue>",
    ]
    assert signatures == expected_signatures


def test_get_entities_from_file_rs_stubs(entities):
    stubs = [e.stub for e in entities]
    expected_stubs = [
        "fn parse(value: &'a HeaderValue) -> Result<Cookie<'a>, CookieParseError> {\n    // TODO: Implement this function\n}",
        "pub fn name(&self) -> &str {\n    // TODO: Implement this function\n}",
        "pub fn value(&self) -> &str {\n    // TODO: Implement this function\n}",
        "pub fn http_only(&self) -> bool {\n    // TODO: Implement this function\n}",
        "pub fn secure(&self) -> bool {\n    // TODO: Implement this function\n}",
        "pub fn same_site_lax(&self) -> bool {\n    // TODO: Implement this function\n}",
        "pub fn same_site_strict(&self) -> bool {\n    // TODO: Implement this function\n}",
        "pub fn path(&self) -> Option<&str> {\n    // TODO: Implement this function\n}",
        "pub fn domain(&self) -> Option<&str> {\n    // TODO: Implement this function\n}",
        "pub fn max_age(&self) -> Option<std::time::Duration> {\n    // TODO: Implement this function\n}",
        "pub fn expires(&self) -> Option<SystemTime> {\n    // TODO: Implement this function\n}",
        "fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {\n    // TODO: Implement this function\n}",
        "pub(crate) fn extract_response_cookie_headers<'a>(headers: &'a hyper::HeaderMap) -> impl Iterator<Item = &'a HeaderValue> + 'a {\n    // TODO: Implement this function\n}",
        "pub(crate) fn extract_response_cookies<'a>(headers: &'a hyper::HeaderMap) -> impl Iterator<Item = Result<Cookie<'a>, CookieParseError>> + 'a {\n    // TODO: Implement this function\n}",
        "fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {\n    // TODO: Implement this function\n}",
        "fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {\n    // TODO: Implement this function\n}",
        "pub fn add_cookie_str(&self, cookie: &str, url: &url::Url) {\n    // TODO: Implement this function\n}",
        "fn set_cookies(&self, cookie_headers: &mut dyn Iterator<Item = &HeaderValue>, url: &url::Url) {\n    // TODO: Implement this function\n}",
        "fn cookies(&self, url: &url::Url) -> Option<HeaderValue> {\n    // TODO: Implement this function\n}",
    ]
    assert stubs == expected_stubs
