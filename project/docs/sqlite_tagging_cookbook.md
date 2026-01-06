# SQLite Tagging Cookbook

This comprehensive guide covers the SQLite data layer and tagging system in CV Generator. It explains concepts, operations, extending the system, and troubleshooting.

## Table of Contents

1. [Concepts](#concepts)
   - [Entity Table Design](#entity-table-design)
   - [Deterministic IDs](#deterministic-ids)
   - [Generic Tagging Model](#generic-tagging-model)
   - [type_key Sync Rules](#type_key-sync-rules)
2. [Operations](#operations)
   - [Initialize Database](#initialize-database)
   - [Import CVs](#import-cvs)
   - [Export CVs](#export-cvs)
   - [Tag Lifecycle](#tag-lifecycle)
   - [Tagging from CLI vs UI](#tagging-from-cli-vs-ui)
   - [Database Health Check](#database-health-check)
3. [Extending the System](#extending-the-system)
   - [Adding a New CV Section](#adding-a-new-cv-section)
   - [Adding a New Field to an Entry](#adding-a-new-field-to-an-entry)
   - [Enabling type_key for New Entity Types](#enabling-type_key-for-new-entity-types)
   - [Writing Migrations Safely](#writing-migrations-safely)
   - [Updating Importer/Exporter Mapping](#updating-importerexporter-mapping)
   - [Updating Tests and Fixtures](#updating-tests-and-fixtures)
4. [Troubleshooting](#troubleshooting)
   - [IDs Changed Unexpectedly](#ids-changed-unexpectedly)
   - [Duplicate Tags](#duplicate-tags)
   - [Export Structure Mismatch](#export-structure-mismatch)
   - [Encoding Issues](#encoding-issues)

---

## Concepts

### Entity Table Design

The database uses a **flexible, JSON-blob approach** that preserves unknown fields and avoids schema churn.

#### Core Tables

```sql
-- Person table (who the CV belongs to)
person (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE,        -- e.g., "ramin", "ramin_de"
    display_name TEXT,       -- e.g., "Ramin Yazdani"
    created_at TEXT
)

-- Entry table (all CV sections stored as JSON blobs)
entry (
    id INTEGER PRIMARY KEY,
    person_id INTEGER,       -- FK to person
    section TEXT,            -- e.g., "projects", "education"
    order_idx INTEGER,       -- preserves list order
    data_json TEXT,          -- full JSON object for entry
    identity_key TEXT,       -- stable ID for re-import matching
    created_at TEXT
)

-- Tag table (type_key values)
tag (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,        -- e.g., "Full CV", "Academic"
    description TEXT,
    created_at TEXT
)

-- Entry-Tag relationship (many-to-many)
entry_tag (
    entry_id INTEGER,
    tag_id INTEGER,
    PRIMARY KEY (entry_id, tag_id)
)
```

#### Why This Design?

1. **Preserves unknown keys** - Any field in the JSON is stored and restored exactly
2. **No schema churn** - New sections or fields require no database migration
3. **Generic tagging** - Tags can be applied to any entry type
4. **Future-proof** - New entity types get tagging automatically

### Deterministic IDs

Each entry gets an `identity_key` computed from its content. This allows:
- Re-importing a modified JSON file and matching existing entries
- Detecting when entries change
- Stable references for tagging

#### Identity Key Computation

| Section | Key Components |
|---------|----------------|
| projects | `title` + `url` |
| experiences | `role` + `institution` + `duration` |
| publications | `doi` or `title` |
| education | `institution` + `area` + `startDate` |
| references | `name` or `email` |
| profiles | `url` or `network` |
| languages | `language` |
| basics | `fname` + `lname` |
| workshop_and_certifications | `issuer` |
| **skills** | Entry path: `skills/<parent>/<sub>/<skill_key>` |

Example identity key: `projects:url=https://github.com/user/repo`

### Skills Section: Nested Structure and Tagging

The `skills` section uses a **nested dictionary structure** unlike other flat list sections. This requires special handling for tagging individual skill items.

#### Skills JSON Structure

```json
{
  "skills": {
    "Programming & Scripting": {
      "Programming Languages": [
        {
          "long_name": "Python",
          "short_name": "Python",
          "type_key": ["Full CV", "Programming"]
        },
        {
          "long_name": "JavaScript",
          "short_name": "JS",
          "type_key": ["Full CV", "Web"]
        }
      ],
      "Machine Learning": [
        {
          "long_name": "TensorFlow",
          "short_name": "TensorFlow",
          "type_key": ["Full CV", "AI"]
        }
      ]
    },
    "Soft Skills": {
      "Core": [
        {
          "long_name": "Problem-Solving",
          "short_name": "Problem-Solving",
          "type_key": ["Full CV"]
        }
      ]
    }
  }
}
```

Structure:
- **Parent categories**: Top-level keys (e.g., "Programming & Scripting")
- **Sub-categories**: Second-level keys (e.g., "Programming Languages")
- **Skill items**: List of objects with `short_name`, `long_name`, and optional `type_key`

#### Entry Paths for Skills

Each skill item gets a unique, stable **entry path** for identification:

```
skills/<parent_category>/<sub_category>/<skill_key>
```

Example paths:
- `skills/Programming%20%26%20Scripting/Programming%20Languages/Python`
- `skills/Soft%20Skills/Core/Problem-Solving`

The `skill_key` is determined by:
1. `short_name` (preferred, if unique within the sub-category)
2. `short_name` with hash suffix (if duplicates exist)
3. `long_name` fallback
4. Index as last resort (`idx_0`)

#### Collision Handling

If two skills in the same sub-category share the same `short_name`, they are disambiguated:

```json
{
  "Machine Learning": [
    {"short_name": "ML", "long_name": "Supervised Learning"},
    {"short_name": "ML", "long_name": "Unsupervised Learning"}
  ]
}
```

Results in paths:
- `skills/.../Machine%20Learning/ML`
- `skills/.../Machine%20Learning/ML_abc123` (suffix derived from `long_name` hash)

#### Web UI: Skills Tree View

When viewing the skills section in the Web UI, skills are displayed grouped by category:

```
📁 Programming & Scripting
  📂 Programming Languages
    🔹 Python - [Full CV] [Programming]
    🔹 JS (JavaScript) - [Full CV] [Web]
  📂 Machine Learning
    🔹 TensorFlow - [Full CV] [AI]

📁 Soft Skills
  📂 Core
    🔹 Problem-Solving - [Full CV]
```

You can:
- Search across all skills (includes category names in search)
- Click any skill to edit its tags
- Changes apply to the specific skill item only

#### Import/Export with Skills

On **import**:
- Each skill item is stored as a separate database entry
- `identity_key` is set to the entry path
- `type_key` values become tag associations

On **export**:
- Individual skill entries are reconstructed into nested structure
- Order within sub-categories is preserved
- Updated `type_key` values are applied if `--apply-tags` is used

### Generic Tagging Model

Tags are stored separately from entry data, enabling:
- Creating tags before assigning them
- Renaming tags without touching entries
- Querying entries by tag across sections
- Applying tags to any entity type

```
[Entry 1: "Project A"] ──┬──> [Tag: "Full CV"]
                         └──> [Tag: "Academic"]

[Entry 2: "Education B"] ──┬──> [Tag: "Full CV"]
                           └──> [Tag: "Bioinformatics"]
```

### type_key Sync Rules

The `type_key` field in JSON is synchronized with the database tags:

#### On Import
1. Extract `type_key` array from entry JSON
2. Create tags for each value (if not exists)
3. Link entry to tags via `entry_tag` table
4. Store original `type_key` in `data_json`

#### On Export (default behavior)
- Write `type_key` back **only** for entries that originally had it
- Preserve the exact values stored in `data_json`

#### On Export with `--apply-tags`
- Rebuild `type_key` from `entry_tag` relationships
- Only for entries that originally had `type_key`

#### On Export with `--apply-tags-to-all`
- Add `type_key` to ALL entries from database tags
- Even entries that didn't originally have `type_key`

---

## Operations

### Initialize Database

Create a new database with the schema:

```bash
# Using default location (data/db/cv.db)
cvgen db init

# Custom location
cvgen db init --db /path/to/cv.db

# Force recreate (destroys existing data!)
cvgen db init --force
```

The schema version is tracked in the `meta` table for future migrations.

### Import CVs

Import CV JSON files into the database:

```bash
# Import all CVs from default location (data/cvs/)
cvgen db import

# Import from custom directory
cvgen db import -i /path/to/cvs

# Import specific person
cvgen db import --name ramin

# Overwrite existing entries (with backup)
cvgen db import --overwrite

# Overwrite without backup
cvgen db import --overwrite --no-backup
```

#### What Happens During Import

1. Parse filename to get person slug and language
2. Load JSON data
3. Create/update person record
4. For each section in JSON:
   - Create entry with `data_json` blob
   - Compute `identity_key`
   - Extract `type_key` and create tag relationships

### Export CVs

Export database content to JSON files:

```bash
# Export all persons to default directory
cvgen db export --force

# Export to custom directory
cvgen db export -o /path/to/output --force

# Export specific person
cvgen db export --name ramin --force

# Apply tags from database
cvgen db export --apply-tags --force

# Add type_key to all entries
cvgen db export --apply-tags-to-all --force

# Minified output
cvgen db export --format min --force
```

The `--force` flag is required to overwrite existing files.

### Tag Lifecycle

#### Create Tags

```bash
# Via Web UI
cvgen web tags
# Navigate to /tags/create

# Tags are also created automatically during import
```

#### Rename Tags

```bash
# Via Web UI
cvgen web tags
# Navigate to /tags/<name>/edit
```

#### Delete Tags

Deleting a tag performs a **hard delete with cascade cleanup**:

1. Removes the tag from the tag catalog
2. Removes all `entry_tag` relationships
3. Updates `data_json` `type_key` arrays in all affected entries
4. If `type_key` becomes empty, it is removed entirely

```bash
# Via Web UI
cvgen web tags
# Click delete on /tags page
```

**Important:** Tag deletion is atomic - all changes occur in a single database transaction. If anything fails, the entire operation is rolled back.

#### Remove Tag from Single Entry

To remove a tag from a specific entry (without deleting the tag from the catalog):

1. Navigate to the entry in the Web UI
2. Uncheck the tag in the tag selection
3. Save changes

This updates both:
- The `entry_tag` relationship table
- The `type_key` field in `data_json`

#### Cleanup Orphan Tag References

If you suspect stale tag references in `data_json` (from manual edits or older versions), you can run cleanup:

```python
from cv_generator.db import cleanup_orphan_tag_references

result = cleanup_orphan_tag_references(db_path)
print(f"Cleaned {result['entries_cleaned']} entries")
print(f"Removed orphan tags: {result['orphan_tags_found']}")
```

This function:
- Scans all entries for `type_key` values
- Removes any tags that don't exist in the catalog
- Updates `data_json` accordingly

#### Assign Tags to Entries

1. Start the web UI: `cvgen web tags`
2. Navigate to a person's section
3. Click on an entry
4. Select/deselect tags
5. Save changes

### Tag Data Integrity

The tagging system maintains referential integrity between:

1. **Tag Catalog** (`tag` table) - the list of available tags
2. **Entry-Tag Relationships** (`entry_tag` table) - which entries have which tags
3. **Data JSON** (`entry.data_json` `type_key`) - the stored JSON representation

**Invariant:** After any tag mutation (create, delete, assign, remove), all three representations must agree.

This is enforced by:
- `delete_tag()` - updates all three when deleting
- `update_entry_tags()` - updates entry_tag and data_json atomically
- `remove_tag_from_entry()` - removes single tag from one entry
- `cleanup_orphan_tag_references()` - fixes any stale data_json references

### Export Consistency

Exports from the Web UI always use `apply_tags=True`, which:
- Rebuilds `type_key` from the `entry_tag` relationships
- Ensures the latest database state is exported
- Never reintroduces deleted tags

### Tagging from CLI vs UI

| Method | Use Case | How |
|--------|----------|-----|
| Web UI | Interactive browsing and editing | `cvgen web tags` |
| Import | Bulk tagging from JSON | Edit JSON `type_key` arrays, then import |
| Export | Apply DB tags to JSON | `cvgen db export --apply-tags` |

### Database Health Check

Run diagnostics on your database:

```bash
# Basic health check
cvgen db doctor

# JSON output for scripting
cvgen db doctor --format json

# Custom database
cvgen db doctor --db /path/to/cv.db
```

#### Checks Performed

- **Schema version** - Matches expected version
- **Orphaned entries** - Entries without valid person
- **Orphaned tags** - Tags not used by any entry
- **Duplicate tags** - Case-insensitive duplicates
- **Missing identity keys** - Entries without stable IDs
- **Invalid JSON** - Corrupted `data_json` fields

---

## Extending the System

### Adding a New CV Section

Suppose you want to add an `awards` section.

#### 1. Add to Your JSON

```json
{
  "awards": [
    {
      "title": "Best Paper Award",
      "issuer": "IEEE",
      "date": "2024-01-15",
      "type_key": ["Full CV", "Academic"]
    }
  ]
}
```

#### 2. Import Normally

```bash
cvgen db import --overwrite
```

The system automatically:
- Detects `awards` as a list section
- Stores each award as an entry
- Extracts `type_key` values as tags

#### 3. (Optional) Add Identity Key Logic

Edit `src/cv_generator/db.py`, add to `_compute_identity_key()`:

```python
elif section == "awards":
    if item.get("title") and item.get("issuer"):
        return f"awards:{item['title']}-{item['issuer']}"
```

#### 4. (Optional) Add Web UI Summary

Edit `src/cv_generator/web.py`, add to `get_entry_summary()`:

```python
elif section == "awards":
    title = data.get("title", "Untitled Award")
    issuer = data.get("issuer", "")
    return f"{title}" + (f" ({issuer})" if issuer else "")
```

### Adding a New Field to an Entry

Since we use JSON blobs, new fields are automatically preserved:

1. Add the field to your JSON:
   ```json
   {
     "projects": [
       {
         "title": "My Project",
         "status": "active",  // New field!
         "priority": 1        // Another new field!
       }
     ]
   }
   ```

2. Import normally - fields are preserved in `data_json`

3. Export - new fields appear in output

No database migration needed!

### Enabling type_key for New Entity Types

The system already supports `type_key` for any entity. To enable it:

1. **Add `type_key` to your JSON entries:**
   ```json
   {
     "experiences": [
       {
         "role": "Developer",
         "type_key": ["Full CV", "Technical"]
       }
     ]
   }
   ```

2. **Import the CV:**
   ```bash
   cvgen db import --overwrite
   ```

3. **Use the Web UI to manage tags:**
   ```bash
   cvgen web tags
   ```

4. **Export with tags:**
   ```bash
   cvgen db export --apply-tags --force
   ```

### Writing Migrations Safely

For schema changes, use the migrations pattern:

#### 1. Update SCHEMA_VERSION

In `src/cv_generator/db.py`:
```python
SCHEMA_VERSION = 2  # Was 1
```

#### 2. Add Migration Logic

```python
def _migrate_v1_to_v2(conn):
    """Migrate from v1 to v2 schema."""
    cursor = conn.cursor()
    # Add new column, create new table, etc.
    cursor.execute("ALTER TABLE entry ADD COLUMN new_field TEXT")
    conn.commit()
```

#### 3. Update init_db()

```python
def init_db(db_path, force=False):
    # ... existing code ...
    
    # Check for migration
    cursor.execute("SELECT value FROM meta WHERE key = 'schema_version'")
    row = cursor.fetchone()
    if row:
        current_version = int(row[0])
        if current_version < SCHEMA_VERSION:
            logger.info(f"Migrating from v{current_version} to v{SCHEMA_VERSION}")
            if current_version == 1:
                _migrate_v1_to_v2(conn)
            # Update version
            cursor.execute(
                "UPDATE meta SET value = ?, updated_at = ? WHERE key = 'schema_version'",
                (str(SCHEMA_VERSION), _utcnow())
            )
```

### Updating Importer/Exporter Mapping

#### Importer Changes

Key functions in `src/cv_generator/db.py`:

- `import_cv()` - Main import logic
- `_compute_identity_key()` - Generate stable IDs
- `_extract_type_keys()` - Extract tags from entries

#### Exporter Changes

Key functions:

- `export_cv()` - Main export logic
- `export_cv_to_file()` - Write to disk
- `_rebuild_type_keys()` - Reconstruct from `entry_tag`

### Updating Tests and Fixtures

#### Add Test Fixtures

Create `tests/fixtures/new_test_cv.json`:
```json
{
  "basics": [{"fname": "Test", "lname": "User"}],
  "new_section": [{"field": "value"}]
}
```

#### Add Tests

In `tests/test_db.py`:
```python
def test_new_section_round_trip(self, tmp_path):
    """Test that new sections are preserved."""
    # Create and import test data
    # Export and verify
```

---

## Troubleshooting

### IDs Changed Unexpectedly

**Symptom:** After reimporting, entries have different IDs

**Causes:**
1. Identity key fields changed (title, URL, etc.)
2. Using `--overwrite` which deletes old entries

**Solutions:**
1. Check which fields changed
2. Use a stable identifier like URL or DOI
3. For debugging, enable debug logging:
   ```bash
   cvgen --debug db import
   ```

### Duplicate Tags

**Symptom:** Multiple tags with similar names (case differences)

**Detection:**
```bash
cvgen db doctor
```
Look for "Duplicate tags" in output.

**Fix:**
1. Identify duplicates via Web UI or doctor output
2. Manually rename/merge via Web UI
3. Delete the unwanted tags

### Export Structure Mismatch

**Symptom:** Exported JSON doesn't match original structure

**Common Issues:**
1. **Empty lists missing:** Fixed in current version
2. **Dict sections as lists:** Check your JSON structure
3. **Field order changed:** JSON doesn't guarantee order

**Debugging:**
```bash
# Compare original and exported
cvgen db diff --name ramin
```

### Encoding Issues

**Symptom:** Unicode characters corrupted or displayed wrong

**Causes:**
1. File saved with wrong encoding
2. Terminal doesn't support UTF-8

**Solutions:**
1. Ensure JSON files are UTF-8:
   ```python
   with open("cv.json", "w", encoding="utf-8") as f:
       json.dump(data, f, ensure_ascii=False)
   ```

2. Use a UTF-8 terminal

3. Check database encoding:
   ```bash
   sqlite3 cv.db "PRAGMA encoding;"
   # Should show: UTF-8
   ```

---

## Quick Reference

### CLI Commands

```bash
# Database initialization
cvgen db init [--db PATH] [--force]

# Import from JSON
cvgen db import [--db PATH] [-i DIR] [--name NAME] [--overwrite]

# Export to JSON
cvgen db export [--db PATH] [-o DIR] [--name NAME] [--apply-tags] [--force]

# Compare JSON with database
cvgen db diff [--db PATH] [-i DIR] [--name NAME]

# List database contents
cvgen db list [--db PATH] [--what persons|tags]

# Health check
cvgen db doctor [--db PATH] [-f text|json]

# Web UI
cvgen web tags [--db PATH] [--host HOST] [--port PORT]
```

### Default Paths

| Item | Default Path |
|------|--------------|
| Database | `data/db/cv.db` |
| CV JSONs | `data/cvs/` |
| Templates | `templates/` |
| Output | `output/` |
