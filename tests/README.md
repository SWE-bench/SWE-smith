# SWE-smith Tests

This directory contains tests for the SWE-smith package.

## Structure

- `conftest.py`: Common pytest fixtures and configuration
- `test_data/`: Directory containing test data files
- `test_*.py`: Test files for different components of SWE-smith

## Running Tests

To run the tests, you can use pytest:

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run tests with coverage
pytest --cov=swesmith

# Run a specific test file
pytest tests/test_specific_file.py
```

## Adding Tests

When adding new tests:

1. Create a new file named `test_*.py` for the component you're testing
2. Use pytest fixtures from `conftest.py` where appropriate
3. Add any necessary test data to the `test_data/` directory