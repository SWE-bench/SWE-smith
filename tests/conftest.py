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
def go_test_file():
    return Path("tests", "test_data", "file.go")
