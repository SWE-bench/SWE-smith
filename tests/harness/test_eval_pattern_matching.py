"""
Tests for pattern matching functionality in swesmith.harness.eval module.
"""

import pytest
from swesmith.harness.eval import matches_instance_filter


class TestInstanceFilterMatching:
    """Test cases for the matches_instance_filter function."""

    def test_exact_match(self):
        """Test exact matching of instance IDs."""
        assert matches_instance_filter("exact_match", ["exact_match"]) is True
        assert matches_instance_filter("exact_match", ["different_match"]) is False

    def test_pattern_matching_asterisk(self):
        """Test pattern matching with asterisk wildcard."""
        # Test repository-specific pattern matching
        assert (
            matches_instance_filter(
                "life4__textdistance.c3aca916.1", ["life4__textdistance.c3aca916.*"]
            )
            is True
        )
        assert (
            matches_instance_filter(
                "life4__textdistance.c3aca916.2", ["life4__textdistance.c3aca916.*"]
            )
            is True
        )
        assert (
            matches_instance_filter(
                "other__repo.abc123.1", ["life4__textdistance.c3aca916.*"]
            )
            is False
        )

        # Test broader patterns
        assert matches_instance_filter("test__repo.123.1", ["test__repo.*"]) is True
        assert matches_instance_filter("test__repo.456.2", ["test__repo.*"]) is True
        assert matches_instance_filter("other__repo.123.1", ["test__repo.*"]) is False

    def test_pattern_matching_question_mark(self):
        """Test pattern matching with question mark wildcard."""
        assert matches_instance_filter("test_1", ["test_?"]) is True
        assert matches_instance_filter("test_2", ["test_?"]) is True
        assert matches_instance_filter("test_12", ["test_?"]) is False
        assert matches_instance_filter("test_", ["test_?"]) is False

    def test_multiple_filters(self):
        """Test matching against multiple filters."""
        filters = ["test__repo.*", "other__repo.*"]
        assert matches_instance_filter("test__repo.123.1", filters) is True
        assert matches_instance_filter("other__repo.456.2", filters) is True
        assert matches_instance_filter("third__repo.789.3", filters) is False

    def test_none_filter(self):
        """Test that None filter matches everything."""
        assert matches_instance_filter("any_instance", None) is True
        assert matches_instance_filter("another_instance", None) is True

    def test_empty_filter_list(self):
        """Test that empty filter list matches nothing."""
        assert matches_instance_filter("any_instance", []) is False

    def test_mixed_exact_and_pattern(self):
        """Test mixing exact matches and patterns in the same filter list."""
        filters = ["exact_match", "pattern__*"]
        assert matches_instance_filter("exact_match", filters) is True
        assert matches_instance_filter("pattern__test.1", filters) is True
        assert matches_instance_filter("other__test.1", filters) is False

    def test_complex_patterns(self):
        """Test more complex pattern matching scenarios."""
        # Test patterns with multiple wildcards
        assert (
            matches_instance_filter("repo__name.commit.1", ["repo__*.commit.*"]) is True
        )
        assert (
            matches_instance_filter("repo__name.other.1", ["repo__*.commit.*"]) is False
        )

        # Test patterns with character ranges (if supported by fnmatch)
        assert matches_instance_filter("test1", ["test[0-9]"]) is True
        assert matches_instance_filter("testa", ["test[0-9]"]) is False

    @pytest.mark.parametrize(
        "instance_id,filter_list,expected",
        [
            (
                "life4__textdistance.c3aca916.1",
                ["life4__textdistance.c3aca916.*"],
                True,
            ),
            (
                "life4__textdistance.c3aca916.2",
                ["life4__textdistance.c3aca916.*"],
                True,
            ),
            ("other__repo.abc123.1", ["life4__textdistance.c3aca916.*"], False),
            ("exact_match", ["exact_match"], True),
            ("exact_match", ["different_match"], False),
            ("any_instance", None, True),
            ("test__repo.123.1", ["test__repo.*", "other__repo.*"], True),
            ("test__repo.123.1", ["other__repo.*"], False),
        ],
    )
    def test_parametrized_matching(self, instance_id, filter_list, expected):
        """Parametrized test for various matching scenarios."""
        assert matches_instance_filter(instance_id, filter_list) is expected
