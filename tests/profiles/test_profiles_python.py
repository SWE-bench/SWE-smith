import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

# Mock docker import
with patch("docker.from_env", return_value=MagicMock()):
    from swesmith.profiles.python import PythonProfile, Addict75284f95, AutogradAc044f0d
    from swesmith.profiles import global_registry


def test_python_profile_defaults():
    """Test PythonProfile default values"""
    profile = PythonProfile()

    assert profile.python_version == "3.10"
    assert profile.install_cmds == ["python -m pip install -e ."]
    assert profile.test_cmd == "pytest --disable-warnings --color=no --tb=no --verbose"


def test_python_profile_build_image():
    """Test PythonProfile.build_image method"""
    profile = Addict75284f95()

    mock_client = MagicMock()
    mock_env_yml_content = "name: test_env\ndependencies:\n  - python=3.10"

    with (
        patch("docker.from_env", return_value=mock_client),
        patch("builtins.open", mock_open(read_data=mock_env_yml_content)),
        patch("swesmith.profiles.python.build_image_sweb") as mock_build,
        patch("swesmith.profiles.python.get_dockerfile_env", return_value="FROM test"),
    ):
        profile.build_image()

        # Verify build_image_sweb was called with correct parameters
        mock_build.assert_called_once()
        call_args = mock_build.call_args
        assert call_args[1]["image_name"] == profile.image_name
        assert call_args[1]["platform"] == profile.pltf
        assert call_args[1]["client"] == mock_client

        # Verify setup script contains expected commands
        setup_script = call_args[1]["setup_scripts"]["setup_env.sh"]
        assert "git clone" in setup_script
        assert "conda env create" in setup_script
        assert "conda activate" in setup_script
        assert profile.install_cmds[0] in setup_script


def test_python_profile_log_parser():
    """Test PythonProfile.log_parser method"""
    profile = PythonProfile()

    log = """
test_file1.py PASSED
test_file2.py FAILED
test_file3.py SKIPPED
"""

    result = profile.log_parser(log)

    assert result["test_file1.py"] == "PASSED"
    assert result["test_file2.py"] == "FAILED"
    assert result["test_file3.py"] == "SKIPPED"


def test_python_profile_log_parser_no_matches():
    """Test PythonProfile.log_parser with no matching lines"""
    profile = PythonProfile()

    log = """
Some random text
No test results here
"""

    result = profile.log_parser(log)
    assert result == {}


def test_python_profile_env_yml_property():
    """Test PythonProfile._env_yml property"""
    profile = Addict75284f95()

    expected_path = Path(
        f"logs/build_images/env/{profile.repo_name}/sweenv_{profile.repo_name}.yml"
    )
    assert profile._env_yml == expected_path


def test_autograd_log_parser():
    """Test AutogradAc044f0d custom log_parser"""
    profile = AutogradAc044f0d()

    log = """
[gw0] PASSED test_autograd.py
[gw1] FAILED test_gradients.py
[gw2] SKIPPED test_hessian.py
"""

    result = profile.log_parser(log)

    assert result["test_autograd.py"] == "PASSED"
    assert result["test_gradients.py"] == "FAILED"
    assert result["test_hessian.py"] == "SKIPPED"


def test_python_profile_inheritance():
    """Test that Python profiles properly inherit from PythonProfile"""
    # Test a few different profiles
    profiles_to_test = [
        Addict75284f95,
        AutogradAc044f0d,
    ]

    for profile_class in profiles_to_test:
        profile = profile_class()
        assert isinstance(profile, PythonProfile)
        assert hasattr(profile, "python_version")
        assert hasattr(profile, "install_cmds")
        assert hasattr(profile, "test_cmd")
        assert hasattr(profile, "build_image")
        assert hasattr(profile, "log_parser")


def test_python_profile_custom_install_cmds():
    """Test Python profiles with custom install commands"""
    # Test Apispec8b421526 which has custom install_cmds
    from swesmith.profiles.python import Apispec8b421526

    profile = Apispec8b421526()
    assert profile.install_cmds == ["pip install -e .[dev]"]
    assert profile.install_cmds != PythonProfile().install_cmds


def test_python_profile_custom_test_cmd():
    """Test Python profiles with custom test commands"""
    # Test Gpxpy09fc46b3 which has custom test_cmd
    from swesmith.profiles.python import Gpxpy09fc46b3

    profile = Gpxpy09fc46b3()
    expected_cmd = "pytest test.py --verbose --color=no --tb=no --disable-warnings"
    assert profile.test_cmd == expected_cmd
    assert profile.test_cmd != PythonProfile().test_cmd


def test_python_profile_custom_python_version():
    """Test Python profiles with custom Python versions"""
    # Test Pydicom7d361b3d which has custom python_version
    from swesmith.profiles.python import Pydicom7d361b3d

    profile = Pydicom7d361b3d()
    assert profile.python_version == "3.11"
    assert profile.python_version != PythonProfile().python_version


def test_python_profile_min_testing_flag():
    """Test Python profiles with min_testing flag"""
    # Test JaxEbd90e06f which has min_testing=True
    from swesmith.profiles.python import JaxEbd90e06f

    profile = JaxEbd90e06f()
    assert profile.min_testing is True
    assert profile.min_pregold is True


def test_python_profile_complex_install_cmds():
    """Test Python profiles with complex install commands"""
    # Test FvcoreA491d5b9 which has multiple install commands
    from swesmith.profiles.python import FvcoreA491d5b9

    profile = FvcoreA491d5b9()
    assert len(profile.install_cmds) > 1
    assert any("pip install" in cmd for cmd in profile.install_cmds)


def test_python_profile_registry_integration():
    """Test that Python profiles are properly registered in global registry"""
    # Test that some Python profiles are in the registry
    python_profile_keys = [
        "mewwts__addict.75284f95",  # Addict75284f95
        "HIPS__autograd.ac044f0d",  # AutogradAc044f0d
    ]

    for key in python_profile_keys:
        profile = global_registry.get(key)
        assert profile is not None
        assert isinstance(profile, PythonProfile)


def test_python_profile_log_parser_edge_cases():
    """Test PythonProfile.log_parser with edge cases"""
    profile = PythonProfile()

    # Test empty log
    result = profile.log_parser("")
    assert result == {}

    # Test log with only whitespace
    result = profile.log_parser("   \n  \t  \n")
    assert result == {}

    # Test log with partial matches
    log = """
test_file.py PASS
test_file.py PASSED
test_file.py FAIL
"""
    result = profile.log_parser(log)
    # Should only match the complete status values
    assert "test_file.py" in result
    assert result["test_file.py"] in ["PASSED", "FAILED"]


def test_python_profile_build_image_error_handling():
    """Test PythonProfile.build_image error handling"""
    profile = Addict75284f95()

    with patch("docker.from_env", side_effect=Exception("Docker error")):
        with pytest.raises(Exception, match="Docker error"):
            profile.build_image()


def test_python_profile_custom_log_parser_inheritance():
    """Test that custom log_parser methods properly override the base method"""
    # Test AutogradAc044f0d which has a custom log_parser
    autograd_profile = AutogradAc044f0d()
    base_profile = PythonProfile()

    # They should have different log_parser methods
    assert autograd_profile.log_parser != base_profile.log_parser

    # Test that they produce different results for the same input
    log = "[gw0] PASSED test_file.py"

    autograd_result = autograd_profile.log_parser(log)
    base_result = base_profile.log_parser(log)

    # Autograd should parse this, base should not
    assert "test_file.py" in autograd_result
    assert "test_file.py" not in base_result


def test_python_profile_log_parser_with_real_pytest_output(test_output_pytest):
    """Test PythonProfile.log_parser method with real pytest output"""
    profile = PythonProfile()

    # Read the actual pytest output file
    log_content = test_output_pytest.read_text()

    # Parse the log using the profile's log_parser method
    result = profile.log_parser(log_content)

    # Verify the result is a dictionary with string keys and values
    assert isinstance(result, dict)
    assert all(
        isinstance(key, str) and isinstance(value, str) for key, value in result.items()
    )

    # Test specific test results that we know should be in the output
    expected_results = [
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
    ]

    for test_name, expected_status in expected_results:
        assert test_name in result, f"Test {test_name} not found in parsed results"
        assert result[test_name] == expected_status, (
            f"Expected {test_name} to be {expected_status}, got {result[test_name]}"
        )

    # Verify that we have a reasonable number of test results
    # The actual file contains many more tests, so we should have a substantial number
    assert len(result) > 100, f"Expected many test results, got {len(result)}"

    # Verify that all status values are valid
    valid_statuses = {"PASSED", "FAILED", "SKIPPED"}
    for status in result.values():
        assert status in valid_statuses, f"Invalid status: {status}"

    # Verify that we have both passed and failed tests
    status_counts = {}
    for status in result.values():
        status_counts[status] = status_counts.get(status, 0) + 1

    assert "PASSED" in status_counts, "No PASSED tests found"
    assert "FAILED" in status_counts, "No FAILED tests found"
    assert status_counts["PASSED"] == 377, (
        f"Expected many PASSED tests, got {status_counts['PASSED']}"
    )
    assert status_counts["FAILED"] == 9, (
        f"Expected at least 9 FAILED tests, got {status_counts['FAILED']}"
    )
