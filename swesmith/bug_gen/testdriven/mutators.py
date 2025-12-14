"""
Test mutation operators for test-driven bug generation.

This module provides mutation operators that modify test code to:
- Broaden input ranges
- Relax assertions
- Add parameter combinations
- Modify edge cases
- Generalize type constraints
"""

import logging
import random
import re
from abc import ABC, abstractmethod
from typing import Optional

from swesmith.bug_gen.testdriven.discover import TestCandidate
from swesmith.constants import BugRewrite

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestMutation(ABC):
    """Base class for test mutations."""

    @abstractmethod
    def can_apply(self, test: TestCandidate) -> bool:
        """Check if mutation can be applied to test."""
        pass

    @abstractmethod
    def mutate(self, test: TestCandidate) -> Optional[BugRewrite]:
        """
        Apply mutation to test.

        Returns:
            BugRewrite with mutated test code, or None if mutation failed
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of mutation type."""
        pass

    def _create_rewrite(self, mutated_code: str, explanation: str) -> BugRewrite:
        """Create BugRewrite object for mutated test."""
        return BugRewrite(
            rewrite=mutated_code,
            explanation=explanation,
            strategy="testdriven_mutation",
            cost=0,  # No LLM cost for mutations
            output=f"{self.name}: {explanation}",
        )


class BroadenInputRange(TestMutation):
    """
    Mutation: Expand input ranges in test.

    Example:
        Original: test_process(value=5)
        Mutated:  test_process(value=1000)

    Targets: Numeric literals in function calls
    """

    @property
    def name(self) -> str:
        return "broaden_input"

    def can_apply(self, test: TestCandidate) -> bool:
        """Check for numeric literals in test."""
        src = test.test_function.src_code
        # Check for numeric literals
        return bool(re.search(r"\d+", src) and "(" in src)

    def mutate(self, test: TestCandidate) -> Optional[BugRewrite]:
        """Broaden numeric input values."""
        src = test.test_function.src_code

        # Find numeric literals and multiply them
        def replace_number(match):
            num = int(match.group(0))
            # Broaden: small numbers -> larger, large numbers -> much larger
            if num < 10:
                return str(num * 100)
            elif num < 100:
                return str(num * 10)
            else:
                return str(num * 2)

        mutated = re.sub(r"\b(\d+)\b", replace_number, src, count=3)

        if mutated == src:
            return None

        return self._create_rewrite(
            mutated,
            "Broadened numeric input ranges (multiplied values)",
        )


class RelaxAssertion(TestMutation):
    """
    Mutation: Weaken assertion conditions.

    Example:
        Original: assert result == 10
        Mutated:  assert result >= 10

    Targets: Equality assertions
    """

    @property
    def name(self) -> str:
        return "relax_assertion"

    def can_apply(self, test: TestCandidate) -> bool:
        """Check for equality assertions."""
        src = test.test_function.src_code
        return "assert" in src and ("==" in src or "is " in src)

    def mutate(self, test: TestCandidate) -> Optional[BugRewrite]:
        """Relax assertion operators."""
        src = test.test_function.src_code
        mutated = src

        # Replace == with >= or <=
        # Prioritize == first
        if " == " in mutated:
            # Randomly choose >= or <=
            replacement = " >= " if random.random() > 0.5 else " <= "
            mutated = mutated.replace(" == ", replacement, 1)
            explanation = f"Relaxed == to {replacement.strip()}"

        # Replace 'is' with 'isinstance'
        elif re.search(r"assert\s+\w+\s+is\s+", mutated):
            # This is more complex, for now skip
            return None

        else:
            return None

        if mutated == src:
            return None

        return self._create_rewrite(mutated, explanation)


class AddParameterCombination(TestMutation):
    """
    Mutation: Add new parameter combinations.

    Example:
        Original: func(a=1, b=2)
        Mutated:  func(a=1, b=2, c=0)

    Targets: Function calls with keyword arguments
    """

    @property
    def name(self) -> str:
        return "add_parameter"

    def can_apply(self, test: TestCandidate) -> bool:
        """Check for function calls with keyword arguments."""
        src = test.test_function.src_code
        # Look for keyword arguments pattern
        return bool(re.search(r"\w+\s*=\s*\w+", src))

    def mutate(self, test: TestCandidate) -> Optional[BugRewrite]:
        """Add a new parameter to function call."""
        src = test.test_function.src_code

        # Find function calls with keyword args
        # Pattern: function_name(arg1=val1, arg2=val2)
        pattern = r"(\w+)\(((?:\w+\s*=\s*[^,)]+,?\s*)+)\)"

        def add_param(match):
            func_name = match.group(1)
            args = match.group(2).rstrip(", ")
            # Add a new parameter
            new_param = "extra_param=None"
            return f"{func_name}({args}, {new_param})"

        mutated = re.sub(pattern, add_param, src, count=1)

        if mutated == src:
            return None

        return self._create_rewrite(
            mutated,
            "Added extra parameter to function call",
        )


class ModifyEdgeCase(TestMutation):
    """
    Mutation: Change edge case values.

    Example:
        Original: test_empty_list([])
        Mutated:  test_empty_list([None])

    Targets: Empty collections, None, 0, empty strings
    """

    @property
    def name(self) -> str:
        return "modify_edge_case"

    def can_apply(self, test: TestCandidate) -> bool:
        """Check for edge case values."""
        src = test.test_function.src_code
        return any(
            edge in src for edge in ["[]", "{}", '""', "''", "None", " 0,", " 0)", "=0"]
        )

    def mutate(self, test: TestCandidate) -> Optional[BugRewrite]:
        """Modify edge case values to near-edge values."""
        src = test.test_function.src_code
        mutated = src

        # Replace empty list with list containing None
        if "[]" in mutated:
            mutated = mutated.replace("[]", "[None]", 1)
            explanation = "Changed empty list to [None]"

        # Replace empty string with space
        elif '""' in mutated:
            mutated = mutated.replace('""', '" "', 1)
            explanation = "Changed empty string to single space"

        # Replace 0 with 1
        elif re.search(r"[=,\(]\s*0\s*[,\)]", mutated):
            mutated = re.sub(r"([=,\(]\s*)0(\s*[,\)])", r"\g<1>1\2", mutated, 1)
            explanation = "Changed 0 to 1"

        # Replace None with 0 or empty value
        elif "None" in mutated:
            mutated = mutated.replace("None", "0", 1)
            explanation = "Changed None to 0"

        else:
            return None

        if mutated == src:
            return None

        return self._create_rewrite(mutated, explanation)


class GeneralizeType(TestMutation):
    """
    Mutation: Generalize type constraints.

    Example:
        Original: assert isinstance(result, list)
        Mutated:  assert isinstance(result, (list, tuple))

    Targets: isinstance checks
    """

    @property
    def name(self) -> str:
        return "generalize_type"

    def can_apply(self, test: TestCandidate) -> bool:
        """Check for isinstance checks."""
        src = test.test_function.src_code
        return "isinstance" in src

    def mutate(self, test: TestCandidate) -> Optional[BugRewrite]:
        """Generalize isinstance type checks."""
        src = test.test_function.src_code

        # Pattern: isinstance(obj, type)
        # Replace with isinstance(obj, (type, related_type))

        # Common type generalizations
        generalizations = {
            "list": "(list, tuple)",
            "dict": "(dict, OrderedDict)",
            "str": "(str, bytes)",
            "int": "(int, float)",
            "tuple": "(tuple, list)",
        }

        mutated = src
        explanation = None

        for original, generalized in generalizations.items():
            pattern = rf"isinstance\s*\([^,]+,\s*{original}\s*\)"
            if re.search(pattern, mutated):
                mutated = re.sub(
                    rf"({original})(\s*\))",
                    rf"{generalized}\2",
                    mutated,
                    count=1,
                )
                explanation = f"Generalized isinstance({original}) to {generalized}"
                break

        if mutated == src or not explanation:
            return None

        return self._create_rewrite(mutated, explanation)


class ExpandAssertionScope(TestMutation):
    """
    Mutation: Expand assertion scope to check more conditions.

    Example:
        Original: assert len(result) > 0
        Mutated:  assert len(result) > 0 and len(result) < 1000

    Targets: Simple assertions
    """

    @property
    def name(self) -> str:
        return "expand_scope"

    def can_apply(self, test: TestCandidate) -> bool:
        """Check for simple assertions."""
        src = test.test_function.src_code
        return "assert" in src and " and " not in src and " or " not in src

    def mutate(self, test: TestCandidate) -> Optional[BugRewrite]:
        """Add additional conditions to assertions."""
        src = test.test_function.src_code

        # Find simple assert statements
        pattern = r"(assert\s+[^#\n]+)(\n|$)"

        def expand_assertion(match):
            original = match.group(1).rstrip()
            # Add an always-true condition to make it pass
            expanded = f"{original} and True  # Expanded assertion"
            return expanded + match.group(2)

        mutated = re.sub(pattern, expand_assertion, src, count=1)

        if mutated == src:
            return None

        return self._create_rewrite(
            mutated,
            "Expanded assertion with additional condition",
        )


# Registry of all mutations
MUTATION_REGISTRY = [
    BroadenInputRange(),
    RelaxAssertion(),
    AddParameterCombination(),
    ModifyEdgeCase(),
    GeneralizeType(),
    ExpandAssertionScope(),
]


# Mutation groups for easier selection
MUTATION_GROUPS = {
    "basic": [BroadenInputRange(), RelaxAssertion(), ModifyEdgeCase()],
    "advanced": [AddParameterCombination(), GeneralizeType(), ExpandAssertionScope()],
    "all": MUTATION_REGISTRY,
}


def get_mutations_by_name(names: list[str]) -> list[TestMutation]:
    """Get mutation operators by name."""
    return [m for m in MUTATION_REGISTRY if m.name in names]


def get_applicable_mutations(
    test: TestCandidate, mutation_names: Optional[list[str]] = None
) -> list[TestMutation]:
    """
    Get all mutations applicable to a test.

    Args:
        test: TestCandidate to check
        mutation_names: Optional list of mutation names to filter by

    Returns:
        List of applicable mutation operators
    """
    if mutation_names:
        mutations = get_mutations_by_name(mutation_names)
    else:
        mutations = MUTATION_REGISTRY

    return [m for m in mutations if m.can_apply(test)]
