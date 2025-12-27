# Copilot Background Jobs Documentation

This document explains how to work with Copilot background jobs in this repository.

## Overview

Copilot background jobs use a custom environment setup to ensure consistent and fast execution. This repository is configured with:

1. **Setup workflow**: `.github/workflows/copilot-setup-steps.yml`
2. **CI validation**: `.github/workflows/ci.yml`
3. **Smoke validation**: `scripts/smoke_validate.py`
4. **Generation tests**: `scripts/test_cv_generation.py`

## Running the Setup Workflow Manually

To validate the setup workflow:

1. Go to the repository's **Actions** tab on GitHub
2. Select **"Copilot Setup Steps"** workflow
3. Click **"Run workflow"**
4. Select branch and click **"Run workflow"**

This will:
- Install Python 3.11
- Install jinja2 dependency
- Verify installation

## Environment Variables

The following environment variables may be configured in the Copilot environment:

| Variable | Description | Required |
|----------|-------------|----------|
| `PYTHON_VERSION` | Python version to use | No (default: 3.11) |
| `SHOW_COMMENTS` | Enable LaTeX comments in output | No (default: True) |

**Note**: Do not create secrets in this document. Document names only.

## Firewall Considerations

Copilot background jobs run with network restrictions. If dependencies fail to install:

### Allowed by Default
- PyPI (pip install)
- npm registry
- GitHub repositories

### If Dependencies Fail

1. **Check the error message** for the blocked domain
2. **Request allowlisting** for required hosts via repository settings
3. **Use cached dependencies** when possible (setup workflow caches pip)
4. **Do NOT disable firewall** unless explicitly authorized

### Firewall Scope

Important: The firewall only applies to:
- Processes started by the agent via Bash

The firewall does NOT apply to:
- MCP servers
- Setup steps in the copilot-setup-steps workflow

This means dependencies can be safely installed in the setup workflow.

## Debugging Failed Jobs

### Common Issues

1. **Missing jinja2**
   ```
   ModuleNotFoundError: No module named 'jinja2'
   ```
   Solution: Ensure setup workflow runs before agent tasks

2. **Template errors**
   ```
   jinja2.exceptions.UndefinedError: 'key' is undefined
   ```
   Solution: Check that JSON data has all required keys

3. **Locked file modified**
   ```
   sha256sum: WARNING: 1 computed checksum did NOT match
   ```
   Solution: Revert changes to locked JSON files

### Viewing Logs

1. Go to **Actions** tab
2. Select the failed workflow run
3. Click on the failed job
4. Expand steps to see detailed logs

## CI Pipeline

The CI workflow runs on every push/PR and validates:

1. **Locked file integrity**: SHA-256 hash verification
2. **Smoke validation**: JSON structure and content
3. **Generation test**: Template rendering without LaTeX

### What CI Catches

- Modifications to locked JSON files
- Invalid JSON structure
- Missing required fields
- Template rendering errors
- "undefined" or "null" strings in output

### Artifacts

CI produces these artifacts:
- `validation-report.json`: Detailed validation results
- `docs/visual-proof/`: Rendered templates for visual verification

## Visual Proof

Visual proof is generated for each CV to confirm non-empty rendering:

```
docs/visual-proof/
├── ramin/
│   ├── header.tex
│   ├── education.tex
│   ├── experience.tex
│   ├── ...
│   └── RENDERING_PROOF.txt
└── mahsa/
    └── ...
```

Each `RENDERING_PROOF.txt` confirms:
- Number of sections rendered
- Lines and characters per section
- Success status

## Best Practices

1. **Always run smoke validation** before pushing changes
2. **Never modify locked JSON files** (data/cvs/ramin.json, data/cvs/mahsa.json)
3. **Check visual proof** after template changes
4. **Use the debug filter** (`| debug`) to troubleshoot template issues
5. **Verify hashes** if unsure about file changes:
   ```bash
   sha256sum data/cvs/*.json
   ```
