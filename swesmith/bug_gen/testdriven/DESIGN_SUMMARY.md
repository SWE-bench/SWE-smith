# Test-Driven Bug Injection - Design Summary

## Core Concept

**Generate bugs by mutating tests, then using an LM to reconcile code** - creating "spec-overfitting bugs" where implementation satisfies a modified test but breaks others.

## Key Innovation

Unlike other bug generation methods that modify code directly, this approach:
1. **Starts with tests** - the specification
2. **Mutates the spec** - broadens requirements
3. **Asks LM to satisfy new spec** - code reconciliation
4. **Creates regressions** - satisfies one test, breaks others

This mirrors real-world scenarios where:
- Requirements change and code overfits to new requirement
- Edge cases are handled incorrectly
- One fix breaks existing functionality

## Comparison with Existing Methods

| Method | Strategy | Strengths | Limitations |
|--------|----------|-----------|-------------|
| **Procedural** | AST mutations on code | Fast, deterministic, no API costs | Limited to syntax patterns |
| **LM Modify** | LM rewrites functions to introduce bugs | Creative bugs, diverse | Expensive, may not break tests reliably |
| **LM Rewrite** | LM rewrites from scratch | Very diverse | Very expensive, unpredictable |
| **Mirror** | Revert real PRs | Real-world bugs | Requires PR data, limited to historical bugs |
| **Combine** | Merge multiple bugs | Complex multi-file bugs | Requires validated bugs first |
| **TestDriven** ✨ | Mutate tests → LM reconciles code | **Systematic spec exploration, guaranteed test interaction** | Requires good test coverage |

## Why It's Better for Training SWE-Agents

### 1. **Multi-Test Reasoning**
Agents must understand test suite globally, not just fix one failing test.

**Example:**
```python
# Original test
def test_parse_date():
    assert parse("2024-01-01") == date(2024, 1, 1)

# Mutated test (broaden input)
def test_parse_date():
    assert parse("2024-13-45") == date(2024, 1, 1)  # Invalid date

# LM-generated "fix"
def parse(date_str):
    # Now accepts invalid dates, but might break:
    # - test_parse_rejects_invalid()
    # - test_parse_validates_month()
    # - test_parse_raises_on_bad_input()
```

### 2. **Spec-Overfitting Patterns**
Trains agents to recognize when code satisfies one requirement too literally.

### 3. **Systematic Exploration**
Mutation operators systematically explore:
- Boundary conditions
- Type constraints
- Assertion semantics
- Parameter spaces

### 4. **Controllable Difficulty**
Can tune mutation strength:
- **Easy**: Relax single assertion
- **Medium**: Broaden input range
- **Hard**: Multiple mutations + generalize types

## Workflow Comparison

### Procedural/LM Modify
```
Code Entity → Mutate Code → Get Patch → Validate
```

### Test-Driven
```
Test Entity → Mutate Test → LM Reconciles Code → Get Patch → Validate
          ↓
    Also saves mutated test for analysis
```

## Research Questions This Enables

1. **Can agents detect spec-overfitting?**
   - When code passes modified test but breaks suite

2. **How do agents reason about test dependencies?**
   - Understanding which tests interact

3. **What's the failure mode distribution?**
   - Assertion violations vs. exceptions vs. hangs

4. **How does mutation type affect difficulty?**
   - Relaxed assertions vs. broadened inputs

## Implementation Highlights

### Clean Separation of Concerns

```
discover.py  → Finds high-coverage tests
mutators.py  → Pure test mutations (no LM)
reconcile.py → LM-based code updates
generate.py  → Orchestrates pipeline
```

### Follows Existing Patterns

**From `procedural/`:**
- Entity-based processing
- Bug directory structure
- Metadata format

**From `llm/`:**
- LiteLLM integration
- Config-based prompts
- Parallel workers

**From `mirror/`:**
- Prompt structure
- Multi-step validation

### Language Support Strategy

**Phase 1: Python**
- Rich test ecosystem (pytest)
- AST manipulation well-supported
- Can estimate coverage easily

**Phase 2: Go**
- `go test -v` output parsing
- Test function detection
- Similar patterns to Python

**Phase 3: Rust**
- `cargo test` integration
- More complex but feasible

## Key Design Decisions

### 1. Heuristic Coverage Estimation
Instead of running coverage tools (slow), use heuristics:
- Function calls in test → coverage
- Imports → dependencies
- Assertions → test strength

**Why?** Fast, good enough for ranking tests.

### 2. Save Mutated Tests
Store both mutated test AND code patch.

**Why?** Enables:
- Debugging
- Analysis of mutation effectiveness
- Potential future use of mutated tests

### 3. Single-Entity Focus
Each mutation targets one primary code entity.

**Why?**
- Simpler LM task
- Clearer attribution
- Easier to validate

### 4. Context-Aware Prompting
Include related tests in LM prompt.

**Why?** Helps LM understand:
- Expected behavior
- Test conventions
- Edge cases to preserve

## Expected Bug Patterns

### 1. **Boundary Relaxation**
```python
# Before: Strict validation
def process(x):
    if x < 0 or x > 100:
        raise ValueError()
    return x * 2

# After: Accepts broader range (breaks validation tests)
def process(x):
    return x * 2
```

### 2. **Type Generalization**
```python
# Before: Specific type
def format_list(items: list) -> str:
    return ", ".join(items)

# After: Accepts tuple too (breaks type-checking tests)
def format_list(items) -> str:
    return ", ".join(items)
```

### 3. **Assertion Weakening**
```python
# Test mutation: assert x == 10 → assert x >= 10
# Code "fix": Returns 15 instead of 10
# Breaks: Other tests expecting exactly 10
```

### 4. **Edge Case Overfitting**
```python
# Mutated test adds: test_process([None])
# Code adds: special case for None
# Breaks: Tests expecting ValueError on None
```

## Metrics for Success

### Generation Metrics
- Tests per repo discovered
- Applicable mutations per test
- LM success rate
- Cost per bug

### Validation Metrics
- % bugs that break 1+ tests
- % bugs that pass mutated test
- Average # tests broken per bug
- Distribution of FAIL_TO_PASS tests

### Agent Training Metrics
- Solve rate on testdriven bugs vs. others
- Time to solution
- Edit distance from gold patch
- Test pass rate during solving

## Future Extensions

### Advanced Mutations
- **Compositional**: Combine multiple mutations
- **Adversarial**: Specifically target common agent failures
- **Semantic**: Change behavior while preserving syntax

### Coverage Integration
- Actual coverage tools (pytest-cov)
- Mutation testing (mutmut)
- Prioritize high-impact tests

### Multi-File Bugs
- Mutate multiple related tests
- Reconcile across files
- Create complex regressions

### Difficulty Rating
- Automatic classification
- Predict agent solve rate
- Curriculum learning for training

## Expected Challenges

1. **Test Discovery Quality**
   - Heuristic coverage may miss important tests
   - *Mitigation*: Start conservative, iterate

2. **LM Reconciliation Failure**
   - LM may not generate valid code
   - *Mitigation*: Multiple samples, temperature tuning

3. **Mutation Applicability**
   - Not all tests suitable for all mutations
   - *Mitigation*: Strong `can_apply()` checks

4. **Cost**
   - LM calls for each test-mutation pair
   - *Mitigation*: Filter aggressively, use cheaper models

## Success Criteria

**Minimum Viable Product:**
- ✅ Generate 100+ bugs from arrow repo
- ✅ 50%+ validation rate (break tests)
- ✅ Cost < $10 for 100 bugs

**Production Ready:**
- ✅ Works across 5+ Python repos
- ✅ 70%+ validation rate
- ✅ Diverse mutation types
- ✅ Clear documentation

**Research Impact:**
- ✅ Publishable dataset
- ✅ Novel bug patterns
- ✅ Training improvements demonstrated

## Conclusion

Test-driven bug injection provides a **systematic, controllable way to generate spec-overfitting bugs** that require multi-test reasoning - a key capability for SWE-agents.

By starting from tests (specifications) rather than code, we can:
- Explore requirement spaces methodically
- Create realistic regression patterns
- Train agents to think globally about codebases
- Generate bugs that are interesting, not just syntactically different

This complements existing methods and enables new research directions in agent training and evaluation.
