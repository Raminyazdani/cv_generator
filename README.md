# CV Generator – JSON → Awesome-CV PDF

**CV Generator** transforms structured JSON data into polished, professional PDF resumes using the elegant [Awesome-CV](https://github.com/posquit0/Awesome-CV) LaTeX class. Write your CV once in JSON, generate beautiful PDFs in multiple languages (English, German, Persian with RTL support), and use variant filtering to create targeted versions for academia or industry—all from a single source of truth.

## 📁 Repository Structure

This repository is organized for clarity:
- **Root directory**: Core runtime files (`data/`, `templates/`, `generate_cv.py`, `awesome-cv.cls`)
- **`project/` directory**: Development files (`src/`, `tests/`, `docs/`, configuration files, examples)

This structure keeps the root clean for end users while maintaining a complete development environment in `project/`.

## Quick Start (5 lines to first PDF)

```bash
git clone https://github.com/Raminyazdani/cv_generator.git && cd cv_generator
pip install -e .
cvgen build --name ramin
# → output/pdf/ramin/en/ramin_en.pdf
```

> **Prerequisites**: Python 3.9+ and XeLaTeX must be installed. See [Installation](#installation) for details.

---

## Table of Contents

- [Features](#features)  
- [Project Structure](#project-structure)  
- [Prerequisites](#prerequisites)  
- [Installation](#installation)  
- [Usage](#usage)  
  - [Running the generator](#running-the-generator)  
  - [Configuration File](#configuration-file)
  - [Profile Management](#profile-management)
  - [Variant Filtering](#variant-filtering)
  - [Adding a new CV](#adding-a-new-cv)  
  - [Adding a profile picture](#adding-a-profile-picture)  
- [Validating Multilingual CVs](#validating-multilingual-cvs)
- [SQLite Database & Tagging](#sqlite-database--tagging)
  - [Quick Start](#quick-start-1)
  - [Web UI for Tag Management](#web-ui-for-tag-management)
  - [Detailed Documentation](#detailed-documentation)
- [Data Format (JSON Schema Overview)](#data-format-json-schema-overview)  
  - [Basics](#basics)  
  - [Profiles / Social links](#profiles--social-links)  
  - [Education](#education)  
  - [Experience](#experience)  
  - [Skills](#skills)  
  - [Other Sections](#other-sections)  
- [Template System](#template-system)  
  - [Jinja2 configuration](#jinja2-configuration)  
  - [Available filters and helpers](#available-filters-and-helpers)  
  - [Main LaTeX layout](#main-latex-layout)  
- [Output and Intermediate Files](#output-and-intermediate-files)  
- [Common Pitfalls](#common-pitfalls)
- [Troubleshooting](#troubleshooting)  
- [Development Notes](#development-notes)  
- [Documentation](#documentation)
- [License](#license)  
- [Acknowledgements](#acknowledgements)

---

## Features

- **Multi-CV support**: Automatically generates a PDF for every JSON file in `data/cvs/`.
- **Beautiful layout**: Uses the popular Awesome-CV LaTeX class (`awesome-cv.cls`).
- **Modular sections**: Each CV section is a separate Jinja2/LaTeX template under `templates/`:
  - `header`, `education`, `experience`, `skills`, `language`, `projects`, `certificates`, `publications`, `references`, ...
- **Profile photo support**: Optional per-person images under `data/pics/`.
- **Configuration file**: Optional TOML config (`cv_generator.toml`) to reduce repetitive CLI flags.
- **Profile management**: Set a default profile with `cvgen profile use <name>`.
- **Variant filtering**: Create targeted CV versions with `--variant` flag.
- **SQLite database**: Store CV data in SQLite for querying and editing.
- **Tagging system**: Apply tags (via `type_key`) to create targeted CV versions.
- **Web UI**: Browse CV sections and manage tags via a local web interface.
- **Robust cleanup**: Intermediate result directories are cleaned up reliably, with special handling for Windows file locks (e.g., OneDrive / antivirus).
- **Safe templating**: Uses `StrictUndefined` to catch missing fields early; custom LaTeX-escaping filter to avoid compilation errors.

---

## Project Structure

At a glance:

```text
cv_generator/
├─ awesome-cv.cls           # Awesome-CV LaTeX class (upstream)
├─ generate_cv.py           # Main script: JSON → LaTeX (Jinja2) → PDF
├─ README.md                # This file
├─ data/
│  ├─ cvs/                  # Input JSON CVs (one file per person)
│  │  ├─ mahsa.json
│  │  └─ ramin.json
│  ├─ pics/                 # Optional profile photos
│  │  ├─ mahsa.jpg
│  │  └─ ramin.jpg
│  └─ assets/               # Logos and other assets
│     └─ logo_map.json
├─ output/                  # All generated artifacts
│  ├─ pdf/                  # Generated PDFs organized by profile/lang
│  │  └─ ramin/
│  │     ├─ en/
│  │     │  └─ ramin_en.pdf
│  │     └─ de/
│  │        └─ ramin_de.pdf
│  ├─ latex/                # LaTeX sources (when --keep-latex is used)
│  │  └─ ramin/
│  │     └─ en/
│  │        ├─ main.tex
│  │        └─ sections/
│  └─ logs/                 # Generation logs
├─ templates/               # Jinja2+LaTeX section templates
│  ├─ layout.tex            # Main document layout; includes sections inline
│  ├─ header.tex            # Personal info & social links
│  ├─ education.tex
│  ├─ experience.tex
│  ├─ skills.tex
│  ├─ language.tex
│  ├─ projects.tex
│  ├─ certificates.tex
│  ├─ publications.tex
│  ├─ references.tex
│  └─ ... (extendable)
└─ project/                 # Development files
   ├─ src/cv_generator/     # Python package source
   ├─ tests/                # Test suite
   ├─ docs/                 # Documentation source
   ├─ plugins/              # Example plugins
   ├─ scripts/              # Helper scripts
   └─ examples/             # Usage examples
```

---

## Prerequisites

### 1. Python

- **Python 3.9+** recommended.
- Required Python packages:
  - `jinja2`

Install with:

```bash
pip install jinja2
```

(If you prefer, you can create a `requirements.txt` with `jinja2` and run `pip install -r requirements.txt`.)

### 2. LaTeX (XeLaTeX)

You **must** have a LaTeX distribution installed that provides `xelatex` and the fonts/packages used by Awesome-CV. Popular options:

- **Windows**: [MiKTeX](https://miktex.org/) or [TeX Live](https://www.tug.org/texlive/)

Make sure `xelatex` is available in your `PATH`.

The generator calls (simplified):

```bash
xelatex -interaction=nonstopmode -output-directory=./output <rendered.tex>
```

on Windows via `cmd.exe`, so ensure this works from a normal command prompt.

---

## Installation

### Quick Start (End Users)

1. **Clone this repository**:

```bash
git clone https://github.com/Raminyazdani/cv_generator.git
cd cv_generator
```

2. **Create a virtual environment (recommended)**:

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate
```

3. **Install the package**:

```bash
pip install -e .
```

4. **Verify installation**:

```bash
cvgen --version
cvgen --help
```

5. **Verify LaTeX** (required for PDF generation):

```bash
xelatex --version
```

If this fails, install a LaTeX distribution and ensure `xelatex` is on `PATH`.

### Developer Setup

For contributors and developers:

```bash
# Clone and enter the repository
git clone https://github.com/Raminyazdani/cv_generator.git
cd cv_generator

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install with development dependencies
pip install -e ".[dev]"

# Verify everything works
cvgen --version
python -c "import cv_generator; print(cv_generator.__version__)"
pip check
pytest tests/ -q
```

### Editable Install: When to Reinstall

With editable install (`pip install -e .`), code changes reflect immediately without reinstalling.

| Action | Reinstall Needed? |
|--------|-------------------|
| Edit `.py` files | ❌ No |
| Edit templates | ❌ No |
| Dependencies changed in `pyproject.toml` | ✅ Yes: `pip install -e ".[dev]"` |
| Entry points changed | ✅ Yes: `pip install -e ".[dev]"` |
| New venv created | ✅ Yes: `pip install -e ".[dev]"` |
| Switched Python version | ✅ Yes: recreate venv |

### Update Workflow

After pulling new changes from Git:

```bash
git pull

# If pyproject.toml changed (or to be safe):
pip install -e ".[dev]"

# Run tests to verify
pytest tests/ -q
```

---

## Usage

### Running the generator

The CV Generator provides both a modern CLI (`cvgen`) and the original script interface.

#### Using the cvgen CLI (recommended)

```bash
# Generate all CVs
cvgen build

# Generate a specific CV
cvgen build --name ramin

# Dry run (render LaTeX without compiling to PDF)
cvgen build --dry-run

# Keep LaTeX source files for debugging
cvgen build --keep-latex

# Verbose output (INFO level logging)
cvgen -v build

# Debug output (DEBUG level logging)
cvgen --debug build

# Quiet mode (show only errors)
cvgen -q build

# Custom directories
cvgen build --input-dir data/cvs --output-dir output --templates-dir templates

# Show help
cvgen --help
cvgen build --help

# Extended help on specific topics
cvgen help build
cvgen help templates
```

#### Using the original script (backward compatible)

```bash
python generate_cv.py                  # Same as cvgen build
python generate_cv.py --dry-run        # Same as cvgen build --dry-run
python generate_cv.py --name ramin     # Same as cvgen build --name ramin
```

What this does:

1. Loops over every JSON file in `data/cvs/` (e.g. `mahsa.json`, `ramin.json`).
2. For each person and language:
   - Creates directories under `output/latex/<name>/<lang>/sections/`.
   - Renders each template in `templates/` with that person's data into section `.tex` files.
   - Embeds all section content into `templates/layout.tex` and produces `main.tex`.
   - Runs `xelatex` to compile the LaTeX to PDF.
   - Cleans up LaTeX artifacts unless `--keep-latex` is specified.
   - Renames the compiled PDF to `<name>_<lang>.pdf`.
3. Cleans up intermediate files using a cross-platform cleanup helper.

Final PDFs are written to:

```text
output/pdf/<name>/<lang>/<name>_<lang>.pdf
```

For example:

- `output/pdf/mahsa/en/mahsa_en.pdf`
- `output/pdf/ramin/en/ramin_en.pdf`
- `output/pdf/ramin/de/ramin_de.pdf`

---

### Configuration File

CV Generator supports an optional TOML configuration file (`cv_generator.toml`) to reduce repetitive CLI flags:

```toml
# cv_generator.toml - Example configuration

[project]
name = "My CV Project"
default_lang = "en"
variants = ["academic", "industry", "onepage"]

[paths]
cvs = "data/cvs"
templates = "templates"
output = "output"

[build]
keep_latex = true
dry_run = false

[logging]
level = "INFO"
```

Place this file in your project root. Use `--config path/to/config.toml` to specify a different location.

**Precedence**: CLI flags override config values, which override defaults.

See [project/docs/config-reference.md](project/docs/config-reference.md) for full documentation.

---

### Profile Management

Instead of specifying `--name` every time, you can set a default profile:

```bash
# List available profiles
cvgen profile list

# Set ramin as the default profile
cvgen profile use ramin

# Now 'cvgen build' uses ramin automatically
cvgen build

# Switch to a different profile
cvgen profile use mahsa

# Clear the profile selection
cvgen profile clear
```

Profile state is stored in `.cvgen/state.json` (automatically excluded from git).

---

### Variant Filtering

Create targeted CV versions without modifying source JSON using variants:

```bash
# Build CV with only "academic" entries
cvgen build --name ramin --variant academic

# Build CV with only "industry" entries
cvgen build --name ramin --variant industry
```

Entries are filtered by their `type_key` field:
- Entries with matching `type_key` → included
- Entries with `type_key` as a list containing the variant → included
- Entries without `type_key` → always included (universal)

---

### Adding a new CV

1. Create a new JSON file under `data/cvs/`, e.g.:

```text
data/cvs/jane_doe.json
```

2. Follow the existing structure in `mahsa.json` or `ramin.json` (see [Data Format](#data-format-json-schema-overview) below).
3. Optionally add a matching photo (`data/pics/jane_doe.jpg`).
4. Run:

```bash
python generate_cv.py
```

You should get:

```text
output/jane_doe.pdf
```

---

### Adding a profile picture

The generator expects photos in `data/pics/` with the same base name as the JSON file:

- CV file: `data/cvs/ramin.json`
- Photo:   `data/pics/ramin.jpg`

The `header.tex` template uses:

- `find_pic(OPT_NAME)` and `get_pic(OPT_NAME)` to detect and include the photo.
- If no matching `<name>.jpg` is found, it falls back to checking for `./profile_square.jpg` (relative to the project root).

---

### Validating Multilingual CVs

For multilingual CV projects with versions in English, German, and Persian, you can validate that all language files have consistent structure:

```bash
# Check ramin's CV consistency across all languages
cvgen ensure --name ramin

# Check specific languages only
cvgen ensure --name ramin --langs en,de

# Output as JSON for programmatic use
cvgen ensure --name ramin --format json
```

The `ensure` command verifies that:

- All languages have the same sections and fields
- No keys are missing or extra in any language version
- Skill headings are properly translated

Exit codes:
- `0` – All languages are consistent
- `2` – Mismatches found (details printed to stdout)

For more details: `cvgen help ensure`

---

## SQLite Database & Tagging

CV Generator includes an optional SQLite-backed data layer for:
- **Storing CV data** in a queryable database
- **Tagging entries** with `type_key` values for creating targeted CV versions
- **Browsing and editing** via a local web UI
- **Round-trip import/export** that preserves all data

### Quick Start

```bash
# 1. Initialize the database
cvgen db init

# 2. Import your CV JSON files
cvgen db import

# 3. Check database health
cvgen db doctor

# 4. Start the tag manager web UI
cvgen web tags
# Opens at http://127.0.0.1:5000

# 5. Export with updated tags
cvgen db export --apply-tags --force
```

### Web UI for CV JSON Management

Start the local web server:

```bash
cvgen web tags
```

Then open http://127.0.0.1:5000 to access the **CV JSON Manager** which provides:

**Navigation & Browsing:**
- Browse persons and their CV sections
- View entries with rich summaries
- Navigate skills with category tree view
- Switch between languages (EN/DE/FA) via top bar selector

**Entry Management:**
- View and edit individual entries
- Create new entries with multi-language sync
- Delete entries (with confirmation dialogs)
- View linked language variants of entries

**Tag Management:**
- Create, rename, and delete tags
- Assign/unassign tags to entries
- Language-aware tag display with localized labels
- See tag usage counts across entries

**Export & Preview:**
- Preview export JSON before saving to disk
- Export CVs with tag updates in selected language
- View summary of export contents

**Diagnostics & Validation:**
- Database health checks (schema, orphaned entries)
- Detect unused/orphan tags
- Find entries needing translation
- Identify missing language counterparts
- Clean up orphan tag references

### Key Commands

| Command | Description |
|---------|-------------|
| `cvgen db init` | Create database with schema |
| `cvgen db import` | Import CV JSON files |
| `cvgen db export` | Export to JSON files |
| `cvgen db diff` | Compare JSON with database |
| `cvgen db list` | List persons or tags |
| `cvgen db doctor` | Run health checks |
| `cvgen web tags` | Start tag manager web UI |

### Export Flags

```bash
# Apply database tags to entries that originally had type_key
cvgen db export --apply-tags --force

# Add type_key to ALL entries (even those without)
cvgen db export --apply-tags-to-all --force
```

### Detailed Documentation

For comprehensive documentation, see:
- [SQLite Tagging Cookbook](project/docs/sqlite_tagging_cookbook.md) - Concepts, operations, extending the system
- [SQLite Workflows Examples](project/examples/sqlite_workflows.md) - Real command examples

---

## Data Format (JSON Schema Overview)

The JSON schema is loosely based on [JSON Resume](https://jsonresume.org/) with some customizations. Look at `data/cvs/mahsa.json` and `data/cvs/ramin.json` for complete examples.

Below is a conceptual overview of key fields used by existing templates.

### Basics

Used mostly by `header.tex` and `layout.tex`:

```jsonc
{
  "basics": [
    {
      "fname": "Ramin",
      "lname": "Yazdani",
      "label": ["Data Scientist", "Machine Learning Engineer"],
      "location": [
        {
          "city": "Saarbrücken",
          "region": "Saarland",
          "postalCode": "66123",
          "country": "Germany"
        }
      ],
      "phone": {
        "formatted": "+49 (0) 123 456789"
      },
      "email": "user@example.com"
    }
  ]
}
```

Notes:

- `fname` / `lname` required for `\name{...}{...}`.
- `label` is an array and rendered as the position line (`\position{...}`) with separators.
- `location` is an array; only the first entry is used to build a formatted address.
- `phone.formatted` and `email` are optional but recommended.

### Profiles / Social links

Rendered in `header.tex`:

```jsonc
{
  "profiles": [
    {
      "network": "Github",
      "username": "your-github-id"
    },
    {
      "network": "Google Scholar",
      "username": "Display Name",
      "uuid": "wpZDx1cAAAAJ"
    },
    {
      "network": "LinkedIn",
      "username": "your-linkedin-id"
    }
  ]
}
```

Supported `network` values in the current template:

- `"Github"` → `\github{...}`
- `"Google Scholar"` → `\googlescholar{uuid}{google scholar :,username}`
- `"LinkedIn"` → `\linkedin{...}`

Extend `header.tex` if you want more platforms.

### Education

Rendered in `education.tex`:

```jsonc
{
  "education": [
    {
      "studyType": "M.Sc.",
      "area": "Computer Science",
      "institution": "Some University",
      "location": "City, Country",
      "startDate": "2019",
      "endDate": "2021"
    }
  ]
}
```

The section is shown only if `education|length > 1` (i.e., more than one entry). If you want it to appear with a single entry, you can adjust that condition in `templates/education.tex`.

### Experience

Rendered in `experience.tex`:

```jsonc
{
  "experiences": [
    {
      "institution": "Company Name",
      "role": "Job Title",
      "location": "City, Country",
      "duration": "2020 – Present",
      "primaryFocus": "Main focus of role",
      "description": "Additional description or responsibilities"
    }
  ]
}
```

- Both `primaryFocus` and `description` are optional; if either is present, they are rendered as bullet points (`cvitems`).
- Section is shown only if `experiences|length > 1`.

### Skills

Rendered in `skills.tex` with a custom, two-row layout:

```jsonc
{
  "skills": {
    "Technical Skills": {
      "Programming": [
        { "short_name": "Python" },
        { "short_name": "C++" },
        { "short_name": "JavaScript" }
      ],
      "Data Science": [
        { "short_name": "Pandas" },
        { "short_name": "NumPy" },
        { "short_name": "Scikit-learn" }
      ]
    },
    "Soft Skills": {
      "Communication": [
        { "short_name": "Public speaking" },
        { "short_name": "Technical writing" }
      ]
    }
  }
}
```

Structure:

- Top level: **sections** (e.g. `"Technical Skills"`, `"Soft Skills"`).
- Second level: **categories** (e.g. `"Programming"`, `"Data Science"`).
- Items: each item must have a `short_name` field, used in the skills list.
- Items may include a `type_key` array for variant filtering (see [SQLite Tagging Cookbook](project/docs/sqlite_tagging_cookbook.md)).

**Skills Tagging**: Unlike flat sections, skills are stored as individual entries in the database. Each skill item can have its own `type_key` tags, enabling fine-grained filtering by skill. The Web UI displays skills grouped by category, and you can tag/untag individual skills.

### Other Sections

There are templates for:

- `language.tex` – language skills.
- `projects.tex` – projects overview.
- `certificates.tex` – certifications and awards.
- `publications.tex` – academic or professional publications.
- `references.tex` – references.

Their expected JSON structure follows the examples in `mahsa.json` and `ramin.json`. You can open each template under `templates/` to see exactly which keys are referenced and in what shape.

---

## Template System

### Jinja2 configuration

`generate_cv.py` sets up the Jinja2 environment with custom delimiters to avoid conflicts with LaTeX:

- **Blocks**: `<BLOCK> ... </BLOCK>`
- **Variables**: `<VAR> ... </VAR>`
- **Comments**: `/*/*/* ... */*/*/`

Key configuration in `generate_cv.py`:

```python
env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    block_start_string="<BLOCK>",
    block_end_string="</BLOCK>",
    variable_start_string="<VAR>",
    variable_end_string="</VAR>",
    comment_start_string="/*/*/*",
    comment_end_string="*/*/*/",
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    undefined=StrictUndefined,
)
```

Each JSON file is loaded into `data`, then expanded into `env_vars` (so top-level JSON keys become template variables). Additionally:

- `env_vars["OPT_NAME"] = <file base name>` (e.g. `"ramin"`), used for photo lookup.

### Available filters and helpers

The script registers several custom filters/globals:

- `latex_escape(s)` (filter)  
  Escapes LaTeX special characters: `\`, `&`, `%`, `$`, `#`, `_`, `{`, `}`, `~`, `^`.

- `file_exists(path)` (filter)  
  Returns `True` if the given path exists on disk.

- `debug(value)` / `types(value)` (filters)  
  Print debugging info to stdout during rendering; emit nothing in the LaTeX output.

- `cmt(s)` / `cblock(s)` (filters)  
  Emit single-line or multi-line LaTeX comments, gated by `SHOW_COMMENTS`.

- `find_pic(opt_name)` (filter)  
  Checks whether `./data/pics/<opt_name>.jpg` exists.

- `get_pic(opt_name)` (filter)  
  Returns the relative path `./data/pics/<opt_name>.jpg`.

You can use them in templates like:

```latex
<VAR> basics[0]["fname"] | latex_escape </VAR>
<BLOCK> if OPT_NAME | find_pic </BLOCK>
  \photo[circle,noedge,left]{<VAR> OPT_NAME | get_pic </VAR>}
<BLOCK> endif </BLOCK>
```

---

### Main LaTeX layout

`templates/layout.tex` is the root document:

- Uses `\documentclass[11pt, a4paper]{./awesome-cv}`.
- Reconfigures some macros and spacing for sections, bullets, and skills.
- Includes the header via:

  ```latex
  <VAR> header_section | default('') </VAR>
  ```

- Sets up the header and footer:

  ```latex
  \makecvheader

  \makecvfooter
    {\today}
    {<VAR> basics[0]["fname"] | latex_escape </VAR> <VAR> basics[0]["lname"] | latex_escape </VAR>~~~·~~~Curriculum Vitae}
    {\thepage}
  ```

- Inlines all section contents:

  ```latex
  <VAR> education_section    | default('') </VAR>
  <VAR> experience_section   | default('') </VAR>
  <VAR> publications_section | default('') </VAR>
  <VAR> language_section     | default('') </VAR>
  <VAR> certificates_section | default('') </VAR>
  <VAR> skills_section       | default('') </VAR>
  <VAR> projects_section     | default('') </VAR>
  <VAR> references_section   | default('') </VAR>
  ```

Each of these is filled by `generate_cv.py` after rendering the corresponding template file.

---

## Output and Intermediate Files

All generated artifacts are organized under a unified `output/` directory with a predictable structure:

```text
output/
  pdf/
    <profile_name>/
      <lang>/                    # en, de, fa
        <profile>_<lang>.pdf     # e.g., ramin_en.pdf
  latex/
    <profile_name>/
      <lang>/
        main.tex                 # Combined LaTeX document
        sections/                # Individual section .tex files
          header.tex
          education.tex
          ...
  logs/
    run_<datetime>.log           # Generation logs (optional)
```

### Example Output

After running `cvgen build`, you'll find:

- `output/pdf/ramin/en/ramin_en.pdf` – English PDF
- `output/pdf/ramin/de/ramin_de.pdf` – German PDF
- `output/pdf/ramin/fa/ramin_fa.pdf` – Persian PDF

### Keeping LaTeX Sources

By default, LaTeX intermediate files are cleaned up after PDF generation. To keep them for debugging:

```bash
cvgen build --keep-latex
```

This preserves the `.tex` files in `output/latex/<profile>/<lang>/`.

---

## Migration Notes

### Migrating from `result/` + `output/` to unified `output/`

**Prior versions** stored:
- Intermediate `.tex` files in `result/<name>/<lang>/sections/`
- Final PDFs directly in `output/<name>.pdf`

**Current version** uses:
- All artifacts under `output/` with subdirectories: `pdf/`, `latex/`, `json/`, `logs/`
- PDFs at `output/pdf/<name>/<lang>/<name>_<lang>.pdf`
- LaTeX sources (when kept) at `output/latex/<name>/<lang>/`

**What changed:**
1. The `result/` directory is no longer used
2. PDFs are organized by profile and language
3. The `--keep-intermediate` flag is now `--keep-latex`
4. All paths are managed by the `ArtifactPaths` class for consistency

**Backward compatibility:**
- Old `result/` directories can be safely deleted
- The CLI API remains the same, only the flag name changed
- PDF naming convention (`<name>_<lang>.pdf`) is preserved

---

## Common Pitfalls

Before diving into detailed troubleshooting, here are the most common issues new users encounter:

| Problem | Quick Fix |
|---------|-----------|
| **XeLaTeX not installed** | Install [TeX Live](https://www.tug.org/texlive/) (Linux/macOS) or [MiKTeX](https://miktex.org/) (Windows), then verify with `xelatex --version` |
| **Missing fonts** | Install Roboto and Source Sans Pro fonts (see [Installation](#installation)) |
| **Special characters break PDF** | Ensure templates use `| latex_escape` filter for user text containing `#`, `%`, `_`, `&`, `$` |
| **Windows path issues** | Use forward slashes in JSON paths, or escape backslashes (`\\`) |
| **Missing JSON fields** | Templates use `StrictUndefined`—all referenced keys must exist in your JSON |
| **PDF not generated** | Run `cvgen -v build` for verbose output, or `cvgen build --keep-latex` to inspect LaTeX logs |

For detailed solutions, see the [Troubleshooting](#troubleshooting) section below.

---

## Troubleshooting

### `xelatex` command not found

**Symptom**: Terminal shows something like:

> 'xelatex' is not recognized as an internal or external command

**Fix**:

- Install MiKTeX or TeX Live.
- Add the directory containing `xelatex.exe` to your `PATH`.
- Verify with:

  ```bash
  xelatex --version
  ```

### LaTeX compilation errors

**Symptom**: PDF is not produced, or LaTeX logs show errors.

Common causes:

- Unescaped special characters in JSON (e.g., `#`, `%`, `_`).
- Missing fields referenced in templates (due to `StrictUndefined`).

**Tips**:

- Wrap dynamic content with `| latex_escape` in templates when in doubt.
- Ensure all keys used in templates exist in your JSON data.
- Run:

  ```bash
  python generate_cv.py
  ```

  and watch for Jinja `TemplateError` messages, which include the template file name.

### Windows "Access is denied" when cleaning up

The script includes robust cleanup logic (`rmtree_reliable`) with:

- Read-only flag clearing via `attrib`.
- Multiple retries with exponential backoff.

If you still hit issues, ensure:

- You’re not keeping `output/latex/` open in an editor that locks files.
- OneDrive (or similar) isn’t aggressively syncing mid‑delete; pausing sync temporarily can help.

---

## Development Notes

### Package Structure

The project is organized as a Python package for maintainability and extensibility:

```text
cv_generator/
├─ project/
│  └─ src/cv_generator/     # Main package
│  ├─ __init__.py             # Package exports
│  ├─ cli.py                  # Command-line interface (cvgen)
│  ├─ generator.py            # CV generation orchestration
│  ├─ io.py                   # JSON loading and CV file discovery
│  ├─ jinja_env.py            # Jinja2 environment configuration
│  ├─ latex.py                # LaTeX compilation utilities
│  ├─ cleanup.py              # Directory cleanup (Windows-friendly)
│  ├─ paths.py                # Path resolution helpers
│  └─ errors.py               # Error types and exit codes
├─ tests/                     # Test suite
├─ pyproject.toml             # Package configuration
├─ generate_cv.py             # Backward-compatible wrapper
├─ templates/                 # LaTeX/Jinja2 templates
├─ data/cvs/                  # CV JSON files
└─ output/                    # Generated PDFs
```

### Installing for Development

```bash
# Install in editable mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest project/tests/
```

### Reproducible Builds

For reproducible builds with pinned dependency versions, use the lockfile:

```bash
# Install exact dependency versions from lockfile
pip install -r requirements-lock.txt

# Then install the package in editable mode
pip install -e . --no-deps
```

To regenerate the lockfile after updating `pyproject.toml`:

```bash
pip install pip-tools
pip-compile --extra=dev --output-file=requirements-lock.txt pyproject.toml
```

### Continuous Integration

This project uses GitHub Actions for CI. The workflow runs on:
- **Push** to `main`/`master`
- **Pull requests** targeting `main`/`master`

The CI pipeline includes:
- **Install Smoke Tests**: Verifies editable install works on Ubuntu, Windows, macOS with Python 3.9 and 3.12
- **Linting**: Checks code style with `ruff`
- **Testing**: Runs `pytest` across a matrix of:
  - Operating systems: Ubuntu, Windows, macOS
  - Python versions: 3.9, 3.10, 3.11, 3.12
- **Documentation**: Builds MkDocs documentation
- **Coverage**: Generates coverage reports (uploaded as artifacts)

The install smoke tests verify:
- Package installs correctly: `pip install -e ".[dev]"`
- No dependency conflicts: `pip check`
- Package imports: `python -c "import cv_generator; print(cv_generator.__version__)"`
- CLI works: `cvgen --help`

To run CI checks locally:

```bash
# Linting
ruff check .

# Tests with coverage
pytest project/tests/ --cov=project/src/cv_generator --cov-report=term-missing
```

### Adding a new section

1. Create a new template file in `templates/` (e.g. `volunteering.tex`).
2. Reference new JSON data in the template (`<VAR> volunteering ... </VAR>`).
3. The generator automatically picks up **all** `.tex` files in `templates/` as section templates.
4. Add a line to `layout.tex` to embed it:

   ```latex
   <VAR> volunteering_section | default('') </VAR>
   ```

### Debugging template data
  - Use `|debug` or `|types` filters in templates to understand what’s being passed in.
  - Example:

    ```latex
    <VAR> basics | debug </VAR>
    ```

- **Commenting in templates**:
  - Use LaTeX comments (`%`) or the `cmt` / `cblock` filters.
  - Toggle `SHOW_COMMENTS` in `project/src/cv_generator/jinja_env.py` to control whether these get emitted.

---

## Documentation

Full documentation is available at [project/docs/](project/docs/) or can be served locally:

```bash
# Install MkDocs (one-time)
pip install mkdocs mkdocs-material

# Serve documentation locally (from project directory)
cd project
mkdocs serve
# → Open http://127.0.0.1:8000

# Build static site
mkdocs build
# → Output in site/
```

### Documentation Structure

| Section | Description |
|---------|-------------|
| [Installation](project/docs/installation.md) | Detailed setup instructions |
| [Quick Start](project/docs/quickstart.md) | Get your first PDF in 5 minutes |
| [CLI Reference](project/docs/cli.md) | All commands and options |
| [JSON Schema](project/docs/json-schema.md) | Complete data format reference |
| [Templates](project/docs/templates.md) | Customization guide |
| [Languages](project/docs/languages.md) | Multilingual support (en/de/fa) |
| [SQLite Cookbook](project/docs/sqlite_tagging_cookbook.md) | Database and tagging system |
| [Troubleshooting](project/docs/troubleshooting.md) | Common issues and solutions |
| [Plugins](project/docs/plugins.md) | Extending CV Generator |
| [Configuration](project/docs/config-reference.md) | TOML config file reference |

---

## License

- The **Awesome-CV class** (`awesome-cv.cls`) is licensed under **LPPL v1.3c**: <http://www.latex-project.org/lppl>
- The **Awesome-CV template** design and layout are originally by:
  - Claud D. Park – <https://github.com/posquit0/Awesome-CV> – licensed under **CC BY-SA 4.0**.

For this repository’s own Python code and templates, choose and declare a license that fits your needs (e.g. MIT, Apache 2.0, GPL, etc.), and add a `LICENSE` file accordingly.

---

## Acknowledgements

- **Awesome-CV** by [posquit0](https://github.com/posquit0/Awesome-CV) for the class file and design.
- The Jinja2 project for the templating engine.
- LaTeX community and TeX distributions that make high‑quality PDF generation possible.

