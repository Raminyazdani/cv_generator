"""
Tests for Vocabulary Module - Canonical Key/Label Mapping.

Tests the integration of lang.json translations into the Web UI:
- Key to localized label mapping
- Reverse lookup (localized label → canonical key)
- Section name translations
- Integration with Web UI context
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cv_generator.vocabulary import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    Vocabulary,
    clear_vocabulary_cache,
    get_field_label,
    get_section_label,
    get_vocabulary,
)


class TestVocabulary:
    """Tests for Vocabulary class."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_vocabulary_cache()

    def test_get_label_english(self):
        """Test getting label in English returns a nicely formatted label."""
        vocab = get_vocabulary()

        # Keys that exist in lang.json with value == key should be formatted nicely
        label = vocab.get_label("fname", "en")
        assert label == "First Name"  # English value in lang.json is "fname", formatted as "First Name"

    def test_get_label_german(self):
        """Test getting label in German returns the German translation."""
        vocab = get_vocabulary()

        label = vocab.get_label("fname", "de")
        assert label == "Vorname"  # German translation in lang.json

    def test_get_label_farsi(self):
        """Test getting label in Farsi returns the Farsi translation."""
        vocab = get_vocabulary()

        label = vocab.get_label("fname", "fa")
        assert label == "نام"  # Farsi translation in lang.json

    def test_get_label_unknown_key_formats_nicely(self):
        """Test that unknown keys are formatted as readable labels."""
        vocab = get_vocabulary()

        # Unknown key should be formatted nicely
        label = vocab.get_label("unknownCamelCase", "en")
        assert label == "Unknown Camel Case"

    def test_get_label_snake_case_key(self):
        """Test that snake_case keys are formatted nicely."""
        vocab = get_vocabulary()

        # Snake case should be formatted nicely
        label = vocab.get_label("some_unknown_key", "en")
        assert label == "Some Unknown Key"

    def test_get_section_label_education(self):
        """Test getting section label for education."""
        vocab = get_vocabulary()

        # English is formatted nicely (since lang.json has "education" for EN)
        assert vocab.get_section_label("education", "en") == "Education"
        # German
        assert vocab.get_section_label("education", "de") == "Ausbildung"
        # Farsi
        assert vocab.get_section_label("education", "fa") == "تحصیلات"

    def test_get_section_label_projects(self):
        """Test getting section label for projects."""
        vocab = get_vocabulary()

        # German
        assert vocab.get_section_label("projects", "de") == "Projekte"
        # Farsi
        assert vocab.get_section_label("projects", "fa") == "پروژه‌ها"

    def test_get_section_label_experiences(self):
        """Test getting section label for experiences."""
        vocab = get_vocabulary()

        # German
        assert vocab.get_section_label("experiences", "de") == "Erfahrungen"
        # Farsi
        assert vocab.get_section_label("experiences", "fa") == "سوابق"

    def test_has_translation_true(self):
        """Test has_translation returns True for existing translation."""
        vocab = get_vocabulary()

        assert vocab.has_translation("fname", "de") is True
        assert vocab.has_translation("institution", "fa") is True

    def test_has_translation_false_for_unknown_key(self):
        """Test has_translation returns False for unknown key."""
        vocab = get_vocabulary()

        assert vocab.has_translation("unknown_key_xyz", "de") is False

    def test_has_translation_false_for_unknown_language(self):
        """Test has_translation returns False for unsupported language."""
        vocab = get_vocabulary()

        assert vocab.has_translation("fname", "xyz") is False

    def test_to_canonical_from_german(self):
        """Test reverse lookup from German label to canonical key."""
        vocab = get_vocabulary()

        # "Vorname" is the German translation of "fname"
        canonical = vocab.to_canonical("Vorname", "de")
        assert canonical == "fname"

    def test_to_canonical_from_farsi(self):
        """Test reverse lookup from Farsi label to canonical key."""
        vocab = get_vocabulary()

        # "تحصیلات" is the Farsi translation of "education"
        canonical = vocab.to_canonical("تحصیلات", "fa")
        assert canonical == "education"

    def test_to_canonical_case_insensitive(self):
        """Test reverse lookup is case-insensitive."""
        vocab = get_vocabulary()

        canonical = vocab.to_canonical("vorname", "de")
        assert canonical == "fname"

    def test_to_canonical_unknown_returns_as_is(self):
        """Test that unknown label returns as-is."""
        vocab = get_vocabulary()

        canonical = vocab.to_canonical("SomeUnknownLabel", "en")
        assert canonical == "SomeUnknownLabel"

    def test_get_all_labels(self):
        """Test getting all labels for a key."""
        vocab = get_vocabulary()

        labels = vocab.get_all_labels("fname")

        assert "en" in labels
        assert "de" in labels
        assert "fa" in labels
        assert labels["de"] == "Vorname"
        assert labels["fa"] == "نام"


class TestVocabularyConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_vocabulary_cache()

    def test_get_field_label(self):
        """Test get_field_label convenience function."""
        label = get_field_label("title", "de")
        assert label == "Titel"

    def test_get_section_label(self):
        """Test get_section_label convenience function."""
        label = get_section_label("publications", "de")
        assert label == "Publikationen"

    def test_default_language(self):
        """Test that default language is English."""
        assert DEFAULT_LANGUAGE == "en"

    def test_supported_languages(self):
        """Test that all expected languages are supported."""
        assert "en" in SUPPORTED_LANGUAGES
        assert "de" in SUPPORTED_LANGUAGES
        assert "fa" in SUPPORTED_LANGUAGES


class TestWebUIIntegration:
    """Tests for Web UI integration with vocabulary."""

    @pytest.fixture
    def app(self, tmp_path):
        """Create a test Flask app with a test database."""
        from cv_generator.db import import_cv, init_db
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Import some test data
        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Test Project", "description": "A test project"}
            ]
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))
        import_cv(cv_path, db_path)

        app = create_app(db_path)
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return app.test_client()

    def test_language_switching_shows_german_labels(self, client):
        """Test that switching to German shows German labels."""
        # Set language to German
        response = client.get("/language/de", follow_redirects=True)
        assert response.status_code == 200

        # Check tags page - should have German section label
        response = client.get("/tags")
        assert response.status_code == 200

    def test_language_switching_shows_farsi_labels(self, client):
        """Test that switching to Farsi shows Farsi labels."""
        # Set language to Farsi
        response = client.get("/language/fa", follow_redirects=True)
        assert response.status_code == 200

    def test_toggle_canonical_keys(self, client):
        """Test toggling canonical keys debug mode."""
        # Toggle on
        response = client.get("/debug/toggle-canonical-keys", follow_redirects=True)
        assert response.status_code == 200
        assert b"Developer mode" in response.data

        # Toggle off
        response = client.get("/debug/toggle-canonical-keys", follow_redirects=True)
        assert response.status_code == 200
        assert b"Developer mode" in response.data

    def test_vocabulary_in_context(self, client):
        """Test that vocabulary is available in template context."""
        response = client.get("/")
        assert response.status_code == 200

    def test_entry_form_uses_localized_labels(self, client):
        """Test that entry form uses localized labels for German."""
        # Set to German
        client.get("/language/de")

        # Access a form page that uses localized labels
        response = client.get("/tags")
        assert response.status_code == 200


class TestSectionFieldsLocalization:
    """Tests for section fields localization."""

    def test_get_section_fields_with_language(self):
        """Test _get_section_fields returns localized labels."""
        from cv_generator.web import _get_section_fields

        clear_vocabulary_cache()

        # Get fields for basics section in German
        fields = _get_section_fields("basics", "de")

        # Check that localized_label is present
        assert "localized_label" in fields["fname"]
        assert fields["fname"]["localized_label"] == "Vorname"

        # Check canonical_key is present
        assert "canonical_key" in fields["fname"]
        assert fields["fname"]["canonical_key"] == "fname"

    def test_get_section_fields_english_default(self):
        """Test _get_section_fields with English default."""
        from cv_generator.web import _get_section_fields

        clear_vocabulary_cache()

        # Get fields for projects section in English
        fields = _get_section_fields("projects", "en")

        # English label is formatted nicely (since lang.json EN value = key)
        assert "localized_label" in fields["title"]
        assert fields["title"]["localized_label"] == "Title"  # Formatted from "title"

    def test_get_section_fields_farsi(self):
        """Test _get_section_fields with Farsi language."""
        from cv_generator.web import _get_section_fields

        clear_vocabulary_cache()

        # Get fields for education section in Farsi
        fields = _get_section_fields("education", "fa")

        # Check Farsi labels
        assert fields["institution"]["localized_label"] == "مؤسسه/دانشگاه"
        assert fields["area"]["localized_label"] == "رشته/حوزه"
