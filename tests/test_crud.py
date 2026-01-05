"""
Tests for cv_generator.crud module.

Tests the CRUD operations and multi-language synchronization.
"""

import json
from pathlib import Path

import pytest

from cv_generator.crud import (
    SUPPORTED_LANGUAGES,
    ListSectionAdapter,
    create_entry,
    delete_entry,
    ensure_crud_schema,
    get_entry,
    get_linked_entries,
    get_section_adapter,
    link_existing_entries,
    list_entries,
    update_entry,
)
from cv_generator.db import get_section_entries, import_cv, init_db, list_persons


class TestCrudSchema:
    """Tests for CRUD schema initialization."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test database."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        return db_path

    def test_ensure_crud_schema_creates_tables(self, db):
        """Test that ensure_crud_schema creates the required tables."""
        import sqlite3

        ensure_crud_schema(db)

        conn = sqlite3.connect(db)
        try:
            cursor = conn.cursor()

            # Check stable_entry table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stable_entry'")
            assert cursor.fetchone() is not None

            # Check entry_lang_link table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entry_lang_link'")
            assert cursor.fetchone() is not None
        finally:
            conn.close()

    def test_ensure_crud_schema_idempotent(self, db):
        """Test that ensure_crud_schema can be called multiple times."""
        ensure_crud_schema(db)
        ensure_crud_schema(db)  # Should not raise


class TestSectionAdapter:
    """Tests for section adapter retrieval."""

    def test_get_list_section_adapter(self):
        """Test getting adapter for list sections."""
        adapter = get_section_adapter("projects")
        assert isinstance(adapter, ListSectionAdapter)

    def test_get_adapter_for_unsupported_section_raises(self):
        """Test that unsupported sections raise an error."""
        from cv_generator.errors import ValidationError

        with pytest.raises(ValidationError):
            get_section_adapter("unknown_section")


class TestCreateEntry:
    """Tests for entry creation with multi-language sync."""

    @pytest.fixture
    def populated_db(self, tmp_path):
        """Create a database with EN/DE/FA person variants."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Create EN CV
        cv_en = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Existing Project", "url": "https://example.com", "type_key": ["Full CV"]}
            ]
        }
        cv_en_path = tmp_path / "cvs" / "testuser.json"
        cv_en_path.parent.mkdir(parents=True, exist_ok=True)
        cv_en_path.write_text(json.dumps(cv_en, ensure_ascii=False))
        import_cv(cv_en_path, db_path)

        # Create DE CV
        cv_de = {
            "basics": [{"fname": "Test", "lname": "Benutzer"}],
            "projects": [
                {"title": "Bestehendes Projekt", "url": "https://example.com", "type_key": ["Vollständiger Lebenslauf"]}
            ]
        }
        cv_de_path = tmp_path / "cvs" / "testuser_de.json"
        cv_de_path.write_text(json.dumps(cv_de, ensure_ascii=False))
        import_cv(cv_de_path, db_path)

        # Create FA CV
        cv_fa = {
            "basics": [{"fname": "تست", "lname": "کاربر"}],
            "projects": [
                {"title": "پروژه موجود", "url": "https://example.com", "type_key": ["رزومه کامل"]}
            ]
        }
        cv_fa_path = tmp_path / "cvs" / "testuser_fa.json"
        cv_fa_path.write_text(json.dumps(cv_fa, ensure_ascii=False))
        import_cv(cv_fa_path, db_path)

        return db_path

    def test_create_entry_in_en_syncs_to_de_fa(self, populated_db):
        """Test that creating an entry in EN creates placeholders in DE/FA."""
        result = create_entry(
            person_slug="testuser",
            section="projects",
            data={
                "title": "New Project",
                "description": "A new project",
                "url": "https://new-project.com",
                "type_key": ["Full CV", "Programming"]
            },
            db_path=populated_db,
            sync_languages=True
        )

        assert result["stable_id"] is not None
        assert result["source_language"] == "en"
        assert "en" in result["entries"]
        assert "de" in result["entries"]
        assert "fa" in result["entries"]

        # Verify entries exist in all languages
        for lang in ["en", "de", "fa"]:
            entry_id = result["entries"][lang]
            slug = "testuser" if lang == "en" else f"testuser_{lang}"
            entries = list_entries(slug, "projects", populated_db)
            entry_ids = [e["id"] for e in entries]
            assert entry_id in entry_ids

    def test_create_entry_without_sync(self, populated_db):
        """Test creating an entry without multi-language sync."""
        result = create_entry(
            person_slug="testuser",
            section="projects",
            data={"title": "Solo Project"},
            db_path=populated_db,
            sync_languages=False
        )

        assert result["stable_id"] is not None
        assert "en" in result["entries"]
        assert "de" not in result["entries"]
        assert "fa" not in result["entries"]

    def test_create_entry_in_de_syncs_to_en_fa(self, populated_db):
        """Test that creating an entry in DE syncs to EN/FA."""
        result = create_entry(
            person_slug="testuser_de",
            section="projects",
            data={
                "title": "Neues Projekt",
                "description": "Ein neues Projekt",
                "url": "https://neues-projekt.de"
            },
            db_path=populated_db,
            sync_languages=True
        )

        assert result["source_language"] == "de"
        assert "en" in result["entries"]
        assert "de" in result["entries"]
        assert "fa" in result["entries"]


class TestUpdateEntry:
    """Tests for entry update with shared field sync."""

    @pytest.fixture
    def db_with_linked_entries(self, tmp_path):
        """Create a database with linked multi-language entries."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Create EN CV
        cv_en = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": []
        }
        cv_en_path = tmp_path / "cvs" / "testuser.json"
        cv_en_path.parent.mkdir(parents=True, exist_ok=True)
        cv_en_path.write_text(json.dumps(cv_en, ensure_ascii=False))
        import_cv(cv_en_path, db_path)

        # Create DE CV
        cv_de = {
            "basics": [{"fname": "Test", "lname": "Benutzer"}],
            "projects": []
        }
        cv_de_path = tmp_path / "cvs" / "testuser_de.json"
        cv_de_path.write_text(json.dumps(cv_de, ensure_ascii=False))
        import_cv(cv_de_path, db_path)

        # Create a linked entry
        result = create_entry(
            person_slug="testuser",
            section="projects",
            data={
                "title": "Original Title",
                "url": "https://original.com",
                "type_key": ["Full CV"]
            },
            db_path=db_path,
            sync_languages=True
        )

        return db_path, result

    def test_update_entry_text_fields_not_synced_by_default(self, db_with_linked_entries):
        """Test that text field updates don't sync by default."""
        db_path, create_result = db_with_linked_entries
        en_entry_id = create_result["entries"]["en"]
        de_entry_id = create_result["entries"]["de"]

        # Update EN entry title
        update_entry(
            entry_id=en_entry_id,
            data={"title": "Updated Title EN", "url": "https://original.com"},
            section="projects",
            db_path=db_path,
            sync_shared_fields=False
        )

        # Check DE entry still has placeholder title
        de_entry = get_entry(de_entry_id, "projects", db_path)
        assert de_entry["data"]["title"] == "Original Title"

    def test_update_entry_syncs_shared_fields(self, db_with_linked_entries):
        """Test that shared fields can be synced across languages."""
        db_path, create_result = db_with_linked_entries
        en_entry_id = create_result["entries"]["en"]
        de_entry_id = create_result["entries"]["de"]

        # Update EN entry with new URL (shared field)
        update_entry(
            entry_id=en_entry_id,
            data={
                "title": "Updated Title EN",
                "url": "https://new-url.com",
                "type_key": ["Full CV", "Programming"]
            },
            section="projects",
            db_path=db_path,
            sync_shared_fields=True
        )

        # Check DE entry has updated URL
        de_entry = get_entry(de_entry_id, "projects", db_path)
        assert de_entry["data"]["url"] == "https://new-url.com"
        # But title should still be placeholder
        assert de_entry["data"]["title"] == "Original Title"


class TestDeleteEntry:
    """Tests for entry deletion with multi-language sync."""

    @pytest.fixture
    def db_with_linked_entries(self, tmp_path):
        """Create a database with linked multi-language entries."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Create CVs for all languages
        for lang in ["", "_de", "_fa"]:
            cv = {
                "basics": [{"fname": "Test", "lname": "User"}],
                "projects": []
            }
            cv_path = tmp_path / "cvs" / f"testuser{lang}.json"
            cv_path.parent.mkdir(parents=True, exist_ok=True)
            cv_path.write_text(json.dumps(cv, ensure_ascii=False))
            import_cv(cv_path, db_path)

        # Create a linked entry
        result = create_entry(
            person_slug="testuser",
            section="projects",
            data={"title": "To Be Deleted"},
            db_path=db_path,
            sync_languages=True
        )

        return db_path, result

    def test_delete_entry_removes_all_language_variants(self, db_with_linked_entries):
        """Test that deleting an entry removes all language variants."""
        db_path, create_result = db_with_linked_entries
        en_entry_id = create_result["entries"]["en"]

        # Verify entries exist
        for lang, entry_id in create_result["entries"].items():
            entry = get_entry(entry_id, "projects", db_path)
            assert entry is not None

        # Delete from EN
        result = delete_entry(en_entry_id, "projects", db_path, sync_languages=True)
        assert result is True

        # Verify all language variants are deleted
        for lang, entry_id in create_result["entries"].items():
            entry = get_entry(entry_id, "projects", db_path)
            assert entry is None

    def test_delete_entry_without_sync(self, db_with_linked_entries):
        """Test deleting only one language variant."""
        db_path, create_result = db_with_linked_entries
        en_entry_id = create_result["entries"]["en"]
        de_entry_id = create_result["entries"]["de"]

        # Delete only EN variant
        result = delete_entry(en_entry_id, "projects", db_path, sync_languages=False)
        assert result is True

        # EN should be deleted
        en_entry = get_entry(en_entry_id, "projects", db_path)
        assert en_entry is None

        # DE should still exist
        de_entry = get_entry(de_entry_id, "projects", db_path)
        assert de_entry is not None


class TestGetLinkedEntries:
    """Tests for getting linked language variants."""

    @pytest.fixture
    def db_with_linked_entries(self, tmp_path):
        """Create a database with linked multi-language entries."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Create CVs for all languages
        for lang in ["", "_de", "_fa"]:
            cv = {
                "basics": [{"fname": "Test", "lname": "User"}],
                "projects": []
            }
            cv_path = tmp_path / "cvs" / f"testuser{lang}.json"
            cv_path.parent.mkdir(parents=True, exist_ok=True)
            cv_path.write_text(json.dumps(cv, ensure_ascii=False))
            import_cv(cv_path, db_path)

        # Create a linked entry
        result = create_entry(
            person_slug="testuser",
            section="projects",
            data={"title": "Linked Project"},
            db_path=db_path,
            sync_languages=True
        )

        return db_path, result

    def test_get_linked_entries_returns_all_variants(self, db_with_linked_entries):
        """Test getting all linked language variants."""
        db_path, create_result = db_with_linked_entries
        en_entry_id = create_result["entries"]["en"]

        linked = get_linked_entries(en_entry_id, "projects", db_path)

        assert "en" in linked
        assert "de" in linked
        assert "fa" in linked
        assert linked["en"]["id"] == en_entry_id

    def test_get_linked_entries_shows_needs_translation(self, db_with_linked_entries):
        """Test that linked entries show needs_translation flag."""
        db_path, create_result = db_with_linked_entries
        en_entry_id = create_result["entries"]["en"]

        linked = get_linked_entries(en_entry_id, "projects", db_path)

        # EN was the source, so it doesn't need translation
        assert linked["en"]["needs_translation"] is False
        # DE and FA were created as placeholders
        assert linked["de"]["needs_translation"] is True
        assert linked["fa"]["needs_translation"] is True


class TestLinkExistingEntries:
    """Tests for linking existing entries from different languages."""

    @pytest.fixture
    def db_with_unlinked_entries(self, tmp_path):
        """Create a database with unlinked entries in different languages."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Create EN CV with a project
        cv_en = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [{"title": "EN Project", "url": "https://example.com"}]
        }
        cv_en_path = tmp_path / "cvs" / "testuser.json"
        cv_en_path.parent.mkdir(parents=True, exist_ok=True)
        cv_en_path.write_text(json.dumps(cv_en, ensure_ascii=False))
        import_cv(cv_en_path, db_path)

        # Create DE CV with equivalent project
        cv_de = {
            "basics": [{"fname": "Test", "lname": "Benutzer"}],
            "projects": [{"title": "DE Projekt", "url": "https://example.com"}]
        }
        cv_de_path = tmp_path / "cvs" / "testuser_de.json"
        cv_de_path.write_text(json.dumps(cv_de, ensure_ascii=False))
        import_cv(cv_de_path, db_path)

        # Get the entry IDs
        en_entries = get_section_entries("testuser", "projects", db_path)
        de_entries = get_section_entries("testuser_de", "projects", db_path)

        return db_path, en_entries[0]["id"], de_entries[0]["id"]

    def test_link_existing_entries(self, db_with_unlinked_entries):
        """Test linking existing entries from different languages."""
        db_path, en_entry_id, de_entry_id = db_with_unlinked_entries

        stable_id = link_existing_entries(
            entry_ids={"en": en_entry_id, "de": de_entry_id},
            section="projects",
            db_path=db_path
        )

        assert stable_id is not None

        # Verify linking works
        linked = get_linked_entries(en_entry_id, "projects", db_path)
        assert "en" in linked
        assert "de" in linked
        assert linked["en"]["id"] == en_entry_id
        assert linked["de"]["id"] == de_entry_id


class TestExportConsistency:
    """Tests for export consistency across languages."""

    @pytest.fixture
    def db_with_synced_entries(self, tmp_path):
        """Create a database with synced multi-language entries."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Create CVs for all languages
        for lang in ["", "_de", "_fa"]:
            cv = {
                "basics": [{"fname": "Test", "lname": "User"}],
                "projects": []
            }
            cv_path = tmp_path / "cvs" / f"testuser{lang}.json"
            cv_path.parent.mkdir(parents=True, exist_ok=True)
            cv_path.write_text(json.dumps(cv, ensure_ascii=False))
            import_cv(cv_path, db_path)

        # Create multiple synced entries
        create_entry(
            person_slug="testuser",
            section="projects",
            data={"title": "Project A", "url": "https://a.com"},
            db_path=db_path,
            sync_languages=True
        )
        create_entry(
            person_slug="testuser",
            section="projects",
            data={"title": "Project B", "url": "https://b.com"},
            db_path=db_path,
            sync_languages=True
        )

        return db_path

    def test_all_languages_have_same_entry_count(self, db_with_synced_entries):
        """Test that all languages have the same number of entries."""
        db_path = db_with_synced_entries

        en_entries = list_entries("testuser", "projects", db_path)
        de_entries = list_entries("testuser_de", "projects", db_path)
        fa_entries = list_entries("testuser_fa", "projects", db_path)

        assert len(en_entries) == len(de_entries) == len(fa_entries) == 2

    def test_entries_have_matching_stable_ids(self, db_with_synced_entries):
        """Test that corresponding entries have matching stable IDs."""
        db_path = db_with_synced_entries

        en_entries = list_entries("testuser", "projects", db_path)
        de_entries = list_entries("testuser_de", "projects", db_path)

        en_stable_ids = {e["stable_id"] for e in en_entries if e["stable_id"]}
        de_stable_ids = {e["stable_id"] for e in de_entries if e["stable_id"]}

        assert en_stable_ids == de_stable_ids
