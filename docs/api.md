# API Reference

This document provides a reference for the CV Generator Python API. Use these functions to integrate CV generation into your own scripts and applications.

## Installation

```bash
pip install -e .
```

## Quick Example

```python
from cv_generator import generate_cv, load_cv_json

# Load CV data
data = load_cv_json("data/cvs/jane.json")

# Generate PDF
generate_cv(
    cv_data=data,
    name="jane",
    output_dir="output",
    templates_dir="templates"
)
```

## Core Functions

### generate_cv

Generate a PDF for a single CV.

```python
from cv_generator import generate_cv

generate_cv(
    cv_data: dict,
    name: str,
    output_dir: str = "output",
    templates_dir: str = "templates",
    keep_latex: bool = False,
    dry_run: bool = False,
    variant: str | None = None
) -> None
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `cv_data` | dict | CV data loaded from JSON |
| `name` | str | Base name for output files |
| `output_dir` | str | Output directory (default: "output") |
| `templates_dir` | str | Templates directory (default: "templates") |
| `keep_latex` | bool | Keep LaTeX source files |
| `dry_run` | bool | Render templates without PDF compilation |
| `variant` | str | Filter entries by type_key |

**Example:**

```python
from cv_generator import generate_cv, load_cv_json

data = load_cv_json("data/cvs/jane.json")

# Generate with variant filtering
generate_cv(
    cv_data=data,
    name="jane",
    variant="academic",
    keep_latex=True
)
```

### generate_all_cvs

Generate PDFs for all CV files in a directory.

```python
from cv_generator import generate_all_cvs

generate_all_cvs(
    input_dir: str = "data/cvs",
    output_dir: str = "output",
    templates_dir: str = "templates",
    name_filter: str | None = None,
    keep_latex: bool = False,
    dry_run: bool = False
) -> None
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `input_dir` | str | Directory containing CV JSON files |
| `output_dir` | str | Output directory |
| `templates_dir` | str | Templates directory |
| `name_filter` | str | Only process CVs matching this name |
| `keep_latex` | bool | Keep LaTeX source files |
| `dry_run` | bool | Render templates without PDF compilation |

**Example:**

```python
from cv_generator import generate_all_cvs

# Generate all CVs
generate_all_cvs()

# Generate only jane's CVs
generate_all_cvs(name_filter="jane")
```

## File I/O Functions

### discover_cv_files

Find all CV JSON files in a directory.

```python
from cv_generator import discover_cv_files

discover_cv_files(
    input_dir: str = "data/cvs"
) -> list[Path]
```

**Returns:** List of paths to CV JSON files.

**Example:**

```python
from cv_generator import discover_cv_files

files = discover_cv_files("data/cvs")
for f in files:
    print(f.name)
# jane.json
# jane_de.json
# jane_fa.json
```

### load_cv_json

Load and parse a CV JSON file.

```python
from cv_generator import load_cv_json

load_cv_json(
    path: str | Path
) -> dict
```

**Returns:** Dictionary containing CV data.

**Example:**

```python
from cv_generator import load_cv_json

data = load_cv_json("data/cvs/jane.json")
print(data["basics"][0]["fname"])  # "Jane"
```

### load_lang_map

Load a translation mapping file.

```python
from cv_generator import load_lang_map

load_lang_map(
    path: str | Path | None = None
) -> dict
```

**Returns:** Dictionary mapping terms to language translations.

**Example:**

```python
from cv_generator import load_lang_map

lang_map = load_lang_map("data/cvs/lang.json")
print(lang_map["Technical Skills"]["de"])  # "Technische Fähigkeiten"
```

## Validation Functions

### validate_cv_file

Validate a CV JSON file against the schema.

```python
from cv_generator import validate_cv_file, ValidationReport

validate_cv_file(
    path: str | Path,
    strict: bool = False
) -> ValidationReport
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | str/Path | Path to CV JSON file |
| `strict` | bool | Treat warnings as errors |

**Returns:** `ValidationReport` object with `is_valid`, `errors`, and `warnings`.

**Example:**

```python
from cv_generator import validate_cv_file

report = validate_cv_file("data/cvs/jane.json")
if report.is_valid:
    print("CV is valid!")
else:
    for issue in report.errors:
        print(f"Error: {issue.message}")
```

### validate_cv_json

Validate CV data dictionary.

```python
from cv_generator import validate_cv_json

validate_cv_json(
    data: dict,
    strict: bool = False
) -> ValidationReport
```

### run_ensure

Check consistency across language versions.

```python
from cv_generator import run_ensure, EnsureReport

run_ensure(
    name: str,
    input_dir: str = "data/cvs",
    langs: list[str] = ["en", "de", "fa"],
    lang_map_path: str | None = None
) -> EnsureReport
```

**Returns:** `EnsureReport` with `is_consistent`, `issues`, and `summary`.

**Example:**

```python
from cv_generator import run_ensure

report = run_ensure("jane", langs=["en", "de"])
if report.is_consistent:
    print("All language versions are consistent!")
else:
    for issue in report.issues:
        print(f"{issue.lang}: {issue.message}")
```

## Database Functions

### init_db

Initialize the SQLite database.

```python
from cv_generator import init_db

init_db(
    db_path: str = "data/db/cv.db",
    force: bool = False
) -> None
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `db_path` | str | Path to database file |
| `force` | bool | Recreate database if exists |

### import_cv

Import a single CV file into the database.

```python
from cv_generator import import_cv

import_cv(
    path: str | Path,
    db_path: str = "data/db/cv.db",
    overwrite: bool = False
) -> None
```

### import_all_cvs

Import all CV files into the database.

```python
from cv_generator import import_all_cvs

import_all_cvs(
    input_dir: str = "data/cvs",
    db_path: str = "data/db/cv.db",
    overwrite: bool = False
) -> None
```

### export_cv

Export a CV from the database to JSON.

```python
from cv_generator import export_cv

export_cv(
    name: str,
    lang: str = "en",
    db_path: str = "data/db/cv.db",
    output_dir: str = "output/json"
) -> Path
```

**Returns:** Path to the exported JSON file.

### export_all_cvs

Export all CVs from the database.

```python
from cv_generator import export_all_cvs

export_all_cvs(
    db_path: str = "data/db/cv.db",
    output_dir: str = "output/json"
) -> list[Path]
```

### list_persons

List all persons in the database.

```python
from cv_generator import list_persons

list_persons(
    db_path: str = "data/db/cv.db"
) -> list[dict]
```

**Returns:** List of person dictionaries with `id`, `name`, `languages`.

### list_tags

List all tags in the database.

```python
from cv_generator import list_tags

list_tags(
    db_path: str = "data/db/cv.db"
) -> list[dict]
```

**Returns:** List of tag dictionaries with `id`, `name`, `count`.

## Tag Management

### create_tag

Create a new tag.

```python
from cv_generator import create_tag

create_tag(
    name: str,
    description: str = "",
    db_path: str = "data/db/cv.db"
) -> int
```

**Returns:** ID of the created tag.

### update_tag

Update an existing tag.

```python
from cv_generator import update_tag

update_tag(
    tag_id: int,
    name: str | None = None,
    description: str | None = None,
    db_path: str = "data/db/cv.db"
) -> None
```

### delete_tag

Delete a tag.

```python
from cv_generator import delete_tag

delete_tag(
    tag_id: int,
    db_path: str = "data/db/cv.db"
) -> None
```

### update_entry_tags

Update tags for an entry.

```python
from cv_generator import update_entry_tags

update_entry_tags(
    entry_id: int,
    tag_ids: list[int],
    db_path: str = "data/db/cv.db"
) -> None
```

## v2 Export Engine

### CVExporter

Export engine for database-to-JSON conversion.

```python
from cv_generator import CVExporter

exporter = CVExporter(db_path="data/db/cv.db")

# Export single CV
result = exporter.export_cv("jane", "en")
print(result.path)

# Export all CVs
batch = exporter.export_all()
for result in batch.results:
    print(f"{result.name}: {result.path}")
```

### ExportVerifier

Verify export integrity.

```python
from cv_generator import ExportVerifier

verifier = ExportVerifier(db_path="data/db/cv.db")

# Verify round-trip
result = verifier.verify_roundtrip("data/cvs/jane.json")
if result.is_valid:
    print("Round-trip verification passed!")
else:
    print(f"Differences: {result.differences}")
```

## Template System

### create_jinja_env

Create a configured Jinja2 environment.

```python
from cv_generator import create_jinja_env

create_jinja_env(
    templates_dir: str = "templates"
) -> jinja2.Environment
```

**Returns:** Jinja2 environment with CV Generator configuration.

The environment includes:
- Custom delimiters (`<BLOCK>`, `<VAR>`, `/*/*/*`)
- `latex_escape` filter
- `file_exists`, `find_pic`, `get_pic` filters
- `debug`, `types` debug filters

**Example:**

```python
from cv_generator import create_jinja_env

env = create_jinja_env()
template = env.get_template("layout.tex")

rendered = template.render(
    basics=data["basics"],
    education=data["education"],
    # ...
)
```

## Plugin System

### register_hook

Register a hook function.

```python
from cv_generator import register_hook, HookType

@register_hook(HookType.PRE_RENDER)
def my_pre_render_hook(context):
    print(f"About to render: {context.name}")
```

### HookType

Available hook types:

| Hook | Description |
|------|-------------|
| `PRE_RENDER` | Before template rendering |
| `POST_RENDER` | After template rendering |
| `PRE_COMPILE` | Before LaTeX compilation |
| `POST_COMPILE` | After PDF generation |

### PluginManager

Manage plugins programmatically.

```python
from cv_generator import get_plugin_manager

pm = get_plugin_manager()
pm.load_plugin("my_plugin")
pm.list_plugins()
```

See [Plugin Development](plugins.md) for creating plugins.

## Section Registry

### register_section

Register a custom section handler.

```python
from cv_generator import register_section, GenericSectionAdapter

@register_section("awards")
class AwardsAdapter(GenericSectionAdapter):
    def get_entries(self, data):
        return data.get("awards", [])
```

### SectionRegistry

Access the section registry.

```python
from cv_generator import get_default_registry

registry = get_default_registry()
sections = registry.list_sections()
```

## Utility Functions

### get_repo_root

Get the repository root directory.

```python
from cv_generator import get_repo_root

root = get_repo_root()
print(root)  # /path/to/cv_generator
```

## Error Handling

CV Generator uses specific exception types:

```python
from cv_generator.errors import (
    CVGeneratorError,      # Base exception
    ValidationError,       # Invalid CV data
    TemplateError,         # Template rendering failed
    CompilationError,      # LaTeX compilation failed
    DatabaseError,         # Database operation failed
)
```

**Example:**

```python
from cv_generator import generate_cv, load_cv_json
from cv_generator.errors import CompilationError

try:
    data = load_cv_json("data/cvs/jane.json")
    generate_cv(data, "jane")
except CompilationError as e:
    print(f"LaTeX failed: {e}")
```

## Complete Example

```python
"""Generate academic CVs for all team members."""

from cv_generator import (
    discover_cv_files,
    load_cv_json,
    generate_cv,
    validate_cv_file,
)

def main():
    # Find all CV files
    files = discover_cv_files("data/cvs")
    
    for cv_file in files:
        # Validate first
        report = validate_cv_file(cv_file)
        if not report.is_valid:
            print(f"Skipping {cv_file.name}: validation failed")
            continue
        
        # Load and generate
        data = load_cv_json(cv_file)
        name = cv_file.stem  # "jane" from "jane.json"
        
        # Generate academic version
        generate_cv(
            cv_data=data,
            name=name,
            variant="academic",
            output_dir="output/academic"
        )
        
        print(f"Generated: {name}")

if __name__ == "__main__":
    main()
```

## Related Documentation

- [CLI Reference](cli.md) — Command-line interface
- [JSON Schema](json-schema.md) — CV data format
- [Plugins](plugins.md) — Extending CV Generator
- [Templates](templates.md) — Template customization
