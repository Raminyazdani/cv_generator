"""
Tests for configurable language support.

Tests for F-008: RTL language detection was hardcoded.
Now supports additional RTL languages and configuration via config file.
"""

import pytest
from pathlib import Path

from cv_generator.languages_config import (
    LanguageConfig,
    is_rtl,
    get_language_config,
    set_language_config,
    reset_language_config,
    DEFAULT_RTL_LANGUAGES,
    LANGUAGE_METADATA,
)


class TestDefaultRTLLanguages:
    """Tests for default RTL language configuration."""

    def test_default_rtl_languages_includes_original(self):
        """Test that original RTL languages are included in defaults."""
        config = LanguageConfig()

        # Original languages (fa, ar, he)
        assert config.is_rtl('ar') is True
        assert config.is_rtl('he') is True
        assert config.is_rtl('fa') is True

    def test_default_rtl_languages_includes_new(self):
        """Test that new RTL languages are included (F-008 fix)."""
        config = LanguageConfig()

        # New languages
        assert config.is_rtl('ur') is True  # Urdu
        assert config.is_rtl('ps') is True  # Pashto
        assert config.is_rtl('yi') is True  # Yiddish
        assert config.is_rtl('ug') is True  # Uyghur
        assert config.is_rtl('sd') is True  # Sindhi
        assert config.is_rtl('ku') is True  # Kurdish
        assert config.is_rtl('dv') is True  # Dhivehi

    def test_ltr_languages_not_rtl(self):
        """Test that LTR languages are correctly identified."""
        config = LanguageConfig()

        assert config.is_rtl('en') is False
        assert config.is_rtl('de') is False
        assert config.is_rtl('fr') is False
        assert config.is_rtl('es') is False
        assert config.is_rtl('zh') is False
        assert config.is_rtl('ja') is False
        assert config.is_rtl('ko') is False


class TestCaseInsensitiveRTLDetection:
    """Test that RTL detection is case-insensitive."""

    def test_uppercase_rtl_detection(self):
        """Test RTL detection with uppercase language codes."""
        config = LanguageConfig()

        assert config.is_rtl('AR') is True
        assert config.is_rtl('HE') is True
        assert config.is_rtl('FA') is True

    def test_mixed_case_rtl_detection(self):
        """Test RTL detection with mixed case language codes."""
        config = LanguageConfig()

        assert config.is_rtl('Ar') is True
        assert config.is_rtl('He') is True
        assert config.is_rtl('Fa') is True

    def test_lowercase_rtl_detection(self):
        """Test RTL detection with lowercase language codes."""
        config = LanguageConfig()

        assert config.is_rtl('ar') is True
        assert config.is_rtl('he') is True
        assert config.is_rtl('fa') is True


class TestCustomRTLLanguages:
    """Tests for custom RTL language configuration."""

    def test_custom_rtl_languages_override(self):
        """Test that custom RTL languages override defaults."""
        custom_rtl = {'ar', 'he', 'fa', 'custom'}
        config = LanguageConfig(rtl_languages=custom_rtl)

        assert config.is_rtl('custom') is True
        assert config.is_rtl('ar') is True
        # When providing custom rtl_languages, it overrides defaults
        # So languages not in custom_rtl are not RTL
        assert config.is_rtl('ur') is False  # Not in custom set

    def test_empty_custom_rtl_languages(self):
        """Test empty custom RTL languages set."""
        config = LanguageConfig(rtl_languages=set())

        assert config.is_rtl('ar') is False
        assert config.is_rtl('en') is False


class TestRuntimeLanguageModification:
    """Tests for runtime modification of RTL languages."""

    def test_add_rtl_language(self):
        """Test adding RTL language at runtime."""
        config = LanguageConfig()

        # Initially not RTL
        assert config.is_rtl('test') is False

        # Add at runtime
        config.add_rtl_language('test')

        # Now is RTL
        assert config.is_rtl('test') is True

    def test_remove_rtl_language(self):
        """Test removing RTL language at runtime."""
        config = LanguageConfig()

        # Initially RTL
        assert config.is_rtl('ar') is True

        # Remove at runtime
        config.remove_rtl_language('ar')

        # No longer RTL
        assert config.is_rtl('ar') is False

    def test_add_and_remove_rtl_language(self):
        """Test adding and removing RTL language."""
        config = LanguageConfig()

        config.add_rtl_language('custom')
        assert config.is_rtl('custom') is True

        config.remove_rtl_language('custom')
        assert config.is_rtl('custom') is False


class TestLanguageMetadata:
    """Tests for language metadata retrieval."""

    def test_get_arabic_metadata(self):
        """Test retrieving Arabic metadata."""
        config = LanguageConfig()

        ar_meta = config.get_metadata('ar')
        assert ar_meta['name'] == 'Arabic'
        assert ar_meta['rtl'] is True
        assert 'name_native' in ar_meta
        assert ar_meta['requires_special_fonts'] is True

    def test_get_english_metadata(self):
        """Test retrieving English metadata."""
        config = LanguageConfig()

        en_meta = config.get_metadata('en')
        assert en_meta['name'] == 'English'
        assert en_meta['rtl'] is False
        assert en_meta['requires_special_fonts'] is False

    def test_get_unknown_language_metadata(self):
        """Test retrieving metadata for unknown language."""
        config = LanguageConfig()

        unknown_meta = config.get_metadata('xyz')
        assert unknown_meta['name'] == 'XYZ'
        assert unknown_meta['rtl'] is False

    def test_metadata_is_copy(self):
        """Test that get_metadata returns a copy."""
        config = LanguageConfig()

        meta1 = config.get_metadata('ar')
        meta2 = config.get_metadata('ar')

        # Should be equal but not the same object
        assert meta1 == meta2
        meta1['custom'] = 'value'
        assert 'custom' not in meta2


class TestLanguageName:
    """Tests for language name retrieval."""

    def test_get_english_language_name(self):
        """Test getting language name in English."""
        config = LanguageConfig()

        assert config.get_language_name('de', native=False) == 'German'
        assert config.get_language_name('ar', native=False) == 'Arabic'

    def test_get_native_language_name(self):
        """Test getting native language name."""
        config = LanguageConfig()

        assert config.get_language_name('de', native=True) == 'Deutsch'
        assert config.get_language_name('ar', native=True) == 'العربية'

    def test_unknown_language_name(self):
        """Test language name for unknown language."""
        config = LanguageConfig()

        # Unknown language returns uppercase code
        assert config.get_language_name('xyz', native=False) == 'XYZ'


class TestSpecialFontsRequirement:
    """Tests for special fonts requirement detection."""

    def test_arabic_requires_special_fonts(self):
        """Test that Arabic requires special fonts."""
        config = LanguageConfig()
        assert config.requires_special_fonts('ar') is True

    def test_english_no_special_fonts(self):
        """Test that English doesn't require special fonts."""
        config = LanguageConfig()
        assert config.requires_special_fonts('en') is False

    def test_chinese_requires_special_fonts(self):
        """Test that Chinese requires special fonts."""
        config = LanguageConfig()
        assert config.requires_special_fonts('zh') is True

    def test_unknown_language_no_special_fonts(self):
        """Test that unknown language doesn't require special fonts."""
        config = LanguageConfig()
        assert config.requires_special_fonts('xyz') is False


class TestConfigFileLoading:
    """Tests for loading language config from TOML file."""

    def test_load_from_config_file(self, tmp_path):
        """Test loading language config from TOML file."""
        config_file = tmp_path / 'test_config.toml'
        config_file.write_text("""
[languages]
rtl_languages = ["ar", "he", "fa", "ur", "test"]

[languages.metadata]
[languages.metadata.test]
name = "Test Language"
name_native = "TestLang"
rtl = true
        """)

        config = LanguageConfig(config_file=config_file)

        # Should load custom RTL language
        assert config.is_rtl('test') is True

        # Should load custom metadata
        test_meta = config.get_metadata('test')
        assert test_meta['name'] == 'Test Language'

    def test_nonexistent_config_file(self, tmp_path):
        """Test handling of nonexistent config file."""
        config_file = tmp_path / 'nonexistent.toml'

        # Should not raise, just use defaults
        config = LanguageConfig(config_file=config_file)

        # Should have default RTL languages
        assert config.is_rtl('ar') is True


class TestGlobalLanguageConfig:
    """Tests for global language config instance."""

    def setup_method(self):
        """Reset global config before each test."""
        reset_language_config()

    def teardown_method(self):
        """Reset global config after each test."""
        reset_language_config()

    def test_get_global_instance(self):
        """Test getting global language config instance."""
        config1 = get_language_config()
        assert isinstance(config1, LanguageConfig)

        # Same instance on subsequent calls
        config2 = get_language_config()
        assert config1 is config2

    def test_set_custom_instance(self):
        """Test setting custom global instance."""
        custom_config = LanguageConfig(rtl_languages={'custom'})
        set_language_config(custom_config)

        config = get_language_config()
        assert config is custom_config
        assert config.is_rtl('custom') is True

    def test_reset_global_config(self):
        """Test resetting global config."""
        # Get initial config
        config1 = get_language_config()

        # Set custom
        custom_config = LanguageConfig(rtl_languages={'custom'})
        set_language_config(custom_config)

        # Reset
        reset_language_config()

        # Get new config - should be new instance
        config2 = get_language_config()
        assert config2 is not config1
        assert config2 is not custom_config


class TestConvenienceFunction:
    """Tests for the convenience is_rtl function."""

    def setup_method(self):
        """Reset global config before each test."""
        reset_language_config()

    def teardown_method(self):
        """Reset global config after each test."""
        reset_language_config()

    def test_is_rtl_function(self):
        """Test convenience is_rtl function."""
        assert is_rtl('ar') is True
        assert is_rtl('en') is False
        assert is_rtl('ur') is True

    def test_is_rtl_empty_string(self):
        """Test is_rtl with empty string."""
        assert is_rtl('') is False

    def test_is_rtl_none_handling(self):
        """Test is_rtl with None-like values."""
        # The function should handle empty/None gracefully
        config = LanguageConfig()
        assert config.is_rtl('') is False


class TestGetAllRTLLanguages:
    """Tests for getting all RTL languages."""

    def test_get_all_rtl_languages(self):
        """Test getting all RTL language codes."""
        config = LanguageConfig()
        rtl_langs = config.get_all_rtl_languages()

        # Should be a set
        assert isinstance(rtl_langs, set)

        # Should include known RTL languages
        assert 'ar' in rtl_langs
        assert 'he' in rtl_langs
        assert 'fa' in rtl_langs
        assert 'ur' in rtl_langs

        # Should not include LTR languages
        assert 'en' not in rtl_langs

    def test_get_all_rtl_languages_is_copy(self):
        """Test that get_all_rtl_languages returns a copy."""
        config = LanguageConfig()

        rtl1 = config.get_all_rtl_languages()
        rtl2 = config.get_all_rtl_languages()

        # Modifying one shouldn't affect the other
        rtl1.add('custom')
        assert 'custom' not in rtl2


class TestCustomMetadata:
    """Tests for custom metadata handling."""

    def test_custom_metadata_override(self):
        """Test that custom metadata can override defaults."""
        custom_metadata = {
            'ar': {
                'name': 'Custom Arabic',
            }
        }
        config = LanguageConfig(custom_metadata=custom_metadata)

        ar_meta = config.get_metadata('ar')
        assert ar_meta['name'] == 'Custom Arabic'
        # Other fields should still be present from defaults
        assert ar_meta['rtl'] is True

    def test_custom_metadata_new_language(self):
        """Test adding metadata for new language."""
        custom_metadata = {
            'xyz': {
                'name': 'XYZ Language',
                'name_native': 'XYZ Native',
                'rtl': True,
                'requires_special_fonts': True,
            }
        }
        config = LanguageConfig(custom_metadata=custom_metadata)

        xyz_meta = config.get_metadata('xyz')
        assert xyz_meta['name'] == 'XYZ Language'
        assert xyz_meta['rtl'] is True


class TestDefaultConstants:
    """Tests for module-level constants."""

    def test_default_rtl_languages_constant(self):
        """Test DEFAULT_RTL_LANGUAGES constant."""
        assert isinstance(DEFAULT_RTL_LANGUAGES, set)
        assert 'ar' in DEFAULT_RTL_LANGUAGES
        assert 'he' in DEFAULT_RTL_LANGUAGES
        assert 'fa' in DEFAULT_RTL_LANGUAGES
        assert 'ur' in DEFAULT_RTL_LANGUAGES
        assert 'ps' in DEFAULT_RTL_LANGUAGES

    def test_language_metadata_constant(self):
        """Test LANGUAGE_METADATA constant."""
        assert isinstance(LANGUAGE_METADATA, dict)
        assert 'ar' in LANGUAGE_METADATA
        assert 'en' in LANGUAGE_METADATA
        assert 'de' in LANGUAGE_METADATA
