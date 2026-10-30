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
MINIMAL_CV_TEMPLATE: Dict[str, Any] = {'basics': [{'fname': 'Jane', 'lname': 'Doe', 'label': ['Software Engineer'], 'email': 'jane@example.com', 'phone': {'formatted': '+1 555-0100'}, 'location': [{'city': 'San Francisco', 'region': 'CA', 'country': 'USA'}]}], 'education': [{'studyType': 'B.Sc.', 'area': 'Computer Science', 'institution': 'Example University', 'location': 'San Francisco, CA', 'startDate': '2015', 'endDate': '2019'}], 'experiences': [{'institution': 'Tech Corp', 'role': 'Software Engineer', 'location': 'San Francisco, CA', 'duration': '2019 – Present', 'description': 'Full-stack development with Python and React'}]}

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
    fname = profile_name.capitalize()
    template['basics'][0]['fname'] = fname
    template['basics'][0]['lname'] = 'Doe'
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
    return f'# CV Generator Configuration\n# See: https://github.com/Raminyazdani/cv_generator\n\n[project]\nname = "{profile_name} CV Project"\ndefault_lang = "{lang}"\n\n[paths]\ncvs = "cvs"\noutput = "output"\n# Uncomment to use custom templates:\n# templates = "templates"\n\n[build]\nkeep_latex = false\ndry_run = false\n'

def get_readme_template(profile_name: str, lang: str) -> str:
    """
    Generate README.md content for the scaffolded project.

    Args:
        profile_name: Name of the CV profile.
        lang: Language code.

    Returns:
        README content.
    """
    return f"# {profile_name.capitalize()} CV Project\n\nThis CV project was generated using [CV Generator](https://github.com/Raminyazdani/cv_generator).\n\n## Quick Start\n\n1. **Edit your CV data**\n\n   Open `cvs/{profile_name}.{lang}.json` and customize your information.\n\n2. **Build your PDF**\n\n   ```bash\n   cvgen build --input-dir cvs\n   ```\n\n   Your PDF will be generated at `output/pdf/{profile_name}/{lang}/{profile_name}_{lang}.pdf`\n\n3. **Preview without LaTeX** (optional)\n\n   If you don't have LaTeX installed, you can use dry-run mode to render the LaTeX:\n\n   ```bash\n   cvgen build --input-dir cvs --dry-run --keep-latex\n   ```\n\n   Then inspect the files in `output/latex/`.\n\n## Next Steps\n\n- Edit `cvs/{profile_name}.{lang}.json` with your personal information\n- Run `cvgen lint --file cvs/{profile_name}.{lang}.json` to validate your CV\n- Run `cvgen build --input-dir cvs` to generate the PDF\n\n## Requirements\n\n- Python 3.9+\n- [CV Generator](https://github.com/Raminyazdani/cv_generator) (`pip install cv-generator`)\n- XeLaTeX (for PDF generation)\n\n### Installing LaTeX\n\n**Ubuntu/Debian:**\n```bash\nsudo apt-get install texlive-xetex texlive-fonts-extra\n```\n\n**macOS:**\n```bash\nbrew install --cask mactex\n```\n\n**Windows:**\nDownload and install [MiKTeX](https://miktex.org/download) or [TeX Live](https://tug.org/texlive/acquire-netinstall.html).\n\n## File Structure\n\n```\n{profile_name}-cv/\n├── cvs/\n│   └── {profile_name}.{lang}.json    # Your CV data\n├── output/                            # Generated output (after build)\n├── cv_generator.toml                  # Configuration\n└── README.md                          # This file\n```\n\n## Adding More Languages\n\nTo add a German version of your CV:\n\n1. Copy the JSON file:\n   ```bash\n   cp cvs/{profile_name}.{lang}.json cvs/{profile_name}.de.json\n   ```\n\n2. Edit `cvs/{profile_name}.de.json` and translate the content\n\n3. Rebuild:\n   ```bash\n   cvgen build --input-dir cvs\n   ```\n\n## Documentation\n\n- [CLI Reference](https://github.com/Raminyazdani/cv_generator/blob/main/docs/cli.md)\n- [JSON Schema](https://github.com/Raminyazdani/cv_generator/blob/main/docs/json-schema.md)\n- [Templates](https://github.com/Raminyazdani/cv_generator/blob/main/docs/templates.md)\n"

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

def scaffold_project(dest_path: Path, profile_name: str='mycv', lang: str='en', force: bool=False) -> ScaffoldResult:
    """
    Create a new CV project at the specified path.

    Args:
        dest_path: Destination directory for the new project.
        profile_name: Name of the CV profile (e.g., 'example', 'jane').
        lang: Language code (en, de, fa).
        force: If True, overwrite existing files.

    Returns:
        ScaffoldResult with created files and status. Check result.success
        to determine if scaffolding succeeded, and result.error for the
        error message if it failed.
    """
    result = ScaffoldResult(dest_path)
    if dest_path.exists():
        contents = list(dest_path.iterdir())
        if contents and (not force):
            result.error = f"Directory '{dest_path}' is not empty. Use --force to overwrite existing files."
            return result
    else:
        dest_path.mkdir(parents=True, exist_ok=True)
    try:
        cvs_dir = dest_path / 'cvs'
        cvs_dir.mkdir(exist_ok=True)
        cv_filename = f'{profile_name}.{lang}.json'
        cv_path = cvs_dir / cv_filename
        cv_template = get_cv_template(profile_name, lang)
        with open(cv_path, 'w', encoding='utf-8') as f:
            json.dump(cv_template, f, indent=2, ensure_ascii=False)
            f.write('\n')
        result.add_file(cv_path)
        output_dir = dest_path / 'output'
        output_dir.mkdir(exist_ok=True)
        config_path = dest_path / 'cv_generator.toml'
        config_content = get_config_template(profile_name, lang, dest_path)
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        result.add_file(config_path)
        readme_path = dest_path / 'README.md'
        readme_content = get_readme_template(profile_name, lang)
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        result.add_file(readme_path)
        gitignore_path = dest_path / '.gitignore'
        gitignore_content = '# CV Generator output\noutput/\n!output/.gitkeep\n\n# CV Generator state directory\n.cvgen/\n!.cvgen/.gitkeep\n\n# LaTeX intermediate files\n*.aux\n*.log\n*.out\n*.toc\n*.fdb_latexmk\n*.fls\n*.synctex.gz\n\n# Editor files\n.vscode/\n.idea/\n*.swp\n*~\n\n# OS files\n.DS_Store\nThumbs.db\n'
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write(gitignore_content)
        result.add_file(gitignore_path)
        result.success = True
    except OSError as e:
        result.error = f'Error creating files: {e}'
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
    return [f'cd {dest_path}', f'# Edit cvs/{profile_name}.{lang}.json with your information', 'cvgen build --input-dir cvs']
