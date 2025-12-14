"""
Example/demo script for test-driven bug generation.

This script demonstrates the basic workflow without requiring a full repo.
"""

from swesmith.bug_gen.testdriven.discover import TestCandidate
from swesmith.bug_gen.testdriven.mutators import (
    BroadenInputRange,
    RelaxAssertion,
    ModifyEdgeCase,
    get_applicable_mutations,
)
from swesmith.constants import CodeEntity, BugRewrite


# Example test function as a mock CodeEntity
class MockCodeEntity(CodeEntity):
    def __init__(self, name, src_code):
        self._name = name
        self._src_code = src_code
        self._tags = set()

    @property
    def name(self):
        return self._name

    @property
    def signature(self):
        return f"def {self._name}():"

    @property
    def stub(self):
        return self.signature

    @property
    def src_code(self):
        return self._src_code


def demo_mutations():
    """Demonstrate test mutations without LLM."""
    print("=" * 70)
    print("TEST-DRIVEN BUG GENERATION - MUTATION DEMO")
    print("=" * 70)

    # Example 1: Broaden Input
    print("\n1. BROADEN INPUT RANGE")
    print("-" * 70)

    test_code_1 = """
def test_process_number():
    result = process(value=5)
    assert result == 10
"""

    mock_entity_1 = MockCodeEntity("test_process_number", test_code_1)
    test_1 = TestCandidate(
        file_path="tests/test_example.py",
        test_name="test_process_number",
        test_function=mock_entity_1,
        coverage_score=0.8,
        assertion_count=1,
    )

    mutator_1 = BroadenInputRange()
    if mutator_1.can_apply(test_1):
        mutated_1 = mutator_1.mutate(test_1)
        if mutated_1:
            print("Original test:")
            print(test_code_1)
            print("\nMutated test:")
            print(mutated_1.rewrite)
            print(f"\nExplanation: {mutated_1.explanation}")

    # Example 2: Relax Assertion
    print("\n2. RELAX ASSERTION")
    print("-" * 70)

    test_code_2 = """
def test_calculate_sum():
    result = calculate_sum([1, 2, 3])
    assert result == 6
"""

    mock_entity_2 = MockCodeEntity("test_calculate_sum", test_code_2)
    test_2 = TestCandidate(
        file_path="tests/test_math.py",
        test_name="test_calculate_sum",
        test_function=mock_entity_2,
        coverage_score=0.7,
        assertion_count=1,
    )

    mutator_2 = RelaxAssertion()
    if mutator_2.can_apply(test_2):
        mutated_2 = mutator_2.mutate(test_2)
        if mutated_2:
            print("Original test:")
            print(test_code_2)
            print("\nMutated test:")
            print(mutated_2.rewrite)
            print(f"\nExplanation: {mutated_2.explanation}")

    # Example 3: Modify Edge Case
    print("\n3. MODIFY EDGE CASE")
    print("-" * 70)

    test_code_3 = """
def test_handle_empty_list():
    result = process_list([])
    assert result == []
"""

    mock_entity_3 = MockCodeEntity("test_handle_empty_list", test_code_3)
    test_3 = TestCandidate(
        file_path="tests/test_lists.py",
        test_name="test_handle_empty_list",
        test_function=mock_entity_3,
        coverage_score=0.6,
        assertion_count=1,
    )

    mutator_3 = ModifyEdgeCase()
    if mutator_3.can_apply(test_3):
        mutated_3 = mutator_3.mutate(test_3)
        if mutated_3:
            print("Original test:")
            print(test_code_3)
            print("\nMutated test:")
            print(mutated_3.rewrite)
            print(f"\nExplanation: {mutated_3.explanation}")

    # Example 4: Get All Applicable Mutations
    print("\n4. APPLICABLE MUTATIONS")
    print("-" * 70)

    test_code_4 = """
def test_complex_function():
    result = complex_func(x=10, y=20)
    assert result == 30
    assert isinstance(result, int)
"""

    mock_entity_4 = MockCodeEntity("test_complex_function", test_code_4)
    test_4 = TestCandidate(
        file_path="tests/test_complex.py",
        test_name="test_complex_function",
        test_function=mock_entity_4,
        coverage_score=0.9,
        assertion_count=2,
    )

    applicable = get_applicable_mutations(test_4)
    print(f"Test has {len(applicable)} applicable mutations:")
    for mut in applicable:
        print(f"  - {mut.name}")

    print("\n" + "=" * 70)
    print("Demo complete! This shows mutations without LLM reconciliation.")
    print("Run the full pipeline with: python -m swesmith.bug_gen.testdriven.generate")
    print("=" * 70)


if __name__ == "__main__":
    demo_mutations()
