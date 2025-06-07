from swesmith.harness.log_parsers import (
    parse_log_pytest,
    parse_log_gotest,
)


def test_parse_log_pytest(test_output_pytest):
    status_map = parse_log_pytest(test_output_pytest.read_text())
    assert isinstance(status_map, dict)
    assert all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in status_map.items()
    )
    for test_name, status in [
        ("tests/test_money.py::test_keep_decimal_places[<lambda>3-1]", "FAILED"),
        ("tests/test_models.py::TestDifferentCurrencies::test_sub_default", "FAILED"),
        (
            "tests/contrib/exchange/test_backends.py::TestBackends::test_initial_update_rates[setup0]",
            "PASSED",
        ),
        (
            "tests/test_models.py::TestVanillaMoneyField::test_create_defaults[BaseModel-kwargs4-expected4]",
            "PASSED",
        ),
        ("tests/test_models.py::TestGetOrCreate::test_currency_field_lookup", "PASSED"),
        ("tests/test_money.py::test_get_current_locale[sv-se-sv_SE]", "PASSED"),
    ]:
        assert test_name in status_map
        assert status_map[test_name] == status


def test_parse_log_gotest(test_output_gotest):
    status_map = parse_log_gotest(test_output_gotest.read_text())
    assert isinstance(status_map, dict)
    assert all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in status_map.items()
    )
    for test_name, status in [
        ("TestRouteStaticNoListing", "FAILED"),
        ("TestBasicAuth", "PASSED"),
        ("TestContextGetInt8", "PASSED"),
        (
            "TestContextInitQueryCache/queryCache_should_remain_unchanged_if_already_not_nil",
            "PASSED",
        ),
    ]:
        assert test_name in status_map
        assert status_map[test_name] == status
