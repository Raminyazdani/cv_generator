# Language-Aware Tagging Strategy

## Overview

The CV Generator Web UI implements a **language-aware tagging strategy** that allows users to:
- View and select tags in their preferred language (EN/DE/FA)
- Export CVs with tags translated to the export language
- Maintain a consistent canonical tag identity across all languages

## Strategy: Option A — Canonical Tag IDs with Localized Display

We implement **Option A** from the design specification:

| Aspect | Implementation |
|--------|----------------|
| **Canonical ID** | English key (e.g., `"Full CV"`) |
| **Display** | Localized name per active language |
| **Storage** | Database stores canonical IDs |
| **Export** | Writes language-specific tag strings based on export language |

### Why Option A?

1. **Backward Compatibility**: Existing CV data uses English tag names in `type_key` arrays
2. **Simplicity**: English is the base/default language, making canonical IDs readable
3. **Stability**: Canonical IDs provide stable references that won't change with translations
4. **Deterministic**: Clear rules for converting between localized and canonical forms

## Tag Object Structure

```python
{
    "id": "Full CV",           # Canonical ID (English)
    "labels": {
        "en": "Full CV",
        "de": "Vollständiger Lebenslauf",
        "fa": "رزومه کامل"
    },
    "scopes": ["en", "de", "fa"],  # Languages where this tag is valid
}
```

## Built-in Tag Translations

The following tags have built-in translations in `cv_generator/tags.py`:

| Canonical ID | German (DE) | Farsi (FA) |
|--------------|-------------|------------|
| Full CV | Vollständiger Lebenslauf | رزومه کامل |
| Academic | Akademisch | آکادمیک |
| Biotechnology | Biotechnologie | بیوتکنولوژی |
| Bioinformatics | Bioinformatik | بیوانفورماتیک |
| Programming | Programmierung | برنامه‌نویسی |
| Student Projects | Studentische Projekte | پروژه‌های دانشجویی |
| Web | Web | وب |
| Frontend | Frontend | فرانت‌اند |
| UI | UI | رابط کاربری |
| Robotics | Robotik | رباتیک |
| Embedded Systems | Eingebettete Systeme | سیستم‌های نهفته |
| Research | Forschung | پژوهش |

## Usage

### Setting the Display Language

In the Web UI, click one of the language buttons (EN/DE/FA) on the Tags page or Entry page. This sets the session language for:
- Tag display names
- Warning messages
- Default export language

### Exporting with Language-Specific Tags

When exporting a CV:
1. Tags are read from the database (stored as canonical IDs)
2. Tags are translated to the current session language
3. The exported JSON contains localized tag strings

Example export with German language:
```json
{
  "projects": [
    {
      "title": "My Project",
      "type_key": ["Vollständiger Lebenslauf", "Programmierung"]
    }
  ]
}
```

### Adding Custom Tags

Custom tags created by users are stored with their canonical ID (the name provided). If no translations are defined, the canonical ID is used for all languages.

To add translations for custom tags, extend the `TAG_TRANSLATIONS` dictionary in `cv_generator/tags.py`.

## Filtering Behavior

The UI supports filtering by:
- **Active Language Selection**: Tags display in the selected language
- **Search by Localized Label**: Search works on both canonical ID and translated labels
- **Missing Translation Warnings**: Tags without translation for current language are flagged

## Backward Compatibility

### Existing CV Data
Existing CVs with English tag values in `type_key` work without changes:
- English values are already canonical IDs
- No migration needed for English-language CVs

### Migration for Localized Tags
If CVs contain localized tag values (e.g., German tags), the system:
1. Uses reverse lookup to find the canonical ID
2. Maps localized strings back to canonical IDs
3. Stores canonical IDs in the database

### Ambiguous Mappings
If a localized string cannot be mapped to a canonical ID:
- The string is treated as a custom tag
- The original value becomes the canonical ID
- A warning is logged for review

## Validation & Warnings

The system validates tags and produces warnings for:
- **Missing Translations**: Tags present but lacking translation for current language
- **Unknown Tags**: Tags in entries but not in the catalog
- **Duplicate Tags**: Tags with similar names across languages

Warnings are visible in:
- Web UI (flash messages)
- CLI logs (when using export commands)

## API Reference

### TagCatalog Class

```python
from cv_generator.tags import TagCatalog, get_tag_catalog

catalog = get_tag_catalog()

# Get localized label
label = catalog.get_tag_label("Full CV", "de")  # "Vollständiger Lebenslauf"

# Convert localized to canonical
canonical = catalog.to_canonical("Vollständiger Lebenslauf")  # "Full CV"

# Convert canonical to localized
localized = catalog.from_canonical("Full CV", "de")  # "Vollständiger Lebenslauf"

# Check if translation exists
has_trans = catalog.has_translation("Full CV", "de")  # True
```

### Export Functions

```python
from cv_generator.db import export_cv

# Export with canonical IDs (default)
cv_data = export_cv("ramin", db_path, apply_tags=True)

# Export with German tags
cv_data = export_cv("ramin", db_path, apply_tags=True, tag_language="de")
```

## Constraints

- **`data/` is LOCKED**: Language mapping JSONs are read-only inputs
- **No Breaking Changes**: Existing CV JSON semantics are preserved
- **Canonical = English**: English keys are the source of truth

## Self-Audit Checklist

- [x] Did not modify `data/`
- [x] Implemented canonical tag identity strategy (Option A)
- [x] Documented the strategy in this file
- [x] Tag display and filtering are language-aware in UI
- [x] Export writes correct tag strings per language rules
- [x] Added regression tests for language switching and export
