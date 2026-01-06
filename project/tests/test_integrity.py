"""
Tests for cv_generator.integrity module.

Tests the reference integrity check functionality:
- ID format validation
- Stable entry ID checks
- Entry-language link checks
- Person entity ID checks
- Tag reference checks
"""

import json
import sqlite3
from pathlib import Path

import pytest

from cv_generator.crud import create_entry, ensure_crud_schema
from cv_generator.db import create_tag, import_cv, init_db
from cv_generator.integrity import (
    IntegrityIssue,
    IntegrityReport,
    IssueSeverity,
    is_valid_uuid4,
    run_integrity_check,
    validate_id_format,
)
from cv_generator.person import ensure_person_entity_schema


class TestIdFormatValidation:
    """Tests for ID format validation functions."""

    def test_valid_uuid4(self):
        """Test that valid UUID4 strings are accepted."""
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        ]
        for uuid_str in valid_uuids:
            assert is_valid_uuid4(uuid_str) is True

    def test_invalid_uuid4_wrong_format(self):
        """Test that invalid UUID4 formats are rejected."""
        invalid_uuids = [
            "not-a-uuid",
            "12345",
            "550e8400-e29b-41d4-a716",  # Too short
            "550e8400-e29b-41d4-a716-446655440000-extra",  # Too long
            "550e8400e29b41d4a716446655440000",  # No dashes
            "",
            "  ",
        ]
        for uuid_str in invalid_uuids:
            assert is_valid_uuid4(uuid_str) is False

    def test_validate_id_format_uuid(self):
        """Test validate_id_format with UUID."""
        result = validate_id_format("550e8400-e29b-41d4-a716-446655440000")
        assert result["valid"] is True
        assert result["format"] == "uuid4"

    def test_validate_id_format_integer(self):
        """Test validate_id_format with integer."""
        result = validate_id_format("12345")
        assert result["valid"] is True
        assert result["format"] == "integer"

    def test_validate_id_format_empty(self):
        """Test validate_id_format with empty string."""
        result = validate_id_format("")
        assert result["valid"] is False

    def test_validate_id_format_unknown(self):
        """Test validate_id_format with unknown format."""
        result = validate_id_format("not-valid-id")
        assert result["valid"] is False
        assert result["format"] == "unknown"


class TestIntegrityReport:
    """Tests for IntegrityReport class."""

    def test_empty_report_is_healthy(self):
        """Test that empty report is healthy."""
        report = IntegrityReport()
        assert report.is_healthy is True
        assert report.error_count == 0
        assert report.warning_count == 0

    def test_report_with_error_is_unhealthy(self):
        """Test that report with error is unhealthy."""
        report = IntegrityReport()
        report.add_issue(IntegrityIssue(
            category="test",
            severity=IssueSeverity.ERROR,
            message="Test error"
        ))
        assert report.is_healthy is False
        assert report.error_count == 1

    def test_report_with_warning_is_healthy(self):
        """Test that report with only warnings is healthy."""
        report = IntegrityReport()
        report.add_issue(IntegrityIssue(
            category="test",
            severity=IssueSeverity.WARNING,
            message="Test warning"
        ))
        assert report.is_healthy is True
        assert report.warning_count == 1

    def test_report_to_dict(self):
        """Test report serialization."""
        report = IntegrityReport()
        report.stats["test"] = 42
        report.add_issue(IntegrityIssue(
            category="test",
            severity=IssueSeverity.INFO,
            message="Test info"
        ))

        d = report.to_dict()
        assert d["healthy"] is True
        assert d["summary"]["errors"] == 0
        assert d["summary"]["info"] == 1
        assert d["stats"]["test"] == 42
        assert len(d["issues"]) == 1

    def test_report_format_text(self):
        """Test report text formatting."""
        report = IntegrityReport()
        report.add_issue(IntegrityIssue(
            category="test",
            severity=IssueSeverity.WARNING,
            message="Test warning"
        ))

        text = report.format_text()
        assert "Reference Integrity Check" in text
        assert "Warnings: 1" in text
        assert "Test warning" in text


class TestIntegrityCheckWithDb:
    """Tests for integrity check against a database."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test database."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        return db_path

    @pytest.fixture
    def db_with_crud_schema(self, tmp_path):
        """Create a database with CRUD schema."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        ensure_crud_schema(db_path)
        return db_path

    @pytest.fixture
    def db_with_person_schema(self, tmp_path):
        """Create a database with person entity schema."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        ensure_person_entity_schema(db_path)
        return db_path

    def test_integrity_check_on_empty_db(self, db):
        """Test integrity check on empty database."""
        report = run_integrity_check(db)

        assert report.is_healthy is True
        assert "database" in report.stats

    def test_integrity_check_without_crud_schema(self, db):
        """Test that missing CRUD schema is reported as info."""
        report = run_integrity_check(db)

        # Should have info about missing stable_entry table
        info_issues = [i for i in report.issues if i.severity == IssueSeverity.INFO]
        assert any("stable_entry" in i.message.lower() for i in info_issues)

    def test_integrity_check_with_crud_schema(self, db_with_crud_schema):
        """Test integrity check with CRUD schema."""
        report = run_integrity_check(db_with_crud_schema)

        assert report.is_healthy is True
        assert report.stats.get("stable_entry_table_exists") is True

    def test_integrity_check_with_person_schema(self, db_with_person_schema):
        """Test integrity check with person entity schema."""
        report = run_integrity_check(db_with_person_schema)

        assert report.is_healthy is True
        assert report.stats.get("person_entity_table_exists") is True


class TestStableIdIntegrity:
    """Tests for stable ID integrity checks."""

    @pytest.fixture
    def populated_db(self, tmp_path):
        """Create a database with CV data and CRUD entries."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        ensure_crud_schema(db_path)

        # Create CV data
        cv_en = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": []
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_en))
        import_cv(cv_path, db_path)

        # Create an entry with stable ID
        create_entry(
            person_slug="testuser",
            section="projects",
            data={"title": "Test Project"},
            db_path=db_path,
            sync_languages=False
        )

        return db_path

    def test_valid_stable_ids_pass(self, populated_db):
        """Test that valid stable IDs pass integrity check."""
        report = run_integrity_check(populated_db)

        # Should not have stable_id errors
        stable_id_errors = [
            i for i in report.issues
            if i.category == "stable_id" and i.severity == IssueSeverity.ERROR
        ]
        assert len(stable_id_errors) == 0

    def test_detects_dangling_stable_entry(self, populated_db):
        """Test that dangling stable entries are detected."""
        # Manually create a dangling stable entry
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO stable_entry (id, section, base_person, created_at, updated_at)
               VALUES ('12345678-1234-1234-1234-123456789012', 'projects', 'testuser', '2024-01-01', '2024-01-01')"""
        )
        conn.commit()
        conn.close()

        report = run_integrity_check(populated_db)

        # Should have a warning about stable entry with no linked entries
        dangling_issues = [
            i for i in report.issues
            if i.category == "stable_id" and "no linked entries" in i.message.lower()
        ]
        assert len(dangling_issues) == 1
        assert dangling_issues[0].severity == IssueSeverity.WARNING


class TestEntryRoundTrip:
    """Tests for entry creation and ID persistence."""

    @pytest.fixture
    def db_with_cvs(self, tmp_path):
        """Create a database with CV variants."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        ensure_crud_schema(db_path)

        # Create EN CV
        cv_en = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": []
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_en))
        import_cv(cv_path, db_path)

        return db_path

    def test_create_assigns_stable_id(self, db_with_cvs):
        """Test that creating an entry assigns a stable ID."""
        result = create_entry(
            person_slug="testuser",
            section="projects",
            data={"title": "New Project"},
            db_path=db_with_cvs,
            sync_languages=False
        )

        assert result["stable_id"] is not None
        assert is_valid_uuid4(result["stable_id"])

    def test_stable_id_persists_after_reload(self, db_with_cvs):
        """Test that stable ID persists after database reload."""
        # Create entry
        result = create_entry(
            person_slug="testuser",
            section="projects",
            data={"title": "Persistent Project"},
            db_path=db_with_cvs,
            sync_languages=False
        )
        original_stable_id = result["stable_id"]
        entry_id = result["entries"]["en"]

        # Get entry from database directly
        from cv_generator.db import get_entry
        entry = get_entry(entry_id, db_with_cvs)

        assert entry is not None
        assert entry["stable_id"] == original_stable_id

    def test_edit_does_not_change_stable_id(self, db_with_cvs):
        """Test that editing an entry does not change its stable ID."""
        from cv_generator.crud import get_entry as crud_get_entry, update_entry

        # Create entry
        result = create_entry(
            person_slug="testuser",
            section="projects",
            data={"title": "Original Title"},
            db_path=db_with_cvs,
            sync_languages=False
        )
        original_stable_id = result["stable_id"]
        entry_id = result["entries"]["en"]

        # Update entry
        update_entry(
            entry_id=entry_id,
            data={"title": "Updated Title"},
            section="projects",
            db_path=db_with_cvs
        )

        # Get entry again
        from cv_generator.db import get_entry
        entry = get_entry(entry_id, db_with_cvs)

        # Stable ID should be unchanged
        assert entry["stable_id"] == original_stable_id


class TestTagReferenceIntegrity:
    """Tests for tag reference integrity checks."""

    @pytest.fixture
    def db_with_tags(self, tmp_path):
        """Create a database with tags and entries with orphan references."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Create only some tags
        create_tag("ValidTag1", None, db_path)
        create_tag("ValidTag2", None, db_path)

        # Create CV with valid type_key references first
        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Project A", "type_key": ["ValidTag1", "ValidTag2"]},
            ]
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data))
        import_cv(cv_path, db_path)

        # Now manually inject a type_key reference to a non-existent tag
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, data_json FROM entry WHERE data_json LIKE '%type_key%'")
        row = cursor.fetchone()
        if row:
            entry_id, data_json = row
            data = json.loads(data_json)
            # Add a reference to a tag that doesn't exist in the catalog
            data["type_key"].append("NonExistentTag")
            cursor.execute(
                "UPDATE entry SET data_json = ? WHERE id = ?",
                (json.dumps(data), entry_id)
            )
        conn.commit()
        conn.close()

        return db_path

    def test_detects_missing_tag_references(self, db_with_tags):
        """Test that missing tag references in type_key are detected."""
        report = run_integrity_check(db_with_tags)

        # Should have a warning about NonExistentTag
        tag_issues = [
            i for i in report.issues
            if i.category == "tag_reference" and "NonExistentTag" in i.message
        ]
        assert len(tag_issues) == 1
        assert tag_issues[0].severity == IssueSeverity.WARNING


class TestIntegrityScanDetection:
    """Tests that integrity scan detects injected issues."""

    @pytest.fixture
    def clean_db(self, tmp_path):
        """Create a clean database with valid data."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        ensure_crud_schema(db_path)
        ensure_person_entity_schema(db_path)

        # Create valid CV data
        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": []
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data))
        import_cv(cv_path, db_path)

        # Create valid entry with stable ID
        create_entry(
            person_slug="testuser",
            section="projects",
            data={"title": "Valid Project"},
            db_path=db_path,
            sync_languages=False
        )

        return db_path

    def test_clean_db_passes_integrity(self, clean_db):
        """Test that clean database passes integrity check."""
        report = run_integrity_check(clean_db)

        # Should have no errors
        assert report.error_count == 0

    def test_detects_injected_orphan_stable_link(self, clean_db):
        """Test detection of injected orphan stable link."""
        # Inject an orphan entry_lang_link (references non-existent entry)
        conn = sqlite3.connect(clean_db)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO entry_lang_link (stable_id, entry_id, language, needs_translation, created_at)
               VALUES ('12345678-1234-1234-1234-123456789012', 99999, 'en', 0, '2024-01-01')"""
        )
        conn.commit()
        conn.close()

        report = run_integrity_check(clean_db)

        # Should detect the orphan link
        orphan_issues = [
            i for i in report.issues
            if i.category == "entry_link" and "deleted entry" in i.message.lower()
        ]
        assert len(orphan_issues) >= 1
        assert report.error_count >= 1

    def test_detects_injected_invalid_person_entity_id(self, clean_db):
        """Test detection of injected invalid person entity ID."""
        # Inject a person_entity with invalid ID format
        conn = sqlite3.connect(clean_db)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO person_entity (id, name_key, first_name, last_name, display_name, created_at, updated_at)
               VALUES ('not-a-valid-uuid', 'test|user', 'Test', 'User', 'Test User', '2024-01-01', '2024-01-01')"""
        )
        conn.commit()
        conn.close()

        report = run_integrity_check(clean_db)

        # Should detect the invalid ID format
        invalid_id_issues = [
            i for i in report.issues
            if i.category == "person_entity" and "invalid" in i.message.lower()
        ]
        assert len(invalid_id_issues) >= 1
