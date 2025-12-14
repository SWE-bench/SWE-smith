# Test-Driven Bug Injection - Implementation Plan

## Overview
Generate bugs by mutating tests and using an LM to reconcile code, creating "spec-overfitting bugs" where code satisfies a modified test but breaks previously passing tests.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│           TEST-DRIVEN BUG INJECTION WORKFLOW                 │
└──────────────────────────────────────────────────────────────┘

Input: Repository + Test Suite
         │
         ├─ Step 1: Test Discovery & Selection
         │  ┌────────────────────────────────────┐
         │  │ discover_tests()                   │
         │  │ - Find all test files/functions    │
         │  │ - Parse test AST                   │
         │  │ - Extract test coverage info       │
         │  │ - Filter high-coverage tests       │
         │  └────────────────────────────────────┘
         │           │
         │           v
         ├─ Step 2: Test Mutation
         │  ┌────────────────────────────────────┐
         │  │ mutate_test()                      │
         │  │ - Apply mutation operators         │
         │  │ - Broaden input ranges             │
         │  │ - Relax assertions                 │
         │  │ - Add parameter combinations       │
         │  │ - Modify edge cases                │
         │  └────────────────────────────────────┘
         │           │
         │           v
         ├─ Step 3: Code Reconciliation (LM)
         │  ┌────────────────────────────────────┐
         │  │ reconcile_code_with_test()         │
         │  │ - Prompt LM with:                  │
         │  │   • Original test                  │
         │  │   • Mutated test                   │
         │  │   • Current implementation         │
         │  │   • Other related tests            │
         │  │ - Generate code to satisfy mutated │
         │  │   test while preserving others     │
         │  └────────────────────────────────────┘
         │           │
         │           v
         ├─ Step 4: Validation
         │  ┌────────────────────────────────────┐
         │  │ validate_bug()                     │
         │  │ - Apply code patch                 │
         │  │ - Run full test suite              │
         │  │ - Check:                           │
         │  │   ✓ Mutated test passes            │
         │  │   ✓ Other tests fail (regression)  │
         │  │ - Extract FAIL_TO_PASS tests       │
         │  └────────────────────────────────────┘
         │           │
         │           v
         └─ Output: Bug Patch + Metadata
            ┌────────────────────────────────────┐
            │ bug__testdriven__<hash>.diff       │
            │ metadata__testdriven__<hash>.json  │
            │ {                                  │
            │   original_test: "...",            │
            │   mutated_test: "...",             │
            │   mutation_type: "...",            │
            │   affected_tests: [...],           │
            │   cost: 0.05                       │
            │ }                                  │
            └────────────────────────────────────┘
```

## Module Structure

```
swesmith/bug_gen/testdriven/
├── __init__.py                  # Module exports
├── generate.py                  # Main entry point (follows pattern from procedural/llm)
├── discover.py                  # Test discovery and parsing
├── mutators.py                  # Test mutation operators
├── reconcile.py                 # LM-based code reconciliation
├── prompts.py                   # LM prompts (follows pattern from mirror/prompts.py)
└── utils.py                     # Helper functions
```

## Core Functions

### 1. `generate.py` (Main Entry Point)

```python
def main(
    repo: str,
    model: str,
    n_bugs: int,
    max_bugs: int = -1,
    mutation_types: list[str] = None,
    coverage_threshold: float = 0.3,
    n_workers: int = 1,
) -> None:
    """
    Main entry point for test-driven bug generation.

    Args:
        repo: Repository name (e.g., arrow__1d70d009)
        model: LiteLLM model string (e.g., openai/gpt-4o)
        n_bugs: Number of bug variants per test
        max_bugs: Maximum total bugs to generate
        mutation_types: List of mutation types to apply
        coverage_threshold: Minimum coverage for test selection
        n_workers: Number of parallel workers
    """
    # 1. Clone repo and setup
    rp = registry.get(repo)
    rp.clone()

    # 2. Discover tests
    test_candidates = discover_tests(repo, rp, coverage_threshold)

    # 3. Process each test
    log_dir = LOG_DIR_BUG_GEN / repo / "testdriven"
    log_dir.mkdir(parents=True, exist_ok=True)

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

        # Collect results
        for future in tqdm(as_completed(futures), total=len(futures)):
            result = future.result()
            # Track stats

    # 4. Cleanup
    shutil.rmtree(repo)
```

### 2. `discover.py` (Test Discovery)

```python
@dataclass
class TestCandidate:
    """Represents a test that can be mutated."""
    file_path: str
    test_name: str
    test_function: CodeEntity
    covered_entities: list[CodeEntity]  # Functions/classes it tests
    coverage_score: float
    dependencies: list[str]  # Other tests in same file

def discover_tests(
    repo: str,
    rp: RepoProfile,
    coverage_threshold: float = 0.3,
) -> list[TestCandidate]:
    """
    Discover and rank tests suitable for mutation.

    Strategy:
    1. Find all test files using rp.test_paths
    2. Parse test functions using language adapters
    3. Estimate coverage (heuristic: imports, function calls)
    4. Filter tests with good coverage
    5. Rank by complexity and coverage

    Returns:
        List of TestCandidate objects sorted by suitability
    """
    test_files = rp.test_paths
    candidates = []

    for test_file in test_files:
        # Extract test entities
        entities = get_entities_from_file(test_file, Path(test_file).suffix)

        for entity in entities:
            if not is_test_function(entity):
                continue

            # Analyze coverage
            coverage_info = analyze_test_coverage(entity, repo)

            if coverage_info['score'] >= coverage_threshold:
                candidates.append(TestCandidate(
                    file_path=test_file,
                    test_name=entity.name,
                    test_function=entity,
                    covered_entities=coverage_info['entities'],
                    coverage_score=coverage_info['score'],
                    dependencies=get_related_tests(test_file, entity),
                ))

    # Sort by coverage and complexity
    return sorted(candidates, key=lambda x: x.coverage_score, reverse=True)

def is_test_function(entity: CodeEntity) -> bool:
    """Check if entity is a test function."""
    name = entity.name.lower()
    return name.startswith('test_') or 'test' in name

def analyze_test_coverage(entity: CodeEntity, repo: str) -> dict:
    """
    Heuristically estimate what code a test covers.

    Returns:
        {
            'score': float,  # 0-1 coverage estimate
            'entities': list[CodeEntity],  # Covered code entities
        }
    """
    # Heuristics:
    # - Parse imports in test file
    # - Find function calls in test
    # - Match to actual code entities
    # - Count assertions (more = better coverage)
    pass

def get_related_tests(test_file: str, entity: CodeEntity) -> list[str]:
    """Get other tests in same file/class that might be affected."""
    pass
```

### 3. `mutators.py` (Test Mutation Operators)

```python
class TestMutation:
    """Base class for test mutations."""

    @abstractmethod
    def can_apply(self, test: TestCandidate) -> bool:
        """Check if mutation can be applied to test."""
        pass

    @abstractmethod
    def mutate(self, test: TestCandidate) -> BugRewrite:
        """Apply mutation to test."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of mutation type."""
        pass

class BroadenInputRange(TestMutation):
    """
    Mutation: Expand input ranges in test.

    Example:
        Original: test_process(value=5)
        Mutated:  test_process(value=1000)
    """
    name = "broaden_input"

    def can_apply(self, test: TestCandidate) -> bool:
        # Check for numeric literals in test
        return test.test_function.has_arithmetic

    def mutate(self, test: TestCandidate) -> BugRewrite:
        # Parse test AST
        # Find numeric literals
        # Replace with larger/smaller values
        # Return mutated test code
        pass

class RelaxAssertion(TestMutation):
    """
    Mutation: Weaken assertion conditions.

    Example:
        Original: assert result == 10
        Mutated:  assert result >= 10
    """
    name = "relax_assertion"

    def can_apply(self, test: TestCandidate) -> bool:
        # Check for assertions with equality
        return "assert" in test.test_function.src_code

    def mutate(self, test: TestCandidate) -> BugRewrite:
        # Parse assertions
        # Change == to >= or <=
        # Change 'is' to 'isinstance'
        pass

class AddParameterCombination(TestMutation):
    """
    Mutation: Add new parameter combinations.

    Example:
        Original: func(a=1, b=2)
        Mutated:  func(a=1, b=2, c=3)  # if c is optional
    """
    name = "add_parameter"

    def mutate(self, test: TestCandidate) -> BugRewrite:
        # Identify function under test
        # Find optional parameters not used
        # Add them to test call
        pass

class ModifyEdgeCase(TestMutation):
    """
    Mutation: Change edge case values.

    Example:
        Original: test_empty_list([])
        Mutated:  test_empty_list([None])
    """
    name = "modify_edge_case"

    def mutate(self, test: TestCandidate) -> BugRewrite:
        # Identify edge case values ([], "", 0, None)
        # Replace with near-edge values ([None], " ", 1, 0)
        pass

class GeneralizeType(TestMutation):
    """
    Mutation: Generalize type constraints.

    Example:
        Original: assert isinstance(result, list)
        Mutated:  assert isinstance(result, (list, tuple))
    """
    name = "generalize_type"

    def mutate(self, test: TestCandidate) -> BugRewrite:
        # Find isinstance checks
        # Expand type unions
        pass

# Registry of all mutations
MUTATION_REGISTRY = [
    BroadenInputRange(),
    RelaxAssertion(),
    AddParameterCombination(),
    ModifyEdgeCase(),
    GeneralizeType(),
]
```

### 4. `reconcile.py` (LM Code Reconciliation)

```python
def reconcile_code_with_test(
    test_candidate: TestCandidate,
    mutated_test: str,
    mutation_type: str,
    repo: str,
    model: str,
) -> BugRewrite:
    """
    Use LM to update implementation to satisfy mutated test.

    Args:
        test_candidate: Original test information
        mutated_test: The mutated test code
        mutation_type: Type of mutation applied
        repo: Repository path
        model: LiteLLM model string

    Returns:
        BugRewrite with updated implementation
    """
    # 1. Get current implementation
    target_entities = test_candidate.covered_entities
    if not target_entities:
        return None

    # Focus on primary entity (most called in test)
    primary_entity = target_entities[0]

    # 2. Get context: related tests
    related_tests = get_related_test_code(test_candidate)

    # 3. Build prompt
    messages = [
        {"role": "system", "content": RECONCILIATION_SYSTEM_PROMPT},
        {"role": "user", "content": format_reconciliation_prompt(
            original_test=test_candidate.test_function.src_code,
            mutated_test=mutated_test,
            current_impl=primary_entity.src_code,
            related_tests=related_tests,
            mutation_type=mutation_type,
        )},
    ]

    # 4. Call LM
    response = completion(model=model, messages=messages, temperature=0)

    # 5. Extract code
    new_impl = extract_code_block(response.choices[0].message.content)

    return BugRewrite(
        rewrite=new_impl,
        explanation=f"Reconciled code for mutated test ({mutation_type})",
        strategy="testdriven",
        cost=completion_cost(completion_response=response),
        output=response.choices[0].message.content,
    )

def get_related_test_code(test: TestCandidate) -> str:
    """Get code of related tests for context."""
    # Read test file
    # Extract other test functions
    # Format for prompt
    pass
```

### 5. `prompts.py` (LM Prompts)

```python
RECONCILIATION_SYSTEM_PROMPT = """You are a code modification expert. Your task is to update implementation code to satisfy a modified test specification.

CRITICAL REQUIREMENTS:
1. The updated code MUST pass the modified test
2. Try to maintain compatibility with other tests, but it's OK if some break
3. Make MINIMAL changes - only what's needed to satisfy the new test
4. Preserve code style and structure
5. Do NOT modify the test itself - only the implementation

You will receive:
- The original test
- The modified test (with broader requirements)
- The current implementation
- Related tests for context

Your goal: Update the implementation to pass the modified test while trying to minimize breaking other tests."""

RECONCILIATION_TASK_PROMPT = """## Task

A test has been modified to have broader requirements. Update the implementation to satisfy the new test.

### Original Test
```python
{original_test}
```

### Modified Test ({mutation_type})
```python
{mutated_test}
```

### Current Implementation
```python
{current_impl}
```

### Related Tests (for context)
```python
{related_tests}
```

## Instructions

1. Analyze what changed between original and modified test
2. Identify minimal code changes needed to satisfy modified test
3. Update the implementation accordingly
4. Consider edge cases introduced by the modification

## Output

Provide ONLY the updated implementation code in a ```python code block. Do NOT include:
- The test code
- Explanations outside code comments
- Any other files

The code should be a complete replacement for the current implementation."""

def format_reconciliation_prompt(
    original_test: str,
    mutated_test: str,
    current_impl: str,
    related_tests: str,
    mutation_type: str,
) -> str:
    """Format the reconciliation task prompt."""
    return RECONCILIATION_TASK_PROMPT.format(
        original_test=original_test,
        mutated_test=mutated_test,
        current_impl=current_impl,
        related_tests=related_tests,
        mutation_type=mutation_type,
    )
```

### 6. Processing Pipeline

```python
def process_test(
    test: TestCandidate,
    repo: str,
    rp: RepoProfile,
    model: str,
    n_bugs: int,
    mutation_types: list[str],
    log_dir: Path,
) -> dict:
    """
    Process a single test: mutate and reconcile code.

    Returns:
        Statistics: {success: int, failed: int, cost: float}
    """
    stats = {'success': 0, 'failed': 0, 'cost': 0.0}

    # Get applicable mutations
    mutations = [m for m in MUTATION_REGISTRY
                 if m.can_apply(test) and m.name in mutation_types]

    for mutation in mutations[:n_bugs]:
        try:
            # 1. Mutate test
            mutated = mutation.mutate(test)

            # 2. Reconcile code with LM
            bug_rewrite = reconcile_code_with_test(
                test_candidate=test,
                mutated_test=mutated.rewrite,
                mutation_type=mutation.name,
                repo=repo,
                model=model,
            )

            if not bug_rewrite:
                stats['failed'] += 1
                continue

            stats['cost'] += bug_rewrite.cost

            # 3. Apply code change
            target_entity = test.covered_entities[0]
            apply_code_change(target_entity, bug_rewrite)

            # 4. Also save mutated test
            _save_mutated_test(test, mutated.rewrite, log_dir)

            # 5. Get patch
            patch = get_patch(repo, reset_changes=True)
            if not patch:
                stats['failed'] += 1
                continue

            # 6. Save artifacts
            _save_bug_artifacts(
                log_dir=log_dir,
                test=test,
                mutation_type=mutation.name,
                patch=patch,
                mutated_test=mutated.rewrite,
                bug_rewrite=bug_rewrite,
            )

            stats['success'] += 1

        except Exception as e:
            logging.error(f"Error processing {test.test_name}: {e}")
            stats['failed'] += 1

    return stats

def _save_bug_artifacts(
    log_dir: Path,
    test: TestCandidate,
    mutation_type: str,
    patch: str,
    mutated_test: str,
    bug_rewrite: BugRewrite,
) -> None:
    """Save bug patch and metadata."""
    # Create directory structure similar to procedural/llm
    bug_dir = log_dir / test.file_path.replace("/", "__") / test.test_name
    bug_dir.mkdir(parents=True, exist_ok=True)

    uuid_str = f"testdriven_{mutation_type}__{generate_hash(patch)}"

    # Save patch
    with open(bug_dir / f"{PREFIX_BUG}__{uuid_str}.diff", "w") as f:
        f.write(patch)

    # Save metadata
    metadata = {
        **bug_rewrite.to_dict(),
        "test_file": test.file_path,
        "test_name": test.test_name,
        "mutation_type": mutation_type,
        "mutated_test": mutated_test,
        "coverage_score": test.coverage_score,
    }
    with open(bug_dir / f"{PREFIX_METADATA}__{uuid_str}.json", "w") as f:
        json.dump(metadata, f, indent=2)

def _save_mutated_test(
    test: TestCandidate,
    mutated_test_code: str,
    log_dir: Path,
) -> None:
    """Save mutated test for reference."""
    test_dir = log_dir / "mutated_tests" / test.file_path.replace("/", "__")
    test_dir.mkdir(parents=True, exist_ok=True)

    with open(test_dir / f"{test.test_name}.py", "w") as f:
        f.write(mutated_test_code)
```

## Configuration File

Following the pattern from `configs/bug_gen/lm_modify.yml`:

```yaml
# configs/bug_gen/testdriven.yml
name: testdriven
description: "Test-driven bug injection via test mutation and code reconciliation"

parameters:
  # Mutation settings
  mutation_types:
    - broaden_input
    - relax_assertion
    - modify_edge_case
    - generalize_type

  # Test selection
  coverage_threshold: 0.3  # Minimum coverage score
  max_tests_per_file: 5

  # Reconciliation settings
  include_related_tests: true  # Provide context
  max_context_tests: 3
```

## Usage Examples

```bash
# Basic usage
python -m swesmith.bug_gen.testdriven.generate arrow__1d70d009 \
  --model openai/gpt-4o \
  --n_bugs 2 \
  --config_file configs/bug_gen/testdriven.yml

# With specific mutations
python -m swesmith.bug_gen.testdriven.generate arrow__1d70d009 \
  --model anthropic/claude-3-7-sonnet-20250219 \
  --n_bugs 3 \
  --mutation_types broaden_input relax_assertion \
  --coverage_threshold 0.5 \
  --n_workers 4

# Full pipeline
python -m swesmith.bug_gen.testdriven.generate arrow__1d70d009 \
  --model openai/gpt-4o \
  --n_bugs 2

python -m swesmith.bug_gen.collect_patches logs/bug_gen/arrow__1d70d009

python -m swesmith.harness.valid \
  logs/bug_gen/arrow__1d70d009_all_patches.json \
  --workers 4
```

## Output Structure

```
logs/bug_gen/arrow__1d70d009/testdriven/
├── tests__test_arrow.py/
│   ├── test_parse_datetime_abc123/
│   │   ├── bug__testdriven_broaden_input__xyz789.diff
│   │   ├── metadata__testdriven_broaden_input__xyz789.json
│   │   └── mutated_test.py
│   └── test_format_iso_def456/
│       ├── bug__testdriven_relax_assertion__abc123.diff
│       └── metadata__testdriven_relax_assertion__abc123.json
└── mutated_tests/
    └── tests__test_arrow.py/
        ├── test_parse_datetime.py
        └── test_format_iso.py
```

## Validation Strategy

The validation harness (`swesmith/harness/valid.py`) will automatically:
1. Apply the bug patch (modified implementation)
2. Apply the mutated test
3. Run test suite
4. Check that mutated test passes but other tests fail (regression)

## Research Value

This approach enables studying:
1. **Spec-overfitting**: Code satisfies one modified requirement while breaking others
2. **Multi-test reasoning**: Requires agents to think globally about test suites
3. **Boundary exploration**: Systematic mutation of edge cases and input ranges
4. **Assertion semantics**: How changing assertion strength affects code behavior

## Implementation Order

1. ✅ Create module structure
2. `discover.py` - Test discovery (Python-only first)
3. `mutators.py` - Implement 2-3 basic mutations
4. `prompts.py` - Reconciliation prompts
5. `reconcile.py` - LM integration
6. `generate.py` - Main pipeline
7. Testing with arrow repo
8. Extend to other languages (Go, Rust)
9. Add more sophisticated mutations

## Dependencies

- All existing SWE-smith dependencies
- No new external dependencies needed
- Reuses:
  - `swesmith.bug_gen.adapters` for code parsing
  - `swesmith.bug_gen.utils` for patching
  - `swesmith.profiles` for repo management
  - `litellm` for LM calls
