"""
I/O utilities for CV Generator.

Provides functions for:
- Discovering CV JSON files in a directory
- Loading CV JSON data
- Loading language translation maps
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .errors import ConfigurationError, ValidationError
from .paths import get_default_cvs_path, get_lang_engine_path

logger = logging.getLogger(__name__)


def parse_cv_filename(filename: str) -> Tuple[str, str]:
    """
    Parse CV filename to extract base_name and language code.

    Supports patterns:
    - name-<lang>.json (e.g., ramin-de.json)
    - name_<lang>.json (e.g., ramin_fa.json)
    - name.json (defaults to lang='en')

    Args:
        filename: The CV filename to parse.

    Returns:
        Tuple of (base_name, language_code).
    """
    # Remove .json extension
    name = filename[:-5] if filename.endswith('.json') else filename

    # Pattern: name-lang or name_lang where lang is 2-3 lowercase letters
    match = re.match(r'^(.+?)[-_]([a-z]{2,3})$', name)
    if match:
        return match.group(1), match.group(2)

    # No language suffix - default to English
    return name, "en"


def discover_cv_files(
    cvs_path: Optional[Path] = None,
    name_filter: Optional[str] = None
) -> List[Path]:
    """
    Discover CV JSON files in the specified directory.

    Args:
        cvs_path: Path to the directory containing CV JSON files.
                  Defaults to data/cvs/ under repo root.
        name_filter: If provided, only return CVs matching this base name.

    Returns:
        List of paths to CV JSON files.

    Raises:
        ConfigurationError: If the CVs directory doesn't exist.
    """
    if cvs_path is None:
        cvs_path = get_default_cvs_path()

    cvs_path = Path(cvs_path)

    if not cvs_path.exists():
        raise ConfigurationError(f"CVs directory not found: {cvs_path}")

    if not cvs_path.is_dir():
        raise ConfigurationError(f"CVs path is not a directory: {cvs_path}")

    cv_files = []
    for filepath in sorted(cvs_path.glob("*.json")):
        if name_filter:
            base_name, _ = parse_cv_filename(filepath.name)
            if base_name != name_filter:
                continue
        cv_files.append(filepath)

    logger.debug(f"Discovered {len(cv_files)} CV file(s) in {cvs_path}")
    return cv_files


def load_cv_json(filepath: Path) -> Dict[str, Any]:
    """
    Load CV data from a JSON file.

    Args:
        filepath: Path to the CV JSON file.

    Returns:
        Dictionary containing the CV data.

    Raises:
        ConfigurationError: If the file doesn't exist.
        ValidationError: If the JSON is invalid or missing required fields.
    """
    if not filepath.exists():
        raise ConfigurationError(f"CV file not found: {filepath}")

    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in {filepath.name}: {e}")
    except Exception as e:
        raise ConfigurationError(f"Error reading {filepath.name}: {e}")

    logger.debug(f"Loaded CV data from {filepath.name}")
    return data


def validate_cv_data(data: Dict[str, Any], filename: str) -> bool:
    """
    Validate CV data structure.

    Args:
        data: The CV data dictionary.
        filename: Name of the source file (for error messages).

    Returns:
        True if valid, False if the CV should be skipped.
    """
    if "basics" not in data:
        logger.warning(f"Skipping {filename}: missing 'basics' key (incompatible schema)")
        return False

    return True


def load_lang_map(lang_engine_path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """
    Load the translation mapping from lang_engine/lang.json.

    Expected format:
    {
      "education": { "en": "Education", "de": "Ausbildung", "fa": "تحصیلات" },
      ...
    }

    Args:
        lang_engine_path: Path to the lang_engine directory.

    Returns:
        Translation mapping dictionary.

    Raises:
        ConfigurationError: If the translation file is not found.
    """
    if lang_engine_path is None:
        lang_engine_path = get_lang_engine_path()

    lang_file = lang_engine_path / "lang.json"

    if not lang_file.exists():
        raise ConfigurationError(
            f"Translation file not found at: {lang_file}\n"
            f"Expected format:\n"
            f'{{\n'
            f'  "education": {{ "en": "Education", "de": "Ausbildung", "fa": "تحصیلات" }},\n'
            f'  "email": {{ "en": "Email", "de": "E-Mail", "fa": "ایمیل" }}\n'
            f'}}'
        )

    with open(lang_file, encoding="utf-8") as f:
        lang_map = json.load(f)

    logger.debug(f"Loaded language map with {len(lang_map)} entries")
    return lang_map
