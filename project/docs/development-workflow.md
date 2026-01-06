# Development Workflow

This guide explains the editable install workflow for CV Generator developers and contributors.

## Quick Reference

| Action | Command |
|--------|---------|
| First-time setup | `pip install -e ".[dev]"` |
| Daily development | Just edit `.py` files (no reinstall needed!) |
| Dependencies changed | `pip install -e ".[dev]"` |
| Update from Git | `git pull && pip install -e ".[dev]"` |
| Clean environment | Delete `.venv`, recreate, reinstall |

## First-Time Setup

```bash
# 1. Clone the repository
git clone https://github.com/Raminyazdani/cv_generator.git
cd cv_generator

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate the environment
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat

# 4. Install in editable mode with dev dependencies
pip install -e ".[dev]"

# 5. Verify installation
cvgen --version
python -c "import cv_generator; print(cv_generator.__version__)"
```

## Understanding Editable Installs

When you run `pip install -e .` (editable mode), Python creates a link to your source code instead of copying it. This means:

- **Code changes reflect immediately** — Edit any `.py` file and re-run `cvgen` to see changes
- **No reinstall needed for code** — The link stays valid as long as the environment exists
- **Entry points work from anywhere** — `cvgen` command works from any directory

### When You DO NOT Need to Reinstall

✅ No reinstall needed for:

- Editing `.py` source files
- Editing templates in `templates/`
- Editing config files
- Adding new modules within existing packages
- Fixing bugs or adding features in existing code

### When You DO Need to Reinstall

⚠️ Reinstall required for:

| Change Type | Solution |
|-------------|----------|
| **Dependencies changed** (`pyproject.toml` requirements) | `pip install -e ".[dev]"` |
| **Entry points changed** (CLI commands in `pyproject.toml`) | `pip install -e ".[dev]"` |
| **Package metadata changed** (version, name, etc.) | `pip install -e ".[dev]"` |
| **New environment created** | `pip install -e ".[dev]"` |
| **Switched Python interpreter** | Recreate venv and reinstall |
| **Package structure changed** (new subpackages) | `pip install -e ".[dev]"` |

## Daily Development Workflow

Once installed, your daily workflow is simple:

```bash
# Activate environment (if not already active)
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Edit code...
# Then just run to test:
cvgen build --name ramin

# Run tests
pytest project/tests/ -q

# Check code style
ruff check .
```

## Updating from Git

When you pull new changes from the repository:

```bash
# Get latest changes
git pull

# Check if pyproject.toml changed
git diff HEAD~1 pyproject.toml

# If dependencies/entry points changed, reinstall:
pip install -e ".[dev]"

# If only code changed, no action needed!
```

### Quick Update Script

For convenience, you can always run:

```bash
git pull && pip install -e ".[dev]"
```

This is safe to run even if dependencies haven't changed — pip will recognize the package is already installed and finish quickly.

## Sync Dependencies Command

To ensure your environment matches the project requirements:

```bash
# Sync all dependencies (install new, upgrade existing)
pip install -e ".[dev]" --upgrade

# Or for reproducible builds, use the lockfile:
pip install -r requirements-lock.txt
pip install -e . --no-deps
```

## Troubleshooting

### `cvgen` command not found

**Cause:** Virtual environment not activated, or package not installed.

**Solution:**
```bash
# Check if venv is activated
which python  # Linux/macOS
where python  # Windows

# Activate if needed
source .venv/bin/activate

# Reinstall if needed
pip install -e ".[dev]"
```

### Import errors from repo root

**Cause:** Not using editable install, or wrong Python interpreter.

**Solution:**
```bash
# Verify editable install
pip show cv-generator

# Should show:
# Location: /path/to/cv_generator/src

# If "Editable project location" shows, it's installed correctly
```

### Changes not reflected

**Cause:** Using wrong environment, or package not in editable mode.

**Solution:**
```bash
# Check which cv_generator is being used
python -c "import cv_generator; print(cv_generator.__file__)"

# Should point to your local src/ directory, not site-packages
```

### Dependency conflicts

**Cause:** Incompatible package versions.

**Solution:**
```bash
# Check for issues
pip check

# If conflicts found, recreate environment:
deactivate  # Exit current venv
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Windows PowerShell execution policy

**Cause:** PowerShell blocks running scripts.

**Solution:**
```powershell
# Allow scripts for current user
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate normally
.venv\Scripts\Activate.ps1
```

## Verifying Your Setup

Run these commands to verify your installation is correct:

```bash
# 1. Package imports correctly
python -c "import cv_generator; print(cv_generator.__version__)"
# Should print the current version (e.g., 1.0.0)

# 2. CLI works
cvgen --help
# Should show help output

# 3. Dependencies are satisfied
pip check
# Should print: No broken requirements found.

# 4. Tests pass
pytest project/tests/ -q
# Should show all tests passing

# 5. Linting passes
ruff check .
# Should show no errors
```

## CI Verification

The CI pipeline automatically verifies:

1. Editable install works on Ubuntu, Windows, and macOS
2. Package imports correctly across Python 3.9-3.12
3. CLI runs (`cvgen --help`)
4. No dependency conflicts (`pip check`)
5. All tests pass
6. Code passes linting

If CI passes, you can trust that the installation workflow is working correctly.
