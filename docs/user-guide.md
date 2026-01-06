# User Guide

This comprehensive guide walks through all features of CV Generator, from basic usage to advanced workflows.

## Table of Contents

- [Overview](#overview)
- [Creating Your First CV](#creating-your-first-cv)
- [CV Data Structure](#cv-data-structure)
- [Building PDFs](#building-pdfs)
- [Multi-Language CVs](#multi-language-cvs)
- [Variant Filtering](#variant-filtering)
- [Using the Web UI](#using-the-web-ui)
- [Profile Photos](#profile-photos)
- [Advanced Workflows](#advanced-workflows)

## Overview

CV Generator transforms structured JSON data into professional PDF resumes using:

1. **JSON files** — Your CV data (education, experience, skills, etc.)
2. **Jinja2 templates** — LaTeX templates with Jinja2 syntax
3. **XeLaTeX** — PDF compilation with Unicode support
4. **Awesome-CV** — Beautiful LaTeX class for professional CVs

### Workflow Diagram

```
JSON CV Data → Jinja2 Templates → XeLaTeX → PDF
     ↓              ↓                ↓
 data/cvs/      templates/       output/pdf/
```

## Creating Your First CV

### Option 1: Using `cvgen init` (Recommended)

The fastest way to start is with the `cvgen init` command:

```bash
# Create a new CV project
cvgen init ./my-cv --profile jane

# Navigate to the project
cd my-cv

# Edit your CV data
# Open cvs/jane.en.json in your editor

# Build the PDF
cvgen build --input-dir cvs
```

### Option 2: Manual Setup

1. **Create a JSON file** in `data/cvs/`:

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
    "studyType": "B.Sc.",
    "area": "Computer Science",
    "institution": "Stanford University",
    "location": "Stanford, CA",
    "startDate": "2015",
    "endDate": "2019"
  }],
  "experiences": [{
    "institution": "Tech Corp",
    "role": "Software Engineer",
    "location": "San Francisco, CA",
    "duration": "2019 – Present",
    "description": "Full-stack development"
  }]
}
```

2. **Save as** `data/cvs/jane.json`

3. **Generate the PDF**:

```bash
cvgen build --name jane
```

4. **Find your PDF** at `output/pdf/jane/en/jane_en.pdf`

## CV Data Structure

CV data is stored as JSON files. See [JSON Schema](json-schema.md) for the complete reference.

### Required Sections

| Section | Description |
|---------|-------------|
| `basics` | Personal information (name, contact, location) |

### Optional Sections

| Section | Description |
|---------|-------------|
| `profiles` | Social links (GitHub, LinkedIn, Google Scholar) |
| `education` | Academic history |
| `experiences` | Work experience |
| `skills` | Technical and soft skills |
| `languages` | Language proficiencies |
| `projects` | Personal/professional projects |
| `publications` | Academic publications |
| `workshop_and_certifications` | Certifications and courses |
| `references` | Professional references |

### Example: Adding Education

```json
{
  "education": [
    {
      "studyType": "M.Sc.",
      "area": "Computer Science",
      "institution": "Stanford University",
      "location": "Stanford, CA",
      "startDate": "2019",
      "endDate": "2021",
      "gpa": "3.9/4.0"
    },
    {
      "studyType": "B.Sc.",
      "area": "Software Engineering",
      "institution": "UC Berkeley",
      "location": "Berkeley, CA",
      "startDate": "2015",
      "endDate": "2019"
    }
  ]
}
```

### Example: Adding Skills

Skills use a nested structure: Section → Category → Items

```json
{
  "skills": {
    "Technical Skills": {
      "Programming": [
        {"short_name": "Python"},
        {"short_name": "JavaScript"},
        {"short_name": "Go"}
      ],
      "Frameworks": [
        {"short_name": "React"},
        {"short_name": "Django"}
      ]
    },
    "Soft Skills": {
      "Leadership": [
        {"short_name": "Team Management"},
        {"short_name": "Mentoring"}
      ]
    }
  }
}
```

## Building PDFs

### Basic Build

Generate all CVs:

```bash
cvgen build
```

### Build Specific CV

```bash
cvgen build --name jane
```

### Build with Verbose Output

```bash
cvgen -v build --name jane
```

### Dry Run (No PDF)

Render templates without compiling:

```bash
cvgen build --dry-run
```

### Keep LaTeX Sources

Keep `.tex` files for debugging:

```bash
cvgen build --keep-latex
```

Files are saved to `output/latex/<name>/<lang>/`.

### Watch Mode

Automatically rebuild on changes:

```bash
cvgen build --watch
```

## Multi-Language CVs

CV Generator supports multiple language versions of the same CV.

### Supported Languages

| Code | Language | Direction |
|------|----------|-----------|
| `en` | English | LTR |
| `de` | German | LTR |
| `fa` | Persian | RTL |

### Creating Language Versions

Create separate JSON files with language suffixes:

```
data/cvs/
├── jane.json       # English (default)
├── jane_de.json    # German
└── jane_fa.json    # Persian
```

### Building All Languages

```bash
cvgen build --name jane
```

This generates:
- `output/pdf/jane/en/jane_en.pdf`
- `output/pdf/jane/de/jane_de.pdf`
- `output/pdf/jane/fa/jane_fa.pdf`

### Validating Consistency

Check that all language versions have consistent structure:

```bash
cvgen ensure --name jane
```

See [Languages Guide](languages.md) for detailed multi-language support.

## Variant Filtering

Create targeted CV versions without modifying source JSON.

### Using Tags

Add `type_key` to entries for filtering:

```json
{
  "experiences": [
    {
      "institution": "University Lab",
      "role": "Research Assistant",
      "type_key": ["academic"]
    },
    {
      "institution": "Tech Startup",
      "role": "Software Engineer",
      "type_key": ["industry"]
    }
  ]
}
```

### Building with Variants

```bash
# Academic CV (only entries with "academic" tag)
cvgen build --name jane --variant academic

# Industry CV (only entries with "industry" tag)
cvgen build --name jane --variant industry
```

### How Filtering Works

- Entries with matching `type_key` → included
- Entries with `type_key` list containing the variant → included
- Entries without `type_key` → always included (universal)

See [SQLite Tagging Cookbook](sqlite_tagging_cookbook.md) for advanced tagging.

## Using the Web UI

CV Generator includes a web-based interface for managing CV data.

### Starting the Web UI

```bash
# Initialize database (first time)
cvgen db init

# Import CV data
cvgen db import

# Start the server
cvgen web tags
```

Open http://127.0.0.1:5000 in your browser.

### Web UI Features

| Feature | Description |
|---------|-------------|
| **Browse CVs** | View all persons and their CV sections |
| **Edit Entries** | Modify CV entries through forms |
| **Manage Tags** | Create, rename, and assign tags |
| **Export** | Preview and export CV data |
| **Diagnostics** | Check data health and consistency |

See [Web UI Cookbook](webui_cookbook.md) for detailed usage.

## Profile Photos

### Adding a Photo

1. Place your photo in `data/pics/` with the same name as your CV:
   - CV: `data/cvs/jane.json`
   - Photo: `data/pics/jane.jpg`

2. The photo appears automatically in the header.

### Photo Requirements

- **Format**: JPG (recommended)
- **Size**: Square aspect ratio works best
- **Location**: `data/pics/<name>.jpg`

### Fallback Photo

If no matching photo is found, the generator checks for `./profile_square.jpg` in the project root.

## Advanced Workflows

### Using Configuration Files

Create `cv_generator.toml` to reduce repetitive CLI flags:

```toml
[project]
name = "My CV Project"
default_lang = "en"

[paths]
cvs = "data/cvs"
templates = "templates"
output = "output"

[build]
keep_latex = false
```

See [Configuration Reference](config-reference.md) for all options.

### Profile Management

Set a default profile to avoid specifying `--name` every time:

```bash
# Set default profile
cvgen profile use jane

# Now 'cvgen build' uses jane automatically
cvgen build

# Clear the profile
cvgen profile clear
```

### Database Workflow

Store CV data in SQLite for querying and editing:

```bash
# Initialize database
cvgen db init

# Import CVs
cvgen db import

# Check health
cvgen db doctor

# Export with tags
cvgen db export --apply-tags
```

### Incremental Builds

Skip unchanged CVs for faster builds:

```bash
cvgen build --incremental
```

Force full rebuild:

```bash
cvgen build --no-incremental
```

### Custom Templates

1. Copy and modify templates in `templates/`
2. Use custom template directory:

```bash
cvgen build --templates-dir /path/to/custom/templates
```

See [Templates Guide](templates.md) for customization.

## Next Steps

- [CLI Reference](cli.md) — All commands and options
- [JSON Schema](json-schema.md) — Complete data format
- [Templates](templates.md) — Customize CV appearance
- [Troubleshooting](troubleshooting.md) — Common issues
