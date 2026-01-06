# CV Generator Cookbook

A practical, copy-paste-ready guide with complete scenarios and recipes for common (and edge) workflows.

---

## Table of Contents

1. [Install + Verify](#1-install-verify)
2. [Generate a Single CV](#2-generate-a-single-cv)
3. [Multi-Language Builds](#3-multi-language-builds)
4. [Batch Build Multiple Profiles](#4-batch-build-multiple-profiles)
5. [Validate / Ensure](#5-validate-ensure)
6. [Template Customization](#6-template-customization)
7. [Images](#7-images)
8. [Keep LaTeX Artifacts](#8-keep-latex-artifacts)
9. [Troubleshooting Recipes](#9-troubleshooting-recipes)
10. [Advanced: JSON ↔ SQLite](#10-advanced-json-sqlite)

---

## 1. Install + Verify

### 1.1 Editable Install

**Scenario**: Install the cv-generator package in development mode for local modifications.

**Command(s)**:
```bash
# Clone the repository
git clone https://github.com/Raminyazdani/cv_generator.git
cd cv_generator

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install in editable mode
pip install -e .
```

**What you get**:
- Package installed in editable mode
- `cvgen` CLI available in your PATH

**Notes**:
- Use `-e .` to enable live code changes without reinstalling
- Add `[dev]` for development dependencies: `pip install -e ".[dev]"`

---

### 1.2 Confirm CLI Exists

**Scenario**: Verify that the `cvgen` command is available.

**Command(s)**:
```bash
cvgen --version
```

**What you get**:
```
cvgen 1.0.0
```

**Notes**:
- If not found, ensure the virtual environment is activated
- Alternatively: `python -m cv_generator.cli --version`
- Check help with: `cvgen --help`

---

### 1.3 Confirm XeLaTeX Available

**Scenario**: Verify LaTeX compilation is possible.

**Command(s)**:
```bash
xelatex --version
```

**What you get**:
```
XeTeX 3.141592653-2.6-0.999995 (TeX Live 2023)
...
```

**Notes**:
- Install TeX Live (Linux/macOS) or MiKTeX (Windows) if not found
- On Linux: `sudo apt install texlive-xetex texlive-fonts-extra`
- On macOS: `brew install --cask mactex`
- Required fonts: Roboto, Source Sans Pro

---

## 2. Generate a Single CV

### 2.1 Default Language Build

**Scenario**: Generate a PDF for a single profile with default settings.

**Command(s)**:
```bash
cvgen build --name <PROFILE>
```

**Example**:
```bash
cvgen build --name ramin
```

**What you get**:
- `output/pdf/ramin/en/ramin_en.pdf`

**Notes**:
- Processes all language variants (en, de, fa) if they exist
- JSON file expected at `data/cvs/<PROFILE>.json`
- Without `--name`, all CVs in `data/cvs/` are built

---

### 2.2 Explicit Output Directory

**Scenario**: Save generated PDFs to a custom location.

**Command(s)**:
```bash
cvgen build --name <PROFILE> --output-dir <PATH>
```

**Example**:
```bash
cvgen build --name ramin --output-dir /tmp/cv_output
```

**What you get**:
- `/tmp/cv_output/pdf/ramin/en/ramin_en.pdf`
- `/tmp/cv_output/pdf/ramin/de/ramin_de.pdf` (if de exists)

**Notes**:
- Output structure is preserved: `<output>/pdf/<profile>/<lang>/<profile>_<lang>.pdf`
- Parent directories are created automatically
- Use absolute paths to avoid confusion

---

### 2.3 Verbose Mode

**Scenario**: See detailed progress during generation.

**Command(s)**:
```bash
cvgen -v build --name <PROFILE>
```

**Example**:
```bash
cvgen -v build --name ramin
```

**What you get**:
```
Input directory: data/cvs
Building CV for: ramin
Processing ramin_en...
PDF generated: output/pdf/ramin/en/ramin_en.pdf
```

**Notes**:
- `-v` or `--verbose` enables INFO level logging
- For more detail: `cvgen --debug build --name ramin`
- For errors only: `cvgen -q build --name ramin`

---

## 3. Multi-Language Builds

### 3.1 Generate EN/DE/FA in One Command

**Scenario**: Build all language variants for a multilingual profile.

**Command(s)**:
```bash
cvgen build --name <PROFILE>
```

**Example**:
```bash
cvgen build --name ramin
```

**What you get**:
- `output/pdf/ramin/en/ramin_en.pdf`
- `output/pdf/ramin/de/ramin_de.pdf`
- `output/pdf/ramin/fa/ramin_fa.pdf`

**Notes**:
- The generator automatically detects all language files for a profile
- Expected file patterns: `ramin.json`, `ramin_de.json`, `ramin_fa.json`
- Alternative: `ramin.en.json`, `ramin.de.json`, `ramin.fa.json`

---

### 3.2 File Naming Conventions

**Scenario**: Structure multilingual CV files correctly.

**File Layout (Flat Structure)**:
```
data/cvs/
├── ramin.json       # English (default)
├── ramin_de.json    # German
├── ramin_fa.json    # Persian
├── mahsa.json       # Another profile
```

**Alternative (i18n Structure)**:
```
data/cvs/
└── i18n/
    └── ramin/
        ├── cv.en.json
        ├── cv.de.json
        └── cv.fa.json
```

**Notes**:
- Flat structure is simpler for single-person repos
- i18n structure scales better for many profiles
- Both patterns are auto-detected

---

### 3.3 Language-Specific Output

**Scenario**: Find the correct output file for each language.

**Command(s)**:
```bash
cvgen build --name ramin
ls -la output/pdf/ramin/*/
```

**What you get**:
```
output/pdf/ramin/
├── en/
│   └── ramin_en.pdf
├── de/
│   └── ramin_de.pdf
└── fa/
    └── ramin_fa.pdf
```

**Notes**:
- Each language gets its own subdirectory
- PDF naming: `<profile>_<lang>.pdf`
- Persian (fa) uses RTL text direction

---

## 4. Batch Build Multiple Profiles

### 4.1 Build All Profiles

**Scenario**: Generate PDFs for everyone in the data directory.

**Command(s)**:
```bash
cvgen build
```

**What you get**:
- `output/pdf/ramin/en/ramin_en.pdf`
- `output/pdf/ramin/de/ramin_de.pdf`
- `output/pdf/mahsa/en/mahsa_en.pdf`
- (all profiles × all languages)

**Notes**:
- Processes every `.json` file in `data/cvs/`
- Failed builds are reported but don't stop the batch
- Use `-v` to track progress: `cvgen -v build`

---

### 4.2 Custom Input Directory

**Scenario**: Build from a folder of profiles outside the default location.

**Command(s)**:
```bash
cvgen build --input-dir <PATH>
```

**Example**:
```bash
cvgen build --input-dir /home/user/my_cvs
```

**What you get**:
- All `.json` files from the custom directory are processed
- PDFs written to default `output/` (or specify `--output-dir`)

**Notes**:
- Path can be absolute or relative
- Directory must contain valid CV JSON files
- Combine with `--name` to filter: `--input-dir /path --name jane`

---

### 4.3 Dry Run (No PDF Compilation)

**Scenario**: Test template rendering without running XeLaTeX.

**Command(s)**:
```bash
cvgen build --dry-run
```

**What you get**:
- Templates are rendered to `.tex` files
- XeLaTeX compilation is skipped
- LaTeX sources preserved in `output/latex/`

**Notes**:
- Useful for debugging template issues
- Faster than full builds for testing changes
- Combine with `--keep-latex` for inspection

---

### 4.4 Parallel Processing Note

**Scenario**: Speed up batch builds.

**Notes**:
- Currently, profiles are processed sequentially
- For parallel builds, run multiple `cvgen` instances:

```bash
# Example: parallel build with xargs
ls data/cvs/*.json | xargs -I{} basename {} .json | \
  xargs -P4 -I{} cvgen build --name {}
```

- Each `cvgen` invocation handles one profile
- Ensure output directories don't conflict

---

## 5. Validate / Ensure

### 5.1 Run Ensure Across EN/DE/FA

**Scenario**: Check that all language versions have consistent structure.

**Command(s)**:
```bash
cvgen ensure --name <PROFILE>
```

**Example**:
```bash
cvgen ensure --name ramin
```

**What you get** (all consistent):
```
✓ All language files are consistent!
```

**What you get** (issues found):
```
Found 3 issue(s):

=== Missing Keys/Paths ===
  [de] education[2] (hint: List item at index 2 missing in de version)

=== Extra Keys/Paths ===
  [fa] skills.Soft Skills.Management (hint: Unexpected key 'Management' - not a known translation)

Summary: 1 missing, 1 extra, 0 schema errors, 0 mapping issues
```

**Notes**:
- Exit code 0 = consistent, exit code 2 = mismatches found
- English (en) is the canonical/reference version
- Use in CI to catch translation drift

---

### 5.2 Validate Specific Languages

**Scenario**: Check only English and German versions.

**Command(s)**:
```bash
cvgen ensure --name <PROFILE> --langs en,de
```

**Example**:
```bash
cvgen ensure --name ramin --langs en,de
```

**What you get**:
- Comparison between `ramin.json` (en) and `ramin_de.json` (de)
- Persian file is ignored

**Notes**:
- First language in the list is the canonical reference
- Useful when not all translations are ready
- Languages: `en`, `de`, `fa` supported by default

---

### 5.3 JSON Output for Scripting

**Scenario**: Get machine-readable validation results.

**Command(s)**:
```bash
cvgen ensure --name <PROFILE> --format json
```

**Example**:
```bash
cvgen ensure --name ramin --format json
```

**What you get**:
```json
{
  "missing": [],
  "extra": [],
  "mapping_missing": [],
  "schema_key_errors": [],
  "summary": {
    "total_issues": 0,
    "missing_count": 0,
    "extra_count": 0,
    "mapping_missing_count": 0,
    "schema_key_errors_count": 0
  }
}
```

**Notes**:
- Pipe to `jq` for processing: `cvgen ensure --name ramin -f json | jq .summary`
- Integrate with CI/CD pipelines
- Check exit code: `if cvgen ensure --name ramin; then echo "OK"; fi`

---

### 5.4 Using Custom Language Mapping

**Scenario**: Provide translations for skill headings.

**Sample `lang.json`**:
```json
{
  "Technical Skills": {
    "de": "Technische Fähigkeiten",
    "fa": "مهارت‌های فنی"
  },
  "Soft Skills": {
    "de": "Soft Skills",
    "fa": "مهارت‌های نرم"
  },
  "Programming": {
    "de": "Programmierung",
    "fa": "برنامه‌نویسی"
  }
}
```

**Command(s)**:
```bash
cvgen ensure --name <PROFILE> --lang-map <PATH>
```

**Example**:
```bash
cvgen ensure --name ramin --lang-map data/cvs/lang.json
```

**Notes**:
- Maps English skill headings to translations
- Without mapping, keys must match exactly across languages
- Default mapping at `src/cv_generator/lang_engine/lang.json`

---

## 6. Template Customization

### 6.1 Custom Templates Directory

**Scenario**: Use modified templates for a specific build.

**Command(s)**:
```bash
cvgen build --name <PROFILE> --templates-dir <PATH>
```

**Example**:
```bash
# Copy default templates
cp -r templates/ my_templates/

# Modify as needed
nano my_templates/header.tex

# Build with custom templates
cvgen build --name ramin --templates-dir my_templates
```

**What you get**:
- PDF generated using custom templates
- Default templates remain unchanged

**Notes**:
- Template directory must contain `layout.tex` and section files
- Uses custom Jinja2 delimiters to avoid LaTeX conflicts: `<VAR>`, `<BLOCK>`, `/*/*/*...*/*/*/`
- See `cvgen help templates` for syntax details

---

### 6.2 Template Structure

**Scenario**: Understand which files to modify.

**Template Files**:
```
templates/
├── layout.tex        # Main document structure
├── header.tex        # Personal info + social links
├── education.tex     # Education section
├── experience.tex    # Work experience
├── skills.tex        # Technical/soft skills
├── language.tex      # Language proficiencies
├── projects.tex      # Projects
├── certificates.tex  # Certifications
├── publications.tex  # Academic publications
└── references.tex    # References
```

**Notes**:
- Each section file is optional; missing sections are skipped
- Add new sections by creating `templates/newsection.tex`
- Reference in `layout.tex`: `<VAR> newsection_section | default('') </VAR>`

---

### 6.3 Jinja2 Filters Available

**Scenario**: Use template helpers for dynamic content.

**Common Filters**:
```latex
%% Escape LaTeX special characters
<VAR> text | latex_escape </VAR>

%% Check if file exists
<BLOCK> if OPT_NAME | find_pic </BLOCK>
  \photo{<VAR> OPT_NAME | get_pic </VAR>}
<BLOCK> endif </BLOCK>

%% Default value for optional fields
<VAR> optional_field | default('N/A') </VAR>

%% Debug output (printed to console)
<VAR> skills | debug </VAR>
```

**Notes**:
- `latex_escape`: escapes `#`, `%`, `_`, `&`, `$`, `^`, `~`, `{`, `}`, `\`
- `find_pic` / `get_pic`: profile photo helpers
- `debug`: prints value during rendering (not in output)

---

## 7. Images

### 7.1 With Profile Photo

**Scenario**: Add a profile picture to the CV.

**Setup**:
```
data/cvs/ramin.json    # CV data
data/pics/ramin.jpg    # Profile photo (JPG format)
```

**Command(s)**:
```bash
cvgen build --name ramin
```

**What you get**:
- PDF with profile photo in the header
- Photo is circular with Awesome-CV styling

**Notes**:
- File names must match: `ramin.json` → `ramin.jpg`
- Only JPG format is supported
- Recommended size: 200×200 pixels or larger

---

### 7.2 Missing Photo Behavior

**Scenario**: Build a CV when the profile photo doesn't exist.

**Setup**:
```
data/cvs/jane.json    # CV data exists
# data/pics/jane.jpg  # Photo does NOT exist
```

**Command(s)**:
```bash
cvgen build --name jane
```

**What you get**:
- PDF generated successfully (no error)
- Header renders without photo

**Notes**:
- Missing photos are silently skipped
- Use verbose mode to see photo detection: `cvgen -v build`
- Template uses `find_pic` to check existence before rendering

---

### 7.3 Fallback Profile Photo

**Scenario**: Use a default photo when individual photo is missing.

**Setup**:
```
# Place a fallback photo at repo root
profile_square.jpg
```

**Notes**:
- The `header.tex` template checks for `./profile_square.jpg` as fallback
- This is only used if `data/pics/<name>.jpg` doesn't exist
- Customize behavior by editing `templates/header.tex`

---

## 8. Keep LaTeX Artifacts

### 8.1 Keep LaTeX Source Files

**Scenario**: Preserve generated `.tex` files for debugging or manual editing.

**Command(s)**:
```bash
cvgen build --name <PROFILE> --keep-latex
```

**Example**:
```bash
cvgen build --name ramin --keep-latex
```

**What you get**:
```
output/
├── pdf/ramin/en/ramin_en.pdf
└── latex/
    └── ramin/
        └── en/
            ├── main.tex           # Combined document
            └── sections/
                ├── header.tex
                ├── education.tex
                ├── experience.tex
                ├── skills.tex
                └── ...
```

**Notes**:
- Default behavior: LaTeX files are deleted after PDF compilation
- Use `--keep-latex` or `-k` to preserve them
- Useful for debugging compilation errors

---

### 8.2 Inspect LaTeX Output

**Scenario**: Review the generated LaTeX before compilation.

**Command(s)**:
```bash
# Generate without compiling
cvgen build --name ramin --dry-run --keep-latex

# View the main document
cat output/latex/ramin/en/main.tex

# Or open in editor
code output/latex/ramin/en/
```

**What you get**:
- Complete LaTeX document with all sections embedded
- Individual section files in `sections/` subdirectory

**Notes**:
- `--dry-run` skips XeLaTeX compilation
- Combined with `--keep-latex`, allows template inspection
- Edit and manually compile: `xelatex main.tex`

---

### 8.3 LaTeX Log Location

**Scenario**: Find compilation logs when PDF generation fails.

**Command(s)**:
```bash
cvgen build --name ramin --keep-latex
cat output/latex/ramin/en/main.log
```

**What you get**:
- Full XeLaTeX log with warnings and errors
- Line numbers pointing to problematic LaTeX

**Notes**:
- Log file is only preserved with `--keep-latex`
- Search for "Error" or "!" to find issues
- Also check `main.aux`, `main.out` for auxiliary files

---

## 9. Troubleshooting Recipes

### 9.1 LaTeX Compile Error: Finding Logs

**Scenario**: PDF generation fails with LaTeX errors.

**Command(s)**:
```bash
# Run with keep-latex to preserve logs
cvgen build --name <PROFILE> --keep-latex

# Find the log file
cat output/latex/<PROFILE>/en/main.log | grep -A5 "^!"
```

**What you get**:
```
! Missing $ inserted.
<inserted text>
                $
l.42 ...ogramming experience: 5+ years (C#, Python)
```

**Notes**:
- Line number (l.42) helps locate the issue
- Common causes: unescaped `#`, `%`, `_`, `&`, `$`
- Fix: use `| latex_escape` filter or escape in JSON

---

### 9.2 Missing Fonts

**Scenario**: Font warnings in LaTeX output.

**Symptom**:
```
LaTeX Font Warning: Font shape 'TU/Roboto' undefined
```

**Solution**:
```bash
# Linux
sudo apt install fonts-roboto fonts-font-awesome

# macOS
brew install font-roboto font-source-sans-pro

# Windows: Download from Google Fonts and install
```

**Notes**:
- Awesome-CV uses Roboto and Source Sans Pro fonts
- Font Awesome for icons (optional)
- After installing, rebuild: `cvgen build --name <PROFILE>`

---

### 9.3 Special Characters in JSON Needing Escaping

**Scenario**: Handle LaTeX special characters in your CV data.

**Problematic JSON**:
```json
{
  "description": "Improved performance by 50% using C# & Python"
}
```

**Option 1: Escape in JSON**:
```json
{
  "description": "Improved performance by 50\\% using C\\# \\& Python"
}
```

**Option 2: Template Filter (Preferred)**:
```latex
<VAR> item.description | latex_escape </VAR>
```

**LaTeX Special Characters**:
| Character | Escaped | Description |
|-----------|---------|-------------|
| `#` | `\#` | Hash |
| `%` | `\%` | Percent |
| `_` | `\_` | Underscore |
| `&` | `\&` | Ampersand |
| `$` | `\$` | Dollar |
| `^` | `\^{}` | Caret |
| `~` | `\textasciitilde{}` | Tilde |
| `{` | `\{` | Left brace |
| `}` | `\}` | Right brace |
| `\` | `\textbackslash{}` | Backslash |

**Notes**:
- Default templates already use `latex_escape` for most fields
- Check `templates/*.tex` to verify filter usage
- When in doubt, use the filter on any user-provided text

---

### 9.4 Template Rendering Errors

**Scenario**: Jinja2 template error during generation.

**Symptom**:
```
jinja2.exceptions.UndefinedError: 'publications' is undefined
```

**Command to Debug**:
```bash
cvgen --debug build --name <PROFILE>
```

**Solution Options**:

1. Add the missing section to your JSON:
```json
{
  "publications": []
}
```

2. Use default filter in template:
```latex
<VAR> publications | default([]) </VAR>
```

3. Use conditional blocks:
```latex
<BLOCK> if publications is defined and publications|length > 0 </BLOCK>
  ...
<BLOCK> endif </BLOCK>
```

**Notes**:
- Templates use `StrictUndefined` to catch missing fields early
- This is intentional to avoid silent failures
- Check `data/cvs/ramin.json` for expected structure

---

### 9.5 Windows File Lock Issues

**Scenario**: "Access is denied" when cleaning up output files.

**Symptom**:
```
PermissionError: [WinError 5] Access is denied: 'output\\latex\\ramin'
```

**Solutions**:
1. Close any editors that have files open in `output/`
2. Pause OneDrive or other cloud sync temporarily
3. Run again (generator has automatic retry logic)

**Command with verbose output**:
```bash
cvgen -v build --name ramin
```

**Notes**:
- Generator uses `rmtree_reliable` with retries and backoff
- Antivirus scanning can cause temporary locks
- Consider excluding `output/` from real-time scanning

---

## 10. Advanced: JSON ↔ SQLite

### 10.1 Initialize the Database

**Scenario**: Create a new SQLite database for CV management.

**Command(s)**:
```bash
cvgen db init
```

**What you get**:
```
✅ Database initialized: data/db/cv.db
```

**Notes**:
- Default location: `data/db/cv.db`
- Use `--db <PATH>` for custom location
- Use `--force` to recreate if exists

---

### 10.2 Import JSON to Database

**Scenario**: Load CV JSON files into SQLite for querying and editing.

**Command(s)**:
```bash
# Import all CVs
cvgen db import

# Import specific profile
cvgen db import --name <PROFILE>
```

**Example**:
```bash
cvgen db import --name ramin
```

**What you get**:
```
📥 Import Results:
   Files processed: 3
   Total entries: 42
   ✅ ramin.json: 14 entries
   ✅ ramin_de.json: 14 entries
   ✅ ramin_fa.json: 14 entries
```

**Notes**:
- Each CV section becomes database entries
- Tags extracted from `type_key` fields
- Use `--overwrite` to replace existing entries

---

### 10.3 List Database Contents

**Scenario**: See what's in the database.

**Command(s)**:
```bash
# List all persons
cvgen db list

# List all tags
cvgen db list --what tags
```

**What you get**:
```
👥 Persons in database: 2
   • ramin: 14 entries
     Name: Ramin Yazdani
   • ramin_de: 14 entries
     Name: Ramin Yazdani

🏷️  Tags in database: 8
   • Academic: used 5 times
   • Bioinformatics: used 3 times
   • Full CV: used 10 times
   ...
```

**Notes**:
- Persons are stored by slug (profile name)
- Tags come from `type_key` arrays in JSON
- Use `--format json` for machine-readable output

---

### 10.4 Edit Tags (Web UI)

**Scenario**: Manage tags using a web interface.

**Command(s)**:
```bash
cvgen web tags
```

**What you get**:
```
 * Running on http://127.0.0.1:5000
```

Open in browser to:
- View all entries by section
- Add/remove tags on entries
- Create new tags
- Search and filter

**Notes**:
- Requires database to be initialized and populated
- Use `--port <PORT>` for custom port
- Use `--host 0.0.0.0` for LAN access

---

### 10.5 Export Database to JSON

**Scenario**: Export modified data back to JSON files.

**Command(s)**:
```bash
# Export all persons
cvgen db export

# Export specific profile
cvgen db export --name <PROFILE>

# Export to custom directory
cvgen db export --output-dir <PATH>
```

**Example**:
```bash
cvgen db export --name ramin --output-dir ./exported
```

**What you get**:
```
📤 Export Results:
   Files exported: 1
   ✅ ramin.json
```

**Notes**:
- Exports reconstruct JSON from database entries
- Use `--format min` for minified JSON
- Changes made via web UI are included

---

### 10.6 Compare JSON with Database

**Scenario**: Check if JSON files match database exports.

**Command(s)**:
```bash
cvgen db diff
```

**What you get** (no differences):
```
🔍 Diff Results:
   Files compared: 3
   Matches: 3
   Mismatches: 0
   ✅ ramin.json: Match
   ✅ ramin_de.json: Match
   ✅ ramin_fa.json: Match
```

**What you get** (with differences):
```
🔍 Diff Results:
   Files compared: 1
   Matches: 0
   Mismatches: 1
   ❌ ramin.json: 2 differences
      - education[0].gpa: value_changed
      - skills.Technical Skills.Programming[0].short_name: value_changed
```

**Notes**:
- Use after editing via web UI to see changes
- Exit code 2 if mismatches found
- Use `--format json` for detailed diff output

---

### 10.7 Complete DB Workflow

**Scenario**: Full round-trip from JSON to database and back.

**Command(s)**:
```bash
# 1. Initialize database
cvgen db init

# 2. Import all CVs
cvgen db import

# 3. Start web UI to edit tags
cvgen web tags
# (make edits in browser, then Ctrl+C)

# 4. Check what changed
cvgen db diff

# 5. Export back to JSON
cvgen db export --output-dir data/cvs

# 6. Rebuild PDFs with new data
cvgen build
```

**Notes**:
- Database stores structured entries with tags
- Web UI provides visual tag management
- Export preserves all data including tag changes
- Use version control to track JSON changes

---

## Sample JSON Snippet

For reference, here's a minimal CV JSON structure:

```json
{
  "basics": [{
    "fname": "Jane",
    "lname": "Doe",
    "label": ["Software Engineer"],
    "email": "jane@example.com",
    "phone": {"formatted": "+1 555-0100"},
    "location": [{
      "city": "San Francisco",
      "region": "CA",
      "country": "USA"
    }]
  }],
  "education": [{
    "studyType": "M.Sc.",
    "area": "Computer Science",
    "institution": "Stanford University",
    "location": "Stanford, CA",
    "startDate": "2018",
    "endDate": "2020"
  }],
  "experiences": [{
    "institution": "Tech Corp",
    "role": "Senior Engineer",
    "location": "San Francisco, CA",
    "duration": "2020 – Present",
    "primaryFocus": "Backend development",
    "description": "Built scalable microservices"
  }],
  "skills": {
    "Technical Skills": {
      "Programming": [
        {"short_name": "Python", "long_name": "Python 3.x"},
        {"short_name": "Go"}
      ]
    }
  }
}
```

---

## Self-Audit Checklist

- [x] Every example uses real commands/flags verified against CLI source
- [x] Output paths match the unified `output/pdf/<profile>/<lang>/` structure
- [x] Placeholders (`<PROFILE>`, `<PATH>`, `<LANG>`) are consistent
- [x] Each recipe follows the template: Scenario → Commands → What you get → Notes
