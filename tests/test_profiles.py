from swesmith.profiles import global_registry, RepoProfile
from swesmith.profiles.utils import INSTALL_CMAKE, INSTALL_BAZEL


def test_registry_keys_and_lookup():
    # Should have many keys after importing profiles
    keys = global_registry.keys()
    assert len(keys) > 0
    # Pick a known profile
    key = "swesmith/mewwts__addict.75284f95"
    repo_profile = global_registry.get(key)
    assert repo_profile is not None
    assert isinstance(repo_profile, RepoProfile)
    assert repo_profile.owner == "mewwts"
    assert repo_profile.repo == "addict"
    assert repo_profile.commit.startswith("75284f95")
    # Mirror name matches key
    assert repo_profile.get_mirror_name() == key


def test_get_image_name():
    repo_profile = global_registry.get("swesmith/mewwts__addict.75284f95")
    image_name = repo_profile.get_image_name()
    assert "swesmith" in image_name
    assert repo_profile.owner in image_name
    assert repo_profile.repo in image_name
    assert repo_profile.commit[:8] in image_name


def test_python_log_parser():
    # Use the default PythonProfile log_parser
    repo_profile = global_registry.get("swesmith/mewwts__addict.75284f95")
    log = "test_foo.py PASSED\ntest_bar.py FAILED\ntest_baz.py SKIPPED"

    # Patch TestStatus for this test
    class DummyStatus:
        PASSED = type("T", (), {"value": "PASSED"})
        FAILED = type("T", (), {"value": "FAILED"})
        SKIPPED = type("T", (), {"value": "SKIPPED"})

    import swebench.harness.constants as harness_constants

    old = harness_constants.TestStatus
    harness_constants.TestStatus = [
        DummyStatus.PASSED,
        DummyStatus.FAILED,
        DummyStatus.SKIPPED,
    ]
    try:
        result = repo_profile.log_parser(log)
        assert result["test_foo.py"] == "PASSED"
        assert result["test_bar.py"] == "FAILED"
        assert result["test_baz.py"] == "SKIPPED"
    finally:
        harness_constants.TestStatus = old


def test_golang_log_parser():
    # Use Gin3c12d2a8 Go profile
    key = "swesmith/gin-gonic__gin.3c12d2a8"
    repo_profile = global_registry.get(key)
    log = """
--- PASS: TestFoo (0.01s)
--- FAIL: TestBar (0.02s)
--- SKIP: TestBaz (0.00s)
"""

    class DummyStatus:
        PASSED = type("T", (), {"value": "PASSED"})
        FAILED = type("T", (), {"value": "FAILED"})
        SKIPPED = type("T", (), {"value": "SKIPPED"})

    import swebench.harness.constants as harness_constants

    old = harness_constants.TestStatus
    harness_constants.TestStatus = DummyStatus
    try:
        result = repo_profile.log_parser(log)
        assert result["TestFoo"] == "PASSED"
        assert result["TestBar"] == "FAILED"
        assert result["TestBaz"] == "SKIPPED"
    finally:
        harness_constants.TestStatus = old


def test_utils_install_constants():
    assert isinstance(INSTALL_CMAKE, list)
    assert any("cmake" in cmd for cmd in INSTALL_CMAKE)
    assert isinstance(INSTALL_BAZEL, list)
    assert any("bazel" in cmd for cmd in INSTALL_BAZEL)
