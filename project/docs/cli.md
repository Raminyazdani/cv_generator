# CLI Reference

The `cvgen` command-line interface provides commands for generating CVs, validating data, and managing the database.

## Global Options

These options apply to all commands:

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Enable INFO level logging |
| `--debug` | Enable DEBUG level logging |
| `-q, --quiet` | Show only error messages |
| `--version` | Show version number |
| `-h, --help` | Show help message |

## Commands

### init

Create a new CV project with a minimal working structure.

```bash
cvgen init <path> [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `<path>` | Directory where the project will be created |

**Options:**

| Option | Description |
|--------|-------------|
| `-p, --profile NAME` | Name for your CV profile (default: mycv) |
| `-l, --lang LANG` | Language code: en, de, or fa (default: en) |
| `-f, --force` | Overwrite existing files if directory is not empty |

**Examples:**

```bash
# Create a new project
cvgen init ./my-cv --profile jane

# Create a German CV project
cvgen init ./german-cv --profile hans --lang de

# Overwrite an existing project
cvgen init ./my-cv --force
```

**Generated Structure:**

```
<path>/
├── cvs/
│   └── <profile>.<lang>.json    # Your CV data (edit this!)
├── output/                       # Build output directory
├── cv_generator.toml             # Configuration file
├── README.md                     # Next steps documentation
└── .gitignore                    # Git ignore rules
```

### build

Generate PDF CVs from JSON files.

```bash
cvgen build [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-n, --name NAME` | Build only CVs matching this base name |
| `-i, --input-dir DIR` | Input directory (default: data/cvs) |
| `-o, --output-dir DIR` | Output directory (default: output) |
| `-t, --templates-dir DIR` | Templates directory (default: templates) |
| `-k, --keep-latex` | Keep LaTeX sources after compilation |
| `-d, --dry-run` | Render LaTeX without PDF compilation |
| `-V, --variant VARIANT` | Filter entries by variant/type_key (e.g., 'academic', 'industry') |
| `--incremental` | Enable incremental builds (skip unchanged CVs based on input hashing) |
| `--no-incremental` | Force full rebuild, ignoring cache |
| `-w, --watch` | Watch for file changes and rebuild automatically |

**Examples:**

```bash
# Generate all CVs
cvgen build

# Generate only ramin's CV
cvgen build --name ramin

# Verbose dry run
cvgen -v build --dry-run

# Keep LaTeX files for debugging
cvgen build --keep-latex

# Build academic variant only
cvgen build --name ramin --variant academic

# Watch for changes
cvgen build --watch
```

### ensure

Validate multilingual CV JSON consistency.

```bash
cvgen ensure --name NAME [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-n, --name NAME` | Person's name (required) |
| `-l, --langs LANGS` | Comma-separated languages (default: en,de,fa) |
| `-f, --format FMT` | Output format: text or json |
| `-i, --input-dir DIR` | Input directory |
| `-D, --dir DIR` | Directory containing CV files |
| `--path-en PATH` | Explicit path to English CV |
| `--path-de PATH` | Explicit path to German CV |
| `--path-fa PATH` | Explicit path to Persian CV |
| `--lang-map PATH` | Path to language mapping file |
| `--fail-fast` | Stop at first batch of errors |
| `--max-errors N` | Maximum errors before stopping |

**Examples:**

```bash
# Check ramin's CV consistency
cvgen ensure --name ramin

# Check only English and German
cvgen ensure --name ramin --langs en,de

# Output as JSON
cvgen ensure --name ramin --format json
```

**Exit Codes:**

- `0` — All languages consistent
- `2` — Mismatches found

### db

SQLite database operations for CV data management.

#### db init

Initialize the database.

```bash
cvgen db init [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--db PATH` | Database file path (default: data/db/cv.db) |
| `--force` | Recreate database if exists |

#### db import

Import CV JSON files into database.

```bash
cvgen db import [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--db PATH` | Database file path |
| `-i, --input-dir DIR` | Input directory |
| `-n, --name NAME` | Import only matching CVs |
| `--overwrite` | Replace existing entries |
| `--no-backup` | Don't backup before overwrite |

#### db export

Export database to JSON files.

```bash
cvgen db export [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--db PATH` | Database file path |
| `-o, --output-dir DIR` | Output directory |
| `-n, --name NAME` | Export only matching CVs |
| `-f, --format FMT` | Output format: pretty or min |

#### db diff

Compare JSON files with database.

```bash
cvgen db diff [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--db PATH` | Database file path |
| `-i, --input-dir DIR` | Input directory |
| `-n, --name NAME` | Compare only matching CVs |
| `-f, --format FMT` | Output format: text or json |

#### db list

List database contents.

```bash
cvgen db list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--db PATH` | Database file path |
| `--what WHAT` | What to list: persons or tags |
| `-f, --format FMT` | Output format: text or json |

### web

Web UI for tag management.

#### web tags

Start the Tag Manager web UI.

```bash
cvgen web tags [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--db PATH` | Database file path |
| `--host HOST` | Host to bind (default: 127.0.0.1) |
| `--port PORT` | Port to listen on (default: 5000) |

### help

Show extended help for a topic.

```bash
cvgen help [TOPIC]
```

**Available Topics:**

| Topic | Description |
|-------|-------------|
| `build` | PDF generation details |
| `ensure` | Validation details |
| `languages` | Language support info |
| `templates` | Template customization |
| `json-schema` | CV data format |
| `troubleshooting` | Common issues |

**Examples:**

```bash
# List all topics
cvgen help

# Get help on build command
cvgen help build

# Get help on templates
cvgen help templates
```

### lint

Validate CV JSON files against schema.

```bash
cvgen lint [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-n, --name NAME` | Validate only CVs matching this base name |
| `-f, --file FILE` | Path to a specific CV JSON file to validate |
| `-i, --input-dir DIR` | Input directory (default: data/cvs) |
| `--strict` | Treat all schema issues as errors (fail on any issue) |
| `--format {text,json}` | Output format (default: text) |

**Examples:**

```bash
# Lint all CV files
cvgen lint

# Lint a specific profile
cvgen lint --name ramin

# Lint a specific file
cvgen lint --file path/to/cv.json

# Strict mode (fail on any issue)
cvgen lint --strict
```

### profile

Manage CV profile selection.

```bash
cvgen profile {list,use,clear}
```

**Subcommands:**

| Subcommand | Description |
|------------|-------------|
| `list` | List available profiles |
| `use NAME` | Set the current profile |
| `clear` | Clear the current profile |

**Examples:**

```bash
# List available profiles
cvgen profile list

# Set ramin as the default profile
cvgen profile use ramin

# Now 'cvgen build' uses ramin automatically
cvgen build

# Clear the profile selection
cvgen profile clear
```

### export

Export CVs to alternative formats (HTML, Markdown).

```bash
cvgen export [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-n, --name NAME` | Export only CVs matching this base name |
| `-l, --lang LANG` | Export only CVs with this language code |
| `-f, --format {html,md}` | Export format (default: html) |
| `-i, --input-dir DIR` | Input directory (default: data/cvs) |
| `-o, --output-dir DIR` | Output directory (default: output) |

**Examples:**

```bash
# Export all CVs to HTML
cvgen export

# Export a specific profile to Markdown
cvgen export --name ramin --format md

# Export only English CVs
cvgen export --lang en
```

### doctor

Run system health checks.

```bash
cvgen doctor [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-t, --templates-dir DIR` | Templates directory to check (default: templates) |
| `-o, --output-dir DIR` | Output directory to check (default: output) |
| `-f, --format {text,json}` | Output format (default: text) |

**Examples:**

```bash
# Run health checks
cvgen doctor

# JSON output for scripting
cvgen doctor --format json
```

**Checks Performed:**

- XeLaTeX installation and version
- Required fonts availability
- Templates directory structure
- Output directory permissions
- Python package dependencies

## Logging Levels

The CLI supports three logging levels:

| Flag | Level | Description |
|------|-------|-------------|
| (default) | WARNING | Warnings and errors only |
| `-v, --verbose` | INFO | Main steps and status |
| `--debug` | DEBUG | Detailed debug information |
| `-q, --quiet` | ERROR | Errors only |

**Example:**

```bash
# Verbose output shows progress
cvgen -v build

# Debug output for troubleshooting
cvgen --debug build

# Quiet mode for scripts
cvgen -q build
```

## Keeping Documentation in Sync

To ensure CLI documentation stays in sync with the actual implementation:

### Regenerating CLI Help

```bash
# View current help for any command
cvgen --help
cvgen build --help
cvgen db --help

# Capture help output for reference
cvgen --help > /tmp/cli-help.txt
```

### Verifying Documentation

When updating CLI options in the code:

1. Run `cvgen <command> --help` to see current options
2. Update `docs/cli.md` to match
3. Verify with `mkdocs build` to catch broken links

### CI Verification

The CI pipeline verifies documentation builds correctly:

```bash
mkdocs build --strict
```

This ensures all internal links are valid and the site builds without errors.
