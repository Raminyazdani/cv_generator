# Contributing

Thank you for your interest in contributing to CV Generator! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.9+
- XeLaTeX (for PDF generation testing)
- Git

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/Raminyazdani/cv_generator.git
cd cv_generator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install with development dependencies
pip install -e ".[dev]"

# Verify installation
cvgen --version
pytest project/tests/ -q
```

## Code Quality

### Linting

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .
```

### Testing

Run the test suite with pytest:

```bash
# Run all tests
pytest project/tests/

# Run with coverage
pytest project/tests/ --cov=project/src/cv_generator --cov-report=term-missing

# Run specific test file
pytest project/tests/test_cli.py -v

# Run specific test
pytest project/tests/test_cli.py::test_build_command -v
```

### Pre-commit Checks

Before submitting a PR, ensure:

1. All tests pass: `pytest project/tests/ -q`
2. Linting passes: `ruff check .`
3. Documentation builds: `mkdocs build`

## Project Structure

```
cv_generator/
├── project/src/cv_generator/     # Main Python package
│   ├── cli.py            # Command-line interface
│   ├── generator.py      # CV generation logic
│   ├── jinja_env.py      # Jinja2 environment setup
│   ├── io.py             # JSON loading utilities
│   ├── db.py             # SQLite database layer
│   └── ...
├── templates/            # Jinja2/LaTeX templates
├── project/tests/                # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── e2e/              # End-to-end tests
├── docs/                 # MkDocs documentation
└── plugins/              # Plugin examples
```

## Making Changes

### Code Changes

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Add tests for new functionality
4. Run the test suite
5. Submit a pull request

### Documentation Changes

1. Edit files in `docs/`
2. Preview locally: `mkdocs serve`
3. Verify build: `mkdocs build`
4. Submit a pull request

### Template Changes

1. Edit templates in `templates/`
2. Test with sample CVs: `cvgen build --keep-latex`
3. Inspect generated LaTeX for correctness

## Adding New Features

### New CLI Command

1. Add command function in `project/src/cv_generator/cli.py`
2. Register in the argument parser
3. Add tests in `project/tests/test_cli.py`
4. Document in `docs/cli.md`

### New CV Section

1. Create template in `templates/` (e.g., `awards.tex`)
2. Add to layout in `templates/layout.tex`
3. Document JSON schema in `docs/json-schema.md`
4. Add example data to test fixtures

### New Plugin Hook

1. Define hook type in `project/src/cv_generator/hooks.py`
2. Add hook invocation in generator pipeline
3. Document in `docs/plugins.md`
4. Add tests

## Code Style

- Follow PEP 8 for Python code
- Use type hints where beneficial
- Write docstrings for public functions
- Keep functions focused and small
- Prefer descriptive variable names

## Commit Messages

Use clear, descriptive commit messages:

```
feat: add variant filtering for CV sections
fix: handle missing profile photos gracefully
docs: update CLI reference with new options
test: add integration tests for multilingual builds
```

## Pull Request Guidelines

- Keep PRs focused on a single change
- Include tests for new functionality
- Update documentation as needed
- Link related issues in the PR description
- Respond to review feedback promptly

## Getting Help

- Check existing [issues](https://github.com/Raminyazdani/cv_generator/issues)
- Read the [documentation](https://raminyazdani.github.io/cv_generator/)
- Open a new issue for bugs or feature requests

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).
