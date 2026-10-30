"""
I/O utilities for CV Generator.

Provides functions for:
- Discovering CV JSON files in a directory
- Loading CV JSON data
- Loading language translation maps
- Language code validation
"""
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from .errors import ConfigurationError, ValidationError
from .paths import get_default_cvs_path, get_lang_engine_path
logger = logging.getLogger(__name__)
VALID_LANGUAGE_CODES = {'en', 'de', 'fr', 'es', 'it', 'pt', 'nl', 'ru', 'zh', 'ja', 'ko', 'ar', 'he', 'fa', 'tr', 'pl', 'uk', 'cs', 'sv', 'da', 'no', 'fi', 'hu', 'ro', 'bg', 'hr', 'sr', 'sk', 'sl', 'et', 'lv', 'lt', 'el', 'hi', 'bn', 'ur', 'vi', 'th', 'id', 'ms', 'tl'}
VALID_LANGUAGE_CODES_3LETTER = {'eng', 'deu', 'fra', 'spa', 'ita', 'por', 'nld', 'rus', 'zho', 'jpn', 'kor', 'ara', 'heb', 'fas', 'tur', 'pol', 'ukr', 'ces', 'swe', 'dan', 'nor', 'fin', 'hun', 'ron', 'bul', 'hrv', 'srp', 'slk', 'slv', 'est', 'lav', 'lit', 'ell', 'hin', 'ben', 'urd', 'vie', 'tha', 'ind', 'msa'}

def is_valid_language_code(code: str) -> bool:
    """
    Check if string is a valid ISO 639 language code.

    Args:
        code: Potential language code.

    Returns:
        True if valid language code.
    """
    if not code:
        return False
    code_lower = code.lower()
    if len(code) == 2:
        return code_lower in VALID_LANGUAGE_CODES
    if len(code) == 3:
        return code_lower in VALID_LANGUAGE_CODES_3LETTER
    return False

def parse_cv_filename(filename: str) -> Tuple[str, str]:
    """
    Parse CV filename to extract base_name and language code.

    Supports patterns:
    - name-<lang>.json (e.g., example-de.json)
    - name_<lang>.json (e.g., example_fa.json)
    - name.json (defaults to lang='en')

    Note: Language suffix is only recognized if it's a valid ISO 639 code.
    For example, john_doe.json returns (john_doe, en), not (john, doe).

    Args:
        filename: The CV filename to parse.

    Returns:
        Tuple of (base_name, language_code).
    """
    name = filename[:-5] if filename.endswith('.json') else filename
    match = re.match('^(.+?)[-_]([a-z]{2,3})$', name)
    if match:
        potential_lang = match.group(2)
        if is_valid_language_code(potential_lang):
            return (match.group(1), potential_lang)
        logger.debug(f"'{potential_lang}' is not a valid language code, treating '{name}' as full base name")
    return (name, 'en')

def discover_cv_files(cvs_path: Optional[Path]=None, name_filter: Optional[str]=None) -> List[Path]:
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
        raise ConfigurationError(f'CVs directory not found: {cvs_path}')
    if not cvs_path.is_dir():
        raise ConfigurationError(f'CVs path is not a directory: {cvs_path}')
    cv_files = []
    for filepath in sorted(cvs_path.glob('*.json')):
        if name_filter:
            base_name, _ = parse_cv_filename(filepath.name)
            if base_name != name_filter:
                continue
        cv_files.append(filepath)
    logger.debug(f'Discovered {len(cv_files)} CV file(s) in {cvs_path}')
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
        raise ConfigurationError(f'CV file not found: {filepath}')
    try:
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValidationError(f'Invalid JSON in {filepath.name}: {e}')
    except Exception as e:
        raise ConfigurationError(f'Error reading {filepath.name}: {e}')
    logger.debug(f'Loaded CV data from {filepath.name}')
    return data

def validate_cv_data(data: Dict[str, Any], filename: str) -> bool:
    """
    Validate CV data structure.

    Performs quick structural validation:
    1. Checks that data is a dictionary
    2. Checks for required 'basics' section
    3. Validates that basics is a list/array (per schema)
    4. Validates that list sections are actually lists
    5. Validates that skills section is a dict if present

    Args:
        data: The CV data dictionary.
        filename: Name of the source file (for error messages).

    Returns:
        True if valid, False if the CV should be skipped.
    """
    if not isinstance(data, dict):
        logger.warning(f'Skipping {filename}: CV data must be a dictionary, got {type(data).__name__}')
        return False
    if 'basics' not in data:
        logger.warning(f"Skipping {filename}: missing 'basics' key (incompatible schema)")
        return False
    basics = data['basics']
    if not isinstance(basics, list):
        logger.warning(f"Skipping {filename}: section 'basics' should be a list, got {type(basics).__name__}")
        return False
    if len(basics) == 0:
        logger.warning(f"Skipping {filename}: section 'basics' is empty")
        return False
    list_sections = ['education', 'experiences', 'projects', 'publications', 'references', 'languages', 'workshop_and_certifications', 'awards', 'honors', 'profiles']
    for section in list_sections:
        if section in data and (not isinstance(data[section], list)):
            logger.warning(f"Skipping {filename}: section '{section}' should be a list, got {type(data[section]).__name__}")
            return False
    if 'skills' in data and (not isinstance(data['skills'], dict)):
        logger.warning(f"Skipping {filename}: section 'skills' should be a dictionary, got {type(data['skills']).__name__}")
        return False
    return True

def load_lang_map(lang_engine_path: Optional[Path]=None) -> Dict[str, Dict[str, str]]:
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
    lang_file = lang_engine_path / 'lang.json'
    if not lang_file.exists():
        raise ConfigurationError(f'Translation file not found at: {lang_file}\nExpected format:\n{{\n  "education": {{ "en": "Education", "de": "Ausbildung", "fa": "تحصیلات" }},\n  "email": {{ "en": "Email", "de": "E-Mail", "fa": "ایمیل" }}\n}}')
    with open(lang_file, encoding='utf-8') as f:
        lang_map = json.load(f)
    logger.debug(f'Loaded language map with {len(lang_map)} entries')
    return lang_map
