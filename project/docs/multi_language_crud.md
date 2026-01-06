# Multi-Language Entry Sync and CRUD Engine

This document explains how the generalized JSON CRUD engine works and how multi-language synchronization is implemented.

## Overview

The CV Generator supports managing CVs in multiple languages (English, German, Persian/Farsi). The CRUD engine provides a unified way to:

1. **Create** entries that are automatically synced across all available languages
2. **Update** entries with optional shared field synchronization
3. **Delete** entries across all language variants
4. **Link** existing entries from different languages together

## Key Concepts

### Stable Entry IDs

Each entry has a stable ID that links corresponding entries across languages. This allows:
- Tracking which EN/DE/FA entries are translations of each other
- Syncing shared fields (URLs, dates, etc.) across languages
- Ensuring structural consistency across language variants

Stable IDs are stored in the database in the `stable_entry` and `entry_lang_link` tables.

### Shared vs. Text Fields

Fields are categorized as:

- **Shared Fields**: Data that should be identical across languages
  - URLs, DOIs, dates, type_key (tags)
  - When sync is enabled, these are updated in all language variants

- **Text Fields**: Content that needs translation
  - Titles, descriptions, names
  - These are only updated in the current language

### Section Adapters

Each CV section type has an adapter that handles CRUD operations:

| Section Type | Adapter | Notes |
|--------------|---------|-------|
| projects | ListSectionAdapter | Standard list-based section |
| experiences | ListSectionAdapter | Standard list-based section |
| publications | ListSectionAdapter | Includes DOI as shared field |
| references | ListSectionAdapter | Email/phone are shared fields |
| education | ListSectionAdapter | Dates, GPA are shared fields |
| languages | ListSectionAdapter | Standard list-based section |
| profiles | ListSectionAdapter | URL, username are shared fields |
| workshop_and_certifications | ListSectionAdapter | Dates are shared fields |
| skills | (Not yet supported) | Requires tree adapter (see extending) |

## Multi-Language Sync Rules

### When Creating an Entry

1. Entry is created in the source language (e.g., English)
2. Placeholder entries are created in all other available languages (DE, FA)
3. Placeholders contain:
   - Shared fields: copied exactly from source
   - Text fields: copied from source as placeholders (marked as needing translation)
4. All entries share the same `stable_id`

### When Updating an Entry

1. **Default behavior**: Only the current language entry is updated
2. **With sync_shared_fields=True**:
   - Shared fields are propagated to all language variants
   - Text fields remain unchanged in other languages

### When Deleting an Entry

1. **With sync_languages=True** (default): All language variants are deleted
2. **With sync_languages=False**: Only the specified entry is deleted

## Using the CRUD API

### Python API

```python
from cv_generator.crud import (
    create_entry,
    update_entry,
    delete_entry,
    get_entry,
    list_entries,
    get_linked_entries,
)

# Create a new project with multi-language sync
result = create_entry(
    person_slug="ramin",
    section="projects",
    data={
        "title": "My Project",
        "description": "Project description",
        "url": "https://github.com/example/project",
        "type_key": ["Full CV", "Programming"]
    },
    sync_languages=True  # Creates placeholders in DE/FA
)

print(f"Created with stable_id: {result['stable_id']}")
print(f"Entries created: {result['entries']}")  # {"en": 1, "de": 2, "fa": 3}

# Update an entry with shared field sync
update_entry(
    entry_id=1,
    data={
        "title": "Updated Title",
        "url": "https://new-url.com"
    },
    section="projects",
    sync_shared_fields=True  # URL will update in DE/FA too
)

# Delete entry from all languages
delete_entry(
    entry_id=1,
    section="projects",
    sync_languages=True
)

# Get all language variants of an entry
linked = get_linked_entries(entry_id=1, section="projects")
for lang, entry in linked.items():
    print(f"{lang}: {entry['data']['title']} (needs_translation: {entry['needs_translation']})")
```

### Web UI

The Web UI provides forms for:

1. **Creating entries** (`/p/<person>/<section>/create`)
   - Multi-language sync checkbox (enabled by default)
   - Creates placeholders in all available languages

2. **Editing entries** (`/entry/<id>/edit`)
   - Sync shared fields checkbox
   - Shows linked language variants

3. **Viewing linked entries** (`/entry/<id>/linked`)
   - Shows all language variants
   - Indicates which need translation

4. **Deleting entries** (from edit form)
   - Option to delete from all languages

## Extending for New Sections

### Adding a New List Section

To add support for a new list-based section:

1. Add the section name to `LIST_SECTIONS` in `crud.py`:

```python
LIST_SECTIONS = [
    "projects", "experiences", "publications", "references",
    "education", "languages", "profiles", "workshop_and_certifications",
    "new_section",  # Add your section here
]
```

2. Define shared fields for the section in `SHARED_FIELDS`:

```python
SHARED_FIELDS = {
    # ... existing sections ...
    "new_section": ["url", "date", "type_key"],  # Fields that should sync
}
```

3. Add form fields to `entry_form.html` template if needed.

### Creating a Custom Adapter

For sections with special structure (like skills with nested categories), create a custom adapter:

```python
from cv_generator.crud import SectionAdapter

class TreeSectionAdapter(SectionAdapter):
    """Adapter for tree-structured sections like skills."""
    
    def list_entries(self, person_slug, db_path=None):
        # Custom implementation for nested structure
        pass
    
    def get_entry(self, entry_id, db_path=None):
        # Custom implementation
        pass
    
    def create_entry(self, person_slug, data, db_path=None, sync_languages=True):
        # Handle nested structure creation
        pass
    
    def update_entry(self, entry_id, data, db_path=None, sync_shared_fields=False):
        # Custom update logic
        pass
    
    def delete_entry(self, entry_id, db_path=None, sync_languages=True):
        # Custom delete logic
        pass
```

Then register it:

```python
# In crud.py, add to get_section_adapter()
if section == "skills":
    _adapters[section] = TreeSectionAdapter(section)
```

## Database Schema

The CRUD engine extends the existing database with these tables:

```sql
-- Stable entry ID for multi-language linking
CREATE TABLE stable_entry (
    id TEXT PRIMARY KEY,
    section TEXT NOT NULL,
    base_person TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Link between stable_entry and actual entries per language
CREATE TABLE entry_lang_link (
    stable_id TEXT NOT NULL,
    language TEXT NOT NULL,
    entry_id INTEGER NOT NULL,
    needs_translation INTEGER DEFAULT 0,
    PRIMARY KEY (stable_id, language),
    FOREIGN KEY (stable_id) REFERENCES stable_entry(id),
    FOREIGN KEY (entry_id) REFERENCES entry(id)
);
```

## Important Notes

1. **data/ is LOCKED**: The CRUD engine does not modify files in the `data/` directory. All changes are stored in the SQLite database.

2. **Export to output/**: To get updated JSON files, use the export functionality which writes to `output/` directory.

3. **Existing entries**: Entries imported before the CRUD engine may not have stable IDs. Use `link_existing_entries()` to link them manually.

4. **Translation workflow**: Entries marked as `needs_translation=True` should be reviewed and translated by a human editor.
