# Test-Driven Bug Injection

**Generate spec-overfitting bugs by mutating tests and reconciling code with LLMs.**

## Overview

This module implements a novel bug generation strategy:
1. **Discover** high-coverage tests in the repository
2. **Mutate** tests to broaden requirements or relax constraints
3. **Reconcile** implementation code to satisfy mutated test using LLM
4. **Validate** that new code passes mutated test but breaks other tests

This creates **spec-overfitting bugs** - realistic regressions where code satisfies one (changed) specification while violating others.

## Why This Matters

Unlike traditional bug generation that modifies code directly, test-driven injection:
- ✅ **Requires multi-test reasoning** - agents must think about test suite interactions
- ✅ **Explores specification spaces** - systematically probes boundary conditions
- ✅ **Creates realistic regressions** - mirrors how requirements changes cause bugs
- ✅ **Controllable difficulty** - tune mutation strength and type

## Quick Start

```bash
# Generate bugs from arrow repo
python -m swesmith.bug_gen.testdriven.generate arrow__1d70d009 \
  --model openai/gpt-4o \
  --n_bugs 2 \
  --mutation_types broaden_input relax_assertion

# Validate bugs
python -m swesmith.bug_gen.collect_patches logs/bug_gen/arrow__1d70d009
python -m swesmith.harness.valid logs/bug_gen/arrow__1d70d009_all_patches.json
```

## Module Structure

```
testdriven/
├── README.md                    ← You are here
├── IMPLEMENTATION_PLAN.md       ← Detailed technical plan
├── DESIGN_SUMMARY.md            ← Design rationale and research value
├── __init__.py                  ← Module exports
├── generate.py                  ← Main entry point
├── discover.py                  ← Test discovery and ranking
├── mutators.py                  ← Test mutation operators
├── reconcile.py                 ← LLM code reconciliation
├── prompts.py                   ← LLM prompt templates
└── utils.py                     ← Helper functions
```

## Core Concepts

### Test Mutation Operators

**1. Broaden Input Range**
```python
# Original
def test_parse_date():
    assert parse("2024-01-01") == date(2024, 1, 1)

# Mutated
def test_parse_date():
    assert parse("2024-13-45") == date(2024, 1, 1)  # Invalid month/day
```

**2. Relax Assertion**
```python
# Original
assert result == 10

# Mutated
assert result >= 10  # Weakened constraint
```

**3. Add Parameter Combination**
```python
# Original
func(a=1, b=2)

# Mutated
func(a=1, b=2, c=3)  # New optional param
```

**4. Modify Edge Case**
```python
# Original
test_empty_list([])

# Mutated
test_empty_list([None])  # Near-edge case
```

**5. Generalize Type**
```python
# Original
assert isinstance(result, list)

# Mutated
assert isinstance(result, (list, tuple))
```

### Code Reconciliation

The LLM receives:
- Original test
- Mutated test
- Current implementation
- Related tests (for context)

And generates updated code that:
- ✅ Passes the mutated test
- ❌ May break other tests (desired!)

### Example Workflow

```
1. Discover Tests
   └─ test_format_date() covers format_date()

2. Mutate Test
   └─ Relax assertion: == → >=

3. LLM Reconciles Code
   └─ format_date() updated to pass mutated test

4. Validation
   ├─ ✅ Mutated test passes
   └─ ❌ test_format_consistency() fails (regression!)

5. Bug Created! 🎉
   └─ Spec-overfitting: satisfies one test, breaks another
```

## Command-Line Interface

```bash
python -m swesmith.bug_gen.testdriven.generate <repo> [options]

Required:
  repo                  Repository name (e.g., arrow__1d70d009)

Options:
  --model TEXT          LiteLLM model (default: openai/gpt-4o)
  --n_bugs INT          Bugs per test (default: 2)
  --max_bugs INT        Total bug limit (default: -1, unlimited)
  --mutation_types LIST Mutation types to apply
  --coverage_threshold  Minimum test coverage (default: 0.3)
  --n_workers INT       Parallel workers (default: 1)
  --config_file PATH    YAML config file
```

## Configuration

`configs/bug_gen/testdriven.yml`:
```yaml
name: testdriven
description: "Test-driven bug injection"

parameters:
  mutation_types:
    - broaden_input
    - relax_assertion
    - modify_edge_case
    - generalize_type

  coverage_threshold: 0.3
  max_tests_per_file: 5
  include_related_tests: true
  max_context_tests: 3
```

## Output Structure

```
logs/bug_gen/<repo>/testdriven/
├── tests__test_module.py/
│   └── test_function_xyz/
│       ├── bug__testdriven_broaden_input__abc123.diff
│       ├── metadata__testdriven_broaden_input__abc123.json
│       └── mutated_test.py
└── mutated_tests/
    └── tests__test_module.py/
        └── test_function.py
```

**Metadata Format:**
```json
{
  "rewrite": "def format_date(...)...",
  "explanation": "Reconciled for broadened input range",
  "strategy": "testdriven",
  "cost": 0.05,
  "test_file": "tests/test_dates.py",
  "test_name": "test_format_date",
  "mutation_type": "broaden_input",
  "mutated_test": "def test_format_date()...",
  "coverage_score": 0.75
}
```

## Implementation Checklist

- [ ] **Phase 1: Core Infrastructure**
  - [ ] `discover.py`: Test discovery for Python
  - [ ] `mutators.py`: Basic mutations (broaden, relax, edge)
  - [ ] `prompts.py`: Reconciliation prompts
  - [ ] `reconcile.py`: LLM integration

- [ ] **Phase 2: Pipeline**
  - [ ] `generate.py`: Main orchestration
  - [ ] `utils.py`: Helper functions
  - [ ] Config file support
  - [ ] Error handling

- [ ] **Phase 3: Testing**
  - [ ] Test on arrow repo
  - [ ] Validate bugs break tests
  - [ ] Measure cost and success rate
  - [ ] Iterate on prompts

- [ ] **Phase 4: Extensions**
  - [ ] Multi-language support (Go, Rust)
  - [ ] Advanced mutations
  - [ ] Coverage integration
  - [ ] Multi-file bugs

## Key Functions

### `discover.py`
```python
def discover_tests(repo: str, rp: RepoProfile,
                   coverage_threshold: float) -> list[TestCandidate]:
    """Find and rank tests suitable for mutation."""

class TestCandidate:
    """Test with coverage information."""
    file_path: str
    test_name: str
    test_function: CodeEntity
    covered_entities: list[CodeEntity]
    coverage_score: float
```

### `mutators.py`
```python
class TestMutation(ABC):
    """Base class for test mutations."""
    def can_apply(self, test: TestCandidate) -> bool: ...
    def mutate(self, test: TestCandidate) -> BugRewrite: ...

MUTATION_REGISTRY = [
    BroadenInputRange(),
    RelaxAssertion(),
    # ...
]
```

### `reconcile.py`
```python
def reconcile_code_with_test(
    test_candidate: TestCandidate,
    mutated_test: str,
    mutation_type: str,
    repo: str,
    model: str,
) -> BugRewrite:
    """Use LLM to update implementation for mutated test."""
```

## Research Applications

### Training SWE-Agents
- Multi-test reasoning
- Spec-overfitting detection
- Global test suite understanding

### Benchmarking
- Difficulty calibration
- Agent capability profiling
- Failure mode analysis

### Analysis
- Mutation effectiveness
- LLM reconciliation patterns
- Bug pattern distribution

## Success Metrics

**Generation:**
- Tests discovered per repo
- Mutation applicability rate
- LLM success rate
- Cost per bug

**Validation:**
- % bugs breaking 1+ tests
- % bugs passing mutated test
- Avg tests broken per bug

**Training:**
- Agent solve rate improvement
- Generalization to unseen mutations

## Comparison with Existing Methods

| Method | Test Interaction | Cost | Diversity | Realism |
|--------|------------------|------|-----------|---------|
| Procedural | Low | Free | Medium | Low |
| LM Modify | Low | Medium | High | Medium |
| Mirror | Medium | Low | High | **Very High** |
| **TestDriven** | **Very High** | **Medium** | **High** | **High** |

## Future Directions

1. **Compositional Mutations**: Combine multiple mutations
2. **Adversarial Generation**: Target specific agent weaknesses
3. **Coverage-Guided**: Use actual coverage tools
4. **Multi-File**: Coordinate mutations across files
5. **Difficulty Prediction**: ML model for bug difficulty

## Contributing

When implementing:
1. Follow existing SWE-smith patterns (see `IMPLEMENTATION_PLAN.md`)
2. Start with Python, extend to other languages
3. Test on multiple repos
4. Document prompts and mutations clearly
5. Add examples and tests

## References

- **Design rationale**: `DESIGN_SUMMARY.md`
- **Technical details**: `IMPLEMENTATION_PLAN.md`
- **SWE-smith docs**: https://swesmith.com/
- **Paper**: https://arxiv.org/abs/2504.21798

## Questions?

See `IMPLEMENTATION_PLAN.md` for detailed architecture and `DESIGN_SUMMARY.md` for research motivation.
