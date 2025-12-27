# AGENTS.md - Runbook for Copilot Background Jobs

This document provides a quick reference for Copilot agents working in this repository.

## Quick Start Runbook

### 1. Install Dependencies
```bash
pip install jinja2
```

### 2. Run Tests / Smoke Validation
```bash
python scripts/smoke_validate.py
```

### 3. Build (Generate CVs)
```bash
python generate_cv.py
```

### 4. Smoke Checks (All CVs)
```bash
python scripts/smoke_validate.py --all
```

## Locked Files (DO NOT TOUCH)

**The following files are READ-ONLY and must never be modified:**

| File | SHA-256 Hash |
|------|--------------|
| `data/cvs/ramin.json` | `1ee82702bd82b8a46c8fd907f9c691ab124671350a8769f5d98adbfc5925e7b1` |
| `data/cvs/mahsa.json` | `e83738f284a565811a8eca795a91f094faa81873ede61221d57e4db0d131e85d` |

**Verify file integrity:**
```bash
sha256sum data/cvs/ramin.json data/cvs/mahsa.json
```

## Single Command Validation (All CVs)

To validate that all CVs render correctly without errors:

```bash
python scripts/smoke_validate.py --all
```

This command:
- Loads all JSON files from `data/cvs/`
- Validates JSON structure
- Checks for required fields
- Ensures no `undefined` or `null` strings in output
- Reports pass/fail status for each CV

## Common Tasks

### Adding a New CV
1. Create `data/cvs/newperson.json` following existing structure
2. Optionally add `data/pics/newperson.jpg`
3. Run `python generate_cv.py`
4. Check output in `output/newperson.pdf`

### Debugging Template Issues
1. Run `python generate_cv.py` and watch for Jinja2 errors
2. Add `| debug` filter to suspicious template variables
3. Check that all referenced keys exist in the JSON

### Modifying Templates
1. Edit templates in `templates/` directory
2. Run `python generate_cv.py` to regenerate
3. Verify output with `python scripts/smoke_validate.py`

## File Reference

| Path | Purpose |
|------|---------|
| `generate_cv.py` | Main CV generation script |
| `templates/layout.tex` | Master LaTeX layout |
| `templates/*.tex` | Section templates |
| `data/cvs/*.json` | CV data (some are LOCKED) |
| `scripts/smoke_validate.py` | Smoke validation script |
| `output/*.pdf` | Generated PDF CVs |

## CI Workflow

The CI pipeline runs:
1. Install dependencies
2. Smoke validation (all CVs)
3. Build (generate CVs without LaTeX compilation in CI)

## Environment Requirements

- Python 3.9+
- jinja2 package
- xelatex (for PDF generation - not required for smoke tests)
