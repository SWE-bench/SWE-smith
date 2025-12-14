# Test-Driven Bug Generation - Quick Start

## Installation

The test-driven module is part of SWE-smith and requires no additional dependencies.

## Basic Usage

### 1. Generate bugs from a repository

```bash
# Basic usage (generates ~10-20 bugs)
python -m swesmith.bug_gen.testdriven.generate arrow__1d70d009 \
  --model openai/gpt-4o \
  --n_bugs 2 \
  --max_bugs 20

# With specific mutation types
python -m swesmith.bug_gen.testdriven.generate arrow__1d70d009 \
  --model openai/gpt-4o \
  --mutation_types broaden_input relax_assertion

# With parallel processing
python -m swesmith.bug_gen.testdriven.generate arrow__1d70d009 \
  --model openai/gpt-4o \
  --n_workers 4
```

### 2. Collect and validate bugs

```bash
# Collect patches
python -m swesmith.bug_gen.collect_patches logs/bug_gen/arrow__1d70d009

# Validate bugs (check they break tests)
python -m swesmith.harness.valid \
  logs/bug_gen/arrow__1d70d009_all_patches.json \
  --workers 4

# Gather validated bugs
python -m swesmith.harness.gather logs/run_validation/<run_id>
```

## Command-Line Options

```
python -m swesmith.bug_gen.testdriven.generate <repo> [OPTIONS]

Required:
  repo                    Repository name (e.g., arrow__1d70d009)

Options:
  --model TEXT            LiteLLM model (default: openai/gpt-4o)
  --n_bugs INT            Bugs per test (default: 2)
  --max_bugs INT          Total bug limit (default: -1, unlimited)
  --mutation_types LIST   Specific mutations: broaden_input, relax_assertion,
                         modify_edge_case, generalize_type, etc.
  --coverage_threshold    Minimum coverage (default: 0.3)
  --max_tests_per_file   Tests per file limit (default: -1)
  --n_workers INT        Parallel workers (default: 1)
```

## Available Mutation Types

| Mutation | Description | Example |
|----------|-------------|---------|
| `broaden_input` | Increase numeric values | `value=5` → `value=500` |
| `relax_assertion` | Weaken assertions | `== 10` → `>= 10` |
| `modify_edge_case` | Change edge values | `[]` → `[None]` |
| `generalize_type` | Broaden types | `isinstance(x, list)` → `isinstance(x, (list, tuple))` |
| `add_parameter` | Add parameters | `func(a=1)` → `func(a=1, b=0)` |
| `expand_scope` | Add conditions | `assert x` → `assert x and True` |

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
        └── test_function__broaden_input.py
```

## Examples

### Example 1: Quick Test (5 bugs)

```bash
python -m swesmith.bug_gen.testdriven.generate arrow__1d70d009 \
  --max_bugs 5 \
  --coverage_threshold 0.5
```

### Example 2: Focus on Specific Mutations

```bash
python -m swesmith.bug_gen.testdriven.generate arrow__1d70d009 \
  --mutation_types relax_assertion modify_edge_case \
  --n_bugs 3
```

### Example 3: Production Run

```bash
# Generate 100 bugs with parallel processing
python -m swesmith.bug_gen.testdriven.generate arrow__1d70d009 \
  --model openai/gpt-4o \
  --max_bugs 100 \
  --n_workers 4 \
  --coverage_threshold 0.4

# Collect and validate
python -m swesmith.bug_gen.collect_patches logs/bug_gen/arrow__1d70d009
python -m swesmith.harness.valid logs/bug_gen/arrow__1d70d009_all_patches.json --workers 4
```

### Example 4: Use Cheaper Model

```bash
# Use GPT-4o-mini for lower cost
python -m swesmith.bug_gen.testdriven.generate arrow__1d70d009 \
  --model openai/gpt-4o-mini \
  --max_bugs 50
```

## Understanding the Output

### Bug Metadata

Each bug includes metadata like:

```json
{
  "rewrite": "def updated_function()...",
  "explanation": "Reconciled code for mutated test (broaden_input)",
  "strategy": "testdriven",
  "cost": 0.05,
  "test_file": "tests/test_dates.py",
  "test_name": "test_parse_date",
  "mutation_type": "broaden_input",
  "original_test": "def test_parse_date()...",
  "mutated_test": "def test_parse_date()...",
  "coverage_score": 0.75,
  "assertion_count": 3
}
```

### Success Metrics

Good run:
- **Success rate**: 50-70%
- **Cost per bug**: $0.01-0.05
- **Validation rate**: 40-60% (after running validation harness)

## Troubleshooting

### Issue: No tests discovered

```
Solution: Lower coverage_threshold
python -m swesmith.bug_gen.testdriven.generate <repo> --coverage_threshold 0.1
```

### Issue: High failure rate

```
Solutions:
1. Use better model: --model openai/gpt-4o (instead of gpt-4o-mini)
2. Focus on simpler mutations: --mutation_types relax_assertion modify_edge_case
3. Increase coverage threshold: --coverage_threshold 0.5
```

### Issue: Too expensive

```
Solutions:
1. Use cheaper model: --model openai/gpt-4o-mini
2. Limit bugs: --max_bugs 20
3. Reduce n_bugs: --n_bugs 1
```

## Next Steps

After generating bugs:

1. **Validate**: Run validation harness to check which bugs break tests
2. **Analyze**: Examine metadata to understand mutation patterns
3. **Train**: Use validated bugs to train SWE-agents
4. **Iterate**: Adjust mutation types and thresholds based on results

## Tips for Best Results

1. **Start small**: Test with `--max_bugs 10` first
2. **Check coverage**: Higher coverage tests → better bugs
3. **Review mutations**: Use `--mutation_types` to focus on what works
4. **Parallelize**: Use `--n_workers 4+` for speed
5. **Monitor cost**: Check summary for cost per bug

## Support

- Documentation: See `IMPLEMENTATION_PLAN.md` and `DESIGN_SUMMARY.md`
- Issues: Check validation logs in `logs/run_validation/`
- Examples: See test cases in `tests/bug_gen/testdriven/`
