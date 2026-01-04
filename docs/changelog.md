# Changelog

All notable changes to CV Generator are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024

### Added

- **CLI Interface**: Modern `cvgen` command with subcommands
  - `cvgen build` - Generate PDF CVs from JSON
  - `cvgen ensure` - Validate multilingual CV consistency
  - `cvgen lint` - Validate CV JSON files against schema
  - `cvgen profile` - Manage CV profile selection
  - `cvgen doctor` - Run system health checks
  - `cvgen export` - Export CVs to HTML or Markdown
  - `cvgen db` - SQLite database operations
  - `cvgen web tags` - Web UI for tag management
  - `cvgen help` - Extended help on topics

- **Multilingual Support**
  - English, German, and Persian (Farsi) with RTL support
  - Translation mapping for skill headings
  - `ensure` command for consistency validation

- **SQLite Database Layer**
  - Store CV data in queryable SQLite database
  - Tag entries with `type_key` for variant filtering
  - Round-trip import/export preserving all data
  - Web UI for browsing and editing tags

- **Variant Filtering**
  - Filter entries by `type_key` during build
  - Create targeted CV versions (academic, industry, etc.)

- **Plugin System**
  - Register custom section adapters
  - Hook into the CV generation pipeline
  - Extend functionality without modifying core code

- **Configuration File**
  - TOML configuration (`cv_generator.toml`)
  - Reduce repetitive CLI flags
  - Project-level defaults

- **Unified Output Structure**
  - All artifacts under `output/`
  - Organized by profile and language
  - PDFs at `output/pdf/<name>/<lang>/<name>_<lang>.pdf`

- **Documentation**
  - MkDocs-based documentation site
  - CLI reference, JSON schema, templates guide
  - SQLite tagging cookbook
  - Troubleshooting guide

### Changed

- Output directory structure unified under `output/`
- `--keep-intermediate` flag renamed to `--keep-latex`
- Improved Windows file cleanup with retry logic

### Deprecated

- `result/` directory no longer used (migrated to `output/latex/`)

---

## How to Update This Changelog

When making changes to CV Generator:

1. Add entries under `[Unreleased]` section
2. Categorize changes: Added, Changed, Deprecated, Removed, Fixed, Security
3. When releasing, rename `[Unreleased]` to the version number with date
4. Create a new `[Unreleased]` section at the top
