# SQLite Workflows Examples

Real-world examples of using the SQLite database and tagging features in CV Generator.

## Example 1: Basic Workflow

### Goal
Set up a new database, import your CV, browse it, and export.

### Commands

```bash
# Step 1: Initialize the database
cvgen db init
# Output: ✅ Database initialized: data/db/cv.db

# Step 2: Import your CV files
cvgen db import
# Output:
# 📥 Import Results:
#    Files processed: 1
#    Total entries: 65
#    ✅ ramin.json: 65 entries

# Step 3: Check database health
cvgen db doctor
# Output:
# 🏥 Database Health Check: data/db/cv.db
#    Status: ✅ Healthy
#
# 📊 Statistics:
#    Persons: 1
#    Entries: 65
#    Tags: 23
#    Tag Assignments: 150

# Step 4: Start the web UI to browse and tag
cvgen web tags
# Output: 🏷️  Tag Manager running at http://127.0.0.1:5000

# Step 5: After making changes, export with tags
cvgen db export --apply-tags --force
# Output:
# 📤 Export Results:
#    Files exported: 1
#    ✅ ramin.json
```

---

## Example 2: Multi-Language CV Workflow

### Goal
Manage CVs in multiple languages (English, German, Persian).

### Commands

```bash
# Import all language versions
cvgen db import -i data/cvs
# Output:
# 📥 Import Results:
#    Files processed: 3
#    Total entries: 195
#    ✅ ramin.json: 65 entries
#    ✅ ramin_de.json: 65 entries
#    ✅ ramin_fa.json: 65 entries

# List all persons in database
cvgen db list --what persons
# Output:
# 👥 Persons in database: 3
#    • ramin: 65 entries
#      Name: Ramin Yazdani
#    • ramin_de: 65 entries
#      Name: Ramin Yazdani
#    • ramin_fa: 65 entries
#      Name: رامین یزدانی

# Export only English version
cvgen db export --name ramin -o output/cvs --force
# Output:
# 📤 Export Results:
#    Files exported: 1
#    ✅ ramin.json
```

---

## Example 3: Creating Targeted CVs with Tags

### Goal
Create different CV versions using tags (Academic, Industry, Full CV).

### Step-by-Step

```bash
# 1. Start the web UI
cvgen web tags

# 2. In the browser:
#    - Navigate to http://127.0.0.1:5000
#    - Click on your person
#    - Go through each section (projects, experiences, etc.)
#    - Apply appropriate tags:
#      * "Academic" for research projects
#      * "Industry" for commercial work
#      * "Full CV" for everything

# 3. Export with tags
cvgen db export --apply-tags --force
```

### Expected JSON Output

```json
{
  "projects": [
    {
      "title": "Bioinformatics Pipeline",
      "type_key": ["Full CV", "Academic", "Bioinformatics"]
    },
    {
      "title": "E-commerce Platform",
      "type_key": ["Full CV", "Industry", "Programming"]
    }
  ]
}
```

---

## Example 4: Checking for Problems

### Goal
Identify and fix database issues.

### Commands

```bash
# Run health check
cvgen db doctor
# Output:
# 🏥 Database Health Check: data/db/cv.db
#    Status: ✅ Healthy
#
# 📊 Statistics:
#    Persons: 1
#    Entries: 65
#    Tags: 23
#    Tag Assignments: 150
#
# ⚠️  Issues (1):
#    • Found 2 unused tags: OldTag, DeprecatedTag
#
# 🔍 Checks:
#    ✅ Schema version: v1 (expected v1)
#    ✅ Orphaned entries: 0
#    ℹ️  Unused tags: 2
#    ✅ Duplicate tags: 0

# Get JSON output for scripting
cvgen db doctor --format json
# Output:
# {
#   "database": "data/db/cv.db",
#   "healthy": true,
#   "issues": ["Found 2 unused tags: OldTag, DeprecatedTag"],
#   "stats": {
#     "persons": 1,
#     "entries": 65,
#     "tags": 23,
#     "tag_assignments": 150
#   }
# }
```

---

## Example 5: Comparing JSON with Database

### Goal
Check if your JSON files are in sync with the database.

### Commands

```bash
# Compare all CVs
cvgen db diff
# Output:
# 🔍 Diff Results:
#    Files compared: 3
#    Matches: 2
#    Mismatches: 1
#    ✅ ramin.json: Match
#    ✅ ramin_de.json: Match
#    ❌ ramin_fa.json: 5 differences
#       - education[0].gpa: value_changed
#       - projects[2].description: value_changed
#       ... and 3 more

# Compare specific CV with JSON output
cvgen db diff --name ramin --format json
# Output: JSON with detailed difference information
```

---

## Example 6: Updating CV Content

### Goal
Update your CV content and sync with database.

### Workflow

```bash
# Option A: Edit JSON, then reimport
# 1. Edit data/cvs/ramin.json
# 2. Reimport with overwrite
cvgen db import --name ramin --overwrite
# The --overwrite flag:
# - Creates a backup of the database
# - Deletes existing entries for this person
# - Imports fresh from JSON

# Option B: Use Web UI for tag changes
# 1. Edit tags in web UI
cvgen web tags
# 2. Export changes back to JSON
cvgen db export --apply-tags --force
```

---

## Example 7: Starting Fresh

### Goal
Reset the database and start over.

### Commands

```bash
# Force recreate the database (WARNING: destroys all data!)
cvgen db init --force
# Output: ✅ Database initialized: data/db/cv.db

# Reimport all CVs
cvgen db import
# Output:
# 📥 Import Results:
#    Files processed: 3
#    Total entries: 195
```

---

## Example 8: Custom Database Location

### Goal
Use a different database file.

### Commands

```bash
# Initialize custom database
cvgen db init --db /path/to/my-cvs.db

# Import to custom database
cvgen db import --db /path/to/my-cvs.db -i /path/to/json-files

# Export from custom database
cvgen db export --db /path/to/my-cvs.db -o /path/to/output --force

# Start web UI with custom database
cvgen web tags --db /path/to/my-cvs.db

# Health check on custom database
cvgen db doctor --db /path/to/my-cvs.db
```

---

## Example 9: Scripting with JSON Output

### Goal
Use CV Generator in automation scripts.

### Bash Script Example

```bash
#!/bin/bash
set -e

DB_PATH="data/db/cv.db"
OUTPUT_DIR="output/generated"

# Initialize if needed
if [ ! -f "$DB_PATH" ]; then
    cvgen db init
fi

# Import latest CVs
cvgen db import --overwrite

# Check health
HEALTH=$(cvgen db doctor --format json)
HEALTHY=$(echo "$HEALTH" | python -c "import json,sys; print(json.load(sys.stdin)['healthy'])")

if [ "$HEALTHY" != "True" ]; then
    echo "Database has issues!"
    exit 1
fi

# Export with tags
mkdir -p "$OUTPUT_DIR"
cvgen db export -o "$OUTPUT_DIR" --apply-tags --force

echo "Export complete!"
```

### Python Script Example

```python
#!/usr/bin/env python3
import subprocess
import json

def run_cvgen(*args):
    """Run cvgen command and return output."""
    result = subprocess.run(
        ["cvgen"] + list(args),
        capture_output=True,
        text=True
    )
    return result.stdout, result.stderr, result.returncode

# Get database health as JSON
stdout, _, _ = run_cvgen("db", "doctor", "--format", "json")
health = json.loads(stdout)

print(f"Database: {health['database']}")
print(f"Healthy: {health['healthy']}")
print(f"Entries: {health['stats']['entries']}")
print(f"Tags: {health['stats']['tags']}")

if health['issues']:
    print("Issues found:")
    for issue in health['issues']:
        print(f"  - {issue}")
```

---

## Tips and Best Practices

### 1. Backup Before Major Changes

```bash
# Manual backup
cp data/db/cv.db data/db/cv.db.backup

# Or use --overwrite which creates automatic backups
cvgen db import --overwrite
# Creates: data/db/cv.backup.20240115_143022.db
```

### 2. Use --debug for Troubleshooting

```bash
# Enable verbose debug output
cvgen --debug db import

# Shows detailed logging about:
# - Which files are being processed
# - How identity keys are computed
# - Tag extraction and linking
```

### 3. Regular Health Checks

```bash
# Add to your workflow or CI
cvgen db doctor --format json | jq '.healthy'
```

### 4. Consistent Tag Naming

- Use Title Case: "Full CV", "Academic"
- Be consistent across languages
- Avoid duplicate tags with different cases
