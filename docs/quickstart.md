# Quick Start

Get your first PDF CV generated in under 5 minutes.

## Option 1: Quick Start with `cvgen init` (Recommended)

The fastest way to get started is with the `cvgen init` command:

```bash
# Create a new CV project
cvgen init ./my-cv --profile jane

# Navigate to the project
cd my-cv

# Edit your CV data
# Open cvs/jane.en.json in your favorite editor

# Build the PDF
cvgen build --input-dir cvs
```

Your PDF will be generated at `output/pdf/jane/en/jane_en.pdf`.

### What `cvgen init` Creates

```
my-cv/
├── cvs/
│   └── jane.en.json    # Your CV data (edit this!)
├── output/              # Build output directory
├── cv_generator.toml    # Configuration file
├── README.md            # Next steps documentation
└── .gitignore           # Git ignore rules
```

### Different Languages

Create a German CV project:

```bash
cvgen init ./german-cv --profile hans --lang de
```

---

## Option 2: Manual Setup

### Step 1: Prepare Your CV Data

Create a JSON file in `data/cvs/` with your CV information. Here's a minimal example:

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
    "description": "Full-stack development with Python and React"
  }]
}
```

Save as `data/cvs/jane.json`.

### Step 2: Generate the PDF

```bash
cvgen build --name jane
```

Or with verbose output:

```bash
cvgen -v build --name jane
```

### Step 3: Find Your PDF

The generated PDF is at:

```
output/pdf/jane/en/jane_en.pdf
```

## Common Workflows

### Generate All CVs

Process all JSON files in `data/cvs/`:

```bash
cvgen build
```

### Dry Run (Preview)

Render LaTeX without compiling to PDF:

```bash
cvgen build --dry-run
```

This is useful for debugging template issues.

### Keep LaTeX Sources

Keep the generated `.tex` files for inspection:

```bash
cvgen build --keep-latex
```

Files are saved to `output/latex/<name>/<lang>/`.

### Custom Directories

Use custom input/output paths:

```bash
cvgen build \
  --input-dir /path/to/cvs \
  --output-dir /path/to/output \
  --templates-dir /path/to/templates
```

## Adding a Profile Photo

1. Place your photo in `data/pics/` with the same name as your CV:
   - CV: `data/cvs/jane.json`
   - Photo: `data/pics/jane.jpg`

2. The photo will automatically appear in the header.

## Multiple Languages

Create language-specific CV files:

- `data/cvs/jane.json` (English, default)
- `data/cvs/jane_de.json` (German)
- `data/cvs/jane_fa.json` (Persian)

All versions will be processed:

```bash
cvgen build --name jane
```

This generates:
- `output/pdf/jane/en/jane_en.pdf`
- `output/pdf/jane/de/jane_de.pdf`
- `output/pdf/jane/fa/jane_fa.pdf`

## Next Steps

- [CLI Reference](cli.md) — All commands and options
- [JSON Schema](json-schema.md) — Complete data format
- [Templates](templates.md) — Customization guide
- [Troubleshooting](troubleshooting.md) — Common issues
