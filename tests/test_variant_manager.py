"""
Tests for cv_generator.variant_manager module.

Tests the variant lifecycle management (add, remove, link, unlink, merge).
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cv_generator.variant_manager import (
    AddVariantResult,
    DuplicateCandidate,
    LinkResult,
    MergeResult,
    OrphanedVariant,
    RemoveVariantResult,
    UnlinkResult,
    VariantManager,
)
from cv_generator.schema_v2 import init_db_v2


def _create_test_resume(db_path: Path, resume_key: str, languages: list) -> None:
    """Helper to create a test resume with specified languages."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    # Create resume_set
    cursor.execute(
        "INSERT INTO resume_sets (resume_key, base_lang_code, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (resume_key, languages[0] if languages else "en", now, now)
    )

    # Create resume_versions for each language
    for i, lang in enumerate(languages):
        cursor.execute(
            "INSERT INTO resume_versions (resume_key, lang_code, is_base, is_published, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (resume_key, lang, 1 if i == 0 else 0, 0, now, now)
        )

    # Create person
    cursor.execute(
        "INSERT INTO persons (resume_key, email, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (resume_key, f"{resume_key}@example.com", now, now)
    )
    person_id = cursor.lastrowid

    # Create person_i18n for each version
    cursor.execute("SELECT id, lang_code FROM resume_versions WHERE resume_key = ?", (resume_key,))
    versions = cursor.fetchall()
    for version_id, lang in versions:
        cursor.execute(
            "INSERT INTO person_i18n (person_id, resume_version_id, fname, lname) VALUES (?, ?, ?, ?)",
            (person_id, version_id, f"Test_{lang}", "User")
        )

    conn.commit()
    conn.close()


class TestVariantManagerInit:
    """Tests for VariantManager initialization."""

    def test_init_with_valid_db(self, tmp_path):
        """Test that VariantManager initializes with valid database."""
        db_path = tmp_path / "test.db"
        init_db_v2(db_path)

        manager = VariantManager(db_path)
        assert manager.db_path == db_path

    def test_init_with_missing_db_raises(self, tmp_path):
        """Test that VariantManager raises for missing database."""
        from cv_generator.errors import ConfigurationError

        db_path = tmp_path / "nonexistent.db"

        with pytest.raises(ConfigurationError):
            VariantManager(db_path)


class TestAddVariant:
    """Tests for add_variant method."""

    @pytest.fixture
    def db_with_resume(self, tmp_path):
        """Create a database with a resume."""
        db_path = tmp_path / "test.db"
        init_db_v2(db_path)
        _create_test_resume(db_path, "testuser", ["en"])
        return db_path

    def test_add_variant_success(self, db_with_resume):
        """Test successfully adding a new language variant."""
        manager = VariantManager(db_with_resume)

        result = manager.add_variant("testuser", "de")

        assert result.success is True
        assert result.resume_key == "testuser"
        assert result.lang_code == "de"
        assert result.version_id > 0
        assert result.records_created > 0

    def test_add_variant_with_copy_from(self, db_with_resume):
        """Test adding variant with copy from source language."""
        manager = VariantManager(db_with_resume)

        result = manager.add_variant("testuser", "de", copy_from="en")

        assert result.success is True
        assert result.copied_from == "en"

    def test_add_variant_invalid_language(self, db_with_resume):
        """Test adding variant with invalid language code."""
        manager = VariantManager(db_with_resume)

        result = manager.add_variant("testuser", "xx")

        assert result.success is False
        assert "Unsupported language" in result.error

    def test_add_variant_already_exists(self, db_with_resume):
        """Test adding variant that already exists."""
        manager = VariantManager(db_with_resume)

        result = manager.add_variant("testuser", "en")

        assert result.success is False
        assert "already exists" in result.error

    def test_add_variant_unknown_resume_key(self, db_with_resume):
        """Test adding variant for unknown resume_key."""
        manager = VariantManager(db_with_resume)

        result = manager.add_variant("unknown_user", "de")

        assert result.success is False
        assert "not found" in result.error


class TestRemoveVariant:
    """Tests for remove_variant method."""

    @pytest.fixture
    def db_with_variants(self, tmp_path):
        """Create a database with multiple language variants."""
        db_path = tmp_path / "test.db"
        init_db_v2(db_path)
        _create_test_resume(db_path, "testuser", ["en", "de"])
        return db_path

    def test_remove_variant_success(self, db_with_variants):
        """Test successfully removing a language variant."""
        manager = VariantManager(db_with_variants)

        result = manager.remove_variant("testuser", "de")

        assert result.success is True
        assert result.resume_key == "testuser"
        assert result.lang_code == "de"
        assert result.records_deleted > 0

    def test_remove_last_variant_fails_without_force(self, tmp_path):
        """Test removing last variant fails without force."""
        db_path = tmp_path / "test.db"
        init_db_v2(db_path)
        _create_test_resume(db_path, "testuser", ["en"])

        manager = VariantManager(db_path)
        result = manager.remove_variant("testuser", "en", force=False)

        assert result.success is False
        assert result.was_last_variant is True
        assert "Cannot delete last variant" in result.error

    def test_remove_last_variant_with_force(self, tmp_path):
        """Test removing last variant succeeds with force."""
        db_path = tmp_path / "test.db"
        init_db_v2(db_path)
        _create_test_resume(db_path, "testuser", ["en"])

        manager = VariantManager(db_path)
        result = manager.remove_variant("testuser", "en", force=True)

        assert result.success is True
        assert result.was_last_variant is True
        assert result.resume_set_deleted is True

    def test_remove_unknown_variant(self, db_with_variants):
        """Test removing unknown variant."""
        manager = VariantManager(db_with_variants)

        result = manager.remove_variant("testuser", "fa")

        assert result.success is False
        assert "not found" in result.error


class TestLinkOrphanVariant:
    """Tests for link_orphan_variant method."""

    @pytest.fixture
    def db_with_orphan(self, tmp_path):
        """Create a database with an orphaned variant."""
        db_path = tmp_path / "test.db"
        init_db_v2(db_path)
        # Create main person with EN
        _create_test_resume(db_path, "testuser", ["en"])
        # Create orphan with DE in separate resume_set
        _create_test_resume(db_path, "orphan_de", ["de"])
        return db_path

    def test_link_orphan_success(self, db_with_orphan):
        """Test successfully linking an orphan variant."""
        manager = VariantManager(db_with_orphan)

        # Get the orphan version ID
        conn = sqlite3.connect(db_with_orphan)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM resume_versions WHERE resume_key = ?", ("orphan_de",))
        orphan_version_id = cursor.fetchone()[0]
        conn.close()

        result = manager.link_orphan_variant(orphan_version_id, "testuser")

        assert result.success is True
        assert result.target_resume_key == "testuser"
        assert result.previous_resume_key == "orphan_de"

    def test_link_orphan_conflict(self, db_with_orphan):
        """Test linking orphan when target already has that language."""
        manager = VariantManager(db_with_orphan)

        # Get the EN version ID (target already has EN)
        conn = sqlite3.connect(db_with_orphan)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM resume_versions WHERE resume_key = ? AND lang_code = ?", ("orphan_de", "de"))
        orphan_version_id = cursor.fetchone()[0]

        # First add DE to target
        cursor.execute(
            "INSERT INTO resume_versions (resume_key, lang_code, is_base, is_published, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("testuser", "de", 0, 0, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        conn.close()

        result = manager.link_orphan_variant(orphan_version_id, "testuser")

        assert result.success is False
        assert "already has de variant" in result.error


class TestUnlinkVariant:
    """Tests for unlink_variant method."""

    @pytest.fixture
    def db_with_variants(self, tmp_path):
        """Create a database with multiple language variants."""
        db_path = tmp_path / "test.db"
        init_db_v2(db_path)
        _create_test_resume(db_path, "testuser", ["en", "de"])
        return db_path

    def test_unlink_with_new_resume_set(self, db_with_variants):
        """Test unlinking variant creates new resume_set."""
        manager = VariantManager(db_with_variants)

        result = manager.unlink_variant("testuser", "de", create_new_resume_set=True)

        assert result.success is True
        assert result.new_resume_key is not None
        assert result.variant_deleted is False

    def test_unlink_with_delete(self, db_with_variants):
        """Test unlinking variant deletes it."""
        manager = VariantManager(db_with_variants)

        result = manager.unlink_variant("testuser", "de", create_new_resume_set=False)

        assert result.success is True
        assert result.variant_deleted is True


class TestMergeResumeSets:
    """Tests for merge_resume_sets method."""

    @pytest.fixture
    def db_with_two_resumes(self, tmp_path):
        """Create a database with two resume sets."""
        db_path = tmp_path / "test.db"
        init_db_v2(db_path)
        _create_test_resume(db_path, "testuser1", ["en"])
        _create_test_resume(db_path, "testuser2", ["de"])
        return db_path

    def test_merge_success(self, db_with_two_resumes):
        """Test successfully merging two resume_sets."""
        manager = VariantManager(db_with_two_resumes)

        result = manager.merge_resume_sets("testuser2", "testuser1")

        assert result.success is True
        assert result.variants_moved == 1
        assert result.source_deleted is True

    def test_merge_with_conflict(self, tmp_path):
        """Test merging with language conflict."""
        db_path = tmp_path / "test.db"
        init_db_v2(db_path)
        _create_test_resume(db_path, "testuser1", ["en"])
        _create_test_resume(db_path, "testuser2", ["en"])  # Both have EN

        manager = VariantManager(db_path)
        result = manager.merge_resume_sets("testuser2", "testuser1")

        assert result.success is True
        assert len(result.conflicts) == 1
        assert result.variants_moved == 0

    def test_merge_same_key_fails(self, db_with_two_resumes):
        """Test merging same key fails."""
        manager = VariantManager(db_with_two_resumes)

        result = manager.merge_resume_sets("testuser1", "testuser1")

        assert result.success is False
        assert "cannot be the same" in result.error


class TestGetOrphanedVariants:
    """Tests for get_orphaned_variants method."""

    @pytest.fixture
    def db_with_orphan(self, tmp_path):
        """Create a database with an orphaned variant."""
        db_path = tmp_path / "test.db"
        init_db_v2(db_path)
        # Single variant = potential orphan
        _create_test_resume(db_path, "orphan", ["en"])
        return db_path

    def test_find_orphaned_variants(self, db_with_orphan):
        """Test finding orphaned variants."""
        manager = VariantManager(db_with_orphan)

        orphans = manager.get_orphaned_variants()

        assert len(orphans) >= 1
        assert isinstance(orphans[0], OrphanedVariant)

    def test_no_orphans_when_all_linked(self, tmp_path):
        """Test no orphans when all variants are properly linked."""
        db_path = tmp_path / "test.db"
        init_db_v2(db_path)
        _create_test_resume(db_path, "testuser", ["en", "de", "fa"])

        manager = VariantManager(db_path)
        orphans = manager.get_orphaned_variants()

        # Multi-variant resume should not be an orphan
        orphan_keys = [o.resume_key for o in orphans]
        assert "testuser" not in orphan_keys


class TestGetDuplicateCandidates:
    """Tests for get_duplicate_candidates method."""

    @pytest.fixture
    def db_with_duplicates(self, tmp_path):
        """Create a database with potential duplicates."""
        db_path = tmp_path / "test.db"
        init_db_v2(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        # Create two resume_sets with same email
        for key in ["user1", "user2"]:
            cursor.execute(
                "INSERT INTO resume_sets (resume_key, base_lang_code, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (key, "en", now, now)
            )
            cursor.execute(
                "INSERT INTO resume_versions (resume_key, lang_code, is_base, is_published, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (key, "en", 1, 0, now, now)
            )
            cursor.execute(
                "INSERT INTO persons (resume_key, email, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (key, "same@example.com", now, now)  # Same email!
            )

        conn.commit()
        conn.close()

        return db_path

    def test_find_duplicate_candidates(self, db_with_duplicates):
        """Test finding duplicate candidates."""
        manager = VariantManager(db_with_duplicates)

        duplicates = manager.get_duplicate_candidates()

        assert len(duplicates) >= 1
        assert isinstance(duplicates[0], DuplicateCandidate)
        assert duplicates[0].similarity_score > 0


class TestDataclasses:
    """Tests for result dataclass serialization."""

    def test_add_variant_result_to_dict(self):
        """Test AddVariantResult serialization."""
        result = AddVariantResult(
            success=True,
            resume_key="testuser",
            lang_code="de",
            version_id=1,
            records_created=5,
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["lang_code"] == "de"
        assert d["records_created"] == 5

    def test_orphaned_variant_to_dict(self):
        """Test OrphanedVariant serialization."""
        orphan = OrphanedVariant(
            version_id=1,
            lang_code="de",
            resume_key="orphan",
            person_name="Test User",
            possible_matches=["testuser"],
        )

        d = orphan.to_dict()

        assert d["version_id"] == 1
        assert d["lang_code"] == "de"
        assert "testuser" in d["possible_matches"]
