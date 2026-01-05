"""
Configurable language support with RTL detection.

Supports loading language configuration from:
1. Configuration file (cv_generator.toml)
2. Environment variables
3. Built-in defaults

This module addresses F-008: RTL language detection was hardcoded to only
support fa, ar, he. Now supports additional RTL languages like ur, ps, etc.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)

# Built-in default RTL languages (ISO 639-1 codes)
DEFAULT_RTL_LANGUAGES: Set[str] = {
    'ar',  # Arabic
    'he',  # Hebrew
    'fa',  # Farsi/Persian
    'ur',  # Urdu
    'ps',  # Pashto
    'yi',  # Yiddish
    'ug',  # Uyghur
    'sd',  # Sindhi
    'ku',  # Kurdish (some variants)
    'dv',  # Dhivehi/Maldivian
}

# Extended language metadata
LANGUAGE_METADATA: Dict[str, Dict[str, Any]] = {
    'ar': {
        'name': 'Arabic',
        'name_native': 'العربية',
        'rtl': True,
        'requires_special_fonts': True,
    },
    'he': {
        'name': 'Hebrew',
        'name_native': 'עברית',
        'rtl': True,
        'requires_special_fonts': True,
    },
    'fa': {
        'name': 'Persian/Farsi',
        'name_native': 'فارسی',
        'rtl': True,
        'requires_special_fonts': True,
    },
    'ur': {
        'name': 'Urdu',
        'name_native': 'اردو',
        'rtl': True,
        'requires_special_fonts': True,
    },
    'ps': {
        'name': 'Pashto',
        'name_native': 'پښتو',
        'rtl': True,
        'requires_special_fonts': True,
    },
    'yi': {
        'name': 'Yiddish',
        'name_native': 'ייִדיש',
        'rtl': True,
        'requires_special_fonts': True,
    },
    'ug': {
        'name': 'Uyghur',
        'name_native': 'ئۇيغۇرچە',
        'rtl': True,
        'requires_special_fonts': True,
    },
    'sd': {
        'name': 'Sindhi',
        'name_native': 'سنڌي',
        'rtl': True,
        'requires_special_fonts': True,
    },
    'ku': {
        'name': 'Kurdish',
        'name_native': 'کوردی',
        'rtl': True,
        'requires_special_fonts': True,
    },
    'dv': {
        'name': 'Dhivehi/Maldivian',
        'name_native': 'ދިވެހި',
        'rtl': True,
        'requires_special_fonts': True,
    },
    'en': {
        'name': 'English',
        'name_native': 'English',
        'rtl': False,
        'requires_special_fonts': False,
    },
    'de': {
        'name': 'German',
        'name_native': 'Deutsch',
        'rtl': False,
        'requires_special_fonts': False,
    },
    'fr': {
        'name': 'French',
        'name_native': 'Français',
        'rtl': False,
        'requires_special_fonts': False,
    },
    'es': {
        'name': 'Spanish',
        'name_native': 'Español',
        'rtl': False,
        'requires_special_fonts': False,
    },
    'zh': {
        'name': 'Chinese',
        'name_native': '中文',
        'rtl': False,
        'requires_special_fonts': True,
    },
    'ja': {
        'name': 'Japanese',
        'name_native': '日本語',
        'rtl': False,
        'requires_special_fonts': True,
    },
    'ko': {
        'name': 'Korean',
        'name_native': '한국어',
        'rtl': False,
        'requires_special_fonts': True,
    },
}


class LanguageConfig:
    """
    Centralized language configuration.

    Manages RTL detection, language metadata, and custom configurations.
    """

    def __init__(
        self,
        rtl_languages: Optional[Set[str]] = None,
        custom_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
        config_file: Optional[Path] = None,
    ):
        """
        Initialize language configuration.

        Args:
            rtl_languages: Set of RTL language codes (overrides defaults)
            custom_metadata: Custom language metadata
            config_file: Path to configuration file
        """
        # Start with defaults
        self._rtl_languages = DEFAULT_RTL_LANGUAGES.copy()
        self._metadata = {k: v.copy() for k, v in LANGUAGE_METADATA.items()}

        # Load from config file if provided
        if config_file and config_file.exists():
            self._load_from_config(config_file)

        # Apply custom overrides
        if rtl_languages is not None:
            self._rtl_languages = rtl_languages

        if custom_metadata:
            for lang_code, lang_info in custom_metadata.items():
                if lang_code not in self._metadata:
                    self._metadata[lang_code] = {}
                self._metadata[lang_code].update(lang_info)

        logger.debug(f"Language configuration loaded: {len(self._rtl_languages)} RTL languages")
        logger.debug(f"RTL languages: {sorted(self._rtl_languages)}")

    def _load_from_config(self, config_file: Path) -> None:
        """Load language configuration from TOML file."""
        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib

            with open(config_file, 'rb') as f:
                config = tomllib.load(f)

            # Load RTL languages
            if 'languages' in config and 'rtl_languages' in config['languages']:
                rtl_list = config['languages']['rtl_languages']
                if isinstance(rtl_list, list):
                    self._rtl_languages = set(rtl_list)
                    logger.info(f"Loaded RTL languages from config: {rtl_list}")

            # Load custom metadata
            if 'languages' in config and 'metadata' in config['languages']:
                metadata = config['languages']['metadata']
                if isinstance(metadata, dict):
                    for lang_code, lang_info in metadata.items():
                        if lang_code not in self._metadata:
                            self._metadata[lang_code] = {}
                        self._metadata[lang_code].update(lang_info)
                    logger.info(f"Loaded custom metadata for {len(metadata)} languages")

        except ImportError:
            logger.warning("tomli/tomllib not available, cannot load language config from file")
        except Exception as e:
            logger.error(f"Failed to load language config from {config_file}: {e}")

    def is_rtl(self, language_code: str) -> bool:
        """
        Check if language is right-to-left.

        The _rtl_languages set is authoritative for RTL status.
        Metadata is only used as a fallback for languages not in the RTL set.

        Args:
            language_code: ISO 639 language code (e.g., 'ar', 'en')

        Returns:
            True if language is RTL
        """
        if not language_code:
            return False

        # Normalize to lowercase
        lang = language_code.lower()

        # The RTL languages set is authoritative
        return lang in self._rtl_languages

    def get_metadata(self, language_code: str) -> Dict[str, Any]:
        """
        Get metadata for a language.

        Args:
            language_code: ISO 639 language code

        Returns:
            Dictionary of language metadata
        """
        lang = language_code.lower()

        if lang in self._metadata:
            return self._metadata[lang].copy()

        # Return minimal metadata for unknown languages
        return {
            'name': language_code.upper(),
            'name_native': language_code,
            'rtl': self.is_rtl(lang),
            'requires_special_fonts': False,
        }

    def get_language_name(self, language_code: str, native: bool = False) -> str:
        """
        Get human-readable language name.

        Args:
            language_code: ISO 639 language code
            native: If True, return native name (e.g., 'Deutsch' not 'German')

        Returns:
            Language name
        """
        metadata = self.get_metadata(language_code)

        if native:
            return metadata.get('name_native', language_code)
        else:
            return metadata.get('name', language_code.upper())

    def requires_special_fonts(self, language_code: str) -> bool:
        """
        Check if language requires special font configuration.

        Args:
            language_code: ISO 639 language code

        Returns:
            True if special fonts needed
        """
        metadata = self.get_metadata(language_code)
        return metadata.get('requires_special_fonts', False)

    def get_all_rtl_languages(self) -> Set[str]:
        """Get set of all RTL language codes."""
        return self._rtl_languages.copy()

    def add_rtl_language(self, language_code: str) -> None:
        """
        Add a language to RTL set (runtime addition).

        Args:
            language_code: ISO 639 language code
        """
        lang = language_code.lower()
        self._rtl_languages.add(lang)
        logger.debug(f"Added RTL language: {lang}")

    def remove_rtl_language(self, language_code: str) -> None:
        """
        Remove a language from RTL set (runtime removal).

        Args:
            language_code: ISO 639 language code
        """
        lang = language_code.lower()
        self._rtl_languages.discard(lang)
        logger.debug(f"Removed RTL language: {lang}")


# Global instance (can be replaced by application)
_global_language_config: Optional[LanguageConfig] = None


def get_language_config() -> LanguageConfig:
    """
    Get global language configuration instance.

    Returns:
        LanguageConfig instance
    """
    global _global_language_config

    if _global_language_config is None:
        # Initialize with defaults
        _global_language_config = LanguageConfig()

    return _global_language_config


def set_language_config(config: LanguageConfig) -> None:
    """
    Set global language configuration instance.

    Args:
        config: LanguageConfig instance
    """
    global _global_language_config
    _global_language_config = config


def reset_language_config() -> None:
    """
    Reset global language configuration to None.

    This forces re-initialization on next get_language_config() call.
    Useful for testing.
    """
    global _global_language_config
    _global_language_config = None


def is_rtl(language_code: str) -> bool:
    """
    Convenience function to check if language is RTL.

    Args:
        language_code: ISO 639 language code

    Returns:
        True if language is RTL
    """
    return get_language_config().is_rtl(language_code)
