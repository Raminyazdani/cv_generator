# Multi-Language CV Management

This guide covers creating and managing CV variants in multiple languages.

!!! tip "See Also"
    For complete language support documentation including RTL support and translation mapping, see [Languages](languages.md).

## Overview

CV Generator supports maintaining CV variants in multiple languages from a single source of truth. Each person can have CVs in:

| Code | Language | Direction |
|------|----------|-----------|
| `en` | English | LTR (Left-to-Right) |
| `de` | German | LTR |
| `fa` | Persian/Farsi | RTL (Right-to-Left) |

## File Naming Conventions

### Flat Structure (Recommended)

Place language-specific files in `data/cvs/`:

```
data/cvs/
├── jane.json       # English (default, no suffix)
├── jane_de.json    # German
└── jane_fa.json    # Persian
```

Alternative naming with explicit language code:

```
data/cvs/
├── jane.en.json    # English
├── jane.de.json    # German
└── jane.fa.json    # Persian
```

### i18n Directory Structure

Organize by person in subdirectories:

```
data/cvs/i18n/
└── jane/
    ├── cv.en.json   # English
    ├── cv.de.json   # German
    ├── cv.fa.json   # Persian
    └── lang.json    # Translation mapping
```

## Creating Language Variants

### Step 1: Create Base CV (English)

Start with the English version as the canonical reference:

```json
// data/cvs/jane.json
{
  "basics": [{
    "fname": "Jane",
    "lname": "Doe",
    "label": ["Software Engineer"],
    "email": "jane@example.com"
  }],
  "experiences": [{
    "institution": "Tech Corp",
    "role": "Senior Developer",
    "description": "Led development of microservices platform"
  }]
}
```

### Step 2: Create Translated Versions

Copy and translate content for each language:

```json
// data/cvs/jane_de.json
{
  "basics": [{
    "fname": "Jane",
    "lname": "Doe",
    "label": ["Softwareingenieurin"],
    "email": "jane@example.com"
  }],
  "experiences": [{
    "institution": "Tech Corp",
    "role": "Leitende Entwicklerin",
    "description": "Leitung der Entwicklung einer Microservices-Plattform"
  }]
}
```

### Step 3: Build All Languages

```bash
cvgen build --name jane
```

This generates:
- `output/pdf/jane/en/jane_en.pdf`
- `output/pdf/jane/de/jane_de.pdf`
- `output/pdf/jane/fa/jane_fa.pdf`

## Validating Consistency

Use `cvgen ensure` to verify all language versions have consistent structure:

```bash
# Check all languages
cvgen ensure --name jane

# Check specific languages
cvgen ensure --name jane --langs en,de

# JSON output for scripting
cvgen ensure --name jane --format json
```

### What It Checks

1. **Missing keys** — Fields present in English but missing in other languages
2. **Extra keys** — Fields in other languages not present in English
3. **Schema consistency** — Same structure across all versions
4. **Translation mapping** — All skill headings have translations

### Example Output

```
Found 2 issue(s):

=== Missing Keys/Paths ===
  [de] experiences[2].description (hint: Key 'description' missing in de version)

=== Extra Keys/Paths ===
  [fa] skills.Extra Category (found: Extra Category)

Summary: 1 missing, 1 extra, 0 schema errors, 0 mapping issues
```

## Translation Mapping

Skill headings and categories can be automatically translated using a mapping file.

### Location

Translation mappings are loaded from (in order):

1. `data/cvs/i18n/<name>/lang.json` (per-person)
2. `data/cvs/lang.json` (shared)
3. `src/cv_generator/lang_engine/lang.json` (default)

### Format

```json
{
  "Technical Skills": {
    "de": "Technische Fähigkeiten",
    "fa": "مهارت‌های فنی"
  },
  "Programming": {
    "de": "Programmierung",
    "fa": "برنامه‌نویسی"
  },
  "Soft Skills": {
    "de": "Soft Skills",
    "fa": "مهارت‌های نرم"
  }
}
```

### Usage in Templates

The mapping is available as `LANG_MAP` in templates:

```latex
<BLOCK> set translated = LANG_MAP.get(heading, {}).get(LANG, heading) </BLOCK>
{<VAR> translated | latex_escape </VAR>}
```

## Shared vs. Translated Fields

### Fields That Should Stay the Same

These fields should be identical across all language versions:

- Email addresses
- Phone numbers
- URLs and DOIs
- Dates (startDate, endDate)
- Identifiers (IDs, UUIDs)

### Fields That Should Be Translated

These fields should be translated for each language:

- Job titles (`role`, `label`)
- Descriptions
- Institution names (sometimes)
- Skill names
- Section headings

## Web UI Multi-Language Features

The Web UI provides tools for managing multi-language CVs:

### Creating Entries in All Languages

When creating a new entry, enable "Sync to all languages" to:

1. Create the entry in the source language (EN by default)
2. Auto-create placeholder entries in DE and FA
3. Mark non-source entries as "needs translation"

### Viewing Linked Entries

1. Navigate to an entry detail page
2. Click **View Linked Entries**
3. See all language variants of the same entry
4. Navigate between them to compare content

### Checking Translation Status

1. Go to **Diagnostics**
2. Look for "Entries Needing Translation" section
3. Click on entries to navigate to them for translation

### Syncing Shared Fields

When editing an entry:

1. Enable "Sync shared fields"
2. Save changes
3. URL, dates, and identifiers update across all language variants

## Best Practices

1. **English as canonical** — Keep English as the reference version
2. **Consistent structure** — All versions should have the same sections and entries
3. **Keep keys in English** — Only translate values, not JSON keys
4. **Run validation** — Use `cvgen ensure` before generating
5. **Translation memory** — Maintain a shared `lang.json` for consistency
6. **Same entry count** — Each section should have the same number of entries

## Database Multi-Language Support

The SQLite database tracks language variants automatically:

```bash
# Import all language variants
cvgen db import

# Export specific language
cvgen db export --lang en

# Check for missing variants
cvgen db doctor
```

### How Variants Are Linked

Entries with the same:
- Section (e.g., `experiences`)
- Position/order in the section
- Person ID

Are considered variants of the same logical entry.

## Troubleshooting

### Language File Not Found

**Symptom:**
```
CV file not found for language 'de'
```

**Solution:** Create the language file with proper naming:
- `data/cvs/jane.json` (English default)
- `data/cvs/jane_de.json` (German)

### RTL Text Not Working

**Symptom:** Persian text displays incorrectly.

**Solution:**
1. Ensure `polyglossia` package is installed
2. Use XeLaTeX (not pdfLaTeX)
3. Check that templates handle `IS_RTL` variable

### Translation Not Applied

**Symptom:** Skill headings not translated.

**Solution:**
1. Check translation mapping in `lang.json`
2. Ensure heading key matches exactly
3. Verify language code is correct (`de`, not `DE`)

## Related Documentation

- [Languages](languages.md) — Complete language support including RTL
- [JSON Schema](json-schema.md) — CV data format
- [Web UI Cookbook](webui_cookbook.md) — Web interface for multi-language editing
- [Troubleshooting](troubleshooting.md) — Common issues and solutions
