# Import/Export Workflows

This guide covers importing CV data into the database and exporting it back to JSON files.

## Overview

CV Generator uses a SQLite database as an intermediate storage layer:

```
JSON Files → Import → Database → Export → JSON Files
                ↓
            Web UI / CLI Editing
```

This enables:
- Editing CVs through the Web UI
- Managing tags and filtering
- Validating data integrity
- Multi-language synchronization

## Quick Start

```bash
# Initialize database
cvgen db init

# Import all CVs from data/cvs/
cvgen db import

# Make changes via Web UI
cvgen web tags

# Export back to JSON
cvgen db export --output-dir output/json
```

## Importing CVs

### Import All CVs

Import all JSON files from the default directory:

```bash
cvgen db import
```

This imports from `data/cvs/` by default.

### Import from Custom Directory

```bash
cvgen db import --input-dir /path/to/cvs
```

### Import Specific CV

```bash
cvgen db import --name jane
```

This imports `jane.json`, `jane_de.json`, `jane_fa.json`, etc.

### Overwrite Existing Data

By default, existing data is preserved. Use `--overwrite` to replace:

```bash
cvgen db import --overwrite
```

### Import Options

| Option | Description |
|--------|-------------|
| `--input-dir DIR` | Input directory (default: data/cvs) |
| `--name NAME` | Import only matching CVs |
| `--db PATH` | Database file path |
| `--overwrite` | Replace existing entries |
| `--no-backup` | Don't backup before overwrite |

## Exporting CVs

### Export All CVs

Export all CVs to JSON files:

```bash
cvgen db export
```

Files are written to `output/json/` by default.

### Export to Custom Directory

```bash
cvgen db export --output-dir /path/to/output
```

### Export Specific CV

```bash
cvgen db export --name jane
```

### Export Specific Language

```bash
cvgen db export --name jane --lang en
```

### Export with Tags

Apply database tags to the exported JSON:

```bash
# Apply tags to entries that originally had type_key
cvgen db export --apply-tags

# Add type_key to ALL entries
cvgen db export --apply-tags-to-all
```

### Export Options

| Option | Description |
|--------|-------------|
| `--output-dir DIR` | Output directory |
| `--name NAME` | Export only matching CVs |
| `--lang LANG` | Export specific language |
| `--format {pretty,min}` | JSON formatting |
| `--apply-tags` | Include database tags |
| `--apply-tags-to-all` | Add tags to all entries |
| `--force` | Overwrite existing files |

## Comparing Database with Files

### Diff All CVs

Compare database content with JSON files:

```bash
cvgen db diff
```

### Diff Specific CV

```bash
cvgen db diff --name jane
```

### Diff Output Formats

```bash
# Human-readable output
cvgen db diff --format text

# JSON output for scripting
cvgen db diff --format json
```

### Understanding Diff Output

```
=== jane.json ===
+ experiences[2]                    # New entry in JSON
- skills.Programming[3]             # Entry removed from JSON
~ education[0].institution          # Modified field
```

## Round-Trip Verification

Verify that import/export preserves data integrity:

```bash
cvgen audit roundtrip data/cvs/
```

This:

1. Imports the JSON files
2. Exports them back
3. Compares original with exported
4. Reports any differences

### Verification Options

```bash
# Verify single file
cvgen audit roundtrip data/cvs/jane.json

# Verbose output
cvgen audit roundtrip data/cvs/ --verbose

# JSON output
cvgen audit roundtrip data/cvs/ --format json
```

## Web UI Export

The Web UI provides a visual interface for export:

1. Navigate to a person's dashboard
2. Click **👁️ Preview Export**
3. Review the JSON that will be exported
4. Switch languages to see localized versions
5. Click **💾 Export to File** when ready

### Export Preview

The preview shows exactly what will be written:

- All sections and entries
- Tag assignments
- Language-specific content
- Shared fields (URLs, dates)

## Python API

### Import CVs Programmatically

```python
from cv_generator import import_cv, import_all_cvs

# Import single file
import_cv("data/cvs/jane.json")

# Import all files
import_all_cvs(input_dir="data/cvs")
```

### Export CVs Programmatically

```python
from cv_generator import export_cv, export_all_cvs

# Export single CV
path = export_cv("jane", lang="en")
print(f"Exported to: {path}")

# Export all CVs
paths = export_all_cvs(output_dir="output/json")
```

### Using the v2 Export Engine

```python
from cv_generator import CVExporter, ExportVerifier

# Create exporter
exporter = CVExporter(db_path="data/db/cv.db")

# Export with options
result = exporter.export_cv(
    name="jane",
    lang="en",
    apply_tags=True
)

print(f"Exported: {result.path}")
print(f"Entries: {result.entry_count}")

# Verify round-trip
verifier = ExportVerifier(db_path="data/db/cv.db")
verification = verifier.verify_roundtrip("data/cvs/jane.json")

if verification.is_valid:
    print("Round-trip OK!")
else:
    print(f"Differences found: {len(verification.differences)}")
```

## Best Practices

### Before Importing

1. **Backup your database**:
   ```bash
   cp data/db/cv.db data/db/cv.db.backup
   ```

2. **Validate JSON files**:
   ```bash
   cvgen lint
   ```

3. **Check for conflicts**:
   ```bash
   cvgen db diff
   ```

### Export Strategy

1. **Export to separate directory** to preserve source files:
   ```bash
   cvgen db export --output-dir output/json
   ```

2. **Preview before exporting** using the Web UI

3. **Verify after export**:
   ```bash
   cvgen audit roundtrip output/json/
   ```

### Multi-Language Workflow

1. Import all language variants together
2. Make edits through the Web UI (shared fields sync automatically)
3. Export all languages at once
4. Validate consistency:
   ```bash
   cvgen ensure --name jane
   ```

## Troubleshooting

### Import Fails

**Symptom:**
```
Error: Invalid JSON in jane.json
```

**Solution:**
1. Validate JSON syntax:
   ```bash
   python -m json.tool < data/cvs/jane.json
   ```
2. Check for common issues:
   - Trailing commas
   - Unquoted keys
   - Missing brackets

### Export Missing Entries

**Symptom:** Exported JSON has fewer entries than expected.

**Solution:**
1. Check database health:
   ```bash
   cvgen db doctor
   ```
2. Re-import with overwrite:
   ```bash
   cvgen db import --overwrite
   ```

### Round-Trip Differences

**Symptom:** `cvgen audit roundtrip` shows differences.

**Common causes:**
- Field ordering (cosmetic, not a real difference)
- Null vs. missing fields
- Number formatting (1.0 vs 1)

**Solution:**
- Review differences manually
- Use `--verbose` to see details
- Accept cosmetic differences

### Tags Not in Export

**Symptom:** Tags assigned in Web UI don't appear in exported JSON.

**Solution:**
Use the `--apply-tags` flag:
```bash
cvgen db export --apply-tags
```

## Related Documentation

- [SQLite Tagging Cookbook](sqlite_tagging_cookbook.md) — Database concepts
- [Web UI Cookbook](webui_cookbook.md) — Web interface guide
- [CLI Reference](cli.md) — All CLI commands
- [API Reference](api.md) — Python API
