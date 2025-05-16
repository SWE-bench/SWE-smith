"""
Common pytest fixtures and configuration for SWE-smith tests.
"""

import os
import sys
import pytest

# Add the repository root to the Python path to ensure imports work correctly
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)


@pytest.fixture
def sample_repo_path():
    """Return a path to a sample repository for testing."""
    return os.path.join(os.path.dirname(__file__), "test_data", "sample_repo")
