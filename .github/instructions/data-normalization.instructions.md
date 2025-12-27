---
applyTo: "generate_cv.py,templates/**/*.tex,scripts/**/*.py"
---

# Data Normalization Instructions

## Overview

This file provides instructions for code that loads and normalizes CV JSON data.

## Locked Files Policy

**NEVER MODIFY** the following JSON files:
- `data/cvs/ramin.json`
- `data/cvs/mahsa.json`

These are read-only inputs. Normalization happens at runtime, not by editing source files.

## Data Loading Best Practices

1. **Always use UTF-8 encoding**: `open(path, encoding="utf-8")`
2. **Handle missing keys gracefully**: Use `.get(key, default)` instead of direct access
3. **Validate data types**: Check arrays are arrays, objects are objects
4. **Preserve original structure**: Don't mutate loaded data; create copies if needed

## Template Variable Safety

When providing data to templates:
- Use `| default('')` filter for optional string fields
- Use `| default([])` filter for optional array fields
- Check array length before iteration: `<BLOCK> if items|length > 0 </BLOCK>`

## Common Pitfalls

1. **null vs undefined**: JSON `null` becomes Python `None` - handle explicitly
2. **Empty arrays**: Check length before assuming content exists
3. **Missing nested keys**: Use safe navigation: `data.get('basics', [{}])[0].get('fname', '')`
4. **Type coercion**: Don't assume types - validate or convert explicitly

## Validation Requirements

Before passing data to templates, validate:
- Required fields exist (basics, profiles, education at minimum)
- Arrays contain expected object structure
- Dates are parseable or "present"
- URLs are valid format (if present)
