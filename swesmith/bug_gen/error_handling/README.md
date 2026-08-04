# Error Handling Corruption Module

A bug generation methodology for SWE-smith that creates synthetic bugs by removing exception handling mechanisms from code.

## 1. What Kind of Bug is Being Created

This module generates bugs by **removing error handling constructs**, creating three types of defects:

### TryExceptRemover
Removes `try/except` blocks, keeping only the try body. This exposes code to **unhandled exceptions**.

| Before | After |
|--------|-------|
| `try:`<br>`    x = risky_call()`<br>`except Exception:`<br>`    x = None` | `x = risky_call()` |

### AssertRemover
Removes `assert` statements. This eliminates **input validation and precondition checks**.

| Before | After |
|--------|-------|
| `assert x > 0`<br>`return x * 2` | `return x * 2` |

### RaiseRemover
Replaces `raise` statements with `pass`. This causes **silent failures** instead of explicit errors.

| Before | After |
|--------|-------|
| `if x < 0:`<br>`    raise ValueError("negative")` | `if x < 0:`<br>`    pass` |

## 2. Constraints

| Constraint | Details |
|------------|---------|
| **Language** | Python only (`.py` files) |
| **Parser** | Uses `libcst` for AST transformations |
| **Target** | Functions containing error handling constructs |
| **Conditions** | Each modifier requires specific `CodeProperty` flags:<br>- `HAS_TRY_EXCEPT` for TryExceptRemover<br>- `HAS_ASSERT` for AssertRemover<br>- `HAS_RAISE` for RaiseRemover |

## 3. Example Usages

### Basic Usage
```bash
# Generate bugs for a repository
python -m swesmith.bug_gen.error_handling.generate "instagram__monkeytype.70c3acf6"
```

### With Options
```bash
# Generate max 10 bugs per modifier with a specific seed
python -m swesmith.bug_gen.error_handling.generate "instagram__monkeytype.70c3acf6" \
    --seed 42 \
    --max_bugs 10

# Interleave modifiers randomly
python -m swesmith.bug_gen.error_handling.generate "instagram__monkeytype.70c3acf6" \
    --interleave \
    --max_candidates 50

# Set a timeout
python -m swesmith.bug_gen.error_handling.generate "instagram__monkeytype.70c3acf6" \
    --timeout_seconds 300
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `repo` | required | Repository name |
| `--seed` | 24 | Random seed for reproducibility |
| `--max_bugs` | -1 | Max bugs per modifier (-1 = unlimited) |
| `--interleave` | false | Randomize modifier order |
| `--max_entities` | -1 | Limit entities to process |
| `--max_candidates` | -1 | Limit (candidate, modifier) pairs |
| `--timeout_seconds` | None | Generation timeout in seconds |

### Output

Generated bugs are saved to `logs/bug_gen/<repo>/`:
```
logs/bug_gen/instagram__monkeytype.70c3acf6/
├── metadata__error_handling_try_except__abc123.json
├── bug__error_handling_try_except__abc123.diff
├── metadata__error_handling_assert__def456.json
├── bug__error_handling_assert__def456.diff
└── ...
```

### Running Tests
```bash
# Run error handling tests only
python -m pytest tests/bug_gen/error_handling/ -v

# Run full test suite
python -m pytest -q
```

## Author

Thomas Pumir - January 2025
