"""
Code reconciliation using LLMs.

This module handles updating implementation code to satisfy mutated tests,
potentially creating spec-overfitting bugs.
"""

import logging
from typing import Optional

from litellm import completion
from litellm.cost_calculator import completion_cost

from swesmith.bug_gen.llm.utils import extract_code_block
from swesmith.bug_gen.testdriven.discover import TestCandidate
from swesmith.bug_gen.testdriven.prompts import (
    RECONCILIATION_SYSTEM_PROMPT,
    format_reconciliation_prompt,
    get_mutation_description,
)
from swesmith.constants import BugRewrite, CodeEntity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def reconcile_code_with_test(
    test_candidate: TestCandidate,
    mutated_test: str,
    mutation_type: str,
    repo: str,
    model: str,
    target_entity: Optional[CodeEntity] = None,
) -> Optional[BugRewrite]:
    """
    Use LLM to update implementation to satisfy mutated test.

    This is the core function that generates the "bug" - code that passes
    the mutated test but may break other tests.

    Args:
        test_candidate: Original test information
        mutated_test: The mutated test code
        mutation_type: Type of mutation applied
        repo: Repository path
        model: LiteLLM model string
        target_entity: Specific entity to modify (if known)

    Returns:
        BugRewrite with updated implementation, or None if failed
    """
    # 1. Get target implementation entity
    if target_entity is None:
        target_entity = _identify_target_entity(test_candidate, repo)

    if target_entity is None:
        logger.warning(
            f"Could not identify target entity for {test_candidate.test_name}"
        )
        return None

    # 2. Get context: related tests
    related_tests = _get_related_test_code(test_candidate)

    # 3. Build prompt
    mutation_description = get_mutation_description(mutation_type)

    user_prompt = format_reconciliation_prompt(
        original_test=test_candidate.test_function.src_code,
        mutated_test=mutated_test,
        current_impl=target_entity.src_code,
        mutation_type=mutation_type,
        mutation_description=mutation_description,
        related_tests=related_tests,
    )

    messages = [
        {"role": "system", "content": RECONCILIATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    # 4. Call LLM
    try:
        response = completion(
            model=model,
            messages=messages,
            temperature=0,  # Deterministic for reproducibility
            n=1,
        )

        # 5. Extract code
        response_content = response.choices[0].message.content
        new_impl = extract_code_block(response_content)

        if not new_impl or len(new_impl.strip()) == 0:
            logger.warning(
                f"Failed to extract code from LLM response for {test_candidate.test_name}"
            )
            return None

        # 6. Create BugRewrite
        cost = completion_cost(completion_response=response)

        return BugRewrite(
            rewrite=new_impl,
            explanation=f"Reconciled code for mutated test ({mutation_type}): {mutation_description}",
            strategy="testdriven",
            cost=cost,
            output=response_content,
        )

    except Exception as e:
        logger.error(f"Error calling LLM for reconciliation: {e}")
        return None


def _identify_target_entity(
    test_candidate: TestCandidate, repo: str
) -> Optional[CodeEntity]:
    """
    Identify the code entity that the test is testing.

    For now, we use a simple heuristic:
    - Use the first covered entity if available
    - Otherwise, return None and require manual specification

    Future improvements:
    - Parse imports and function calls to identify target
    - Use static analysis or coverage tools
    - Match test name to function name (test_foo -> foo)

    Args:
        test_candidate: Test to analyze
        repo: Repository path

    Returns:
        CodeEntity to modify, or None if cannot determine
    """
    # Use covered entities if available
    if test_candidate.covered_entities:
        return test_candidate.covered_entities[0]

    # Try to infer from test name
    # e.g., test_parse_date -> parse_date
    test_name = test_candidate.test_name
    if test_name.startswith("test_"):
        potential_func_name = test_name[5:]  # Remove "test_" prefix

        # TODO: Search for function with this name in repo
        # For now, return None
        logger.debug(
            f"Could infer target function name: {potential_func_name}, "
            "but entity lookup not implemented"
        )

    return None


def _get_related_test_code(
    test_candidate: TestCandidate,
    max_tests: int = 3,
) -> str:
    """
    Get code of related tests for context.

    Args:
        test_candidate: Test to get related tests for
        max_tests: Maximum number of related tests to include

    Returns:
        Concatenated code of related tests
    """
    if not test_candidate.dependencies:
        return ""

    # Read test file and extract related test functions
    try:
        with open(test_candidate.file_path, "r") as f:
            file_content = f.read()

        # Simple extraction: look for function definitions
        # This is a simplification - a better approach would parse the AST
        related_code = []
        for test_name in test_candidate.dependencies[:max_tests]:
            # Find function definition
            func_pattern = f"def {test_name}("
            if func_pattern in file_content:
                # Extract function (rough heuristic)
                start_idx = file_content.index(func_pattern)
                # Find next function or end of file
                next_func_idx = file_content.find("\ndef ", start_idx + 1)
                if next_func_idx == -1:
                    next_func_idx = len(file_content)

                func_code = file_content[start_idx:next_func_idx].strip()
                related_code.append(func_code)

        return "\n\n".join(related_code)

    except Exception as e:
        logger.debug(f"Could not extract related test code: {e}")
        return ""


def reconcile_with_retry(
    test_candidate: TestCandidate,
    mutated_test: str,
    mutation_type: str,
    repo: str,
    model: str,
    target_entity: Optional[CodeEntity] = None,
    max_retries: int = 2,
) -> Optional[BugRewrite]:
    """
    Reconcile code with retry logic.

    If the first attempt fails to extract code, retry with different
    temperature or prompt variations.

    Args:
        test_candidate: Test candidate
        mutated_test: Mutated test code
        mutation_type: Mutation type
        repo: Repository path
        model: LLM model
        target_entity: Target entity to modify
        max_retries: Maximum retry attempts

    Returns:
        BugRewrite or None
    """
    for attempt in range(max_retries + 1):
        result = reconcile_code_with_test(
            test_candidate=test_candidate,
            mutated_test=mutated_test,
            mutation_type=mutation_type,
            repo=repo,
            model=model,
            target_entity=target_entity,
        )

        if result is not None:
            return result

        logger.debug(
            f"Retry {attempt + 1}/{max_retries} for {test_candidate.test_name}"
        )

    return None


def batch_reconcile(
    test_mutations: list[tuple[TestCandidate, str, str]],
    repo: str,
    model: str,
    max_workers: int = 1,
) -> list[Optional[BugRewrite]]:
    """
    Reconcile multiple test mutations in batch.

    Args:
        test_mutations: List of (test_candidate, mutated_test, mutation_type)
        repo: Repository path
        model: LLM model
        max_workers: Number of parallel workers

    Returns:
        List of BugRewrites (same order as input, None for failures)
    """
    results = []

    # For now, process sequentially
    # TODO: Add parallel processing with ThreadPoolExecutor
    for test_candidate, mutated_test, mutation_type in test_mutations:
        result = reconcile_code_with_test(
            test_candidate=test_candidate,
            mutated_test=mutated_test,
            mutation_type=mutation_type,
            repo=repo,
            model=model,
        )
        results.append(result)

    return results
