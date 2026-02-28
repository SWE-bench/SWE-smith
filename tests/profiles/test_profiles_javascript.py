from unittest.mock import patch

from swesmith.constants import ENV_NAME
from swesmith.profiles.javascript import (
    default_npm_install_dockerfile,
    parse_log_karma,
    parse_log_jasmine,
    GithubReadmeStats3e974011,
    Commanderjs395cf714,
    Colorfef7b619,
)
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


# --- Tests for default_npm_install_dockerfile and mirror_url usage ---


def test_default_npm_install_dockerfile_default_node():
    result = default_npm_install_dockerfile("https://github.com/org/repo")
    assert "FROM node:18-bullseye" in result
    assert f"git clone https://github.com/org/repo /{ENV_NAME}" in result
    assert "npm install" in result


def test_default_npm_install_dockerfile_custom_node():
    result = default_npm_install_dockerfile(
        "https://github.com/org/repo", node_version="22"
    )
    assert "FROM node:22-bullseye" in result


def test_default_npm_install_dockerfile_ssh_url():
    result = default_npm_install_dockerfile("git@github.com:org/repo.git")
    assert f"git clone git@github.com:org/repo.git /{ENV_NAME}" in result


def test_github_readme_stats_dockerfile_uses_mirror_url():
    profile = GithubReadmeStats3e974011()
    with patch.object(type(profile), "_is_repo_private", return_value=False):
        dockerfile = profile.dockerfile
        assert f"https://github.com/{profile.mirror_name}" in dockerfile


def test_github_readme_stats_dockerfile_ssh_when_private():
    profile = GithubReadmeStats3e974011()
    with patch.object(type(profile), "_is_repo_private", return_value=True):
        dockerfile = profile.dockerfile
        assert f"git@github.com:{profile.mirror_name}.git" in dockerfile


def test_commanderjs_uses_node_20():
    profile = Commanderjs395cf714()
    with patch.object(type(profile), "_is_repo_private", return_value=False):
        dockerfile = profile.dockerfile
        assert "FROM node:20-bullseye" in dockerfile
        assert f"https://github.com/{profile.mirror_name}" in dockerfile


def test_color_uses_node_22():
    profile = Colorfef7b619()
    with patch.object(type(profile), "_is_repo_private", return_value=False):
        dockerfile = profile.dockerfile
        assert "FROM node:22-bullseye" in dockerfile
        assert f"https://github.com/{profile.mirror_name}" in dockerfile
