# Copilot Instructions for CV Generator

This repository generates PDF CVs from JSON data using Python, Jinja2 templates, and LaTeX (xelatex).

## Quick Start Commands

### Install Dependencies
```bash
pip install jinja2
```

### Run CV Generator
```bash
python generate_cv.py
```

### Verify LaTeX Installation
```bash
xelatex --version
```

## Locked Files Policy (READ-ONLY)

The following files are **locked** and must **NOT** be modified in any way:
- `data/cvs/ramin.json`
- `data/cvs/mahsa.json`

**No formatting changes, no sorting, no newline edits, no key renames, nothing.**

These files are treated as read-only inputs. If tests need fixtures, copy them to `tests/fixtures/` as byte-identical copies.

## Project Structure

```
cv_generator/
├── generate_cv.py          # Main script: JSON → LaTeX (Jinja2) → PDF
├── awesome-cv.cls          # Awesome-CV LaTeX class
├── data/
│   ├── cvs/               # Input JSON CVs (LOCKED - do not modify)
│   │   ├── ramin.json
│   │   └── mahsa.json
│   └── pics/              # Profile photos
├── templates/             # Jinja2+LaTeX section templates
│   ├── layout.tex         # Main document layout
│   ├── header.tex         # Personal info & social links
│   ├── education.tex
│   ├── experience.tex
│   ├── skills.tex
│   └── ...
├── output/                # Generated PDFs
└── scripts/               # Utility scripts for validation
```

## Where Language Selection is Implemented

Currently, language is implicit based on the JSON file content. Each JSON file (`ramin.json`, `mahsa.json`) contains all content in its respective language.

## Where CV Data is Loaded

CV data is loaded in `generate_cv.py`:
- Line 29: `JSON_PATH = os.path.join(CVS_PATH, people)`
- Line 116-117: `with open(JSON_PATH, encoding="utf-8") as f: data = json.load(f)`

The data is then made available to templates via `env_vars = {**data}`.

## Canonical Data-Shape Expectations

The UI/templates expect these top-level keys in JSON:

### Required Keys
- `basics` (array) - Personal info with `fname`, `lname`, `label`, `email`, `phone`, `location`, `Pictures`
- `profiles` (array) - Social links with `network`, `username`, `url`
- `education` (array) - Education entries with `institution`, `studyType`, `area`, `startDate`, `endDate`

### Optional Keys
- `experiences` (array) - Work experience entries
- `skills` (object) - Nested structure: section → category → items with `short_name`
- `languages` (array) - Language proficiency
- `projects` (array) - Projects with `title`, `description`, `url`
- `publications` (array) - Publications
- `references` (array) - References
- `workshop_and_certifications` (array) - Certifications

### Type Expectations
- Arrays must remain arrays (not objects)
- Dates should be ISO format or "present"
- All text fields should be strings (not null for display fields)

## Debugging Missing/Undefined Sections Checklist

1. **Check template references**: Open the template file and verify all `<VAR>` references exist in JSON
2. **Check for null values**: Search JSON for `null` values that templates may not handle
3. **Check array lengths**: Templates often check `|length > 1` before rendering sections
4. **Use debug filter**: Add `| debug` to template variables to print data to console
5. **Check Jinja errors**: `StrictUndefined` will fail loudly on missing variables
6. **Verify JSON syntax**: Use `python -m json.tool data/cvs/file.json` to validate

## What "Done" Means

A task is complete when:
1. All CV JSON files render without Jinja2 errors
2. All sections appear correctly in the output LaTeX
3. No `undefined` or `null` strings appear in rendered output
4. The smoke validation script passes for all CVs
5. Locked JSON files have identical SHA-256 hashes to original
