"""
Project scaffolding for CV Generator.

Provides the `cvgen init` command to create a minimal working CV project
outside the main repository.
"""

import copy
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Minimal valid CV JSON template
MINIMAL_CV_TEMPLATE: Dict[str, Any] = {
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
        "institution": "Example University",
        "location": "San Francisco, CA",
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


def get_cv_template(profile_name: str, lang: str) -> Dict[str, Any]:
    """
    Get a CV template customized with the profile name.

    Args:
        profile_name: Name of the CV profile.
        lang: Language code (en, de, fa).

    Returns:
        CV template dictionary.
    """
    template = copy.deepcopy(MINIMAL_CV_TEMPLATE)

    # Customize with profile name (capitalize first letter)
    fname = profile_name.capitalize()
    template["basics"][0]["fname"] = fname
    template["basics"][0]["lname"] = "Doe"

    return template


def get_config_template(profile_name: str, lang: str, dest_path: Path) -> str:
    """
    Generate a cv_generator.toml config file content.

    Args:
        profile_name: Name of the CV profile.
        lang: Language code.
        dest_path: Destination directory path.

    Returns:
        TOML config file content.
    """
    return f'''# CV Generator Configuration
# See: https://github.com/Raminyazdani/cv_generator

[project]
name = "{profile_name} CV Project"
default_lang = "{lang}"

[paths]
cvs = "cvs"
output = "output"
# Uncomment to use custom templates:
# templates = "templates"

[build]
keep_latex = false
dry_run = false
'''


def get_readme_template(profile_name: str, lang: str) -> str:
    """
    Generate README.md content for the scaffolded project.

    Args:
        profile_name: Name of the CV profile.
        lang: Language code.

    Returns:
        README content.
    """
    return f'''# {profile_name.capitalize()} CV Project

This CV project was generated using [CV Generator](https://github.com/Raminyazdani/cv_generator).

## Quick Start

1. **Edit your CV data**

   Open `cvs/{profile_name}.{lang}.json` and customize your information.

2. **Build your PDF**

   ```bash
   cvgen build --input-dir cvs
   ```

   Your PDF will be generated at `output/pdf/{profile_name}/{lang}/{profile_name}_{lang}.pdf`

3. **Preview without LaTeX** (optional)

   If you don't have LaTeX installed, you can use dry-run mode to render the LaTeX:

   ```bash
   cvgen build --input-dir cvs --dry-run --keep-latex
   ```

   Then inspect the files in `output/latex/`.

## Next Steps

- Edit `cvs/{profile_name}.{lang}.json` with your personal information
- Run `cvgen lint --file cvs/{profile_name}.{lang}.json` to validate your CV
- Run `cvgen build --input-dir cvs` to generate the PDF

## Requirements

- Python 3.9+
- [CV Generator](https://github.com/Raminyazdani/cv_generator) (`pip install cv-generator`)
- XeLaTeX (for PDF generation)

### Installing LaTeX

**Ubuntu/Debian:**
```bash
sudo apt-get install texlive-xetex texlive-fonts-extra
```

**macOS:**
```bash
brew install --cask mactex
```

**Windows:**
Download and install [MiKTeX](https://miktex.org/download) or [TeX Live](https://tug.org/texlive/acquire-netinstall.html).

## File Structure

```
{profile_name}-cv/
├── cvs/
│   └── {profile_name}.{lang}.json    # Your CV data
├── output/                            # Generated output (after build)
├── cv_generator.toml                  # Configuration
└── README.md                          # This file
```

## Adding More Languages

To add a German version of your CV:

1. Copy the JSON file:
   ```bash
   cp cvs/{profile_name}.{lang}.json cvs/{profile_name}.de.json
   ```

2. Edit `cvs/{profile_name}.de.json` and translate the content

3. Rebuild:
   ```bash
   cvgen build --input-dir cvs
   ```

## Documentation

- [CLI Reference](https://github.com/Raminyazdani/cv_generator/blob/main/docs/cli.md)
- [JSON Schema](https://github.com/Raminyazdani/cv_generator/blob/main/docs/json-schema.md)
- [Templates](https://github.com/Raminyazdani/cv_generator/blob/main/docs/templates.md)
'''


class ScaffoldResult:
    """Result of scaffolding a new project."""

    def __init__(self, dest_path: Path):
        self.dest_path = dest_path
        self.files_created: List[Path] = []
        self.success: bool = False
        self.error: Optional[str] = None

    def add_file(self, path: Path) -> None:
        """Record a created file."""
        self.files_created.append(path)


def scaffold_project(
    dest_path: Path,
    profile_name: str = "mycv",
    lang: str = "en",
    force: bool = False,
) -> ScaffoldResult:
    """
    Create a new CV project at the specified path.

    Args:
        dest_path: Destination directory for the new project.
        profile_name: Name of the CV profile (e.g., 'ramin', 'jane').
        lang: Language code (en, de, fa).
        force: If True, overwrite existing files.

    Returns:
        ScaffoldResult with created files and status. Check result.success
        to determine if scaffolding succeeded, and result.error for the
        error message if it failed.
    """
    result = ScaffoldResult(dest_path)

    # Validate destination
    if dest_path.exists():
        # Check if it's empty (allow . and ..)
        contents = list(dest_path.iterdir())
        if contents and not force:
            result.error = (
                f"Directory '{dest_path}' is not empty. "
                "Use --force to overwrite existing files."
            )
            return result
    else:
        # Create the destination directory
        dest_path.mkdir(parents=True, exist_ok=True)

    try:
        # Create cvs directory
        cvs_dir = dest_path / "cvs"
        cvs_dir.mkdir(exist_ok=True)

        # Create CV JSON file
        cv_filename = f"{profile_name}.{lang}.json"
        cv_path = cvs_dir / cv_filename
        cv_template = get_cv_template(profile_name, lang)
        with open(cv_path, "w", encoding="utf-8") as f:
            json.dump(cv_template, f, indent=2, ensure_ascii=False)
            f.write("\n")
        result.add_file(cv_path)

        # Create output directory
        output_dir = dest_path / "output"
        output_dir.mkdir(exist_ok=True)

        # Create config file
        config_path = dest_path / "cv_generator.toml"
        config_content = get_config_template(profile_name, lang, dest_path)
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config_content)
        result.add_file(config_path)

        # Create README
        readme_path = dest_path / "README.md"
        readme_content = get_readme_template(profile_name, lang)
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        result.add_file(readme_path)

        # Create .gitignore for output directory
        gitignore_path = dest_path / ".gitignore"
        gitignore_content = """# CV Generator output
output/

# Editor files
.vscode/
.idea/
*.swp
*~

# OS files
.DS_Store
Thumbs.db
"""
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write(gitignore_content)
        result.add_file(gitignore_path)

        result.success = True

    except OSError as e:
        result.error = f"Error creating files: {e}"

    return result


def get_next_steps(dest_path: Path, profile_name: str, lang: str) -> List[str]:
    """
    Get the list of next commands to run after scaffolding.

    Args:
        dest_path: Destination directory.
        profile_name: Name of the CV profile.
        lang: Language code.

    Returns:
        List of command strings.
    """
    return [
        f"cd {dest_path}",
        f"# Edit cvs/{profile_name}.{lang}.json with your information",
        "cvgen build --input-dir cvs",
    ]
