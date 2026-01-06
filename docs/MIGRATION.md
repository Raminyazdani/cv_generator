# Migration Guide

This guide explains migration paths for CV Generator, including deprecated scripts and configuration changes.

---

## Deprecated: generate_cv.py Script

**⚠️ DEPRECATION NOTICE**: The `generate_cv.py` script is deprecated and will be removed in v3.0.0.

### Why is it deprecated?

The new `cvgen` CLI provides:
- Better error messages
- More features (variants, caching, incremental builds)
- Improved performance
- Active development and support

### Migration Steps

Replace your `generate_cv.py` commands with the `cvgen` CLI:

| Old Command | New Command |
|-------------|-------------|
| `python generate_cv.py` | `cvgen build` |
| `python generate_cv.py --name ramin` | `cvgen build --name ramin` |
| `python generate_cv.py --help` | `cvgen build --help` |

### Examples

```bash
# OLD (deprecated)
python generate_cv.py --name ramin

# NEW (recommended)
cvgen build --name ramin --lang en
```

### What happens if I still use generate_cv.py?

The script will continue to work but will display a deprecation warning at runtime. The warning includes:
- A visual banner alerting you to the deprecation
- A Python `DeprecationWarning` for programmatic detection
- A 2-second pause to ensure visibility

### Timeline

- **v1.0.0 - v2.x.x**: `generate_cv.py` works with deprecation warning
- **v3.0.0**: `generate_cv.py` will be removed

---

## Path Flexibility

This section explains how to migrate from the hardcoded `data/` directory structure to the new flexible path configuration system.

### Overview

CV Generator v1.0+ introduces flexible path configuration, allowing you to:
- Store CV data outside the repository
- Use environment variables for deployment
- Support system-wide installations
- Maintain backward compatibility with existing setups

## Backward Compatibility

**No immediate action required!** If you have an existing `data/` directory, everything will continue to work exactly as before. The new system automatically detects and uses your existing structure.

## Path Resolution Precedence

Paths are resolved in this order (first match wins):

1. **CLI flags** - Explicit command-line arguments
2. **Environment variables** - `CVGEN_*` variables
3. **Configuration file** - `cv_generator.toml`
4. **Legacy data/ directory** - Existing structure (backward compatibility)
5. **User home directory** - `~/.cvgen/`
6. **Current directory** - `./` (for some paths)

## Migration Options

### Option 1: Keep Using data/ (No Changes)

Continue using your existing setup. The tool automatically detects and uses your `data/` directory.

```bash
# Works exactly as before
cvgen build --name ramin
```

### Option 2: Use Environment Variables

Great for deployments and CI/CD pipelines:

```bash
# Set base data directory
export CVGEN_DATA_DIR=/var/lib/cv_generator/data

# Or set individual directories
export CVGEN_CVS_DIR=/var/lib/cv_generator/cvs
export CVGEN_PICS_DIR=/var/lib/cv_generator/pics
export CVGEN_DB_PATH=/var/lib/cv_generator/db/cv.db

cvgen build --name ramin
```

### Option 3: Use Configuration File

Create `cv_generator.toml` in your project root:

```toml
[paths]
cvs_dir = "~/my_cvs"
pics_dir = "~/my_pics"
output_dir = "./output"
```

Then run:

```bash
cvgen build --name ramin
```

### Option 4: Use CLI Flags

Specify paths explicitly for each run:

```bash
cvgen build \
  --name ramin \
  --cvs-dir /custom/cvs \
  --pics-dir /custom/pics \
  --output-dir /custom/output
```

### Option 5: Use ~/.cvgen/ (Recommended for Personal Use)

Create user-level directories:

```bash
mkdir -p ~/.cvgen/{cvs,pics,db,templates,assets}

# Copy your data
cp -r data/cvs/* ~/.cvgen/cvs/
cp -r data/pics/* ~/.cvgen/pics/
cp -r data/db/* ~/.cvgen/db/

# Now you can delete the data/ directory if desired
cvgen build --name ramin
```

## Migration Checklist

### For Repository Users

- [ ] No action needed - data/ continues to work
- [ ] Optional: Create cv_generator.toml for your preferences
- [ ] Optional: Add cv_generator.toml to .gitignore if it contains local paths

### For System-Wide Installation

- [ ] Decide on installation directory (e.g., `/opt/cv_generator` or `/var/lib/cv_generator`)
- [ ] Copy templates and assets to installation directory
- [ ] Set environment variables in systemd service or init script
- [ ] Create systemd drop-in with environment variables:

```ini
# /etc/systemd/system/cvgen.service.d/paths.conf
[Service]
Environment="CVGEN_DATA_DIR=/var/lib/cv_generator"
Environment="CVGEN_TEMPLATES_DIR=/opt/cv_generator/templates"
```

### For Docker Deployments

```dockerfile
FROM python:3.11

# Install cv_generator
RUN pip install cv-generator

# Set environment variables
ENV CVGEN_DATA_DIR=/app/data
ENV CVGEN_OUTPUT_DIR=/app/output

# Create directories
RUN mkdir -p /app/data/cvs /app/data/pics /app/output

# Mount volumes at runtime
VOLUME ["/app/data", "/app/output"]
```

## Environment Variables Reference

### Individual Paths

- `CVGEN_CVS_DIR` - Directory containing CV JSON files
- `CVGEN_PICS_DIR` - Directory containing profile pictures
- `CVGEN_DB_PATH` - Path to SQLite database
- `CVGEN_TEMPLATES_DIR` - LaTeX templates directory
- `CVGEN_OUTPUT_DIR` - Output directory for generated files
- `CVGEN_ASSETS_DIR` - Assets directory (logos, etc.)

### Base Directory

- `CVGEN_DATA_DIR` - Base directory, automatically appends `/cvs`, `/pics`, etc.

Example:
```bash
export CVGEN_DATA_DIR=/var/lib/cvgen
# Automatically resolves to:
#   CVS: /var/lib/cvgen/cvs
#   Pics: /var/lib/cvgen/pics
#   DB: /var/lib/cvgen/db/cv.db
#   Assets: /var/lib/cvgen/assets
```

## CLI Flags Reference

All commands that work with paths now support these flags:

```bash
--cvs-dir PATH          # CV JSON files directory
--pics-dir PATH         # Profile pictures directory
--db-path PATH          # Database file path
--templates-dir PATH    # LaTeX templates directory
--output-dir PATH       # Output directory
--assets-dir PATH       # Assets directory
--config PATH           # Configuration file
```

## Troubleshooting

### "Cannot find CVs directory"

The tool cannot locate your CV files. Solutions:

1. Check if data/cvs exists: `ls data/cvs`
2. Create ~/.cvgen/cvs: `mkdir -p ~/.cvgen/cvs`
3. Specify explicitly: `--cvs-dir /path/to/cvs`
4. Set environment: `export CVGEN_CVS_DIR=/path/to/cvs`

### "Templates directory not found"

Templates are required for PDF generation:

1. Check if templates/ exists in repo
2. Set environment: `export CVGEN_TEMPLATES_DIR=/path/to/templates`
3. Copy from repo: `cp -r templates ~/.cvgen/`

### Pictures Not Showing in PDF

The tool will look for pictures in multiple locations:

1. Explicitly specified: `--pics-dir /path/to/pics`
2. Environment: `CVGEN_PICS_DIR`
3. Legacy: `data/pics` (if exists)
4. User home: `~/.cvgen/pics`

Ensure your picture files are named correctly: `<profile_name>.jpg`

## Examples

### Example 1: Developer Setup

Keep using data/ during development:

```bash
git clone https://github.com/user/cv_generator
cd cv_generator
cvgen build --name myname  # Uses data/ automatically
```

### Example 2: Multi-User Server

Each user has their own CV data:

```bash
# User 1
export CVGEN_DATA_DIR=~/cv_data
cvgen build --name user1

# User 2  
export CVGEN_DATA_DIR=~/cv_data
cvgen build --name user2
```

### Example 3: CI/CD Pipeline

```yaml
# .github/workflows/build-cv.yml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup CV data
        run: |
          mkdir -p ~/.cvgen/{cvs,pics,templates}
          cp -r ${{ secrets.CVS_DATA }} ~/.cvgen/cvs/
          cp -r templates/* ~/.cvgen/templates/
      
      - name: Build CV
        env:
          CVGEN_CVS_DIR: ~/.cvgen/cvs
          CVGEN_TEMPLATES_DIR: ~/.cvgen/templates
        run: cvgen build --name ${{ github.actor }}
```

## Best Practices

1. **Development**: Use local data/ directory
2. **Personal use**: Use ~/.cvgen/ for your CVs
3. **Team projects**: Use configuration file committed to repo
4. **Production deployments**: Use environment variables
5. **CI/CD**: Use environment variables + temporary directories

## Getting Help

If you encounter issues during migration:

1. Run health check: `cvgen doctor`
2. Check paths: `cvgen doctor --format json | jq .paths`
3. Open an issue: https://github.com/Raminyazdani/cv_generator/issues
