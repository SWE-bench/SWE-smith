"""
LLM prompts for test-driven bug generation.

This module contains prompts for code reconciliation - updating implementation
to satisfy mutated tests while potentially breaking other tests.
"""

RECONCILIATION_SYSTEM_PROMPT = """You are a code modification expert. Your task is to update implementation code to satisfy a modified test specification.

CRITICAL REQUIREMENTS:
1. The updated code MUST pass the modified test
2. Try to maintain compatibility with other tests, but it's OK if some break (this is desired for creating regression bugs)
3. Make MINIMAL changes - only what's needed to satisfy the new test
4. Preserve code style and structure
5. Do NOT modify the test itself - only the implementation
6. Do NOT add extensive error handling or validation unless specifically required by the mutated test

You will receive:
- The original test
- The modified test (with broader requirements or relaxed constraints)
- The current implementation
- Related tests for context (DO NOT modify these)

Your goal: Update the implementation to pass the modified test. It's acceptable (and sometimes desired) if this breaks other tests, as we're exploring spec-overfitting scenarios."""


RECONCILIATION_TASK_PROMPT = """## Task

A test has been modified to have different requirements. Update the implementation to satisfy the new test.

### Mutation Applied
**Type:** {mutation_type}
**Description:** {mutation_description}

### Original Test
```python
{original_test}
```

### Modified Test
```python
{mutated_test}
```

### Current Implementation
```python
{current_impl}
```

{related_tests_section}

## Instructions

1. **Analyze the change:** Understand what changed between original and modified test
2. **Identify minimal changes:** Determine the minimal code changes needed to satisfy the modified test
3. **Update implementation:** Modify the code to pass the mutated test
4. **Consider side effects:** Think about how this might affect other tests (it's OK if they break)

## Output Format

Provide ONLY the updated implementation code in a ```python code block.

Requirements:
- Complete, runnable implementation (not a diff)
- Same function/class signature
- No explanations outside code comments
- No test code
- No other files

Example:
```python
def example_function(x, y):
    # Updated to handle broader input range
    if x > 1000:  # New condition for mutated test
        return x * 2
    return x + y
```

Now provide the updated implementation:"""


RELATED_TESTS_SECTION = """### Related Tests (for context - DO NOT modify these)
```python
{related_tests}
```

Note: Your changes may cause some of these tests to fail. That's acceptable."""


def format_reconciliation_prompt(
    original_test: str,
    mutated_test: str,
    current_impl: str,
    mutation_type: str,
    mutation_description: str,
    related_tests: str = "",
) -> str:
    """
    Format the reconciliation task prompt.

    Args:
        original_test: Original test code
        mutated_test: Mutated test code
        current_impl: Current implementation code
        mutation_type: Name of mutation type applied
        mutation_description: Description of what was mutated
        related_tests: Other related test code for context

    Returns:
        Formatted prompt string
    """
    # Add related tests section if available
    related_section = ""
    if related_tests and related_tests.strip():
        related_section = RELATED_TESTS_SECTION.format(
            related_tests=related_tests
        )

    return RECONCILIATION_TASK_PROMPT.format(
        original_test=original_test,
        mutated_test=mutated_test,
        current_impl=current_impl,
        mutation_type=mutation_type,
        mutation_description=mutation_description,
        related_tests_section=related_section,
    )


# Alternative: More aggressive prompt for creating obvious bugs
AGGRESSIVE_RECONCILIATION_PROMPT = """## Task: Create a Regression Bug

Your goal is to update the implementation to pass the mutated test WHILE INTENTIONALLY BREAKING other tests.

This is for generating training data for AI agents learning to fix bugs.

### Modified Test (MUST PASS)
```python
{mutated_test}
```

### Current Implementation
```python
{current_impl}
```

### Related Tests (Should FAIL after your changes)
```python
{related_tests}
```

## Strategy

Make changes that:
1. ✅ Satisfy the mutated test
2. ❌ Break at least one related test
3. Look like realistic bugs (overfitting to one requirement)

Common patterns:
- Remove validation that the mutated test no longer checks
- Broaden type constraints if mutated test generalizes types
- Remove bounds checking if mutated test uses larger values
- Add special cases that break general behavior

## Output

Provide ONLY the updated Python code:"""


def format_aggressive_prompt(
    mutated_test: str,
    current_impl: str,
    related_tests: str = "",
) -> str:
    """Format aggressive prompt that explicitly aims to break tests."""
    return AGGRESSIVE_RECONCILIATION_PROMPT.format(
        mutated_test=mutated_test,
        current_impl=current_impl,
        related_tests=related_tests or "# No related tests found",
    )


# Mutation type descriptions for better prompting
MUTATION_DESCRIPTIONS = {
    "broaden_input": "Input values were increased/broadened to test larger ranges",
    "relax_assertion": "Assertion operator was relaxed (e.g., == changed to >=)",
    "add_parameter": "Additional parameter was added to function call",
    "modify_edge_case": "Edge case value was changed to near-edge value (e.g., [] to [None])",
    "generalize_type": "Type constraint was generalized (e.g., list to (list, tuple))",
    "expand_scope": "Assertion scope was expanded with additional conditions",
}


def get_mutation_description(mutation_type: str) -> str:
    """Get human-readable description of mutation type."""
    return MUTATION_DESCRIPTIONS.get(
        mutation_type,
        f"Test was modified using {mutation_type} mutation",
    )
