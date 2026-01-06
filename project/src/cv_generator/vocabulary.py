"""
Vocabulary Module - Canonical Key/Label Mapping for CV Generator Web UI.

This module integrates the lang engine's lang.json translations into the Web UI,
providing:
- Canonical key to localized label mapping for form fields
- Reverse lookup (localized label → canonical key)
- Section name translations
- Debug mode to show canonical keys

The vocabulary uses the existing lang.json file from the lang_engine module
which contains translations for all CV field keys in EN/DE/FA.

Strategy:
=========
- Canonical key: The English key name (e.g., "fname", "institution")
- Localized label: The human-readable label in the selected language
- Forms display localized labels; database stores canonical keys
- Export uses canonical keys (English) by default, can translate on export
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Path to the lang.json file in the lang_engine module
_LANG_JSON_PATH = Path(__file__).parent / "lang_engine" / "lang.json"

# Supported languages
SUPPORTED_LANGUAGES = ["en", "de", "fa"]
DEFAULT_LANGUAGE = "en"


class VocabularyError(Exception):
    """Error in vocabulary operations."""
    pass


@lru_cache(maxsize=1)
def _load_lang_map() -> dict[str, dict[str, str]]:
    """
    Load the lang.json translation map.

    Returns:
        Dict mapping canonical keys to language-specific labels.
        Example: {"fname": {"en": "fname", "de": "Vorname", "fa": "نام"}}
    """
    if not _LANG_JSON_PATH.exists():
        logger.warning(f"lang.json not found at {_LANG_JSON_PATH}")
        return {}

    try:
        content = _LANG_JSON_PATH.read_text(encoding="utf-8")
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse lang.json: {e}")
        return {}
    except Exception as e:
        logger.error(f"Failed to load lang.json: {e}")
        return {}


def clear_vocabulary_cache() -> None:
    """Clear the vocabulary cache. Useful for testing or after updates."""
    _load_lang_map.cache_clear()
    _build_reverse_lookup.cache_clear()


@lru_cache(maxsize=1)
def _build_reverse_lookup() -> dict[str, dict[str, str]]:
    """
    Build reverse lookup from localized labels to canonical keys.

    Returns:
        Dict mapping lowercase localized labels to canonical keys, per language.
        Example: {"vorname": {"de": "fname"}, "نام": {"fa": "fname"}}
    """
    lang_map = _load_lang_map()
    reverse: dict[str, dict[str, str]] = {}

    for canonical_key, translations in lang_map.items():
        if not isinstance(translations, dict):
            continue
        for lang, label in translations.items():
            if isinstance(label, str) and label.strip():
                lower_label = label.lower()
                if lower_label not in reverse:
                    reverse[lower_label] = {}
                reverse[lower_label][lang] = canonical_key

    return reverse


class Vocabulary:
    """
    Provides key/label mapping for the Web UI.

    This class wraps the lang.json translations and provides:
    - get_label(key, lang): Get localized label for a canonical key
    - to_canonical(label, lang): Reverse lookup from localized label to canonical key
    - get_section_labels(): Get all section name translations
    - get_field_labels(section, lang): Get field labels for a section
    """

    def __init__(self, additional_translations: Optional[dict[str, dict[str, str]]] = None):
        """
        Initialize the vocabulary.

        Args:
            additional_translations: Optional additional translations to merge.
        """
        self._lang_map = _load_lang_map()
        if additional_translations:
            self._lang_map = {**self._lang_map, **additional_translations}
        self._reverse_lookup = _build_reverse_lookup()

    def get_label(self, key: str, language: str = DEFAULT_LANGUAGE) -> str:
        """
        Get the localized label for a canonical key.

        Args:
            key: Canonical key (e.g., "fname", "institution")
            language: Target language code (en, de, fa)

        Returns:
            Localized label if available, otherwise the key itself.
            For English, if the translation equals the key, we format it nicely.
            For other languages, we use the translation as-is.
        """
        if key in self._lang_map:
            translations = self._lang_map[key]
            if isinstance(translations, dict) and language in translations:
                label = translations[language]
                if isinstance(label, str) and label.strip():
                    # For English: if the value equals the key, format it nicely
                    # (lang.json has "title" for English which should display as "Title")
                    if language == "en" and label == key:
                        return self._format_key_as_label(key)
                    return label

        # Fallback: format the key nicely
        return self._format_key_as_label(key)

    def _format_key_as_label(self, key: str) -> str:
        """
        Format a key as a human-readable label.

        Examples:
            "fname" -> "First Name" (using known mappings)
            "startDate" -> "Start Date"
            "type_key" -> "Type Key"
        """
        # Common key mappings for better labels
        key_label_map = {
            "fname": "First Name",
            "lname": "Last Name",
            "startDate": "Start Date",
            "endDate": "End Date",
            "studyType": "Study Type",
            "countryCode": "Country Code",
            "postalCode": "Postal Code",
            "birthDate": "Birth Date",
            "examDate": "Exam Date",
            "maxScore": "Max Score",
            "minScore": "Min Score",
            "primaryFocus": "Primary Focus",
            "type_key": "Type Key",
            "short_name": "Short Name",
            "long_name": "Long Name",
            "logo_url": "Logo URL",
            "repository_url": "Repository URL",
            "gpa": "GPA",
            "doi": "DOI",
            "url": "URL",
            "isbn": "ISBN",
            "issn": "ISSN",
        }

        if key in key_label_map:
            return key_label_map[key]

        # Handle camelCase
        result = re.sub(r'([a-z])([A-Z])', r'\1 \2', key)
        # Handle snake_case
        result = result.replace("_", " ")
        return result.title()

    def to_canonical(self, label: str, language: str = DEFAULT_LANGUAGE) -> str:
        """
        Convert a localized label back to its canonical key.

        Args:
            label: Localized label (e.g., "Vorname" for German)
            language: The language of the label

        Returns:
            Canonical key if found, otherwise the label itself.
        """
        lower_label = label.lower()
        if lower_label in self._reverse_lookup:
            mappings = self._reverse_lookup[lower_label]
            if language in mappings:
                return mappings[language]
            # Try any language as fallback
            if mappings:
                return next(iter(mappings.values()))

        # Not found - return as-is (might already be canonical)
        return label

    def has_translation(self, key: str, language: str) -> bool:
        """
        Check if a key has a translation for the given language.

        Args:
            key: Canonical key
            language: Target language code

        Returns:
            True if translation exists and is non-empty.
        """
        if key not in self._lang_map:
            return False
        translations = self._lang_map[key]
        if not isinstance(translations, dict):
            return False
        return language in translations and bool(translations[language])

    def get_all_labels(self, key: str) -> dict[str, str]:
        """
        Get all translations for a key.

        Args:
            key: Canonical key

        Returns:
            Dict mapping language codes to labels.
        """
        if key in self._lang_map:
            translations = self._lang_map[key]
            if isinstance(translations, dict):
                return {
                    lang: label
                    for lang, label in translations.items()
                    if isinstance(label, str) and label.strip()
                }
        return {"en": self._format_key_as_label(key)}

    def get_section_label(self, section: str, language: str = DEFAULT_LANGUAGE) -> str:
        """
        Get the localized label for a section name.

        Args:
            section: Section key (e.g., "projects", "experiences")
            language: Target language code

        Returns:
            Localized section name.
        """
        return self.get_label(section, language)

    def get_field_labels(
        self,
        fields: list[str],
        language: str = DEFAULT_LANGUAGE,
        show_canonical: bool = False,
    ) -> dict[str, dict[str, Any]]:
        """
        Get localized labels for a list of field keys.

        Args:
            fields: List of canonical field keys
            language: Target language code
            show_canonical: If True, include canonical key in output

        Returns:
            Dict mapping field keys to label info:
            {
                "fname": {
                    "label": "Vorname",
                    "canonical": "fname",  # Only if show_canonical=True
                    "has_translation": True
                }
            }
        """
        result = {}
        for field in fields:
            label = self.get_label(field, language)
            info: dict[str, Any] = {
                "label": label,
                "has_translation": self.has_translation(field, language),
            }
            if show_canonical:
                info["canonical"] = field
            result[field] = info
        return result


# Global vocabulary instance
_vocabulary: Optional[Vocabulary] = None


def get_vocabulary() -> Vocabulary:
    """Get the global vocabulary instance."""
    global _vocabulary
    if _vocabulary is None:
        _vocabulary = Vocabulary()
    return _vocabulary


def get_field_label(key: str, language: str = DEFAULT_LANGUAGE) -> str:
    """
    Convenience function to get a field label.

    Args:
        key: Canonical key
        language: Target language code

    Returns:
        Localized label for the key.
    """
    return get_vocabulary().get_label(key, language)


def get_section_label(section: str, language: str = DEFAULT_LANGUAGE) -> str:
    """
    Convenience function to get a section label.

    Args:
        section: Section key
        language: Target language code

    Returns:
        Localized section name.
    """
    return get_vocabulary().get_section_label(section, language)
