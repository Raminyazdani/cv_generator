# CLI Reference

The `cvgen` command-line interface provides commands for generating CVs, validating data, and managing the database.

## Global Options

These options apply to all commands:

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Enable INFO level logging |
| `--debug` | Enable DEBUG level logging |
| `-q, --quiet` | Suppress output except errors |
| `--version` | Show version number |
| `-h, --help` | Show help message |

## Commands

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
