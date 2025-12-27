---
applyTo: "tests/**/*,scripts/smoke_*.py"
---

# Testing Instructions

## Overview

This file provides instructions for test files and smoke validation scripts.

## Testing Philosophy

1. **Non-destructive**: Tests must NEVER modify locked JSON files
2. **Deterministic**: Same inputs should produce same outputs
3. **Fast**: Smoke tests should complete in seconds
4. **Comprehensive**: Cover all CV files and sections

## Locked Files Policy (Critical)

**NEVER MODIFY** these files in tests:
- `data/cvs/ramin.json`
- `data/cvs/mahsa.json`

For test fixtures:
- Read directly from locked files at runtime, OR
- Copy to `tests/fixtures/` as byte-identical copies (document this clearly)

## Smoke Validation Requirements

The smoke validator must fail CI if:
1. Any core section becomes empty unintentionally
2. Any visible field becomes literal string `undefined` or `null`
3. Normalization outputs wrong types (arrays become objects, etc.)
4. JSON files cannot be parsed
5. Required keys are missing from JSON

## Test Categories

### Unit Tests
- Test individual filters (latex_escape, debug, etc.)
- Test data normalization functions
- Test template rendering in isolation

### Integration Tests
- Test full pipeline from JSON to LaTeX output
- Verify all sections render for each CV

### Smoke Tests
- Quick validation that all CVs process without error
- Check for presence of expected content
- Validate no "undefined" or "null" strings appear

## Assertions to Include

```python
# Check no undefined in output
assert "undefined" not in rendered_output.lower()
assert "null" not in rendered_output  # careful: might be valid LaTeX

# Check required sections exist
assert "\\cvsection{Education}" in rendered_output

# Check data integrity
assert len(data.get('basics', [])) > 0
assert isinstance(data.get('education'), list)
```

## Running Tests

```bash
# Run smoke validation
python scripts/smoke_validate.py

# Run with verbose output
python scripts/smoke_validate.py -v
```

## Test Stability

- Don't rely on exact output matching (whitespace may vary)
- Use regex or partial matching for content checks
- Tests should pass regardless of template formatting changes
