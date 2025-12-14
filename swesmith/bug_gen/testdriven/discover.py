"""
Test discovery and analysis for test-driven bug generation.

This module identifies tests suitable for mutation by analyzing:
- Test file structure
- Code coverage (heuristic)
- Test complexity
- Test dependencies
"""

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from swesmith.bug_gen.adapters import get_entities_from_file
from swesmith.constants import CodeEntity
from swesmith.profiles.base import RepoProfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TestCandidate:
    """
    Represents a test that can be mutated.

    Attributes:
        file_path: Path to test file
        test_name: Name of test function
        test_function: CodeEntity for the test
        covered_entities: Code entities this test covers (heuristic)
        coverage_score: Estimated coverage score (0-1)
        dependencies: Other test names in same file
        assertion_count: Number of assertions in test
        has_parametrize: Whether test is parametrized
    """

    file_path: str
    test_name: str
    test_function: CodeEntity
    covered_entities: list[CodeEntity] = field(default_factory=list)
    coverage_score: float = 0.0
    dependencies: list[str] = field(default_factory=list)
    assertion_count: int = 0
    has_parametrize: bool = False

    def __repr__(self) -> str:
        return f"TestCandidate({self.test_name}, coverage={self.coverage_score:.2f})"


def discover_tests(
    repo: str,
    rp: RepoProfile,
    coverage_threshold: float = 0.3,
    max_tests_per_file: int = -1,
) -> list[TestCandidate]:
    """
    Discover and rank tests suitable for mutation.

    Strategy:
    1. Find all test files using rp.test_paths
    2. Parse test functions using language adapters
    3. Estimate coverage (heuristic: imports, function calls, assertions)
    4. Filter tests with good coverage
    5. Rank by complexity and coverage

    Args:
        repo: Repository path
        rp: RepoProfile instance
        coverage_threshold: Minimum coverage score (0-1)
        max_tests_per_file: Limit tests per file (-1 for unlimited)

    Returns:
        List of TestCandidate objects sorted by suitability
    """
    logger.info(f"Discovering tests in {repo}...")

    # Get test file paths
    test_files = rp.test_paths
    if not test_files:
        logger.warning(f"No test files found in {repo}")
        return []

    logger.info(f"Found {len(test_files)} test files")

    candidates = []
    for test_file in test_files:
        try:
            file_candidates = _discover_tests_in_file(
                test_file=test_file,
                repo=repo,
                rp=rp,
                coverage_threshold=coverage_threshold,
            )
            candidates.extend(file_candidates)

            # Limit per file if specified
            if max_tests_per_file > 0:
                candidates = candidates[:max_tests_per_file]

        except Exception as e:
            logger.debug(f"Error processing {test_file}: {e}")
            continue

    # Sort by coverage score (descending) and assertion count
    candidates = sorted(
        candidates,
        key=lambda x: (x.coverage_score, x.assertion_count),
        reverse=True,
    )

    logger.info(
        f"Discovered {len(candidates)} test candidates (threshold={coverage_threshold})"
    )

    return candidates


def _discover_tests_in_file(
    test_file: Path,
    repo: str,
    rp: RepoProfile,
    coverage_threshold: float,
) -> list[TestCandidate]:
    """Discover tests in a single file."""
    candidates = []

    # Get all entities from test file
    ext = test_file.suffix
    if ext not in rp.exts:
        return []

    try:
        entities = get_entities_from_file(str(test_file), ext)
    except Exception as e:
        logger.debug(f"Could not parse {test_file}: {e}")
        return []

    # Get all test names in this file for dependency tracking
    all_test_names = [e.name for e in entities if _is_test_function(e.name, ext)]

    for entity in entities:
        if not _is_test_function(entity.name, ext):
            continue

        # Analyze test coverage and complexity
        coverage_info = _analyze_test_coverage(entity, repo, rp)

        if coverage_info["score"] < coverage_threshold:
            continue

        # Get dependencies (other tests in same file)
        dependencies = [name for name in all_test_names if name != entity.name]

        candidates.append(
            TestCandidate(
                file_path=str(test_file),
                test_name=entity.name,
                test_function=entity,
                covered_entities=coverage_info["entities"],
                coverage_score=coverage_info["score"],
                dependencies=dependencies,
                assertion_count=coverage_info["assertion_count"],
                has_parametrize=coverage_info["has_parametrize"],
            )
        )

    return candidates


def _is_test_function(name: str, ext: str) -> bool:
    """
    Check if entity name indicates it's a test function.

    Supports:
    - Python: test_*, Test*
    - Go: Test*, Benchmark*
    - Rust: #[test]
    """
    name_lower = name.lower()

    if ext == ".py":
        return name_lower.startswith("test_") or name.startswith("Test")
    elif ext == ".go":
        return name.startswith("Test") or name.startswith("Benchmark")
    elif ext == ".rs":
        # Rust tests are marked with #[test] attribute
        # This is handled in the adapter
        return "test" in name_lower

    return False


def _analyze_test_coverage(entity: CodeEntity, repo: str, rp: RepoProfile) -> dict:
    """
    Heuristically estimate what code a test covers.

    Heuristics:
    1. Count assertions (more = better coverage)
    2. Count function calls (more = more code exercised)
    3. Check for parametrize (indicates comprehensive testing)
    4. Identify imported modules/functions

    Returns:
        {
            'score': float (0-1),
            'entities': list[CodeEntity],
            'assertion_count': int,
            'has_parametrize': bool,
        }
    """
    src_code = entity.src_code

    # Count assertions
    assertion_count = src_code.count("assert")

    # Count function calls (rough heuristic)
    function_call_count = src_code.count("(") - src_code.count("def ")

    # Check for parametrize decorators
    has_parametrize = (
        "@pytest.mark.parametrize" in src_code or "@parametrize" in src_code
    )

    # Heuristic scoring
    score = 0.0

    # Assertions contribute most
    if assertion_count > 0:
        score += min(assertion_count * 0.2, 0.6)  # Cap at 0.6

    # Function calls indicate complexity
    if function_call_count > 2:
        score += min(function_call_count * 0.05, 0.3)  # Cap at 0.3

    # Parametrized tests are valuable
    if has_parametrize:
        score += 0.2

    # Normalize to 0-1
    score = min(score, 1.0)

    # Try to identify covered entities (simplified for now)
    covered_entities = _identify_covered_entities(entity, repo, rp)

    return {
        "score": score,
        "entities": covered_entities,
        "assertion_count": assertion_count,
        "has_parametrize": has_parametrize,
    }


def _identify_covered_entities(
    test_entity: CodeEntity, repo: str, rp: RepoProfile
) -> list[CodeEntity]:
    """
    Identify code entities covered by this test.

    This is a simplified heuristic version. A more sophisticated version
    would:
    - Parse imports to find modules
    - Match function calls to actual implementations
    - Use static analysis or coverage tools

    For now, we return an empty list and rely on manual specification
    or future enhancement.
    """
    # TODO: Implement sophisticated coverage analysis
    # For now, return empty list
    return []


def get_related_tests(test_file: str, test_name: str) -> list[str]:
    """
    Get other tests in the same file that might be affected by mutations.

    Args:
        test_file: Path to test file
        test_name: Name of the test function

    Returns:
        List of related test names
    """
    try:
        ext = Path(test_file).suffix
        entities = get_entities_from_file(test_file, ext)

        related = [
            e.name
            for e in entities
            if _is_test_function(e.name, ext) and e.name != test_name
        ]

        return related
    except Exception as e:
        logger.debug(f"Could not get related tests from {test_file}: {e}")
        return []


def filter_by_coverage(
    candidates: list[TestCandidate], threshold: float = 0.5
) -> list[TestCandidate]:
    """Filter test candidates by coverage score."""
    return [c for c in candidates if c.coverage_score >= threshold]


def filter_by_assertions(
    candidates: list[TestCandidate], min_assertions: int = 1
) -> list[TestCandidate]:
    """Filter test candidates by assertion count."""
    return [c for c in candidates if c.assertion_count >= min_assertions]


def rank_by_complexity(candidates: list[TestCandidate]) -> list[TestCandidate]:
    """
    Rank test candidates by complexity.

    Complexity factors:
    - Coverage score
    - Assertion count
    - Parametrization
    """
    return sorted(
        candidates,
        key=lambda x: (
            x.coverage_score,
            x.assertion_count,
            x.has_parametrize,
        ),
        reverse=True,
    )
