"""
Tests for Language-Aware Tagging functionality.

Tests the canonical tag ID strategy (Option A):
- Tag display in selected language
- Tag export in export language
- Missing translation warnings
- Language switching
"""

import json
from pathlib import Path

import pytest

from cv_generator.db import (
    export_cv,
    get_section_entries,
    import_cv,
    init_db,
    update_entry_tags,
)
from cv_generator.tags import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    TAG_TRANSLATIONS,
    TagCatalog,
    canonicalize_tags,
    export_tags,
    get_tag_catalog,
    translate_tags,
    validate_tags,
)


class TestTagCatalog:
    """Tests for TagCatalog class."""

    def test_get_all_tags(self):
        """Test getting all canonical tag IDs."""
        catalog = TagCatalog()
        tags = catalog.get_all_tags()

        assert "Full CV" in tags
        assert "Academic" in tags
        assert "Programming" in tags

    def test_get_tag_label_english(self):
        """Test getting tag label in English (default)."""
        catalog = TagCatalog()

        label = catalog.get_tag_label("Full CV", "en")
        assert label == "Full CV"

    def test_get_tag_label_german(self):
        """Test getting tag label in German."""
        catalog = TagCatalog()

        label = catalog.get_tag_label("Full CV", "de")
        assert label == "Vollständiger Lebenslauf"

    def test_get_tag_label_farsi(self):
        """Test getting tag label in Farsi."""
        catalog = TagCatalog()

        label = catalog.get_tag_label("Full CV", "fa")
        assert label == "رزومه کامل"

    def test_get_tag_label_unknown_language_falls_back_to_canonical(self):
        """Test fallback to canonical ID for unknown language."""
        catalog = TagCatalog()

        label = catalog.get_tag_label("Full CV", "unknown")
        assert label == "Full CV"

    def test_get_tag_label_unknown_tag_returns_tag_id(self):
        """Test that unknown tags return the tag ID as-is."""
        catalog = TagCatalog()

        label = catalog.get_tag_label("Custom User Tag", "de")
        assert label == "Custom User Tag"

    def test_to_canonical_with_canonical_id(self):
        """Test to_canonical with already canonical ID."""
        catalog = TagCatalog()

        canonical = catalog.to_canonical("Full CV")
        assert canonical == "Full CV"

    def test_to_canonical_with_localized_german(self):
        """Test to_canonical with German localized name."""
        catalog = TagCatalog()

        canonical = catalog.to_canonical("Vollständiger Lebenslauf")
        assert canonical == "Full CV"

    def test_to_canonical_with_localized_farsi(self):
        """Test to_canonical with Farsi localized name."""
        catalog = TagCatalog()

        canonical = catalog.to_canonical("برنامه‌نویسی")
        assert canonical == "Programming"

    def test_to_canonical_case_insensitive(self):
        """Test to_canonical is case-insensitive."""
        catalog = TagCatalog()

        canonical = catalog.to_canonical("full cv")
        assert canonical == "Full CV"

    def test_to_canonical_unknown_tag_returns_as_is(self):
        """Test to_canonical with unknown tag returns as-is."""
        catalog = TagCatalog()

        canonical = catalog.to_canonical("Custom Tag")
        assert canonical == "Custom Tag"

    def test_from_canonical_english(self):
        """Test from_canonical to English."""
        catalog = TagCatalog()

        localized = catalog.from_canonical("Programming", "en")
        assert localized == "Programming"

    def test_from_canonical_german(self):
        """Test from_canonical to German."""
        catalog = TagCatalog()

        localized = catalog.from_canonical("Programming", "de")
        assert localized == "Programmierung"

    def test_has_translation_true(self):
        """Test has_translation returns True for existing translation."""
        catalog = TagCatalog()

        assert catalog.has_translation("Full CV", "de") is True
        assert catalog.has_translation("Full CV", "fa") is True

    def test_has_translation_false_for_unknown_tag(self):
        """Test has_translation returns False for unknown tag."""
        catalog = TagCatalog()

        assert catalog.has_translation("Unknown Tag", "de") is False

    def test_get_missing_translations(self):
        """Test getting list of tags missing translations."""
        catalog = TagCatalog()

        # Add a tag without German translation
        catalog.add_tag("TestOnly", {"en": "TestOnly"})

        missing = catalog.get_missing_translations("de")
        assert "TestOnly" in missing

    def test_add_tag(self):
        """Test adding a new tag to catalog."""
        catalog = TagCatalog()

        result = catalog.add_tag("New Tag", {"en": "New Tag", "de": "Neuer Tag"})

        assert result["id"] == "New Tag"
        assert catalog.get_tag_label("New Tag", "de") == "Neuer Tag"

    def test_add_tag_sets_english_default(self):
        """Test that add_tag sets English label to tag_id by default."""
        catalog = TagCatalog()

        result = catalog.add_tag("Another Tag")

        assert result["labels"]["en"] == "Another Tag"

    def test_register_tag_if_missing(self):
        """Test registering a tag if it doesn't exist."""
        catalog = TagCatalog()

        # New tag
        assert catalog.register_tag_if_missing("BrandNewTag") is True
        # Already exists
        assert catalog.register_tag_if_missing("BrandNewTag") is False
        # Built-in tag
        assert catalog.register_tag_if_missing("Full CV") is False


class TestTagTranslationFunctions:
    """Tests for module-level translation functions."""

    def test_translate_tags(self):
        """Test translate_tags returns tuples of canonical and localized."""
        result = translate_tags(["Full CV", "Programming"], "de")

        assert len(result) == 2
        assert result[0] == ("Full CV", "Vollständiger Lebenslauf")
        assert result[1] == ("Programming", "Programmierung")

    def test_canonicalize_tags(self):
        """Test canonicalize_tags converts localized to canonical."""
        result = canonicalize_tags(["Vollständiger Lebenslauf", "Programmierung"])

        assert result == ["Full CV", "Programming"]

    def test_export_tags(self):
        """Test export_tags returns localized strings."""
        result = export_tags(["Full CV", "Academic"], "de")

        assert result == ["Vollständiger Lebenslauf", "Akademisch"]

    def test_validate_tags_no_warnings(self):
        """Test validate_tags with valid tags."""
        result = validate_tags(["Full CV", "Academic"], "en")

        assert result["valid"] is True
        assert len(result["warnings"]) == 0
        assert result["canonical_tags"] == ["Full CV", "Academic"]

    def test_validate_tags_with_missing_translations(self):
        """Test validate_tags warns about missing translations."""
        # Use a custom tag without German translation
        result = validate_tags(["CustomTag"], "de")

        assert len(result["warnings"]) > 0
        assert "CustomTag" in result["missing_translations"]


class TestExportWithLanguage:
    """Tests for language-aware export functionality."""

    @pytest.fixture
    def populated_db(self, tmp_path):
        """Create a database with imported CV data."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Project A", "type_key": ["Full CV", "Programming"]},
                {"title": "Project B", "type_key": ["Academic"]}
            ]
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))

        import_cv(cv_path, db_path)
        return db_path

    def test_export_without_language_uses_canonical(self, populated_db):
        """Test export without language uses canonical (English) IDs."""
        exported = export_cv("testuser", populated_db, apply_tags=True)

        project_a = exported["projects"][0]
        assert project_a["type_key"] == ["Full CV", "Programming"]

    def test_export_with_german_language(self, populated_db):
        """Test export with German language translates tags."""
        exported = export_cv(
            "testuser", populated_db, apply_tags=True, tag_language="de"
        )

        project_a = exported["projects"][0]
        assert project_a["type_key"] == ["Vollständiger Lebenslauf", "Programmierung"]

    def test_export_with_farsi_language(self, populated_db):
        """Test export with Farsi language translates tags."""
        exported = export_cv(
            "testuser", populated_db, apply_tags=True, tag_language="fa"
        )

        project_a = exported["projects"][0]
        assert project_a["type_key"] == ["رزومه کامل", "برنامه‌نویسی"]

    def test_export_with_english_language_uses_canonical(self, populated_db):
        """Test export with English language uses canonical IDs."""
        exported = export_cv(
            "testuser", populated_db, apply_tags=True, tag_language="en"
        )

        project_a = exported["projects"][0]
        assert project_a["type_key"] == ["Full CV", "Programming"]

    def test_export_preserves_unknown_tags(self, populated_db):
        """Test that unknown tags are preserved as-is in export."""
        # Update with a custom tag
        entries = get_section_entries("testuser", "projects", populated_db)
        entry_id = entries[0]["id"]
        update_entry_tags(entry_id, ["CustomTag", "Full CV"], populated_db)

        exported = export_cv(
            "testuser", populated_db, apply_tags=True, tag_language="de"
        )

        project_a = exported["projects"][0]
        # CustomTag should remain, Full CV should be translated
        assert "CustomTag" in project_a["type_key"]
        assert "Vollständiger Lebenslauf" in project_a["type_key"]


class TestLanguageSwitching:
    """Tests for language switching behavior."""

    def test_same_tag_different_display_per_language(self):
        """Test same canonical tag shows differently per language."""
        catalog = get_tag_catalog()

        en_label = catalog.get_tag_label("Full CV", "en")
        de_label = catalog.get_tag_label("Full CV", "de")
        fa_label = catalog.get_tag_label("Full CV", "fa")

        assert en_label == "Full CV"
        assert de_label == "Vollständiger Lebenslauf"
        assert fa_label == "رزومه کامل"

        # All refer to the same canonical ID
        assert catalog.to_canonical(en_label) == "Full CV"
        assert catalog.to_canonical(de_label) == "Full CV"
        assert catalog.to_canonical(fa_label) == "Full CV"

    def test_switching_language_preserves_tag_identity(self):
        """Test that switching language doesn't lose tags."""
        tags = ["Full CV", "Academic", "Programming"]

        # Translate to German
        de_tags = export_tags(tags, "de")
        assert len(de_tags) == 3

        # Canonicalize back
        canonical = canonicalize_tags(de_tags)
        assert canonical == tags

    def test_round_trip_through_all_languages(self):
        """Test round-trip through all supported languages."""
        original_tags = ["Full CV", "Bioinformatics"]

        for lang in SUPPORTED_LANGUAGES:
            # Export to language
            localized = export_tags(original_tags, lang)
            # Back to canonical
            canonical = canonicalize_tags(localized)

            assert canonical == original_tags, f"Failed for language: {lang}"


class TestWebLanguageAwareness:
    """Tests for Flask web app language-aware features."""

    @pytest.fixture
    def app(self, tmp_path):
        """Create a test Flask app with a test database."""
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Import some test data with known tags
        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Test Project", "type_key": ["Full CV", "Programming"]}
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

    def test_tags_page_shows_language_selector(self, client):
        """Test tags page shows language selector."""
        response = client.get("/tags")
        assert response.status_code == 200
        assert b"EN" in response.data
        assert b"DE" in response.data
        assert b"FA" in response.data

    def test_set_language_changes_session(self, client):
        """Test setting language changes the session."""
        # Set language to German
        response = client.get("/language/de", follow_redirects=True)
        assert response.status_code == 200

        # Now check tags page
        response = client.get("/tags")
        assert response.status_code == 200
        # The German translation should appear
        assert "Vollständiger Lebenslauf".encode() in response.data

    def test_invalid_language_shows_error(self, client):
        """Test setting invalid language shows error."""
        response = client.get("/language/invalid", follow_redirects=True)
        assert response.status_code == 200
        assert b"Unsupported language" in response.data

    def test_entry_page_shows_entry_language_indicator(self, client):
        """Test entry page shows entry language indicator (not session language selector)."""
        # First get an entry ID (skip basics which is id 1)
        response = client.get("/entry/2")
        assert response.status_code == 200
        # Check for entry language indicator
        assert b"Entry Language:" in response.data
        # English entry should show EN
        assert b"EN" in response.data

    def test_tags_display_in_selected_language(self, client):
        """Test tags display in the selected language."""
        # Set to German
        client.get("/language/de")

        # Check tags page
        response = client.get("/tags")
        assert response.status_code == 200

        # Should show German translations with English canonical in parentheses
        assert "Vollständiger Lebenslauf".encode() in response.data
        # English canonical should also appear
        assert b"Full CV" in response.data


class TestEntryLanguageAwareTags:
    """Tests for entry-specific language-aware tag display."""

    @pytest.fixture
    def multilang_app(self, tmp_path):
        """Create a test Flask app with multilingual CV data."""
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Import English CV
        cv_en = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Test Project EN", "type_key": ["Full CV", "Programming"]}
            ]
        }
        cv_path_en = tmp_path / "cvs" / "testuser.json"
        cv_path_en.parent.mkdir(parents=True, exist_ok=True)
        cv_path_en.write_text(json.dumps(cv_en, ensure_ascii=False))
        import_cv(cv_path_en, db_path)

        # Import German CV
        cv_de = {
            "basics": [{"fname": "Test", "lname": "Benutzer"}],
            "projects": [
                {"title": "Testprojekt DE", "type_key": ["Full CV", "Programming"]}
            ]
        }
        cv_path_de = tmp_path / "cvs" / "testuser_de.json"
        cv_path_de.write_text(json.dumps(cv_de, ensure_ascii=False))
        import_cv(cv_path_de, db_path)

        # Import Farsi CV
        cv_fa = {
            "basics": [{"fname": "تست", "lname": "کاربر"}],
            "projects": [
                {"title": "پروژه تست FA", "type_key": ["Full CV", "Programming"]}
            ]
        }
        cv_path_fa = tmp_path / "cvs" / "testuser_fa.json"
        cv_path_fa.write_text(json.dumps(cv_fa, ensure_ascii=False))
        import_cv(cv_path_fa, db_path)

        app = create_app(db_path)
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def multilang_client(self, multilang_app):
        """Create a test client for multilingual app."""
        return multilang_app.test_client()

    def test_english_entry_shows_tags_in_english(self, multilang_client):
        """Test that English entry displays tags in English."""
        # Get the English project entry (id 2 is projects for testuser)
        response = multilang_client.get("/entry/2")
        assert response.status_code == 200
        # Should show entry language indicator
        assert b"Entry Language:" in response.data
        assert b">EN</span>" in response.data or b">EN<" in response.data
        # Tags should be in English canonical form
        assert b"Full CV" in response.data
        assert b"Programming" in response.data

    def test_german_entry_shows_tags_in_german(self, multilang_client):
        """Test that German entry displays tags in German."""
        # Get the German project entry (id 4 is projects for testuser_de)
        response = multilang_client.get("/entry/4")
        assert response.status_code == 200
        # Should show DE language indicator
        assert b"Entry Language:" in response.data
        # Tags should be in German
        assert "Vollständiger Lebenslauf".encode() in response.data
        assert "Programmierung".encode() in response.data

    def test_farsi_entry_shows_tags_in_farsi(self, multilang_client):
        """Test that Farsi entry displays tags in Farsi."""
        # Get the Farsi project entry (id 6 is projects for testuser_fa)
        response = multilang_client.get("/entry/6")
        assert response.status_code == 200
        # Should show FA language indicator
        assert b"Entry Language:" in response.data
        # Tags should be in Farsi
        assert "رزومه کامل".encode() in response.data
        assert "برنامه‌نویسی".encode() in response.data

    def test_entry_language_independent_of_session_language(self, multilang_client):
        """Test that entry tag language is based on entry, not session."""
        # Set session language to German
        multilang_client.get("/language/de")

        # Access English entry - should still show English tags
        response = multilang_client.get("/entry/2")
        assert response.status_code == 200
        # Tags should still be in English (based on entry), not German
        assert b"Full CV" in response.data
        # The entry language indicator should show EN
        assert b"Entry Language:" in response.data
