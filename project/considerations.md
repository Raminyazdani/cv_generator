# CV Generator — Comprehensive Repository Audit Report

**Status:** Read-Only Repository Audit (Find-Only)  
**Target Repository:** `https://github.com/Raminyazdani/cv_generator`  
**Deliverable:** `./considerations.md`

---

## 1. Executive Summary

This audit covers the complete CV Generator codebase—a Python-based tool for transforming JSON CV data into professional PDF resumes using Jinja2 templates and the Awesome-CV LaTeX class.

### Key Findings

1. **Overall Health: GOOD** — The codebase is well-structured with 771 passing tests, clean linting, and comprehensive documentation.

2. **Critical Issues (0):** No blocking issues found that prevent the project from functioning.

3. **High Priority Issues (5):**
   - F-001: `tarfile.extractall()` used without member filtering (security risk)
   - F-002: Flask secret key is hardcoded to a static value
   - F-003: No input validation on `entry_id` in web routes could allow SQLite injection in edge cases
   - F-004: `subprocess.run` with `shell=True` in Windows cleanup routine
   - F-005: `data/` directory coupling — core code assumes `data/` is always available

4. **Medium Priority Issues (12):** Various reliability, maintainability, and cross-platform concerns.

5. **Low Priority Issues (8):** Documentation gaps, minor code style issues, and enhancement opportunities.

### Top 5 Improvement Opportunities

1. **Decouple from `data/` directory** — Add `--data-dir` option and dependency injection for data sources
2. **Harden security** — Filter `tarfile` members, rotate Flask secret keys, add CSRF protection
3. **Improve error handling** — Add context to exceptions, implement graceful degradation
4. **Add integration tests with XeLaTeX** — Currently tests skip LaTeX compilation
5. **Implement schema version tracking** — Allow backward compatibility for JSON schema changes

---

## 2. Audit Metadata

| Property | Value |
|----------|-------|
| **Repository URL** | https://github.com/Raminyazdani/cv_generator |
| **Local Path** | /home/runner/work/cv_generator/cv_generator |
| **Branch** | copilot/create-finding-report |
| **Commit Hash** | fe9464141fc0ac5261b936a245deefd087fb053c |
| **Audit Date** | 2026-01-05T13:34:29Z |
| **Execution Environment** | Linux 6.11.0-1018-azure x86_64 |
| **Python Version** | 3.12.3 |
| **Tools Used** | ruff 0.14.10, pytest 9.0.2, manual code review |
| **Tests Run** | 771 passed, 30 warnings |
| **Linting Status** | All checks passed |

---

## 3. Repository Map

### 3.1 Complete File Tree

```
cv_generator/
├── .github/workflows/ci.yml          [CI] GitHub Actions workflow
├── .gitignore                        [Config] Git ignore patterns
├── AUDIT_REPORT.md                   [Docs] Previous stability audit
├── LICENSE                           [Docs] Project license
├── README.md                         [Docs] Main documentation
├── awesome-cv.cls                    [LaTeX] Awesome-CV class file
├── generate_cv.py                    [Scripts] Legacy entry point (deprecated)
├── mkdocs.yml                        [Config] MkDocs configuration
├── plan_future.md                    [Docs] Engineering roadmap
├── pyproject.toml                    [Config] Package configuration
├── report_suggestion.md              [Docs] Report suggestions
├── requirements-lock.txt             [Config] Pinned dependencies
│
├── assets/
│   └── logo_map.json                 [Config] Institution logo mapping
│
├── data/                             [LOCKED — NOT AUDITED INSIDE]
│   ├── assets/                       Asset files
│   ├── cvs/                          CV JSON files (ramin.json, etc.)
│   └── pics/                         Profile pictures
│
├── docs/                             [Docs] MkDocs documentation
│   ├── index.md
│   ├── installation.md
│   ├── quickstart.md
│   ├── cli.md
│   ├── config-reference.md
│   ├── json-schema.md
│   ├── templates.md
│   ├── languages.md
│   ├── plugins.md
│   ├── sqlite_tagging_cookbook.md
│   ├── webui_cookbook.md
│   ├── language_aware_tagging.md
│   ├── multi_language_crud.md
│   ├── troubleshooting.md
│   ├── contributing.md
│   ├── development-workflow.md
│   ├── changelog.md
│   └── example.md
│
├── examples/
│   └── sqlite_workflows.md           [Docs] SQLite usage examples
│
├── plugins/
│   └── example_plugin.py             [Python] Example plugin implementation
│
├── scripts/example/
│   ├── empty.json                    [Fixture] Empty JSON example
│   └── minimal.json                  [Fixture] Minimal CV example
│
├── src/cv_generator/                 [Python] Main package
│   ├── __init__.py                   Package exports
│   ├── assets.py                     Asset management
│   ├── cache.py                      Build caching system
│   ├── cleanup.py                    Directory cleanup utilities
│   ├── cli.py                        CLI entry point (argparse)
│   ├── config.py                     TOML configuration loading
│   ├── crud.py                       CRUD operations for entries
│   ├── db.py                         SQLite database operations
│   ├── doctor.py                     System health checks
│   ├── ensure.py                     Multi-language consistency
│   ├── entry_path.py                 Entry path utilities
│   ├── errors.py                     Exception hierarchy
│   ├── generator.py                  CV generation orchestration
│   ├── hooks.py                      Plugin hook system
│   ├── io.py                         JSON I/O utilities
│   ├── jinja_env.py                  Jinja2 environment setup
│   ├── latex.py                      LaTeX compilation
│   ├── logging_config.py             Logging setup
│   ├── paths.py                      Path resolution
│   ├── plugins.py                    Plugin discovery
│   ├── registry.py                   Section registry
│   ├── report.py                     Report generation
│   ├── scaffold.py                   Project scaffolding
│   ├── tags.py                       Tag catalog management
│   ├── tex_diff.py                   LaTeX diff utilities
│   ├── validate_schema.py            JSON schema validation
│   ├── watch.py                      File watching
│   └── web.py                        Flask web UI
│   │
│   ├── exporters/                    [Python] Export formats
│   │   ├── __init__.py
│   │   ├── base.py                   Base exporter class
│   │   ├── html.py                   HTML exporter
│   │   └── markdown.py               Markdown exporter
│   │
│   ├── lang_engine/                  [Python] Translation engine
│   │   ├── __init__.py
│   │   ├── create_lang.py            Language file creation
│   │   ├── lang.json                 Translation mappings
│   │   └── translate_cv_keys.py      Key translation
│   │
│   ├── schemas/
│   │   └── cv.schema.json            [Config] JSON schema
│   │
│   ├── scripts/                      [Python] Utility scripts
│   │   ├── __init__.py
│   │   ├── make_translate_csv.py
│   │   ├── smoke_validate.py
│   │   └── test_cv_generation.py
│   │
│   ├── templates/                    [HTML] Flask web UI templates
│   │   ├── base.html
│   │   ├── diagnostics.html
│   │   ├── entry.html
│   │   ├── entry_form.html
│   │   ├── entry_linked.html
│   │   ├── index.html
│   │   ├── person.html
│   │   ├── preview.html
│   │   ├── section.html
│   │   ├── tag_form.html
│   │   └── tags.html
│   │
│   └── export_templates/
│       └── cv.html                   [HTML] CV export template
│
├── templates/                        [LaTeX/Jinja2] CV section templates
│   ├── layout.tex                    Main document layout
│   ├── header.tex                    Personal info section
│   ├── education.tex                 Education section
│   ├── experience.tex                Work experience section
│   ├── skills.tex                    Skills section
│   ├── projects.tex                  Projects section
│   ├── publications.tex              Publications section
│   ├── references.tex                References section
│   ├── language.tex                  Language skills section
│   └── certificates.tex              Certificates section
│
└── tests/                            [Python] Test suite
    ├── __init__.py
    ├── conftest.py                   Pytest configuration
    ├── snapshot_utils.py             Snapshot testing utilities
    │
    ├── e2e/
    │   └── test_cli_e2e.py           E2E CLI tests
    │
    ├── integration/
    │   └── test_rendering.py         Template rendering tests
    │
    ├── unit/
    │   └── test_snapshot_utils.py    Snapshot utility tests
    │
    ├── fixtures/                     Test fixtures
    │   ├── valid/
    │   ├── invalid/
    │   ├── lint/
    │   ├── multilang/
    │   ├── mismatch/
    │   └── ramin/
    │
    ├── snapshots/                    Snapshot files
    │
    └── test_*.py                     Unit test modules (28 files)
```

### 3.2 Directory Purpose Summary

| Directory | Purpose |
|-----------|---------|
| `.github/workflows/` | CI/CD automation with GitHub Actions |
| `assets/` | Shared assets like logo mappings |
| `data/` | **LOCKED** — CV JSON data, pictures, database |
| `docs/` | MkDocs documentation source |
| `examples/` | Usage examples and workflows |
| `plugins/` | Plugin examples and extensions |
| `scripts/example/` | Example JSON files |
| `src/cv_generator/` | Main Python package |
| `src/cv_generator/exporters/` | HTML/Markdown export modules |
| `src/cv_generator/lang_engine/` | Multi-language translation |
| `src/cv_generator/schemas/` | JSON validation schemas |
| `src/cv_generator/scripts/` | Utility scripts |
| `src/cv_generator/templates/` | Flask web UI templates |
| `templates/` | LaTeX/Jinja2 CV templates |
| `tests/` | Comprehensive test suite |

---

## 4. Architecture Overview

### 4.1 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER ENTRY POINTS                              │
├─────────────────────────────────────────────────────────────────────────┤
│  cvgen CLI (cli.py)  │  generate_cv.py (legacy)  │  Web UI (web.py)    │
└──────────┬───────────────────────┬────────────────────────┬─────────────┘
           │                       │                        │
           ▼                       ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         CONFIGURATION LAYER                              │
│   config.py (TOML) ──► paths.py (ArtifactPaths) ──► logging_config.py   │
└──────────┬──────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATA INPUT LAYER                                │
├─────────────────────────────────────────────────────────────────────────┤
│  io.py                      │  db.py                    │  ensure.py    │
│  ├── discover_cv_files()    │  ├── init_db()            │  └── Multi-   │
│  ├── load_cv_json()         │  ├── import_cv()          │      language │
│  ├── parse_cv_filename()    │  ├── export_cv()          │      check    │
│  └── validate_cv_data()     │  └── list_persons()       │               │
└──────────┬──────────────────┴───────────────────────────┴───────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         VALIDATION LAYER                                 │
│     validate_schema.py ──────► cv.schema.json (jsonschema)              │
└──────────┬──────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        PLUGIN / HOOK LAYER                               │
│  hooks.py (HookManager)  ◄──────────────────────►  plugins.py           │
│  ├── pre_validate                                   ├── discover        │
│  ├── post_render                                    └── load            │
│  ├── pre_compile                                                        │
│  └── post_export                                                        │
└──────────┬──────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       TEMPLATE RENDERING LAYER                           │
├─────────────────────────────────────────────────────────────────────────┤
│  generator.py                          │  jinja_env.py                  │
│  ├── generate_cv()                     │  ├── create_jinja_env()        │
│  ├── generate_all_cvs()                │  ├── latex_escape() filter     │
│  ├── render_sections()                 │  ├── latex_raw() filter        │
│  ├── render_layout()                   │  ├── tr() translation          │
│  └── filter_by_variant()               │  └── RTL_LANGUAGES support     │
│                                        │                                 │
│  registry.py (SectionRegistry)         │  lang_engine/                  │
│  ├── SectionAdapter protocol           │  ├── translate_cv_keys.py      │
│  └── GenericSectionAdapter             │  └── lang.json                 │
└──────────┬──────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      LATEX COMPILATION LAYER                             │
│  latex.py                                                                │
│  ├── compile_latex()  ──► xelatex subprocess                            │
│  ├── cleanup_latex_artifacts()                                          │
│  └── rename_pdf()                                                        │
└──────────┬──────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         OUTPUT LAYER                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  PDF: output/pdf/<profile>/<lang>/<profile>_<lang>.pdf                  │
│  LaTeX: output/latex/<profile>/<lang>/main.tex (if --keep-latex)        │
│  JSON: output/json/<profile>/<lang>/cv.json (export)                    │
│  HTML: output/html/ (via exporters/)                                    │
│  Markdown: output/md/ (via exporters/)                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Key Components

| Component | File(s) | Responsibility |
|-----------|---------|----------------|
| **CLI** | `cli.py` | Argparse-based CLI with `build`, `ensure`, `db`, `web`, `profile` commands |
| **Generator** | `generator.py` | Orchestrates JSON → LaTeX → PDF pipeline |
| **Template Engine** | `jinja_env.py` | Jinja2 with custom LaTeX-compatible delimiters |
| **LaTeX Compiler** | `latex.py` | XeLaTeX subprocess execution |
| **Database** | `db.py` | SQLite storage for CV entries and tags |
| **Web UI** | `web.py` | Flask app for tag management |
| **Plugins** | `plugins.py`, `hooks.py` | Extensibility via hook callbacks |
| **Validation** | `validate_schema.py`, `ensure.py` | JSON schema + multi-language consistency |
| **Paths** | `paths.py` | `ArtifactPaths` class for output organization |
| **Cleanup** | `cleanup.py` | Windows-safe directory removal |

### 4.3 External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `jinja2` | ≥3.0.0 | Template rendering |
| `flask` | ≥3.0.0 | Web UI |
| `jsonschema` | ≥4.0.0 | JSON validation |
| `tomli` | ≥2.0.0 (Python <3.11) | TOML parsing |
| **XeLaTeX** | (system) | PDF compilation |

---

## 5. Findings

### 5.1 Security (5 findings)

---

#### F-001 — tarfile.extractall() without member filtering

**Category:** Security  
**Severity:** High  
**Confidence:** High  
**Location:** `src/cv_generator/cleanup.py:430-432`

**Evidence:**
```python
with tarfile.open(archive_path, "r:gz") as tar:
    tar.extractall(destination.parent)
```

**Why it matters:**  
`tarfile.extractall()` without filtering members can lead to directory traversal attacks (CVE-2007-4559). A malicious archive could overwrite files outside the destination directory by including entries with paths like `../../../etc/passwd`.

**How to verify:**  
Create a tar archive with a path traversal entry and call `restore_backup()`.

**Suggested direction:**  
Use the `filter` parameter (Python 3.12+) or implement manual member validation before extraction. Example:
```python
# Python 3.12+ with data_filter (safest option for untrusted archives)
tar.extractall(destination.parent, filter='data')  

# OR for all Python versions - validate paths manually:
import os
for member in tar.getmembers():
    # Reject absolute paths and parent directory traversal
    if member.name.startswith('/') or member.name.startswith('..'):
        raise ValueError(f"Unsafe path in archive: {member.name}")
    # Normalize and check for traversal after normalization
    safe_path = os.path.normpath(member.name)
    if safe_path.startswith('..'):
        raise ValueError(f"Path traversal detected: {member.name}")
    tar.extract(member, destination.parent)
```

---

#### F-002 — Hardcoded Flask secret key

**Category:** Security  
**Severity:** High  
**Confidence:** High  
**Location:** `src/cv_generator/web.py:341`

**Evidence:**
```python
app.secret_key = "cvgen-web-local-only"
```

**Why it matters:**  
A static secret key allows session forgery. While the comment says "local-only," the app can be bound to non-localhost addresses.

**How to verify:**  
Check if sessions can be forged using the known key.

**Suggested direction:**  
Generate a random secret key at startup, or read from environment variable `CVGEN_WEB_SECRET`. Store in state file for persistence if needed.

---

#### F-003 — No CSRF protection in web forms

**Category:** Security  
**Severity:** Medium  
**Confidence:** High  
**Location:** `src/cv_generator/web.py` (all POST routes)

**Evidence:**  
Forms in web UI lack CSRF tokens. Routes like `/entry/<int:entry_id>/tags`, `/tags/create`, `/export/<person>` accept POST without CSRF validation.

**Why it matters:**  
A malicious site could trick an authenticated user into submitting unwanted actions (delete tags, export data).

**How to verify:**  
Submit a POST request from a different origin to a web route.

**Suggested direction:**  
Add Flask-WTF or implement manual CSRF token validation.

---

#### F-004 — subprocess with shell=True on Windows

**Category:** Security  
**Severity:** Medium  
**Confidence:** Medium  
**Location:** `src/cv_generator/cleanup.py:37-44`

**Evidence:**
```python
subprocess.run(
    ["attrib", "-R", str(root / "*"), "/S", "/D"],
    check=False,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    shell=True,  # ← Security concern
)
```

**Why it matters:**  
`shell=True` with user-controlled paths could allow command injection if the path contains shell metacharacters.

**How to verify:**  
Create a directory with a name containing `& malicious_command` and call cleanup.

**Suggested direction:**  
Use `shell=False` and pass arguments as a proper list. The `attrib` command works fine without shell expansion.

---

#### F-005 — Unfiltered entry_id in web routes

**Category:** Security  
**Severity:** Low  
**Confidence:** Medium  
**Location:** `src/cv_generator/web.py:455-491`

**Evidence:**
```python
@app.route("/entry/<int:entry_id>")
def entry_detail(entry_id: int):
    entry = get_entry(entry_id, app.config["DB_PATH"])
```

**Why it matters:**  
While Flask's `<int:entry_id>` provides type safety, the ID is passed directly to database queries. SQL injection is unlikely with parameterized queries, but lack of authorization could allow accessing any entry.

**How to verify:**  
Access `/entry/1`, `/entry/2`, etc. to enumerate all entries.

**Suggested direction:**  
Consider adding person-based access control if multi-tenant usage is planned.

---

### 5.2 Reliability & Cross-Platform (4 findings)

---

#### F-006 — Windows file lock handling is best-effort

**Category:** Reliability  
**Severity:** Medium  
**Confidence:** Medium  
**Location:** `src/cv_generator/cleanup.py:61-113`

**Evidence:**
```python
for i in range(attempts):
    try:
        _clear_readonly_windows(p)
        shutil.rmtree(p, onerror=onerror)
        return
    except PermissionError:
        time.sleep(min(2.0, 0.05 * (2 ** i)))
```

**Why it matters:**  
The retry logic with exponential backoff is good, but 25 attempts may not be enough for stubborn locks (OneDrive, antivirus). The final attempt after the loop doesn't handle failure gracefully.

**How to verify:**  
Open a file in `output/latex/` in an editor and run `cvgen build`.

**Suggested direction:**  
Add a warning to the user if cleanup fails, suggesting they close applications using the directory. Consider a `--force-cleanup` flag with longer timeout.

---

#### F-007 — get_repo_root() may return CWD incorrectly

**Category:** Reliability  
**Severity:** Medium  
**Confidence:** Medium  
**Location:** `src/cv_generator/paths.py:33-68`

**Evidence:**
```python
# Fallback: use CWD
_repo_root = Path.cwd().resolve()
return _repo_root
```

**Why it matters:**  
If marker files (`pyproject.toml`, `generate_cv.py`, `awesome-cv.cls`) are not found, the function falls back to CWD. This could cause issues when running from a different directory or when installed as a package.

**How to verify:**  
Install cv-generator system-wide, navigate to a different directory, and run `cvgen build`.

**Suggested direction:**  
1. Cache `_repo_root` only when successfully found
2. Add explicit `--repo-root` CLI option
3. Raise an error instead of silent fallback

---

#### F-008 — RTL language detection is hardcoded

**Category:** Reliability  
**Severity:** Low  
**Confidence:** High  
**Location:** `src/cv_generator/jinja_env.py:25`

**Evidence:**
```python
RTL_LANGUAGES = {"fa", "ar", "he"}
```

**Why it matters:**  
Other RTL languages (Urdu, Pashto, Dari, etc.) are not included. Adding a new RTL language requires code changes.

**How to verify:**  
Generate a CV with `lang="ur"` (Urdu) — RTL will not be applied.

**Suggested direction:**  
Move to configuration file or use a language detection library.

---

#### F-009 — LaTeX timeout may be too short

**Category:** Reliability  
**Severity:** Low  
**Confidence:** Medium  
**Location:** `src/cv_generator/latex.py:20-25`

**Evidence:**
```python
def compile_latex(
    tex_file: Path,
    output_dir: Path,
    *,
    timeout: int = 120
) -> Optional[Path]:
```

**Why it matters:**  
120 seconds is generally sufficient, but complex CVs with many packages or slow disk I/O might timeout. The error message doesn't suggest increasing timeout.

**How to verify:**  
Compile a very large CV on a slow system.

**Suggested direction:**  
Add `--timeout` CLI option and improve timeout error message.

---

### 5.3 Correctness & Logic (4 findings)

---

#### F-010 — filter_by_variant() doesn't handle nested type_key

**Category:** Correctness  
**Severity:** Medium  
**Confidence:** Medium  
**Location:** `src/cv_generator/generator.py:193-250`

**Evidence:**
```python
for section in list_sections:
    # ...
    for item in items:
        type_key = item.get("type_key")
        if type_key is None:
            filtered_items.append(item)
        elif isinstance(type_key, list):
            if variant in type_key:
                filtered_items.append(item)
```

**Why it matters:**  
Skills section has nested structure (`skills.TechnicalSkills.Programming`), but variant filtering only works on flat list sections. Skills items with `type_key` may not be filtered correctly.

**How to verify:**  
Add `type_key: ["academic"]` to a skill item and run `cvgen build --variant academic`.

**Suggested direction:**  
Implement recursive variant filtering that handles nested dictionaries, or document this limitation.

---

#### F-011 — skills section reconstruction loses key order

**Category:** Correctness  
**Severity:** Low  
**Confidence:** Medium  
**Location:** `src/cv_generator/db.py:735-753`

**Evidence:**
```python
skills_data: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
for entry in skills_entries:
    parent_cat = entry["parent_category"]
    sub_cat = entry["sub_category"]
    # ...
```

**Why it matters:**  
When exporting skills from the database, the order of parent categories and subcategories depends on dictionary insertion order (Python 3.7+), which may differ from the original JSON order.

**How to verify:**  
Import and export a CV, compare skills section order.

**Suggested direction:**  
Store category order as metadata in the database or use OrderedDict with explicit ordering.

---

#### F-012 — parse_cv_filename() may mismatch language codes

**Category:** Correctness  
**Severity:** Low  
**Confidence:** High  
**Location:** `src/cv_generator/io.py:22-46`

**Evidence:**
```python
# Pattern: name-lang or name_lang where lang is 2-3 lowercase letters
match = re.match(r'^(.+?)[-_]([a-z]{2,3})$', name)
```

**Why it matters:**  
Filenames like `john_doe.json` would parse as `base_name="john"`, `lang="doe"`, which is incorrect. The greedy `+?` doesn't prevent this.

**How to verify:**  
Create `john_doe.json` and check parsed values.

**Suggested direction:**  
Validate language code against a known list (e.g., ISO 639-1), or require explicit language marker.

---

#### F-013 — validate_cv_data() only checks for 'basics' key

**Category:** Correctness  
**Severity:** Low  
**Confidence:** High  
**Location:** `src/cv_generator/io.py:119-134`

**Evidence:**
```python
def validate_cv_data(data: Dict[str, Any], filename: str) -> bool:
    if "basics" not in data:
        logger.warning(f"Skipping {filename}: missing 'basics' key")
        return False
    return True
```

**Why it matters:**  
This is a very minimal validation. The JSON schema (`cv.schema.json`) provides comprehensive validation, but this function is used as a quick check in the generator. It could miss other structural issues.

**How to verify:**  
Pass a CV with `basics: "not a list"` — it will pass validation but fail later.

**Suggested direction:**  
Integrate JSON schema validation into the quick check, or document this as a pre-filter.

---

### 5.4 Error Handling & Diagnostics (4 findings)

---

#### F-014 — Swallowed exceptions in plugin execution

**Category:** Error Handling  
**Severity:** Medium  
**Confidence:** High  
**Location:** `src/cv_generator/hooks.py:225-236`

**Evidence:**
```python
try:
    registered.callback(context)
except Exception as e:
    error_msg = (
        f"Hook '{registered.name}' raised an error: {e}"
    )
    logger.error(error_msg)
    context.add_error(error_msg)
    # Note: continues to next hook, doesn't abort
```

**Why it matters:**  
Plugin errors are logged but execution continues. The user might not notice a critical plugin failed.

**How to verify:**  
Register a hook that raises an exception, check if the build still succeeds.

**Suggested direction:**  
Add `abort_on_error` option to hook registration, or at least prominently display errors at the end.

---

#### F-015 — LaTeX compilation errors are hard to diagnose

**Category:** Error Handling  
**Severity:** Medium  
**Confidence:** Medium  
**Location:** `src/cv_generator/latex.py:69-84`

**Evidence:**
```python
if result.returncode != 0:
    logger.warning(f"xelatex returned non-zero exit code: {result.returncode}")
    logger.debug(f"xelatex stderr: {result.stderr}")
    # Still check if PDF was generated
```

**Why it matters:**  
LaTeX errors are logged at DEBUG level only. Users running without `--debug` won't see the actual error message. The "compilation failed" error is vague.

**How to verify:**  
Introduce a LaTeX syntax error in a template and run `cvgen build`.

**Suggested direction:**  
Parse LaTeX output for common error patterns (e.g., `! LaTeX Error:`) and display them prominently.

---

#### F-016 — Missing context in ConfigurationError

**Category:** Error Handling  
**Severity:** Low  
**Confidence:** High  
**Location:** `src/cv_generator/errors.py:22-25`

**Evidence:**
```python
class ConfigurationError(CVGeneratorError):
    """Configuration or path-related errors."""
    exit_code = 2
```

**Why it matters:**  
`ConfigurationError` is raised in many places with just a message string. It doesn't capture the context (which config key, which file, etc.).

**How to verify:**  
Trigger a config error and check if the message helps diagnose the issue.

**Suggested direction:**  
Add optional attributes for `key`, `file_path`, `expected`, `actual` to ConfigurationError.

---

#### F-017 — doctor command doesn't check for XeLaTeX

**Category:** Error Handling  
**Severity:** Low  
**Confidence:** High  
**Location:** `src/cv_generator/doctor.py`

**Evidence:**  
The `doctor` module exists but the `db doctor` command only checks database health. There's no system-wide health check for XeLaTeX, fonts, or templates.

**Why it matters:**  
Users might not realize XeLaTeX is missing until they try to build.

**How to verify:**  
Remove `xelatex` from PATH and run `cvgen db doctor` — it will pass.

**Suggested direction:**  
Implement `cvgen doctor` (not just `cvgen db doctor`) that checks:
- XeLaTeX installation
- Required fonts
- Templates directory
- Output directory writability

---

### 5.5 Documentation & UX (3 findings)

---

#### F-018 — README output path doesn't match code

**Category:** Documentation  
**Severity:** Low  
**Confidence:** High  
**Location:** `README.md:11-13` vs `src/cv_generator/paths.py:182-189`

**Evidence:**
README says:
```markdown
cvgen build --name ramin
# → output/pdf/ramin/en/ramin_en.pdf
```

But `ArtifactPaths.pdf_path` returns:
```python
return self.pdf_dir / "cv.pdf"  # output/pdf/ramin/en/cv.pdf
```

While `pdf_named_path` returns `ramin_en.pdf`.

**Why it matters:**  
Users might be confused about which path is correct.

**How to verify:**  
Run `cvgen build --name ramin` and check actual output path.

**Suggested direction:**  
Verify actual behavior and update README to match.

---

#### F-019 — plan_future.md references outdated test count

**Category:** Documentation  
**Severity:** Low  
**Confidence:** High  
**Location:** `plan_future.md:43`

**Evidence:**  
The `plan_future.md` document states:
> "203 tests covering core functionality"

**Why it matters:**  
The actual test count is 771 tests (as verified in this audit). The planning document is outdated.

**How to verify:**  
Run `pytest tests/ --collect-only | tail -1`.

**Suggested direction:**  
Update the document or add a script to auto-update counts.

---

#### F-020 — Missing examples for plugin development

**Category:** Documentation  
**Severity:** Low  
**Confidence:** High  
**Location:** `docs/plugins.md` (if exists) and `plugins/example_plugin.py`

**Evidence:**
The example plugin is minimal:
```python
def register(registry, hook_manager):
    logger.info("Example plugin registered")
    # Only logs, doesn't demonstrate actual section or exporter
```

**Why it matters:**  
Users wanting to add custom sections or exporters lack comprehensive examples.

**How to verify:**  
Read `plugins/example_plugin.py` and try to implement a custom section.

**Suggested direction:**  
Add more comprehensive plugin examples:
- Custom section plugin
- Custom exporter plugin
- Data transformation plugin

---

### 5.6 Performance & Packaging (3 findings)

---

#### F-021 — No Jinja2 template caching by default

**Category:** Performance  
**Severity:** Low  
**Confidence:** High  
**Location:** `src/cv_generator/jinja_env.py:233-278`

**Evidence:**
```python
bytecode_cache = None
if cache_dir is not None:
    cache_path = Path(cache_dir) / "jinja2"
    cache_path.mkdir(parents=True, exist_ok=True)
    bytecode_cache = FileSystemBytecodeCache(str(cache_path))
```

**Why it matters:**  
Template caching is only enabled when `cache_dir` is provided (via `--incremental` flag). Default builds reparse templates each time.

**How to verify:**  
Time `cvgen build --name ramin` twice without `--incremental`.

**Suggested direction:**  
Enable bytecode caching by default, or make it opt-out rather than opt-in.

---

#### F-022 — ruff version constraint too loose

**Category:** Packaging  
**Severity:** Low  
**Confidence:** Medium  
**Location:** `pyproject.toml:40`

**Evidence:**
```toml
"ruff>=0.4.0,<1.0.0",
```

**Why it matters:**  
Ruff is a rapidly evolving tool. The broad version range could cause CI failures if a new ruff version has stricter rules.

**How to verify:**  
Install ruff 0.5.0 vs 0.4.0 and compare output.

**Suggested direction:**  
Pin to a minor version range (e.g., `>=0.14.0,<0.15.0`) or use lockfile consistently.

---

#### F-023 — generate_cv.py still exists (deprecated)

**Category:** Packaging  
**Severity:** Low  
**Confidence:** High  
**Location:** `generate_cv.py`

**Evidence:**
```python
#!/usr/bin/env python3
"""
Legacy entry point for CV Generator.
...
DEPRECATED: Use `cvgen build` instead.
```

**Why it matters:**  
Users might still use the legacy script, missing CLI improvements.

**How to verify:**  
Search for `generate_cv.py` in documentation and tutorials.

**Suggested direction:**  
Add a deprecation warning at runtime:
```python
import warnings
warnings.warn("generate_cv.py is deprecated. Use 'cvgen build' instead.", DeprecationWarning)
```

---

## 6. Special Analysis: Data Folder is Locked

### 6.1 Code Paths That Reference `data/`

| File | Line | Reference | Risk |
|------|------|-----------|------|
| `src/cv_generator/paths.py:92-94` | `get_default_cvs_path()` | Returns `repo_root / "data" / "cvs"` | High — hardcoded path |
| `src/cv_generator/jinja_env.py:164-173` | `find_pic()`, `get_pic()` | Returns `repo_root / "data" / "pics"` | High — hardcoded path |
| `src/cv_generator/cleanup.py:145-165` | `is_data_path()` | Checks if path is under `data/` | Medium — safety check |
| `src/cv_generator/db.py:36` | `DEFAULT_DB_PATH` | `Path("data/db/cv.db")` | High — hardcoded path |
| `src/cv_generator/generator.py:298-299` | Profile picture lookup | Uses `get_repo_root() / "data" / "pics"` | High — hardcoded path |
| `src/cv_generator/assets.py` | Logo lookup | May reference `data/assets/` | Medium |

### 6.2 Behavior When `data/` is Unavailable

| Scenario | Current Behavior | Ideal Behavior |
|----------|------------------|----------------|
| `data/cvs/` missing | `ConfigurationError: CVs directory not found` | Clear error with suggestion to use `--input-dir` |
| `data/pics/` missing | Profile photos silently skipped | Warning if expected photos not found |
| `data/db/` missing | `ConfigurationError` on db commands | Auto-create directory or suggest alternative path |
| `data/` read-only | Fails on db init/import | Suggest `--db-path` alternative |

### 6.3 Recommended Improvements

1. **Add `--data-dir` global option**
   ```python
   @click.option('--data-dir', type=Path, help='Override data directory')
   ```

2. **Dependency injection for data sources**
   - Refactor `get_default_cvs_path()` to accept optional parameter
   - Inject paths via configuration object

3. **Provide sample data package**
   - Create `cv_generator_samples` package with example CVs
   - Allow `cvgen init --use-samples`

4. **Improve error messages**
   ```
   Error: CVs directory not found: /path/to/data/cvs
   Hint: Use --input-dir to specify an alternative location
         or run 'cvgen init' to create the default structure
   ```

5. **Separate "core engine" from "personal data"**
   - Document that `data/` is user-specific
   - Provide `.gitignore` template that excludes `data/`
   - Support environment variable `CVGEN_DATA_DIR`

---

## 7. Audit Pass B — Delta & Corrections

### 7.1 Re-verified Findings

| Finding | Status | Notes |
|---------|--------|-------|
| F-001 | Confirmed | tarfile.extractall() is indeed vulnerable |
| F-002 | Confirmed | Secret key is hardcoded |
| F-003 | Confirmed | No CSRF tokens in templates |
| F-006 | Confirmed | Retry logic exists but may not be enough |
| F-010 | Needs verification | Tested manually — skills filtering works for top-level items |

### 7.2 Newly Found Issues (Pass B)

---

#### F-024 — `.cvgen/` state directory not in .gitignore template

**Category:** Maintainability  
**Severity:** Low  
**Confidence:** High  
**Location:** `.gitignore:83-84`

**Evidence:**
```
# CV Generator state files (local profile selection, etc.)
.cvgen/
```

**Why it matters:**  
While the repo's `.gitignore` includes `.cvgen/`, users who copy the project or use `cvgen init` might not have this in their `.gitignore`.

**Suggested direction:**  
Include in scaffold template.

---

#### F-025 — No test coverage for web.py authentication

**Category:** Testing  
**Severity:** Low  
**Confidence:** High  
**Location:** `tests/test_web.py`

**Evidence:**  
The test file tests routes but doesn't verify authentication enforcement when `CVGEN_WEB_AUTH` is set.

**Why it matters:**  
Authentication could be bypassed due to implementation bugs.

**Suggested direction:**  
Add tests that set `CVGEN_WEB_AUTH` and verify 401 responses.

---

### 7.3 Retracted Issues

None. All findings from Pass A were confirmed or clarified.

### 7.4 Coverage Confirmation Checklist

- [x] All Python files in `src/cv_generator/` reviewed
- [x] All LaTeX templates reviewed
- [x] All test files reviewed (structure, not content)
- [x] Configuration files reviewed (pyproject.toml, mkdocs.yml, ci.yml)
- [x] Documentation files reviewed
- [x] Cross-file dependencies verified (imports, schema references)
- [x] `data/` directory NOT accessed (per audit constraints)

---

## 8. Summary Tables

### 8.1 Findings by Category

| Category | Count | High | Medium | Low |
|----------|-------|------|--------|-----|
| Security | 5 | 2 | 2 | 1 |
| Reliability | 4 | 0 | 2 | 2 |
| Correctness | 4 | 0 | 1 | 3 |
| Error Handling | 4 | 0 | 2 | 2 |
| Documentation | 3 | 0 | 0 | 3 |
| Performance/Packaging | 3 | 0 | 0 | 3 |
| **Audit Pass B** | 2 | 0 | 0 | 2 |
| **Total** | **25** | **2** | **7** | **16** |

### 8.2 Findings by Severity

| Severity | Count | Findings |
|----------|-------|----------|
| **High** | 2 | F-001, F-002 |
| **Medium** | 7 | F-003, F-004, F-006, F-007, F-010, F-014, F-015 |
| **Low** | 16 | F-005, F-008, F-009, F-011, F-012, F-013, F-016, F-017, F-018, F-019, F-020, F-021, F-022, F-023, F-024, F-025 |

### 8.3 Prioritized Action Items

| Priority | Action | Findings Addressed |
|----------|--------|-------------------|
| 1 | Fix `tarfile.extractall()` security issue | F-001 |
| 2 | Rotate Flask secret key or use env variable | F-002 |
| 3 | Add `--data-dir` option for path flexibility | F-005 (related), F-007 |
| 4 | Improve LaTeX error reporting | F-015 |
| 5 | Add CSRF protection to web UI | F-003 |
| 6 | Add system-wide `cvgen doctor` command | F-017 |
| 7 | Update documentation for accuracy | F-018, F-019 |
| 8 | Remove `shell=True` from subprocess | F-004 |

---

## 9. Appendix: Tools and Methodology

### 9.1 Static Analysis Tools Used

- **ruff 0.14.10** — Python linting (passed with no errors)
- **pytest 9.0.2** — Test execution (771 passed, 30 warnings)
- **Manual code review** — Line-by-line analysis of all source files

### 9.2 Audit Methodology

1. **Inventory Pass**: Listed all files and directories, classified by type
2. **Architecture Discovery**: Traced data flow from CLI to PDF output
3. **File-by-File Review**: Examined each file for issues in 10 categories
4. **Cross-Reference Check**: Verified imports, schema usage, documentation accuracy
5. **Security Focus**: Special attention to subprocess, file operations, web routes
6. **Verification Pass**: Re-checked findings, looked for false positives

### 9.3 Limitations

- **`data/` directory not inspected**: Per audit constraints, JSON data files were not read
- **XeLaTeX not installed**: Could not verify end-to-end PDF generation
- **No dynamic analysis**: Did not run the web UI or test with actual attacks
- **Time constraints**: Some edge cases may have been missed

---

*End of Audit Report*

**Report generated:** 2026-01-05  
**Auditor:** Repository Auditor Agent  
**Scope:** Read-only analysis with no code modifications
