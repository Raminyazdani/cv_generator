# CV Generator — Future Vision, Limitations & Roadmap

*A comprehensive engineering roadmap for the cv_generator project*

**Last Updated:** January 2026  
**Status:** Planning Document  
**Scope:** 6–12 month vision with phased implementation

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Map](#2-current-state-map-repository--workflow)
3. [Flaws, Drawbacks, Limitations](#3-flaws-drawbacks-limitations-with-severity)
4. [Missing Features Worth Adding](#4-missing-features-worth-adding-non-breaking)
5. [Roadmap — Phased Plan](#5-roadmap-best-order--phased-plan)
6. [Architecture Proposals](#6-architecture-proposals-additive-non-breaking)
7. [Testing Strategy](#7-testing-strategy-future-proof)
8. [Documentation Strategy](#8-documentation-strategy)
9. [Risk Register & Mitigations](#9-risk-register--mitigations)
10. [Backlog Appendix](#10-backlog-appendix)

---

## 1. Executive Summary

### What This Project Is Today

CV Generator is a Python-based tool that transforms structured JSON CV data into beautiful PDF resumes using:
- **Jinja2 templates** for section-based LaTeX generation
- **Awesome-CV LaTeX class** for professional formatting
- **XeLaTeX** for PDF compilation with Unicode/RTL support
- **Flask web UI** for tag management (SQLite-backed)
- **Multi-language support** (English, German, Persian)

**Current strengths:**
- Well-structured `src/cv_generator/` package with clear module boundaries
- Robust CLI (`cvgen`) with build, ensure, db, and web commands
- SQLite tagging system for flexible entry categorization
- ArtifactPaths class for predictable output structure
- 929 tests covering core functionality

### What "Excellent" Looks Like in 6–12 Months

1. **Zero-friction onboarding**: `pip install cv-generator && cvgen quickstart` creates a working CV in minutes
2. **Bulletproof reproducibility**: Same input → identical output on any platform, any time
3. **Full validation pipeline**: JSON schema enforcement, missing field warnings, template safety checks
4. **Plugin architecture**: Custom sections, exporters, and validators without modifying core
5. **CI/CD ready**: GitHub Actions workflows for automated testing and releases
6. **Professional documentation**: MkDocs site with tutorials, API reference, and troubleshooting

### Core Principles

1. **Correctness First** — Round-trip integrity, no data loss, deterministic output
2. **Backward Compatibility** — Base JSON schema is locked; extensions are additive
3. **Extensibility** — Plugin hooks for custom sections, exporters, validators
4. **Developer Experience** — Clear errors, verbose logging, self-documenting CLI
5. **Cross-Platform** — Windows, macOS, Linux with consistent behavior

---

## 2. Current State Map (Repository & Workflow)

### Repository Tree Overview

```
cv_generator/
├── src/cv_generator/          # Main package
│   ├── cli.py                 # CLI entrypoint (cvgen)
│   ├── generator.py           # Orchestration: JSON → LaTeX → PDF
│   ├── db.py                  # SQLite storage + tagging engine
│   ├── web.py                 # Flask UI for tag management
│   ├── ensure.py              # Multi-language consistency checker
│   ├── jinja_env.py           # Jinja2 configuration + LaTeX escaping
│   ├── latex.py               # XeLaTeX compilation
│   ├── io.py                  # JSON loading + discovery
│   ├── paths.py               # ArtifactPaths + path resolution
│   ├── cleanup.py             # Windows-safe directory removal
│   ├── errors.py              # Exception hierarchy + exit codes
│   ├── lang_engine/           # Translation key mapping
│   └── templates/             # Web UI Jinja2 templates
├── templates/                 # LaTeX section templates
├── data/
│   ├── cvs/                   # Source JSON files
│   ├── pics/                  # Profile photos
│   └── assets/                # Logos and other assets
├── tests/
│   ├── fixtures/              # Test data (ramin/, mismatch/)
│   └── test_*.py              # Test modules
├── docs/                      # Documentation (markdown)
├── examples/                  # Workflow examples
├── generate_cv.py             # Legacy entry point
├── awesome-cv.cls             # LaTeX class file
├── pyproject.toml             # Package configuration
└── mkdocs.yml                 # Documentation config
```

### Current Entrypoints

| Entrypoint | Description | Status |
|------------|-------------|--------|
| `cvgen build` | Generate PDFs from JSON | ✅ Stable |
| `cvgen ensure` | Validate multi-language consistency | ✅ Stable |
| `cvgen db init/import/export` | SQLite operations | ✅ New |
| `cvgen db doctor` | Database health check | ✅ New |
| `cvgen web tags` | Flask tag manager UI | ✅ New |
| `generate_cv.py` | Legacy script | ⚠️ Deprecated |

### Data Flow

```
┌─────────────┐    ┌──────────────┐    ┌────────────┐    ┌─────────┐
│ JSON CV     │───▶│ Validation   │───▶│ Jinja2     │───▶│ LaTeX   │
│ (data/cvs/) │    │ (io.py)      │    │ Templates  │    │ (.tex)  │
└─────────────┘    └──────────────┘    └────────────┘    └────┬────┘
                                                              │
                   ┌──────────────┐    ┌────────────┐    ┌────▼────┐
                   │ SQLite DB    │◀──▶│ Web UI     │    │ XeLaTeX │
                   │ (db.py)      │    │ (web.py)   │    │ Compile │
                   └──────────────┘    └────────────┘    └────┬────┘
                                                              │
                                                         ┌────▼────┐
                                                         │ PDF     │
                                                         │ Output  │
                                                         └─────────┘
```

### Multi-Language Behavior

- **Source files**: `ramin.json` (English), `ramin_de.json` (German), `ramin_fa.json` (Persian)
- **Translation engine**: `lang_engine/translate_cv_keys.py` maps keys between languages
- **RTL support**: Persian/Arabic detected via `RTL_LANGUAGES` in `jinja_env.py`
- **`ensure` command**: Validates structural consistency across language variants

### Output Structure (via ArtifactPaths)

```
output/
├── pdf/<profile>/<lang>/cv.pdf
├── latex/<profile>/<lang>/
│   ├── main.tex
│   ├── sections/*.tex
│   └── build/
├── json/<profile>/<lang>/cv.json
└── logs/run_<datetime>.log
```

---

## 3. Flaws, Drawbacks, Limitations (With Severity)

| # | Problem | Severity | Evidence | Impact | Fix Direction |
|---|---------|----------|----------|--------|---------------|
| 1 | **No JSON Schema validation** | High | `io.py:validate_cv_data()` only checks for `basics` key | Silent failures, invalid data passes through | Add jsonschema with strict mode |
| 2 | **Legacy `generate_cv.py` still exists** | Medium | Root-level script duplicates CLI functionality | User confusion, maintenance burden | Deprecation warning → remove in v2.0 |
| 3 | **No dependency pinning** | Medium | `pyproject.toml` has loose versions (`>=3.0.0`) | Non-reproducible builds across environments | Add `requirements-lock.txt` or use PDM/Poetry |
| 4 | **Missing CI/CD pipeline** | High | No `.github/workflows/` directory | No automated testing, manual releases | Add GitHub Actions for test/lint/release |
| 5 | **Incomplete LaTeX escaping** | Medium | `jinja_env.py:latex_escape()` missing newlines, quotes | Template injection, compile failures | Extend escape function, add tests |
| 6 | **No config file support** | Medium | All settings via CLI flags | Repetitive commands, no project defaults | Add `cv_generator.toml` support |
| 7 | **Windows path issues** | Low | `cleanup.py` has Windows-specific code, but not fully tested | Potential failures on Windows | Add Windows CI runner, path normalization |
| 8 | **Inconsistent logging** | Medium | Mixed use of `print()` and `logger.*` | Hard to filter output, no log levels in some modules | Audit and standardize |
| 9 | **No encoding declaration in templates** | Low | LaTeX templates assume UTF-8 | Persian/special chars may fail without XeLaTeX | Add `\usepackage{fontspec}` checks |
| 10 | **Test fixtures incomplete** | Medium | `tests/fixtures/` has limited samples | Edge cases untested | Add more diverse fixtures |
| 11 | **No snapshot testing** | Medium | No LaTeX output comparison | Regressions go unnoticed | Add hash-based or diff-based snapshots |
| 12 | **`ensure` lacks auto-fix** | Low | Only reports issues, no repair mode | Manual intervention required | Add `--fix` mode for common issues |
| 13 | **No plugin system** | High | Hard-coded section list in `generator.py` | Adding sections requires code changes | Registry pattern + plugin hooks |
| 14 | **Web UI lacks authentication** | Low | Local-only, but no auth | Security risk if exposed | Add optional basic auth |
| 15 | **No rate limiting on web exports** | Low | Export can overwrite files rapidly | Accidental data loss | Throttle or confirmation step |
| 16 | **Missing `--dry-run` for db operations** | Medium | No preview before import/export | Risk of unintended changes | Add dry-run mode |
| 17 | **Skills section nesting is fragile** | Medium | `category → subcategory → list` structure hard-coded | Adding new skill categories risky | Abstract into section adapters |
| 18 | **No metrics/telemetry** | Low | No insight into usage patterns | Can't prioritize features | Optional anonymous usage stats |
| 19 | **Hardcoded section names** | High | Templates reference `education`, `projects` directly | Extending requires template edits | Dynamic section discovery |
| 20 | **No `cvgen doctor` for full system health** | Medium | Only `db doctor` exists | General issues undetected | Add comprehensive health check |

---

## 4. Missing Features Worth Adding (Non-breaking)

### 4.1 Validation & Linting

| Feature | Description | Effort |
|---------|-------------|--------|
| JSON Schema validation | Strict mode with detailed errors | M |
| Schema versioning | Track JSON format version in files | S |
| `cvgen lint` command | Check for common issues, suggest fixes | M |
| Required field warnings | Non-fatal alerts for missing fields | S |

### 4.2 Doctor & Diagnostics

| Feature | Description | Effort |
|---------|-------------|--------|
| `cvgen doctor` | Full system health check (LaTeX installed, templates valid, etc.) | M |
| Build report | Post-generation summary (pages, warnings, timing) | S |
| Diff output | Compare current vs. previous generation | M |
| Template syntax check | Validate Jinja2 templates without rendering | S |

### 4.3 Profile & Variant Management

| Feature | Description | Effort |
|---------|-------------|--------|
| Profile switching | `cvgen profile use ramin` | S |
| CV variants | `--variant academic|industry|onepage` | M |
| Metadata sidecar | `cv.meta.json` for tags, notes, history | S |

### 4.4 Additional Export Formats

| Feature | Description | Effort |
|---------|-------------|--------|
| HTML preview | Quick preview without LaTeX | M |
| Markdown export | Plain text version for copy/paste | S |
| DOCX export (optional) | Via Pandoc, for HR systems | L |

### 4.5 Performance & Caching

| Feature | Description | Effort |
|---------|-------------|--------|
| Incremental builds | Only regenerate changed sections | L |
| Template caching | Precompile Jinja2 templates | S |
| Parallel compilation | Build multiple CVs concurrently | M |

### 4.6 Asset Management

| Feature | Description | Effort |
|---------|-------------|--------|
| Image optimization | Auto-resize photos for PDF | S |
| Asset validation | Check for missing images before build | S |
| Logo library | Centralized institution logos | M |

### 4.7 Developer Experience

| Feature | Description | Effort |
|---------|-------------|--------|
| `cvgen init` | Project scaffolding wizard | M |
| Watch mode | Auto-rebuild on file changes | M |
| Template preview | Render single section for debugging | S |
| VSCode extension | Snippets, validation, preview | L |

---

## 5. Roadmap (Best Order) — Phased Plan

### Phase 1: Foundation Hardening (Weeks 1–4)

**Goals:**
- Establish CI/CD pipeline
- Lock dependencies
- Add comprehensive JSON validation
- Standardize logging

**Tasks:**
- [ ] Create `.github/workflows/ci.yml` with test/lint/coverage
- [ ] Add `requirements-lock.txt` or switch to Poetry/PDM
- [ ] Implement JSON Schema validation in `io.py`
- [ ] Create `schemas/cv.schema.json` with all required fields
- [ ] Audit all modules for logging consistency
- [ ] Remove direct `print()` calls, use `logger.*`
- [ ] Add `--quiet`, `--verbose`, `--debug` to all commands

**Deliverables:**
- `schemas/cv.schema.json`
- `.github/workflows/ci.yml`
- Updated `io.py` with schema validation

**Risks:**
- Schema too strict may break existing CVs → Use lenient mode initially

**Tests Required:**
- Schema validation tests
- CI pipeline green on all platforms

**Acceptance Criteria:**
- All PRs run automated tests
- JSON with missing required fields raises ValidationError
- Logging output consistent across all commands

**Rollout Strategy:**
- Schema validation in warning mode first
- Promote to strict mode in v1.1

---

### Phase 2: Developer Experience (Weeks 5–8)

**Goals:**
- Add config file support
- Implement comprehensive `cvgen doctor`
- Create project scaffolding

**Tasks:**
- [ ] Design config schema (`cv_generator.toml`)
- [ ] Implement config loading in `cli.py`
- [ ] Add `cvgen doctor` command:
  - [ ] Check LaTeX installation
  - [ ] Validate templates
  - [ ] Check image paths
  - [ ] Verify DB health
- [ ] Add `cvgen init` for project scaffolding
- [ ] Add `cvgen lint` for JSON linting
- [ ] Implement `--dry-run` for db operations

**Deliverables:**
- `src/cv_generator/config.py`
- `cvgen doctor` command
- `cvgen init` command
- Sample `cv_generator.toml`

**Risks:**
- Config precedence complexity → Document clearly

**Tests Required:**
- Config loading with various precedence scenarios
- Doctor checks for each subsystem
- Init creates valid project structure

**Acceptance Criteria:**
- `cvgen doctor` reports all issues found
- `cvgen init` creates working project
- Config file overrides CLI defaults

**Rollout Strategy:**
- Config support optional
- Doctor command available immediately

---

### Phase 3: Plugin Architecture (Weeks 9–12)

**Goals:**
- Abstract section handling into registry
- Enable custom sections without code changes
- Add plugin hooks for extensibility

**Tasks:**
- [ ] Create `src/cv_generator/registry.py`
- [ ] Define `SectionAdapter` protocol
- [ ] Migrate existing sections to adapters
- [ ] Add plugin discovery mechanism
- [ ] Implement hook system:
  - [ ] `pre_validate`
  - [ ] `post_render`
  - [ ] `pre_compile`
  - [ ] `post_export`
- [ ] Document plugin development

**Deliverables:**
- `src/cv_generator/registry.py`
- `src/cv_generator/adapters/` directory
- Plugin developer guide

**Risks:**
- Over-engineering → Start minimal, extend as needed

**Tests Required:**
- Custom section registration
- Hook execution order
- Plugin isolation (one bad plugin doesn't break others)

**Acceptance Criteria:**
- New section added via config only
- Hooks fire at correct points
- Example plugin works

**Rollout Strategy:**
- Internal refactor first
- Plugin API in v1.2

---

### Phase 4: Alternative Exports (Weeks 13–16)

**Goals:**
- Add HTML preview
- Add Markdown export
- Optional DOCX via Pandoc

**Tasks:**
- [ ] Create `src/cv_generator/exporters/` module
- [ ] Implement `HtmlExporter`
- [ ] Implement `MarkdownExporter`
- [ ] Add Pandoc integration (optional dependency)
- [ ] Add `cvgen export --format html|md|docx`
- [ ] Create export templates

**Deliverables:**
- `src/cv_generator/exporters/`
- HTML/Markdown export templates
- `cvgen export` command

**Risks:**
- Format fidelity issues → Mark as "preview" quality

**Tests Required:**
- Round-trip: JSON → HTML → visual check
- Markdown readability
- DOCX opens in Word/LibreOffice

**Acceptance Criteria:**
- HTML renders in browser
- Markdown readable in GitHub
- DOCX opens without errors

**Rollout Strategy:**
- HTML/Markdown in v1.3
- DOCX marked experimental

---

### Phase 5: Performance & Polish (Weeks 17–20)

**Goals:**
- Incremental builds
- Watch mode
- Template caching

**Tasks:**
- [ ] Implement content hashing for sections
- [ ] Skip unchanged sections during rebuild
- [ ] Add `cvgen build --watch` mode
- [ ] Precompile Jinja2 templates
- [ ] Add build timing metrics
- [ ] Parallel CV compilation (optional)

**Deliverables:**
- Incremental build support
- Watch mode
- Performance improvements

**Risks:**
- Cache invalidation bugs → Hash all inputs

**Tests Required:**
- Incremental build correctness
- Watch mode detects changes
- Cached builds match full builds

**Acceptance Criteria:**
- Incremental builds 50% faster
- Watch mode updates within 2 seconds
- No cache-related bugs

**Rollout Strategy:**
- Opt-in via `--incremental`
- Default in v2.0

---

### Phase 6: Documentation & Polish (Weeks 21–24)

**Goals:**
- Complete documentation overhaul
- MkDocs site deployment
- Contributor guide
- Video tutorials (optional)

**Tasks:**
- [ ] Restructure `docs/` for MkDocs
- [ ] Write comprehensive tutorials
- [ ] Add API reference (autogenerated)
- [ ] Create troubleshooting guide
- [ ] Write contributor guide
- [ ] Add changelog strategy
- [ ] Deploy to GitHub Pages

**Deliverables:**
- Complete MkDocs documentation
- GitHub Pages deployment
- Contributor guide
- CHANGELOG.md

**Risks:**
- Documentation drift → Automate where possible

**Tests Required:**
- MkDocs builds without errors
- All code examples work
- Links not broken

**Acceptance Criteria:**
- New users can follow quickstart
- All commands documented
- Contributor guide enables PRs

**Rollout Strategy:**
- Continuous updates
- Major version includes doc review

---

## 6. Architecture Proposals (Additive, Non-breaking)

### 6.1 Layered Architecture

```
┌─────────────────────────────────────────────────┐
│                    CLI Layer                     │
│            (cli.py, argparse commands)           │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│                   Core Library                   │
│  generator.py, db.py, io.py, ensure.py, etc.    │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│                  Adapters Layer                  │
│   Section adapters, exporters, validators       │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│                   Plugin Hooks                   │
│  pre_validate, post_render, pre_compile, etc.   │
└─────────────────────────────────────────────────┘
```

### 6.2 Section Registry Pattern

```python
# src/cv_generator/registry.py
from typing import Protocol, Dict, Any

class SectionAdapter(Protocol):
    """Protocol for section handlers."""
    
    section_name: str
    template_file: str
    
    def validate(self, data: Dict[str, Any]) -> list[str]:
        """Validate section data, return list of errors."""
        ...
    
    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data before rendering."""
        ...

class SectionRegistry:
    """Central registry for section adapters."""
    
    _adapters: Dict[str, SectionAdapter] = {}
    
    @classmethod
    def register(cls, adapter: SectionAdapter) -> None:
        cls._adapters[adapter.section_name] = adapter
    
    @classmethod
    def get(cls, name: str) -> SectionAdapter:
        return cls._adapters[name]
```

### 6.3 Configuration Model

```toml
# cv_generator.toml
[project]
name = "ramin"
default_lang = "en"
variants = ["full", "academic", "onepage"]

[paths]
cvs = "data/cvs"
templates = "templates"
output = "output"
db = "data/db/cv.db"

[build]
latex_engine = "xelatex"
incremental = true
parallel = false

[export]
apply_tags = true
force = false

[logging]
level = "info"
file = "output/logs/cv_generator.log"
```

### 6.4 Structured Logging

```python
# src/cv_generator/logging_config.py
import structlog

def configure_logging(level: str = "INFO"):
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### 6.5 Plugin Hook System

```python
# src/cv_generator/hooks.py
from typing import Callable, Dict, Any, List

class HookManager:
    """Manages plugin hooks."""
    
    _hooks: Dict[str, List[Callable]] = {
        "pre_validate": [],
        "post_render": [],
        "pre_compile": [],
        "post_export": [],
    }
    
    @classmethod
    def register(cls, hook_name: str, callback: Callable) -> None:
        if hook_name in cls._hooks:
            cls._hooks[hook_name].append(callback)
    
    @classmethod
    def fire(cls, hook_name: str, **kwargs) -> None:
        for callback in cls._hooks.get(hook_name, []):
            callback(**kwargs)
```

---

## 7. Testing Strategy (Future-Proof)

### 7.1 Test Categories

| Category | Purpose | Location |
|----------|---------|----------|
| Unit | Individual function testing | `tests/test_*.py` |
| Integration | Cross-module workflows | `tests/integration/` |
| Snapshot | LaTeX output comparison | `tests/snapshots/` |
| E2E | Full CLI command testing | `tests/e2e/` |

### 7.2 Fixture Strategy

```
tests/fixtures/
├── valid/
│   ├── minimal.json         # Bare minimum valid CV
│   ├── complete.json        # All fields populated
│   ├── multilang/           # en, de, fa variants
│   └── edge_cases/
│       ├── unicode.json     # Persian, special chars
│       ├── empty_lists.json # Empty sections
│       └── long_content.json
├── invalid/
│   ├── missing_basics.json
│   ├── invalid_dates.json
│   └── bad_encoding.json
└── snapshots/
    └── expected/
        ├── minimal.tex
        └── complete.tex
```

### 7.3 Snapshot Testing

```python
# tests/conftest.py
import hashlib

def assert_snapshot(actual: str, snapshot_path: Path):
    """Compare output against stored snapshot."""
    if not snapshot_path.exists():
        snapshot_path.write_text(actual)
        pytest.skip("Snapshot created")
    
    expected = snapshot_path.read_text()
    if actual != expected:
        diff = unified_diff(expected.splitlines(), actual.splitlines())
        pytest.fail(f"Snapshot mismatch:\n" + "\n".join(diff))
```

### 7.4 CI Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python: ["3.9", "3.10", "3.11", "3.12"]
    
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      
      - name: Install dependencies
        run: pip install -e ".[dev]"
      
      - name: Run tests
        run: pytest --cov=cv_generator --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install ruff mypy
      - run: ruff check src/
      - run: mypy src/cv_generator/
```

### 7.5 Test Coverage Goals

| Module | Current | Target |
|--------|---------|--------|
| cli.py | 70% | 90% |
| generator.py | 60% | 85% |
| db.py | 80% | 90% |
| ensure.py | 75% | 90% |
| io.py | 65% | 85% |
| jinja_env.py | 50% | 80% |

---

## 8. Documentation Strategy

### 8.1 README Structure

```markdown
# CV Generator

One-line description.

## Quick Start (5 lines to first PDF)

## Features

## Installation

## Usage
- Basic usage
- Multi-language
- Tags and variants

## Documentation (link to MkDocs)

## Contributing

## License
```

### 8.2 MkDocs Structure

```
docs/
├── index.md              # Overview + quick start
├── installation.md       # Installation guide
├── quickstart.md         # First PDF in 5 minutes
├── guides/
│   ├── json-format.md    # CV JSON structure
│   ├── templates.md      # Template customization
│   ├── languages.md      # Multi-language setup
│   ├── tagging.md        # Tag management
│   └── exporting.md      # Export options
├── reference/
│   ├── cli.md            # CLI command reference
│   ├── config.md         # Configuration options
│   └── api.md            # Python API (autogen)
├── tutorials/
│   ├── create-cv.md      # Creating your first CV
│   ├── add-section.md    # Adding custom sections
│   └── deploy-pdf.md     # CI/CD for PDFs
├── cookbook/
│   ├── sqlite_tagging_cookbook.md
│   └── workflows.md
├── troubleshooting.md
├── contributing.md
└── changelog.md
```

### 8.3 CLI Help Design

```
cvgen --help

CV Generator - Create beautiful PDF CVs from JSON

Usage: cvgen <command> [options]

Commands:
  build     Generate PDF CVs from JSON files
  ensure    Validate multi-language CV consistency
  db        Database operations (init, import, export)
  web       Start the tag manager web interface
  doctor    Check system health and configuration
  lint      Validate JSON files against schema
  init      Create a new CV project

Global Options:
  -v, --verbose    Enable detailed output
  -q, --quiet      Suppress non-error output
  --debug          Enable debug logging
  --version        Show version and exit
  --help           Show this message

Examples:
  cvgen build                    Build all CVs
  cvgen build --name ramin       Build specific person
  cvgen ensure                   Check consistency
  cvgen web tags                 Start tag manager

Documentation: https://cv-generator.readthedocs.io
```

### 8.4 Versioning Strategy

- **MAJOR**: Breaking changes to JSON schema or CLI interface
- **MINOR**: New features, non-breaking additions
- **PATCH**: Bug fixes, documentation updates

---

## 9. Risk Register & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Data loss from cleanup routines** | Medium | High | Add `--backup` flag, confirmation prompts |
| **Encoding issues (Persian RTL)** | Medium | Medium | Explicit UTF-8 handling, XeLaTeX enforcement |
| **Template injection** | Low | High | Escape all user content, review escape function |
| **Inconsistent translations** | Medium | Medium | `ensure` command with `--strict` mode |
| **Backward compatibility breaks** | Medium | High | Deprecation warnings, migration guides |
| **Windows path issues** | Medium | Medium | Add Windows CI, use pathlib everywhere |
| **Dependency conflicts** | Medium | Low | Lock dependencies, test in isolation |
| **Over-engineering plugins** | Medium | Low | Start minimal, YAGNI principle |
| **Documentation drift** | High | Medium | Automate docs from code, doc tests |
| **LaTeX installation missing** | High | Medium | `doctor` command, clear error messages |

---

## 10. Backlog Appendix

### High Priority (Next 3 months)

| Item | Effort | Value | Prerequisites |
|------|--------|-------|---------------|
| JSON Schema validation | M | High | Schema definition |
| GitHub Actions CI | S | High | None |
| `cvgen doctor` command | M | High | None |
| Config file support | M | Medium | Config schema |
| Dependency locking | S | Medium | None |
| Remove legacy `generate_cv.py` | S | Low | Deprecation notice |

### Medium Priority (3–6 months)

| Item | Effort | Value | Prerequisites |
|------|--------|-------|---------------|
| HTML export | M | Medium | Exporter framework |
| Plugin hooks | L | Medium | Registry pattern |
| Watch mode | M | Medium | File watcher |
| Incremental builds | L | Medium | Content hashing |
| Template preview | S | Medium | None |
| Markdown export | S | Low | Exporter framework |

### Low Priority (6–12 months)

| Item | Effort | Value | Prerequisites |
|------|--------|-------|---------------|
| DOCX export | L | Low | Pandoc integration |
| VSCode extension | L | Low | Stable API |
| Parallel compilation | M | Low | Thread safety |
| Telemetry (opt-in) | M | Low | Privacy policy |
| GUI application | L | Low | Web UI polish |
| Cloud sync | L | Low | API design |

### Continuous Improvement

| Item | Effort | Value | Prerequisites |
|------|--------|-------|---------------|
| Test coverage improvement | Ongoing | High | None |
| Documentation updates | Ongoing | Medium | None |
| Error message improvements | Ongoing | Medium | User feedback |
| Performance optimization | Ongoing | Low | Profiling data |

---

## Appendix: Quick Reference

### Key Files to Modify

| Task | Primary Files |
|------|---------------|
| Add CLI command | `src/cv_generator/cli.py` |
| Add new section | `templates/<section>.tex`, `src/cv_generator/generator.py` |
| Modify validation | `src/cv_generator/io.py` |
| Add export format | `src/cv_generator/exporters/` (new) |
| Change output paths | `src/cv_generator/paths.py` |
| Add web route | `src/cv_generator/web.py` |

### Testing Commands

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=cv_generator --cov-report=html

# Run specific test file
pytest tests/test_generator.py -v

# Run tests matching pattern
pytest -k "test_export" -v
```

### Development Workflow

```bash
# Setup
pip install -e ".[dev]"

# Make changes
# ... edit files ...

# Test
pytest tests/ -v

# Lint
ruff check src/
mypy src/cv_generator/

# Build docs
mkdocs serve

# Commit
git commit -m "feat: add feature X"
```

---

*Document generated as part of the cv_generator roadmap planning initiative.*
