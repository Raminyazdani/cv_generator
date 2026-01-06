# Output Directory Structure

## Overview

CV Generator uses a consistent, hierarchical output structure that organizes generated files by:

1. **Format** (pdf, latex, json, html, etc.)
2. **Profile** (person's name/identifier)
3. **Variant** (optional - academic, full, industry, etc.)
4. **Language** (en, de, fa, etc.)

This structure allows managing multiple CVs, languages, and variants without conflicts.

## Default Structure

```text
output/
├── pdf/                          # Generated PDF files
│   └── <profile>/
│       └── <lang>/
│           └── <profile>_<lang>.pdf
├── latex/                        # LaTeX source files (when --keep-latex)
│   └── <profile>/
│       └── <lang>/
│           ├── main.tex          # Main LaTeX document
│           └── sections/         # Individual section files
│               ├── header.tex
│               ├── education.tex
│               ├── experience.tex
│               └── ...
├── json/                         # Exported JSON files
│   └── <profile>/
│       └── <lang>/
│           └── cv.json
└── logs/                         # Generation logs
    └── run_<timestamp>.log
```

## With Variants

When using the `--variant` flag, an additional level is added:

```text
output/
├── pdf/
│   └── <profile>/
│       └── <variant>/
│           └── <lang>/
│               └── <profile>_<lang>.pdf
├── latex/
│   └── <profile>/
│       └── <variant>/
│           └── <lang>/
│               ├── main.tex
│               └── sections/
└── json/
    └── <profile>/
        └── <variant>/
            └── <lang>/
                └── cv.json
```

## Examples

### Single Language Build

```bash
cvgen build --name ramin --lang en
```

Output:
```text
output/pdf/ramin/en/ramin_en.pdf
```

### Multiple Languages

```bash
cvgen build --name ramin --lang en
cvgen build --name ramin --lang de
cvgen build --name ramin --lang fa
```

Output:
```text
output/pdf/ramin/en/ramin_en.pdf
output/pdf/ramin/de/ramin_de.pdf
output/pdf/ramin/fa/ramin_fa.pdf
```

### With Variant

```bash
cvgen build --name ramin --lang en --variant academic
```

Output:
```text
output/pdf/ramin/academic/en/ramin_en.pdf
```

### Custom Output Directory

```bash
cvgen build --name ramin --lang en --output-dir ./my-cvs
```

Output:
```text
./my-cvs/pdf/ramin/en/ramin_en.pdf
```

### Keep LaTeX Sources

```bash
cvgen build --name ramin --lang en --keep-latex
```

Output:
```text
output/pdf/ramin/en/ramin_en.pdf
output/latex/ramin/en/main.tex
output/latex/ramin/en/sections/header.tex
output/latex/ramin/en/sections/education.tex
...
```

## Path Resolution

The `ArtifactPaths` class in `project/src/cv_generator/paths.py` manages all output paths. You can use it programmatically:

```python
from cv_generator.paths import ArtifactPaths

# Create paths for a specific CV
paths = ArtifactPaths(
    profile="ramin",
    lang="en",
    variant=None,  # or "academic", "full", etc.
    output_root=Path("output"),
)

# Access various paths
print(paths.pdf_dir)        # output/pdf/ramin/en
print(paths.pdf_named_path) # output/pdf/ramin/en/ramin_en.pdf
print(paths.latex_dir)      # output/latex/ramin/en
print(paths.tex_path)       # output/latex/ramin/en/main.tex
print(paths.json_dir)       # output/json/ramin/en
```

## Verification Script

A verification script is provided to confirm output paths:

```bash
python scripts/verify_output_paths.py
```

This script demonstrates the actual paths used by CV Generator for various configurations.

## Migration from Legacy Structure

Prior versions used a different structure:

- Intermediate files in `result/<name>/<lang>/sections/`
- Final PDFs in `output/<name>.pdf`

The current unified structure places all artifacts under `output/` with format-specific subdirectories. The `result/` directory is no longer used.

See [MIGRATION.md](MIGRATION.md) for detailed migration instructions.
