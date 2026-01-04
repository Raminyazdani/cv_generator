# CV Generator

**Transform structured JSON data into polished, professional PDF resumes** using the elegant [Awesome-CV](https://github.com/posquit0/Awesome-CV) LaTeX class. Write your CV once in JSON, generate beautiful PDFs in multiple languages, and create targeted versions for academia or industry—all from a single source of truth.

## Quick Start (5 lines to first PDF)

```bash
git clone https://github.com/Raminyazdani/cv_generator.git && cd cv_generator
pip install -e .
cvgen build --name ramin
# → output/pdf/ramin/en/ramin_en.pdf
```

!!! note "Prerequisites"
    Python 3.9+ and XeLaTeX must be installed. See [Installation](installation.md) for detailed setup.

## Features

| Feature | Description |
|---------|-------------|
| **Multi-CV support** | Generate PDFs for multiple people in batch |
| **Beautiful layout** | Uses the popular Awesome-CV LaTeX class |
| **Multilingual** | English, German, Persian with RTL support |
| **Variant filtering** | Create targeted versions (academic, industry) |
| **Profile photos** | Optional per-person images |
| **SQLite backend** | Database storage with tagging system |
| **Web UI** | Browse and manage CV data via local web interface |
| **Plugin system** | Extend functionality with custom hooks |

## How It Works

```
JSON CV Data → Jinja2 Templates → XeLaTeX → PDF
```

1. **Load** CV data from JSON files in `data/cvs/`
2. **Render** LaTeX using Jinja2 templates in `templates/`
3. **Compile** to PDF using XeLaTeX
4. **Output** organized PDFs to `output/pdf/<name>/<lang>/`

## Documentation

### Getting Started

- [Installation Guide](installation.md) — Detailed setup instructions
- [Quick Start](quickstart.md) — Get your first PDF in 5 minutes
- [Cookbook](example.md) — Copy-paste recipes for common workflows

### Guides

- [Templates](templates.md) — Customize CV appearance
- [Languages](languages.md) — Multilingual support (en/de/fa)
- [SQLite & Tagging](sqlite_tagging_cookbook.md) — Database and tagging system
- [Plugin Development](plugins.md) — Extend CV Generator

### Reference

- [CLI Reference](cli.md) — All commands and options
- [Configuration](config-reference.md) — TOML config file reference
- [JSON Schema](json-schema.md) — Complete data format reference
- [Troubleshooting](troubleshooting.md) — Common issues and solutions

### Contributing

- [Contributing Guide](contributing.md) — How to contribute
- [Changelog](changelog.md) — Version history

## Project Structure

```text
cv_generator/
├── src/cv_generator/     # Python package
├── templates/            # Jinja2/LaTeX templates
├── data/
│   ├── cvs/              # CV JSON files
│   └── pics/             # Profile photos
├── output/               # Generated PDFs
├── docs/                 # MkDocs documentation
└── plugins/              # Plugin examples
```

## License

- **Python code**: MIT License
- **Awesome-CV class**: LPPL v1.3c
- **Awesome-CV design**: CC BY-SA 4.0

## Acknowledgements

- [Awesome-CV](https://github.com/posquit0/Awesome-CV) by posquit0
- [Jinja2](https://jinja.palletsprojects.com/) templating engine
- The LaTeX community
