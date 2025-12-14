"""
Main entry point for test-driven bug generation.

Usage: python -m swesmith.bug_gen.testdriven.generate <repo> --model <model> [options]
"""

import argparse
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from tqdm.auto import tqdm

from swesmith.bug_gen.testdriven.discover import discover_tests
from swesmith.bug_gen.testdriven.mutators import get_applicable_mutations
from swesmith.bug_gen.testdriven.reconcile import reconcile_code_with_test
from swesmith.bug_gen.testdriven.utils import (
    collect_test_statistics,
    create_bug_summary,
    format_bug_summary,
    format_statistics_report,
    save_bug_artifacts,
    save_mutated_test,
)
from swesmith.bug_gen.utils import apply_code_change, get_patch
from swesmith.constants import LOG_DIR_BUG_GEN
from swesmith.profiles import registry

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_test(
    test,
    repo: str,
    rp,
    model: str,
    n_bugs: int,
    mutation_types: Optional[list[str]],
    log_dir: Path,
) -> dict:
    """
    Process a single test: mutate and reconcile code.

    Args:
        test: TestCandidate
        repo: Repository name
        rp: RepoProfile
        model: LLM model
        n_bugs: Number of bug variants per test
        mutation_types: List of mutation types to try
        log_dir: Log directory

    Returns:
        Statistics: {success: int, failed: int, cost: float}
    """
    stats = {"success": 0, "failed": 0, "cost": 0.0}

    # Get applicable mutations
    mutations = get_applicable_mutations(test, mutation_types)

    if not mutations:
        logger.debug(f"No applicable mutations for {test.test_name}")
        return stats

    # Limit to n_bugs mutations
    mutations = mutations[:n_bugs]

    for mutation in mutations:
        try:
            # 1. Mutate test
            mutated = mutation.mutate(test)
            if not mutated:
                stats["failed"] += 1
                continue

            mutated_test_code = mutated.rewrite

            # 2. Save mutated test for reference
            save_mutated_test(test, mutated_test_code, log_dir, mutation.name)

            # 3. Reconcile code with LM
            bug_rewrite = reconcile_code_with_test(
                test_candidate=test,
                mutated_test=mutated_test_code,
                mutation_type=mutation.name,
                repo=repo,
                model=model,
            )

            if not bug_rewrite:
                stats["failed"] += 1
                continue

            stats["cost"] += bug_rewrite.cost

            # 4. Apply code change
            if not test.covered_entities:
                logger.warning(
                    f"No covered entities for {test.test_name}, skipping"
                )
                stats["failed"] += 1
                continue

            target_entity = test.covered_entities[0]
            apply_code_change(target_entity, bug_rewrite)

            # 5. Get patch
            patch = get_patch(repo, reset_changes=True)
            if not patch:
                stats["failed"] += 1
                continue

            # 6. Save artifacts
            save_bug_artifacts(
                log_dir=log_dir,
                test=test,
                mutation_type=mutation.name,
                patch=patch,
                mutated_test=mutated_test_code,
                bug_rewrite=bug_rewrite,
                original_test=test.test_function.src_code,
            )

            stats["success"] += 1

        except Exception as e:
            logger.error(f"Error processing {test.test_name} with {mutation.name}: {e}")
            stats["failed"] += 1

    return stats


def main(
    repo: str,
    model: str = "openai/gpt-4o",
    n_bugs: int = 2,
    max_bugs: int = -1,
    mutation_types: Optional[list[str]] = None,
    coverage_threshold: float = 0.3,
    max_tests_per_file: int = -1,
    n_workers: int = 1,
) -> None:
    """
    Main entry point for test-driven bug generation.

    Args:
        repo: Repository name (e.g., arrow__1d70d009)
        model: LiteLLM model string (e.g., openai/gpt-4o)
        n_bugs: Number of bug variants per test
        max_bugs: Maximum total bugs to generate (-1 for unlimited)
        mutation_types: List of mutation types to apply
        coverage_threshold: Minimum coverage for test selection
        max_tests_per_file: Maximum tests per file (-1 for unlimited)
        n_workers: Number of parallel workers
    """
    logger.info(f"Starting test-driven bug generation for {repo}")
    logger.info(f"Model: {model}")
    logger.info(f"Bugs per test: {n_bugs}")
    logger.info(f"Coverage threshold: {coverage_threshold}")

    # 1. Clone repo and setup
    rp = registry.get(repo)
    rp.clone()

    # 2. Discover tests
    logger.info("Discovering tests...")
    test_candidates = discover_tests(
        repo,
        rp,
        coverage_threshold=coverage_threshold,
        max_tests_per_file=max_tests_per_file,
    )

    if not test_candidates:
        logger.warning(f"No suitable tests found in {repo}")
        shutil.rmtree(repo)
        return

    # Print statistics
    stats = collect_test_statistics(test_candidates)
    logger.info("\n" + format_statistics_report(stats))

    # Limit total bugs if specified
    if max_bugs > 0:
        max_tests = max_bugs // n_bugs
        if max_tests < len(test_candidates):
            test_candidates = test_candidates[:max_tests]
            logger.info(
                f"Limited to {len(test_candidates)} tests "
                f"(max_bugs={max_bugs}, n_bugs={n_bugs})"
            )

    # 3. Setup logging directory
    log_dir = LOG_DIR_BUG_GEN / repo / "testdriven"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Logging bugs to {log_dir}")

    # 4. Process tests
    total_stats = {"success": 0, "failed": 0, "cost": 0.0}

    if n_workers > 1:
        # Parallel processing
        logger.info(f"Processing {len(test_candidates)} tests with {n_workers} workers...")

        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            futures = []
            for test in test_candidates:
                future = executor.submit(
                    process_test,
                    test=test,
                    repo=repo,
                    rp=rp,
                    model=model,
                    n_bugs=n_bugs,
                    mutation_types=mutation_types,
                    log_dir=log_dir,
                )
                futures.append(future)

            # Collect results with progress bar
            with tqdm(total=len(futures), desc="Processing tests") as pbar:
                for future in as_completed(futures):
                    result = future.result()
                    total_stats["success"] += result["success"]
                    total_stats["failed"] += result["failed"]
                    total_stats["cost"] += result["cost"]
                    pbar.update(1)
                    pbar.set_postfix({
                        "success": total_stats["success"],
                        "failed": total_stats["failed"],
                        "cost": f"${total_stats['cost']:.2f}",
                    })
    else:
        # Sequential processing
        logger.info(f"Processing {len(test_candidates)} tests sequentially...")

        for test in tqdm(test_candidates, desc="Processing tests"):
            result = process_test(
                test=test,
                repo=repo,
                rp=rp,
                model=model,
                n_bugs=n_bugs,
                mutation_types=mutation_types,
                log_dir=log_dir,
            )
            total_stats["success"] += result["success"]
            total_stats["failed"] += result["failed"]
            total_stats["cost"] += result["cost"]

    # 5. Cleanup
    shutil.rmtree(repo)

    # 6. Print summary
    total_mutations = total_stats["success"] + total_stats["failed"]
    summary = create_bug_summary(
        total_tests=len(test_candidates),
        total_mutations=total_mutations,
        successful=total_stats["success"],
        failed=total_stats["failed"],
        total_cost=total_stats["cost"],
    )

    logger.info("\n" + format_bug_summary(summary))
    logger.info(f"\nBugs saved to: {log_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate bugs via test-driven mutation and code reconciliation"
    )
    parser.add_argument(
        "repo",
        type=str,
        help="Name of a SWE-smith repository to generate bugs for (e.g., arrow__1d70d009)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="openai/gpt-4o",
        help="LiteLLM model to use for code reconciliation (default: openai/gpt-4o)",
    )
    parser.add_argument(
        "--n_bugs",
        type=int,
        default=2,
        help="Number of bug variants to generate per test (default: 2)",
    )
    parser.add_argument(
        "--max_bugs",
        type=int,
        default=-1,
        help="Maximum total bugs to generate (default: -1, unlimited)",
    )
    parser.add_argument(
        "--mutation_types",
        nargs="+",
        default=None,
        help="Specific mutation types to apply (default: all)",
    )
    parser.add_argument(
        "--coverage_threshold",
        type=float,
        default=0.3,
        help="Minimum coverage score for test selection (default: 0.3)",
    )
    parser.add_argument(
        "--max_tests_per_file",
        type=int,
        default=-1,
        help="Maximum tests to process per file (default: -1, unlimited)",
    )
    parser.add_argument(
        "--n_workers",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1)",
    )

    args = parser.parse_args()
    main(**vars(args))
