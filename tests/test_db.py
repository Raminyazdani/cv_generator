"""
Tests for cv_generator.db module.

Tests the SQLite database operations:
- Database initialization
- CV import/export
- Round-trip data integrity
- Diff functionality
"""

import json
import tempfile
from pathlib import Path

import pytest

from cv_generator.db import (
    SCHEMA_VERSION,
    diff_all_cvs,
    diff_cv,
    export_all_cvs,
    export_cv,
    get_db_path,
    import_all_cvs,
    import_cv,
    init_db,
    list_persons,
    list_tags,
)
from cv_generator.errors import ConfigurationError


class TestInitDb:
    """Tests for database initialization."""

    def test_init_creates_database(self, tmp_path):
        """Test that init_db creates a database file."""
        db_path = tmp_path / "test.db"
        result = init_db(db_path)

        assert result == db_path
        assert db_path.exists()

    def test_init_creates_parent_directories(self, tmp_path):
        """Test that init_db creates parent directories."""
        db_path = tmp_path / "deep" / "nested" / "test.db"
        result = init_db(db_path)

        assert result == db_path
        assert db_path.exists()

    def test_init_with_force_recreates(self, tmp_path):
        """Test that init with force flag recreates database."""
        db_path = tmp_path / "test.db"

        # Create initial database
        init_db(db_path)

        # Get initial modification time
        initial_mtime = db_path.stat().st_mtime

        # Wait a tiny bit and recreate
        import time
        time.sleep(0.1)

        init_db(db_path, force=True)

        # Check it was recreated
        assert db_path.stat().st_mtime > initial_mtime

    def test_init_without_force_skips_existing(self, tmp_path):
        """Test that init without force skips existing database."""
        db_path = tmp_path / "test.db"

        # Create initial database
        init_db(db_path)
        initial_mtime = db_path.stat().st_mtime

        # Wait and try to init again
        import time
        time.sleep(0.1)

        init_db(db_path, force=False)

        # Check it wasn't recreated
        assert db_path.stat().st_mtime == initial_mtime


class TestImportExport:
    """Tests for CV import and export."""

    @pytest.fixture
    def minimal_cv(self, tmp_path):
        """Create a minimal CV JSON file."""
        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "education": [
                {
                    "institution": "Test University",
                    "area": "Testing",
                    "type_key": ["Full CV", "Academic"]
                }
            ],
            "projects": [],
            "skills": {
                "Category": {
                    "Skill A": [{"long_name": "Skill A", "short_name": "A"}]
                }
            }
        }
        cv_path = tmp_path / "cvs" / "test.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))
        return cv_path, cv_data

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test database."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        return db_path

    def test_import_cv(self, minimal_cv, db):
        """Test importing a single CV."""
        cv_path, cv_data = minimal_cv

        stats = import_cv(cv_path, db)

        assert stats["person"] == "test"
        assert stats["entries_imported"] > 0
        assert "basics" in stats["sections"]
        assert "education" in stats["sections"]

    def test_export_cv(self, minimal_cv, db):
        """Test exporting a CV."""
        cv_path, cv_data = minimal_cv

        import_cv(cv_path, db)
        exported = export_cv("test", db)

        assert "basics" in exported
        assert "education" in exported
        assert "skills" in exported

    def test_round_trip_preserves_data(self, minimal_cv, db):
        """Test that import/export round-trip preserves data."""
        cv_path, original_data = minimal_cv

        import_cv(cv_path, db)
        exported_data = export_cv("test", db)

        # Normalize for comparison (sort keys)
        def normalize(obj):
            if isinstance(obj, dict):
                return {k: normalize(v) for k, v in sorted(obj.items())}
            elif isinstance(obj, list):
                return [normalize(x) for x in obj]
            return obj

        assert normalize(original_data) == normalize(exported_data)

    def test_import_preserves_type_key_order(self, tmp_path, db):
        """Test that type_key order is preserved through round-trip."""
        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {
                    "title": "Project A",
                    "type_key": ["Full CV", "Biotechnology", "Academic", "Bioinformatics"]
                }
            ]
        }
        cv_path = tmp_path / "cvs" / "typekey_test.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))

        import_cv(cv_path, db)
        exported = export_cv("typekey_test", db)

        # Check that type_key order is preserved
        original_type_key = cv_data["projects"][0]["type_key"]
        exported_type_key = exported["projects"][0]["type_key"]

        assert original_type_key == exported_type_key

    def test_import_empty_lists(self, tmp_path, db):
        """Test that empty lists are preserved."""
        cv_data = {
            "basics": [{"fname": "Empty", "lname": "Test"}],
            "projects": [],
            "publications": []
        }
        cv_path = tmp_path / "cvs" / "empty.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))

        import_cv(cv_path, db)
        exported = export_cv("empty", db)

        assert exported["projects"] == []
        assert exported["publications"] == []

    def test_import_with_overwrite(self, minimal_cv, db):
        """Test that overwrite replaces existing entries."""
        cv_path, cv_data = minimal_cv

        # Import twice without overwrite
        import_cv(cv_path, db)
        import_cv(cv_path, db)

        persons = list_persons(db)
        # Without overwrite, entries accumulate
        person = [p for p in persons if p["slug"] == "test"][0]
        entries_without_overwrite = person["entry_count"]

        # Reset and import with overwrite
        init_db(db, force=True)
        import_cv(cv_path, db)
        import_cv(cv_path, db, overwrite=True)

        persons = list_persons(db)
        person = [p for p in persons if p["slug"] == "test"][0]
        entries_with_overwrite = person["entry_count"]

        assert entries_with_overwrite < entries_without_overwrite


class TestDiff:
    """Tests for diff functionality."""

    @pytest.fixture
    def matching_setup(self, tmp_path):
        """Create a CV and import it for matching comparison."""
        cv_data = {
            "basics": [{"fname": "Match", "lname": "Test"}],
            "education": [{"institution": "University", "area": "CS"}]
        }
        cv_path = tmp_path / "cvs" / "match.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))

        db_path = tmp_path / "test.db"
        init_db(db_path)
        import_cv(cv_path, db_path)

        return cv_path, db_path

    def test_diff_matching_cv(self, matching_setup):
        """Test that diff reports no differences for matching CV."""
        cv_path, db_path = matching_setup

        result = diff_cv(cv_path, db_path)

        assert result["match"] is True
        assert result["difference_count"] == 0

    def test_diff_modified_cv(self, matching_setup):
        """Test that diff reports differences for modified CV."""
        cv_path, db_path = matching_setup

        # Modify the CV file
        cv_data = json.loads(cv_path.read_text())
        cv_data["education"][0]["area"] = "Modified"
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))

        result = diff_cv(cv_path, db_path)

        assert result["match"] is False
        assert result["difference_count"] > 0


class TestListFunctions:
    """Tests for list functions."""

    @pytest.fixture
    def populated_db(self, tmp_path):
        """Create a populated database."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Project A", "type_key": ["Tag1", "Tag2"]},
                {"title": "Project B", "type_key": ["Tag2", "Tag3"]}
            ]
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))

        import_cv(cv_path, db_path)
        return db_path

    def test_list_persons(self, populated_db):
        """Test listing persons in database."""
        persons = list_persons(populated_db)

        assert len(persons) == 1
        assert persons[0]["slug"] == "testuser"
        assert persons[0]["display_name"] == "Test User"

    def test_list_tags(self, populated_db):
        """Test listing tags in database."""
        tags = list_tags(populated_db)

        tag_names = [t["name"] for t in tags]
        assert "Tag1" in tag_names
        assert "Tag2" in tag_names
        assert "Tag3" in tag_names


class TestErrorHandling:
    """Tests for error handling."""

    def test_import_without_init_raises_error(self, tmp_path):
        """Test that importing without init raises an error."""
        cv_path = tmp_path / "test.json"
        cv_path.write_text('{"basics": [{"fname": "Test"}]}')

        with pytest.raises(ConfigurationError):
            import_cv(cv_path, tmp_path / "nonexistent.db")

    def test_export_nonexistent_person_raises_error(self, tmp_path):
        """Test that exporting nonexistent person raises an error."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        with pytest.raises(ConfigurationError):
            export_cv("nonexistent", db_path)


class TestDoctor:
    """Tests for database doctor/health check."""

    @pytest.fixture
    def healthy_db(self, tmp_path):
        """Create a healthy database with some data."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Project A", "type_key": ["Tag1", "Tag2"]}
            ]
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))

        import_cv(cv_path, db_path)
        return db_path

    def test_doctor_healthy_db(self, healthy_db):
        """Test that doctor reports healthy database."""
        from cv_generator.db import doctor

        results = doctor(healthy_db)

        assert results["healthy"] is True
        assert results["stats"]["persons"] == 1
        assert results["stats"]["entries"] > 0
        assert results["checks"]["schema_version"]["ok"] is True

    def test_doctor_reports_stats(self, healthy_db):
        """Test that doctor reports database statistics."""
        from cv_generator.db import doctor

        results = doctor(healthy_db)

        assert "stats" in results
        assert "persons" in results["stats"]
        assert "entries" in results["stats"]
        assert "tags" in results["stats"]
        assert "tag_assignments" in results["stats"]

    def test_doctor_checks_orphaned_tags(self, healthy_db):
        """Test that doctor checks for orphaned tags."""
        from cv_generator.db import create_tag, doctor

        # Create an orphaned tag (not used by any entry)
        create_tag("OrphanTag", None, healthy_db)

        results = doctor(healthy_db)

        assert "orphaned_tags" in results["checks"]
        assert results["checks"]["orphaned_tags"]["count"] > 0
        assert "OrphanTag" in results["checks"]["orphaned_tags"]["names"]


class TestExportWithFlags:
    """Tests for export with apply-tags flags."""

    @pytest.fixture
    def db_with_tags(self, tmp_path):
        """Create a database with tagged entries."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Project A", "type_key": ["Tag1", "Tag2"]},
                {"title": "Project B"}  # No type_key
            ]
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))

        import_cv(cv_path, db_path)
        return db_path, tmp_path

    def test_export_without_apply_tags(self, db_with_tags):
        """Test export preserves original type_key structure."""
        db_path, tmp_path = db_with_tags

        exported = export_cv("testuser", db_path)

        # Project A should have type_key
        assert "type_key" in exported["projects"][0]
        # Project B should not have type_key (it didn't originally)
        assert "type_key" not in exported["projects"][1]

    def test_export_refuses_overwrite_without_force(self, db_with_tags):
        """Test that export refuses to overwrite without --force."""
        from cv_generator.db import export_cv_to_file

        db_path, tmp_path = db_with_tags
        output_path = tmp_path / "output" / "testuser.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # First export should succeed
        export_cv_to_file("testuser", output_path, db_path, force=True)

        # Second export should fail without force
        with pytest.raises(ConfigurationError) as exc_info:
            export_cv_to_file("testuser", output_path, db_path, force=False)

        assert "already exists" in str(exc_info.value)

    def test_export_with_force_overwrites(self, db_with_tags):
        """Test that export with --force overwrites existing files."""
        from cv_generator.db import export_cv_to_file

        db_path, tmp_path = db_with_tags
        output_path = tmp_path / "output" / "testuser.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # First export
        export_cv_to_file("testuser", output_path, db_path, force=True)
        first_mtime = output_path.stat().st_mtime

        import time
        time.sleep(0.1)

        # Second export with force
        export_cv_to_file("testuser", output_path, db_path, force=True)
        second_mtime = output_path.stat().st_mtime

        assert second_mtime > first_mtime
