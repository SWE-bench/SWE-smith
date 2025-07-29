"""
Common pytest fixtures and configuration for SWE-smith tests.
"""

import os
import pytest
import sys

from pathlib import Path


# Add the repository root to the Python path to ensure imports work correctly
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)


@pytest.fixture
def test_file_c():
    return Path(repo_root) / "tests/test_logs/files/c/tini.c"


@pytest.fixture
def test_file_cpp():
    return Path(repo_root) / "tests/test_logs/files/cpp/util.cpp"


@pytest.fixture
def test_file_c_sharp():
    return Path(repo_root) / "tests/test_logs/files/c_sharp/ReadTraceNexusImporter.cs"


@pytest.fixture
def test_file_go_caddy_listeners():
    return Path(repo_root) / "tests/test_logs/files/go/caddy/listeners.go"


@pytest.fixture
def test_file_go_caddy_usagepool():
    return Path(repo_root) / "tests/test_logs/files/go/caddy/usagepool.go"


@pytest.fixture
def test_file_go_gin():
    return Path(repo_root) / "tests/test_logs/files/go/gin/logger.go"


@pytest.fixture
def test_file_php():
    return Path(repo_root) / "tests/test_logs/files/php/ControllerDispatcher.php"


@pytest.fixture
def test_file_java():
    return Path(repo_root) / "tests/test_logs/files/java/InOrderImpl.java"


@pytest.fixture
def test_file_py():
    return Path(repo_root) / "tests/test_logs/files/python/extension.py"


@pytest.fixture
def test_file_ruby():
    return Path(repo_root) / "tests/test_logs/files/ruby/query_parser.rb"


@pytest.fixture
def test_file_rust():
    return Path(repo_root) / "tests/test_logs/files/rust/cookie.rs"


@pytest.fixture
def test_file_js():
    return Path(repo_root) / "tests/test_logs/files/javascript/sample.js"


@pytest.fixture
def test_output_gotest():
    return (
        Path(repo_root)
        / "tests/test_logs/test_output/gin-gonic__gin.3c12d2a8.lm_rewrite__4pb48n1g.txt"
    )


@pytest.fixture
def test_output_pytest():
    return (
        Path(repo_root)
        / "tests/test_logs/test_output/django-money__django-money.835c1ab8.combine_file__7znr0kum.txt"
    )


@pytest.fixture
def logs_trajectories():
    return Path(repo_root) / "tests/test_logs/trajectories"


@pytest.fixture
def logs_run_evaluation():
    return Path(repo_root) / "tests/test_logs/run_evaluation"


@pytest.fixture
def logs_run_validation():
    return Path(repo_root) / "tests/test_logs/run_validation"


@pytest.fixture
def ft_xml_example():
    return Path(repo_root) / "tests/test_logs/run_evaluation.xml.jsonl"


@pytest.fixture
def task_instance_path():
    return Path(repo_root) / "tests/test_logs/pandas-dev__pandas.95280573.pr_53652.json"
