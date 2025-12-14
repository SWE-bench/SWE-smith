"""
Utility functions for test-driven bug generation.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from swesmith.bug_gen.testdriven.discover import TestCandidate
from swesmith.constants import (
    BugRewrite,
    PREFIX_BUG,
    PREFIX_METADATA,
    generate_hash,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def save_bug_artifacts(
    log_dir: Path,
    test: TestCandidate,
    mutation_type: str,
    patch: str,
    mutated_test: str,
    bug_rewrite: BugRewrite,
    original_test: str,
) -> tuple[Path, Path]:
    """
    Save bug patch and metadata.

    Creates directory structure:
    log_dir/
      <test_file>/
        <test_name>/
          bug__testdriven_<mutation>__<hash>.diff
          metadata__testdriven_<mutation>__<hash>.json

    Args:
        log_dir: Base log directory
        test: TestCandidate
        mutation_type: Type of mutation applied
        patch: Git patch content
        mutated_test: Mutated test code
        bug_rewrite: BugRewrite with reconciled code
        original_test: Original test code

    Returns:
        Tuple of (bug_path, metadata_path)
    """
    # Create directory structure similar to procedural/llm
    bug_dir = (
        log_dir / test.file_path.replace("/", "__").replace("\\", "__") / test.test_name
    )
    bug_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique identifier
    uuid_str = f"testdriven_{mutation_type}__{generate_hash(patch)}"

    # Save patch
    bug_path = bug_dir / f"{PREFIX_BUG}__{uuid_str}.diff"
    with open(bug_path, "w") as f:
        f.write(patch)

    # Save metadata
    metadata = {
        **bug_rewrite.to_dict(),
        "test_file": test.file_path,
        "test_name": test.test_name,
        "mutation_type": mutation_type,
        "original_test": original_test,
        "mutated_test": mutated_test,
        "coverage_score": test.coverage_score,
        "assertion_count": test.assertion_count,
        "has_parametrize": test.has_parametrize,
    }

    metadata_path = bug_dir / f"{PREFIX_METADATA}__{uuid_str}.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.debug(f"Saved bug artifacts to {bug_dir}")

    return bug_path, metadata_path


def save_mutated_test(
    test: TestCandidate,
    mutated_test_code: str,
    log_dir: Path,
    mutation_type: str,
) -> Path:
    """
    Save mutated test for reference and analysis.

    Creates:
    log_dir/mutated_tests/
      <test_file>/
        <test_name>__<mutation_type>.py

    Args:
        test: TestCandidate
        mutated_test_code: Mutated test code
        log_dir: Base log directory
        mutation_type: Type of mutation

    Returns:
        Path to saved mutated test file
    """
    test_dir = (
        log_dir
        / "mutated_tests"
        / test.file_path.replace("/", "__").replace("\\", "__")
    )
    test_dir.mkdir(parents=True, exist_ok=True)

    test_file_path = test_dir / f"{test.test_name}__{mutation_type}.py"
    with open(test_file_path, "w") as f:
        f.write(mutated_test_code)

    logger.debug(f"Saved mutated test to {test_file_path}")

    return test_file_path


def load_test_candidate(metadata_path: Path) -> Optional[TestCandidate]:
    """
    Load TestCandidate from metadata file.

    Args:
        metadata_path: Path to metadata JSON file

    Returns:
        TestCandidate or None if loading fails
    """
    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        # Note: This is a simplified version - the full test_function
        # CodeEntity would need to be reconstructed from the file
        return TestCandidate(
            file_path=metadata["test_file"],
            test_name=metadata["test_name"],
            test_function=None,  # Would need to parse file
            coverage_score=metadata.get("coverage_score", 0.0),
            assertion_count=metadata.get("assertion_count", 0),
            has_parametrize=metadata.get("has_parametrize", False),
        )
    except Exception as e:
        logger.error(f"Error loading test candidate from {metadata_path}: {e}")
        return None


def collect_test_statistics(test_candidates: list[TestCandidate]) -> dict:
    """
    Collect statistics about test candidates.

    Args:
        test_candidates: List of TestCandidates

    Returns:
        Dictionary with statistics
    """
    if not test_candidates:
        return {
            "total": 0,
            "avg_coverage": 0.0,
            "avg_assertions": 0.0,
            "parametrized_count": 0,
        }

    return {
        "total": len(test_candidates),
        "avg_coverage": sum(t.coverage_score for t in test_candidates)
        / len(test_candidates),
        "avg_assertions": sum(t.assertion_count for t in test_candidates)
        / len(test_candidates),
        "parametrized_count": sum(1 for t in test_candidates if t.has_parametrize),
        "min_coverage": min(t.coverage_score for t in test_candidates),
        "max_coverage": max(t.coverage_score for t in test_candidates),
    }


def format_statistics_report(stats: dict) -> str:
    """
    Format statistics as a readable string.

    Args:
        stats: Statistics dictionary

    Returns:
        Formatted string
    """
    return f"""Test Discovery Statistics:
  Total tests found: {stats["total"]}
  Coverage scores:
    - Average: {stats["avg_coverage"]:.2f}
    - Min: {stats.get("min_coverage", 0):.2f}
    - Max: {stats.get("max_coverage", 0):.2f}
  Assertions:
    - Average per test: {stats["avg_assertions"]:.1f}
  Parametrized tests: {stats["parametrized_count"]}"""


def create_bug_summary(
    total_tests: int,
    total_mutations: int,
    successful: int,
    failed: int,
    total_cost: float,
) -> dict:
    """
    Create summary of bug generation run.

    Args:
        total_tests: Number of tests processed
        total_mutations: Total mutations attempted
        successful: Number of successful bug generations
        failed: Number of failures
        total_cost: Total LLM cost

    Returns:
        Summary dictionary
    """
    success_rate = (successful / total_mutations * 100) if total_mutations > 0 else 0

    return {
        "total_tests_processed": total_tests,
        "total_mutations_attempted": total_mutations,
        "successful_bugs": successful,
        "failed_mutations": failed,
        "success_rate_pct": success_rate,
        "total_cost_usd": total_cost,
        "avg_cost_per_bug": total_cost / successful if successful > 0 else 0,
    }


def format_bug_summary(summary: dict) -> str:
    """
    Format bug generation summary as readable string.

    Args:
        summary: Summary dictionary

    Returns:
        Formatted string
    """
    return f"""Bug Generation Summary:
  Tests Processed: {summary["total_tests_processed"]}
  Mutations Attempted: {summary["total_mutations_attempted"]}
  Successful Bugs: {summary["successful_bugs"]}
  Failed Mutations: {summary["failed_mutations"]}
  Success Rate: {summary["success_rate_pct"]:.1f}%
  Total Cost: ${summary["total_cost_usd"]:.2f}
  Avg Cost per Bug: ${summary["avg_cost_per_bug"]:.3f}"""


def validate_test_candidate(test: TestCandidate) -> bool:
    """
    Validate that a TestCandidate has required fields.

    Args:
        test: TestCandidate to validate

    Returns:
        True if valid, False otherwise
    """
    if not test.file_path or not test.test_name:
        logger.warning("Invalid test candidate: missing file_path or test_name")
        return False

    if not test.test_function:
        logger.warning(
            f"Invalid test candidate {test.test_name}: missing test_function"
        )
        return False

    if test.coverage_score < 0 or test.coverage_score > 1:
        logger.warning(
            f"Invalid coverage score for {test.test_name}: {test.coverage_score}"
        )
        return False

    return True


def deduplicate_tests(tests: list[TestCandidate]) -> list[TestCandidate]:
    """
    Remove duplicate tests based on file_path + test_name.

    Args:
        tests: List of TestCandidates

    Returns:
        Deduplicated list
    """
    seen = set()
    unique_tests = []

    for test in tests:
        key = (test.file_path, test.test_name)
        if key not in seen:
            seen.add(key)
            unique_tests.append(test)

    if len(unique_tests) < len(tests):
        logger.info(f"Removed {len(tests) - len(unique_tests)} duplicate tests")

    return unique_tests
