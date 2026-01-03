# CV Generator

Generate beautiful, professional PDF resumes from structured JSON using Jinja2 templates and the Awesome-CV LaTeX class.

## Overview

CV Generator transforms JSON CV data into polished PDF resumes by:

1. Loading CV data from JSON files in `data/cvs/`
2. Rendering LaTeX using Jinja2 templates in `templates/`
3. Compiling to PDF using XeLaTeX

The project supports multiple languages (English, German, Persian) with RTL support, making it ideal for international professionals.

## Features

- **Multi-CV support** — Generate PDFs for multiple people in batch
- **Beautiful layout** — Uses the popular Awesome-CV LaTeX class
- **Modular sections** — Separate templates for education, experience, skills, etc.
- **Multilingual** — Support for en/de/fa with RTL text direction
- **Profile photos** — Optional per-person images
- **Validation** — Check consistency across language versions
- **Database storage** — SQLite backend for CV data management

## Quick Start

```bash
# Install
pip install -e .

# Generate all CVs
cvgen build

# Generate a specific CV
cvgen build --name ramin

# Verbose output (INFO level)
cvgen -v build

# Quiet mode (errors only)
cvgen -q build

# Validate multilingual consistency
cvgen ensure --name ramin

# Extended help on topics
cvgen help build
cvgen help templates
```

## Requirements

- Python 3.9+
- XeLaTeX (TeX Live or MiKTeX)
- Jinja2 (installed automatically)

## Documentation

- [Installation Guide](installation.md)
- [Quick Start](quickstart.md)
- [CLI Reference](cli.md)
- [JSON Schema](json-schema.md)
- [Template Customization](templates.md)
- [Troubleshooting](troubleshooting.md)

## Project Structure

```text
cv_generator/
├── src/cv_generator/     # Python package
├── templates/            # Jinja2/LaTeX templates
├── data/
│   ├── cvs/              # CV JSON files
│   └── pics/             # Profile photos
├── output/               # Generated PDFs
└── docs/                 # Documentation
```

## License

- Python code: MIT License
- Awesome-CV class: LPPL v1.3c
- Awesome-CV design: CC BY-SA 4.0

## Acknowledgements

- [Awesome-CV](https://github.com/posquit0/Awesome-CV) by posquit0
- Jinja2 templating engine
- The LaTeX community
