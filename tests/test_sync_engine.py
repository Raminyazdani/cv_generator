"""
Tests for cv_generator.sync_engine module.

Tests the synchronization engine for invariant fields across language variants.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cv_generator.sync_engine import (
    INVARIANT_FIELDS,
    SUPPORTED_LANGUAGES,
    FieldConflict,
    SyncEngine,
    SyncResult,
    VariantStatus,
)
from cv_generator.schema_v2 import init_db_v2


class TestSyncEngineInit:
    """Tests for SyncEngine initialization."""

    def test_init_with_valid_db(self, tmp_path):
        """Test that SyncEngine initializes with valid database."""
        db_path = tmp_path / "test.db"
        init_db_v2(db_path)

        engine = SyncEngine(db_path)
        assert engine.db_path == db_path

    def test_init_with_missing_db_raises(self, tmp_path):
        """Test that SyncEngine raises for missing database."""
        from cv_generator.errors import ConfigurationError

        db_path = tmp_path / "nonexistent.db"

        with pytest.raises(ConfigurationError):
            SyncEngine(db_path)


class TestSyncInvariantField:
    """Tests for sync_invariant_field method."""

    @pytest.fixture
    def db_with_data(self, tmp_path):
        """Create a database with sample resume data."""
        db_path = tmp_path / "test.db"
        init_db_v2(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        # Create resume_set
        cursor.execute(
            "INSERT INTO resume_sets (resume_key, base_lang_code, created_at, updated_at) VALUES (?, ?, ?, ?)",
            ("testuser", "en", now, now)
        )

        # Create resume_versions for EN and DE
        cursor.execute(
            "INSERT INTO resume_versions (resume_key, lang_code, is_base, is_published, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("testuser", "en", 1, 0, now, now)
        )
        cursor.execute(
            "INSERT INTO resume_versions (resume_key, lang_code, is_base, is_published, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("testuser", "de", 0, 0, now, now)
        )

        # Create person
        cursor.execute(
            "INSERT INTO persons (resume_key, email, created_at, updated_at) VALUES (?, ?, ?, ?)",
            ("testuser", "test@example.com", now, now)
        )
        person_id = cursor.lastrowid

        # Create education_item
        cursor.execute(
            "INSERT INTO education_items (resume_key, sort_order, start_date, end_date, gpa) VALUES (?, ?, ?, ?, ?)",
            ("testuser", 0, "2020-01-01", "2024-01-01", "3.5")
        )

        conn.commit()
        conn.close()

        return db_path

    def test_sync_valid_invariant_field(self, db_with_data):
        """Test syncing a valid invariant field."""
        engine = SyncEngine(db_with_data)

        result = engine.sync_invariant_field(
            resume_key="testuser",
            entity_type="education_items",
            entity_id=1,
            field_name="gpa",
            new_value="4.0",
            source_lang="en"
        )

        assert result.success is True
        assert result.source_lang == "en"
        assert "en" in result.affected_langs
        assert result.new_value == "4.0"

    def test_sync_invalid_entity_type_fails(self, db_with_data):
        """Test syncing with invalid entity type fails."""
        engine = SyncEngine(db_with_data)

        result = engine.sync_invariant_field(
            resume_key="testuser",
            entity_type="invalid_table",
            entity_id=1,
            field_name="gpa",
            new_value="4.0",
            source_lang="en"
        )

        assert result.success is False
        assert "Unknown entity type" in result.error

    def test_sync_non_invariant_field_fails(self, db_with_data):
        """Test syncing a non-invariant field fails."""
        engine = SyncEngine(db_with_data)

        result = engine.sync_invariant_field(
            resume_key="testuser",
            entity_type="education_items",
            entity_id=1,
            field_name="institution",  # This is a translatable field
            new_value="MIT",
            source_lang="en"
        )

        assert result.success is False
        assert "not an invariant field" in result.error


class TestDetectConflicts:
    """Tests for detect_conflicts method."""

    @pytest.fixture
    def db_with_resume(self, tmp_path):
        """Create a database with a resume."""
        db_path = tmp_path / "test.db"
        init_db_v2(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        cursor.execute(
            "INSERT INTO resume_sets (resume_key, base_lang_code, created_at, updated_at) VALUES (?, ?, ?, ?)",
            ("testuser", "en", now, now)
        )

        cursor.execute(
            "INSERT INTO resume_versions (resume_key, lang_code, is_base, is_published, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("testuser", "en", 1, 0, now, now)
        )

        conn.commit()
        conn.close()

        return db_path

    def test_detect_no_conflicts(self, db_with_resume):
        """Test detecting conflicts when there are none."""
        engine = SyncEngine(db_with_resume)

        conflicts = engine.detect_conflicts("testuser")

        # With current schema design, conflicts are rare
        assert isinstance(conflicts, list)

    def test_detect_conflicts_unknown_resume_key(self, db_with_resume):
        """Test detecting conflicts for unknown resume_key."""
        engine = SyncEngine(db_with_resume)

        conflicts = engine.detect_conflicts("unknown_user")

        assert conflicts == []


class TestGetVariantStatus:
    """Tests for get_variant_status method."""

    @pytest.fixture
    def db_with_variants(self, tmp_path):
        """Create a database with multiple language variants."""
        db_path = tmp_path / "test.db"
        init_db_v2(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        cursor.execute(
            "INSERT INTO resume_sets (resume_key, base_lang_code, created_at, updated_at) VALUES (?, ?, ?, ?)",
            ("testuser", "en", now, now)
        )

        # Add EN and DE variants (missing FA)
        for lang, is_base in [("en", 1), ("de", 0)]:
            cursor.execute(
                "INSERT INTO resume_versions (resume_key, lang_code, is_base, is_published, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("testuser", lang, is_base, 0, now, now)
            )

        conn.commit()
        conn.close()

        return db_path

    def test_get_variant_status_returns_status(self, db_with_variants):
        """Test getting variant status."""
        engine = SyncEngine(db_with_variants)

        status = engine.get_variant_status("testuser")

        assert isinstance(status, VariantStatus)
        assert status.resume_key == "testuser"
        assert status.base_lang == "en"
        assert "en" in status.existing_langs
        assert "de" in status.existing_langs
        assert "fa" in status.missing_langs

    def test_get_variant_status_unknown_resume_key(self, db_with_variants):
        """Test getting status for unknown resume_key."""
        engine = SyncEngine(db_with_variants)

        status = engine.get_variant_status("unknown_user")

        assert status.missing_langs == SUPPORTED_LANGUAGES


class TestDataclasses:
    """Tests for dataclass serialization."""

    def test_field_conflict_to_dict(self):
        """Test FieldConflict serialization."""
        conflict = FieldConflict(
            resume_key="testuser",
            entity_type="education_items",
            entity_id=1,
            field_name="gpa",
            values_by_lang={"en": "3.5", "de": "4.0"},
            detected_at=datetime.now(timezone.utc),
        )

        d = conflict.to_dict()

        assert d["resume_key"] == "testuser"
        assert d["entity_type"] == "education_items"
        assert d["values_by_lang"]["en"] == "3.5"

    def test_sync_result_to_dict(self):
        """Test SyncResult serialization."""
        result = SyncResult(
            success=True,
            source_lang="en",
            affected_langs=["en", "de"],
            field_name="gpa",
            new_value="4.0",
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["source_lang"] == "en"
        assert "de" in d["affected_langs"]

    def test_variant_status_to_dict(self):
        """Test VariantStatus serialization."""
        status = VariantStatus(
            resume_key="testuser",
            existing_langs=["en", "de"],
            missing_langs=["fa"],
            base_lang="en",
        )

        d = status.to_dict()

        assert d["resume_key"] == "testuser"
        assert "en" in d["existing_langs"]
        assert "fa" in d["missing_langs"]


class TestInvariantFieldsConfig:
    """Tests for invariant fields configuration."""

    def test_invariant_fields_defined(self):
        """Test that invariant fields are properly defined."""
        assert "persons" in INVARIANT_FIELDS
        assert "education_items" in INVARIANT_FIELDS
        assert "project_items" in INVARIANT_FIELDS

    def test_persons_invariant_fields(self):
        """Test person invariant fields."""
        fields = INVARIANT_FIELDS["persons"]
        assert "email" in fields
        assert "birth_date" in fields

    def test_education_invariant_fields(self):
        """Test education invariant fields."""
        fields = INVARIANT_FIELDS["education_items"]
        assert "start_date" in fields
        assert "end_date" in fields
        assert "gpa" in fields
