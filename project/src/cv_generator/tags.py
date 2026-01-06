"""
Language-Aware Tagging Module for CV Generator.

This module implements the canonical tag ID strategy (Option A):
- Canonical ID: English key (e.g., "Full CV")
- Display: Localized name per active language
- Storage: Database stores canonical IDs
- Export: Writes language-specific tag strings based on export language

Strategy Documentation:
========================
We use English tag names as canonical identifiers because:
1. The existing CV data uses English tag names in type_key arrays
2. English is the base/default language
3. Canonical IDs provide stable references across languages

Tag Object Structure:
---------------------
{
    "id": "Full CV",           # Canonical ID (English)
    "labels": {
        "en": "Full CV",
        "de": "Vollständiger Lebenslauf",
        "fa": "رزومه کامل"
    },
    "scopes": ["en", "de", "fa"],  # Languages where this tag is valid
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}

Backward Compatibility:
----------------------
- Existing type_key values in JSON files are treated as canonical IDs
- If a type_key value is a localized string (e.g., German), the migration
  maps it to the canonical EN key if a reverse lookup is possible
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Supported languages
SUPPORTED_LANGUAGES = ["en", "de", "fa"]
DEFAULT_LANGUAGE = "en"

# Built-in tag translations
# These are the CV type tags used in type_key arrays with their translations
TAG_TRANSLATIONS: dict[str, dict[str, str]] = {
    "Full CV": {
        "en": "Full CV",
        "de": "Vollständiger Lebenslauf",
        "fa": "رزومه کامل"
    },
    "Academic": {
        "en": "Academic",
        "de": "Akademisch",
        "fa": "آکادمیک"
    },
    "Biotechnology": {
        "en": "Biotechnology",
        "de": "Biotechnologie",
        "fa": "بیوتکنولوژی"
    },
    "Bioinformatics": {
        "en": "Bioinformatics",
        "de": "Bioinformatik",
        "fa": "بیوانفورماتیک"
    },
    "Programming": {
        "en": "Programming",
        "de": "Programmierung",
        "fa": "برنامه‌نویسی"
    },
    "Student Projects": {
        "en": "Student Projects",
        "de": "Studentische Projekte",
        "fa": "پروژه‌های دانشجویی"
    },
    "Web": {
        "en": "Web",
        "de": "Web",
        "fa": "وب"
    },
    "Frontend": {
        "en": "Frontend",
        "de": "Frontend",
        "fa": "فرانت‌اند"
    },
    "UI": {
        "en": "UI",
        "de": "UI",
        "fa": "رابط کاربری"
    },
    "Robotics": {
        "en": "Robotics",
        "de": "Robotik",
        "fa": "رباتیک"
    },
    "Embedded Systems": {
        "en": "Embedded Systems",
        "de": "Eingebettete Systeme",
        "fa": "سیستم‌های نهفته"
    },
    "Research": {
        "en": "Research",
        "de": "Forschung",
        "fa": "پژوهش"
    },
}

# Reverse lookup: localized name -> canonical ID
# Built dynamically from TAG_TRANSLATIONS
_REVERSE_LOOKUP: dict[str, str] = {}


def _build_reverse_lookup() -> dict[str, str]:
    """Build reverse lookup from localized names to canonical IDs."""
    result = {}
    for canonical_id, labels in TAG_TRANSLATIONS.items():
        for lang, localized_name in labels.items():
            if localized_name:
                # Use lowercase for case-insensitive lookup
                result[localized_name.lower()] = canonical_id
    return result


def get_reverse_lookup() -> dict[str, str]:
    """Get the reverse lookup dictionary (localized name -> canonical ID)."""
    global _REVERSE_LOOKUP
    if not _REVERSE_LOOKUP:
        _REVERSE_LOOKUP = _build_reverse_lookup()
    return _REVERSE_LOOKUP


class TagCatalog:
    """
    Manages the tag catalog with canonical IDs and localized labels.

    This class provides:
    - Tag lookup by canonical ID
    - Localized label retrieval
    - Translation between canonical ID and localized form
    - Validation of tags and language coverage
    """

    def __init__(self, additional_translations: Optional[dict[str, dict[str, str]]] = None):
        """
        Initialize the tag catalog.

        Args:
            additional_translations: Optional additional tag translations to merge
                                    with the built-in translations.
        """
        self._translations = TAG_TRANSLATIONS.copy()
        if additional_translations:
            self._translations.update(additional_translations)
        # Use the global reverse lookup for efficiency
        self._reverse_lookup = get_reverse_lookup()

    def get_all_tags(self) -> list[str]:
        """Get all canonical tag IDs."""
        return list(self._translations.keys())

    def get_tag_label(self, tag_id: str, language: str = DEFAULT_LANGUAGE) -> str:
        """
        Get the localized label for a tag.

        Args:
            tag_id: Canonical tag ID (English).
            language: Target language code (en, de, fa).

        Returns:
            Localized label if available, otherwise the canonical ID.
        """
        if tag_id in self._translations:
            labels = self._translations[tag_id]
            if language in labels and labels[language]:
                return labels[language]
        # Fallback to canonical ID
        return tag_id

    def get_tag_labels(self, tag_id: str) -> dict[str, str]:
        """
        Get all labels for a tag.

        Args:
            tag_id: Canonical tag ID.

        Returns:
            Dict mapping language codes to labels.
        """
        if tag_id in self._translations:
            return self._translations[tag_id].copy()
        return {"en": tag_id}

    def to_canonical(self, tag_value: str) -> str:
        """
        Convert a tag value (possibly localized) to its canonical ID.

        This handles backward compatibility for CVs that may have
        localized tag values.

        Args:
            tag_value: Tag value (canonical or localized).

        Returns:
            Canonical tag ID.
        """
        # First, check if it's already a canonical ID
        if tag_value in self._translations:
            return tag_value

        # Try reverse lookup (case-insensitive)
        reverse = get_reverse_lookup()
        if tag_value.lower() in reverse:
            return reverse[tag_value.lower()]

        # Not found - return as-is (user-defined tag)
        return tag_value

    def from_canonical(self, tag_id: str, language: str = DEFAULT_LANGUAGE) -> str:
        """
        Convert a canonical tag ID to its localized form.

        Args:
            tag_id: Canonical tag ID.
            language: Target language code.

        Returns:
            Localized tag string.
        """
        return self.get_tag_label(tag_id, language)

    def has_translation(self, tag_id: str, language: str) -> bool:
        """
        Check if a tag has a translation for the given language.

        Args:
            tag_id: Canonical tag ID.
            language: Target language code.

        Returns:
            True if translation exists, False otherwise.
        """
        if tag_id not in self._translations:
            return False
        labels = self._translations[tag_id]
        return language in labels and bool(labels[language])

    def get_missing_translations(self, language: str) -> list[str]:
        """
        Get list of tags missing translations for a language.

        Args:
            language: Target language code.

        Returns:
            List of canonical tag IDs without translations.
        """
        missing = []
        for tag_id in self._translations:
            if not self.has_translation(tag_id, language):
                missing.append(tag_id)
        return missing

    def add_tag(
        self,
        tag_id: str,
        labels: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        Add a new tag to the catalog.

        Args:
            tag_id: Canonical tag ID (should be English).
            labels: Dict of language -> label mappings.

        Returns:
            Tag object dict.
        """
        if labels is None:
            labels = {}

        # Ensure English label exists
        if "en" not in labels:
            labels["en"] = tag_id

        self._translations[tag_id] = labels
        # Update reverse lookup
        for lang, localized_name in labels.items():
            if localized_name:
                self._reverse_lookup[localized_name.lower()] = tag_id

        return {
            "id": tag_id,
            "labels": labels,
            "scopes": list(labels.keys()),
        }

    def register_tag_if_missing(self, tag_id: str) -> bool:
        """
        Register a tag if it's not already in the catalog.

        Args:
            tag_id: Canonical tag ID.

        Returns:
            True if newly registered, False if already exists.
        """
        if tag_id in self._translations:
            return False
        self._translations[tag_id] = {"en": tag_id}
        return True


# Global catalog instance
_catalog: Optional[TagCatalog] = None


def get_tag_catalog() -> TagCatalog:
    """Get the global tag catalog instance."""
    global _catalog
    if _catalog is None:
        _catalog = TagCatalog()
    return _catalog


def translate_tags(
    tags: list[str],
    language: str = DEFAULT_LANGUAGE
) -> list[tuple[str, str]]:
    """
    Translate a list of tags to the target language.

    Args:
        tags: List of canonical tag IDs.
        language: Target language code.

    Returns:
        List of (canonical_id, localized_label) tuples.
    """
    catalog = get_tag_catalog()
    return [(tag, catalog.get_tag_label(tag, language)) for tag in tags]


def canonicalize_tags(tags: list[str]) -> list[str]:
    """
    Convert a list of tag values to canonical IDs.

    Handles backward compatibility for localized tag values.

    Args:
        tags: List of tag values (possibly localized).

    Returns:
        List of canonical tag IDs.
    """
    catalog = get_tag_catalog()
    return [catalog.to_canonical(tag) for tag in tags]


def export_tags(
    tags: list[str],
    language: str = DEFAULT_LANGUAGE
) -> list[str]:
    """
    Export tags in the specified language.

    Args:
        tags: List of canonical tag IDs.
        language: Target language code for export.

    Returns:
        List of localized tag strings.
    """
    catalog = get_tag_catalog()
    return [catalog.from_canonical(tag, language) for tag in tags]


def validate_tags(
    tags: list[str],
    language: str = DEFAULT_LANGUAGE
) -> dict[str, Any]:
    """
    Validate tags and report any issues.

    Args:
        tags: List of tag values.
        language: Target language for translation check.

    Returns:
        Validation result dict with warnings and errors.
    """
    catalog = get_tag_catalog()
    result = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "canonical_tags": [],
        "missing_translations": [],
    }

    for tag in tags:
        canonical = catalog.to_canonical(tag)
        result["canonical_tags"].append(canonical)

        # Check if tag has translation for current language
        if not catalog.has_translation(canonical, language):
            result["warnings"].append(
                f"Tag '{canonical}' has no translation for language '{language}'"
            )
            result["missing_translations"].append(canonical)

    return result


def get_tags_for_language(
    tags: list[str],
    language: str,
    include_all: bool = False
) -> list[tuple[str, str]]:
    """
    Get tags suitable for a specific language.

    Args:
        tags: List of canonical tag IDs.
        language: Target language code.
        include_all: If True, include tags without translation (using canonical ID).

    Returns:
        List of (canonical_id, display_label) tuples.
    """
    catalog = get_tag_catalog()
    result = []

    for tag in tags:
        has_trans = catalog.has_translation(tag, language)
        if has_trans or include_all:
            label = catalog.get_tag_label(tag, language)
            result.append((tag, label))

    return result
