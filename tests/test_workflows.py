"""
End-to-end workflow tests simulating real user actions.

Tests cover:
- Import workflows (first import, add variant, update existing)
- Export workflows (single file, batch, verification)
- Sync workflows (shared field editing, conflict resolution)
- Error workflows (invalid JSON, missing config, collision handling)
"""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from cv_generator.exporter_v2 import CVExporter
from cv_generator.importer_v2 import CVImporter
from cv_generator.schema_v2 import init_db_v2

# ==============================================================================
# Path to real CV data
# ==============================================================================


def get_cvs_dir() -> Path:
    """Get the CVs directory relative to the repository root."""
    test_file = Path(__file__).resolve()
    repo_root = test_file.parent.parent
    cvs_path = repo_root / "data" / "cvs"
    return cvs_path


CVS_DIR = get_cvs_dir()


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def fresh_db(tmp_path):
    """Create a fresh database for each test."""
    db_path = tmp_path / "test_workflow.db"
    init_db_v2(db_path, force=True)
    return db_path


@pytest.fixture
def importer(fresh_db):
    """Create importer instance with fresh DB."""
    return CVImporter(fresh_db)


@pytest.fixture
def exporter(fresh_db):
    """Create exporter instance with the same DB."""
    return CVExporter(fresh_db)


# ==============================================================================
# Import Workflow Tests
# ==============================================================================


class TestImportWorkflow:
    """Tests for complete import workflows."""

    def test_workflow_first_import(self, fresh_db, tmp_path):
        """First-time import of a new CV."""
        # 1. Create test JSON file
        json_path = tmp_path / "new_person.json"
        cv_data = {
            "config": {"lang": "en", "ID": "new_person"},
            "basics": [
                {
                    "fname": "New",
                    "lname": "Person",
                    "label": ["Developer"],
                    "email": "new@example.com",
                    "phone": {"countryCode": "+1", "number": "123", "formatted": "+1 123"},
                    "birthDate": "1990-01-01",
                    "summary": "A new person",
                    "location": [],
                    "Pictures": [],
                }
            ],
            "profiles": [],
            "education": [
                {
                    "institution": "Test University",
                    "location": "Test City",
                    "area": "Computer Science",
                    "studyType": "Bachelor",
                    "startDate": "2010-01-01",
                    "endDate": "2014-06-01",
                    "gpa": "3.5",
                    "logo_url": "",
                    "type_key": ["Full CV"],
                }
            ],
            "languages": [],
            "workshop_and_certifications": [],
            "skills": {},
            "experiences": [],
            "projects": [],
            "publications": [],
            "references": [],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cv_data, f, indent=2)

        # 2. Import the file
        importer = CVImporter(fresh_db)
        result = importer.import_file(json_path)

        # 3. Verify import success
        assert result.success, f"Import failed: {result.error}"
        assert result.resume_key == "new_person"
        assert result.lang_code == "en"

        # 4. Verify data in DB
        conn = sqlite3.connect(fresh_db)
        try:
            cursor = conn.cursor()

            # Check resume_set
            cursor.execute("SELECT * FROM resume_sets WHERE resume_key = ?", ("new_person",))
            row = cursor.fetchone()
            assert row is not None, "resume_set not created"

            # Check resume_version
            cursor.execute(
                "SELECT * FROM resume_versions WHERE resume_key = ? AND lang_code = ?",
                ("new_person", "en"),
            )
            row = cursor.fetchone()
            assert row is not None, "resume_version not created"

            # Check person
            cursor.execute("SELECT * FROM persons WHERE resume_key = ?", ("new_person",))
            row = cursor.fetchone()
            assert row is not None, "person not created"

            # Check education
            cursor.execute("SELECT * FROM education_items WHERE resume_key = ?", ("new_person",))
            row = cursor.fetchone()
            assert row is not None, "education not created"

        finally:
            conn.close()

        # 5. Verify export works
        exporter = CVExporter(fresh_db)
        exported = exporter.export("new_person", "en")
        assert exported["basics"][0]["fname"] == "New"

    def test_workflow_add_language_variant(self, fresh_db, tmp_path):
        """Add German variant to existing English CV."""
        # 1. Create and import English CV
        en_path = tmp_path / "person.json"
        en_data = {
            "config": {"lang": "en", "ID": "bilingual_person"},
            "basics": [
                {
                    "fname": "Test",
                    "lname": "Person",
                    "label": ["Developer"],
                    "email": "test@example.com",
                    "phone": {"countryCode": None, "number": None, "formatted": None},
                    "birthDate": None,
                    "summary": "English summary",
                    "location": [],
                    "Pictures": [],
                }
            ],
            "profiles": [],
            "education": [],
            "languages": [],
            "workshop_and_certifications": [],
            "skills": {},
            "experiences": [],
            "projects": [],
            "publications": [],
            "references": [],
        }

        with open(en_path, "w", encoding="utf-8") as f:
            json.dump(en_data, f, indent=2)

        importer = CVImporter(fresh_db)
        result = importer.import_file(en_path)
        assert result.success

        # 2. Create and import German variant
        de_path = tmp_path / "person_de.json"
        de_data = {
            "config": {"lang": "de", "ID": "bilingual_person"},
            "basics": [
                {
                    "fname": "Test",
                    "lname": "Person",
                    "label": ["Entwickler"],
                    "email": "test@example.com",
                    "phone": {"countryCode": None, "number": None, "formatted": None},
                    "birthDate": None,
                    "summary": "Deutsche Zusammenfassung",
                    "location": [],
                    "Pictures": [],
                }
            ],
            "profiles": [],
            "education": [],
            "languages": [],
            "workshop_and_certifications": [],
            "skills": {},
            "experiences": [],
            "projects": [],
            "publications": [],
            "references": [],
        }

        with open(de_path, "w", encoding="utf-8") as f:
            json.dump(de_data, f, indent=2)

        result = importer.import_file(de_path)
        assert result.success

        # 3. Verify both linked to same resume_key
        conn = sqlite3.connect(fresh_db)
        try:
            cursor = conn.cursor()

            # One resume_set
            cursor.execute("SELECT COUNT(*) FROM resume_sets")
            assert cursor.fetchone()[0] == 1

            # Two resume_versions
            cursor.execute("SELECT lang_code FROM resume_versions WHERE resume_key = ?",
                          ("bilingual_person",))
            langs = [row[0] for row in cursor.fetchall()]
            assert "en" in langs
            assert "de" in langs

            # One person
            cursor.execute("SELECT COUNT(*) FROM persons WHERE resume_key = ?",
                          ("bilingual_person",))
            assert cursor.fetchone()[0] == 1

            # Two person_i18n (one per language)
            cursor.execute("SELECT COUNT(*) FROM person_i18n")
            assert cursor.fetchone()[0] == 2

        finally:
            conn.close()

        # 4. Verify each can be exported correctly
        exporter = CVExporter(fresh_db)

        en_exported = exporter.export("bilingual_person", "en")
        assert en_exported["basics"][0]["summary"] == "English summary"

        de_exported = exporter.export("bilingual_person", "de")
        assert de_exported["basics"][0]["summary"] == "Deutsche Zusammenfassung"

    def test_workflow_update_existing(self, fresh_db, tmp_path):
        """Re-import with updated data using overwrite mode."""
        # 1. Create and import initial version
        json_path = tmp_path / "person.json"
        initial_data = {
            "config": {"lang": "en", "ID": "update_test"},
            "basics": [
                {
                    "fname": "Initial",
                    "lname": "Person",
                    "label": [],
                    "email": "old@example.com",
                    "phone": {"countryCode": None, "number": None, "formatted": None},
                    "birthDate": None,
                    "summary": "Old summary",
                    "location": [],
                    "Pictures": [],
                }
            ],
            "profiles": [],
            "education": [],
            "languages": [],
            "workshop_and_certifications": [],
            "skills": {},
            "experiences": [],
            "projects": [],
            "publications": [],
            "references": [],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, indent=2)

        importer = CVImporter(fresh_db)
        result = importer.import_file(json_path)
        assert result.success

        # 2. Modify JSON file
        updated_data = initial_data.copy()
        updated_data["basics"][0]["fname"] = "Updated"
        updated_data["basics"][0]["summary"] = "New summary"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, indent=2)

        # 3. Re-import with overwrite
        result = importer.import_file(json_path, overwrite=True)
        assert result.success

        # 4. Verify changes applied
        exporter = CVExporter(fresh_db)
        exported = exporter.export("update_test", "en")

        assert exported["basics"][0]["summary"] == "New summary"


# ==============================================================================
# Export Workflow Tests
# ==============================================================================


class TestExportWorkflow:
    """Tests for complete export workflows."""

    def test_workflow_export_single(self, fresh_db, tmp_path):
        """Export single language variant to file."""
        # 1. Create and import test data
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "export_test"},
            "basics": [
                {
                    "fname": "Export",
                    "lname": "Test",
                    "label": ["Tester"],
                    "email": "export@example.com",
                    "phone": {"countryCode": None, "number": None, "formatted": None},
                    "birthDate": None,
                    "summary": "Export test summary",
                    "location": [],
                    "Pictures": [],
                }
            ],
            "profiles": [],
            "education": [],
            "languages": [],
            "workshop_and_certifications": [],
            "skills": {},
            "experiences": [],
            "projects": [],
            "publications": [],
            "references": [],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cv_data, f, indent=2)

        importer = CVImporter(fresh_db)
        importer.import_file(json_path)

        # 2. Export to file
        exporter = CVExporter(fresh_db)
        output_path = tmp_path / "exported.json"
        result = exporter.export_to_file("export_test", "en", output_path)

        # 3. Verify export succeeded
        assert result.success
        assert output_path.exists()

        # 4. Verify file content
        with open(output_path, encoding="utf-8") as f:
            exported = json.load(f)

        assert exported["config"]["ID"] == "export_test"
        assert exported["basics"][0]["fname"] == "Export"

    def test_workflow_export_all_variants(self, fresh_db, tmp_path):
        """Export all language variants for a person."""
        # 1. Create test data with multiple languages
        for lang, summary in [("en", "English"), ("de", "Deutsch"), ("fa", "فارسی")]:
            json_path = tmp_path / f"test_{lang}.json"
            cv_data = {
                "config": {"lang": lang, "ID": "multilang_export"},
                "basics": [
                    {
                        "fname": "Multi",
                        "lname": "Lang",
                        "label": [],
                        "email": "multi@example.com",
                        "phone": {"countryCode": None, "number": None, "formatted": None},
                        "birthDate": None,
                        "summary": summary,
                        "location": [],
                        "Pictures": [],
                    }
                ],
                "profiles": [],
                "education": [],
                "languages": [],
                "workshop_and_certifications": [],
                "skills": {},
                "experiences": [],
                "projects": [],
                "publications": [],
                "references": [],
            }

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(cv_data, f, indent=2, ensure_ascii=False)

            importer = CVImporter(fresh_db)
            importer.import_file(json_path)

        # 2. Export all variants
        exporter = CVExporter(fresh_db)
        output_dir = tmp_path / "exports"
        output_dir.mkdir()

        results = exporter.export_all_variants("multilang_export", output_dir)

        # 3. Verify all exported
        assert len(results) == 3
        assert all(r.success for r in results)

        # 4. Verify files created
        exported_files = list(output_dir.glob("*.json"))
        assert len(exported_files) == 3

    def test_workflow_list_available_exports(self, fresh_db, tmp_path):
        """List all available resume variants for export."""
        # 1. Create test data
        for person, lang in [("alice", "en"), ("alice", "de"), ("bob", "en")]:
            json_path = tmp_path / f"{person}_{lang}.json"
            cv_data = {
                "config": {"lang": lang, "ID": person},
                "basics": [
                    {
                        "fname": person.title(),
                        "lname": "Test",
                        "label": [],
                        "email": f"{person}@example.com",
                        "phone": {"countryCode": None, "number": None, "formatted": None},
                        "birthDate": None,
                        "summary": None,
                        "location": [],
                        "Pictures": [],
                    }
                ],
                "profiles": [],
                "education": [],
                "languages": [],
                "workshop_and_certifications": [],
                "skills": {},
                "experiences": [],
                "projects": [],
                "publications": [],
                "references": [],
            }

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(cv_data, f, indent=2)

            importer = CVImporter(fresh_db)
            importer.import_file(json_path)

        # 2. List available
        exporter = CVExporter(fresh_db)
        available = exporter.list_available()

        # 3. Verify list
        assert len(available) == 3
        assert ("alice", "en") in available
        assert ("alice", "de") in available
        assert ("bob", "en") in available


# ==============================================================================
# Error Handling Workflow Tests
# ==============================================================================


class TestErrorWorkflow:
    """Tests for error handling workflows."""

    def test_workflow_invalid_json_upload(self, fresh_db, tmp_path):
        """Handle malformed JSON gracefully."""
        json_path = tmp_path / "invalid.json"
        json_path.write_text("{invalid json content")

        importer = CVImporter(fresh_db)
        result = importer.import_file(json_path)

        # Verify error is reported
        assert not result.success
        assert "Invalid JSON" in result.error

    def test_workflow_missing_file(self, fresh_db, tmp_path):
        """Handle missing file gracefully."""
        json_path = tmp_path / "nonexistent.json"

        importer = CVImporter(fresh_db)
        result = importer.import_file(json_path)

        assert not result.success
        assert "File not found" in result.error

    def test_workflow_unsupported_language(self, fresh_db, tmp_path):
        """Handle unsupported language code."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "zz", "ID": "test"},
            "basics": [],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cv_data, f)

        importer = CVImporter(fresh_db)
        result = importer.import_file(json_path)

        assert not result.success
        assert "Unsupported language" in result.error

    def test_workflow_export_nonexistent(self, fresh_db):
        """Handle export of non-existent resume."""
        exporter = CVExporter(fresh_db)

        with pytest.raises(ValueError, match="No resume version found"):
            exporter.export("nonexistent", "en")

    def test_workflow_export_wrong_language(self, fresh_db, tmp_path):
        """Handle export of wrong language variant."""
        # Create English only
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "english_only"},
            "basics": [
                {
                    "fname": "Test",
                    "lname": "Person",
                    "label": [],
                    "email": "test@example.com",
                    "phone": {"countryCode": None, "number": None, "formatted": None},
                    "birthDate": None,
                    "summary": None,
                    "location": [],
                    "Pictures": [],
                }
            ],
            "profiles": [],
            "education": [],
            "languages": [],
            "workshop_and_certifications": [],
            "skills": {},
            "experiences": [],
            "projects": [],
            "publications": [],
            "references": [],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cv_data, f)

        importer = CVImporter(fresh_db)
        importer.import_file(json_path)

        # Try to export German (not imported)
        exporter = CVExporter(fresh_db)
        with pytest.raises(ValueError, match="No resume version found"):
            exporter.export("english_only", "de")


# ==============================================================================
# Batch Import Workflow Tests
# ==============================================================================


class TestBatchWorkflow:
    """Tests for batch import/export operations."""

    def test_workflow_batch_import(self, fresh_db, tmp_path):
        """Import multiple files from a directory."""
        # Create test files
        for name in ["alice", "bob", "charlie"]:
            json_path = tmp_path / f"{name}.json"
            cv_data = {
                "config": {"lang": "en", "ID": name},
                "basics": [
                    {
                        "fname": name.title(),
                        "lname": "Test",
                        "label": [],
                        "email": f"{name}@example.com",
                        "phone": {"countryCode": None, "number": None, "formatted": None},
                        "birthDate": None,
                        "summary": None,
                        "location": [],
                        "Pictures": [],
                    }
                ],
                "profiles": [],
                "education": [],
                "languages": [],
                "workshop_and_certifications": [],
                "skills": {},
                "experiences": [],
                "projects": [],
                "publications": [],
                "references": [],
            }

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(cv_data, f)

        # Batch import
        importer = CVImporter(fresh_db)
        result = importer.import_directory(tmp_path)

        # Verify results
        assert result.total_files == 3
        assert result.successful == 3
        assert result.failed == 0

        # Verify all in DB
        exporter = CVExporter(fresh_db)
        available = exporter.list_available()
        assert len(available) == 3

    def test_workflow_batch_export(self, fresh_db, tmp_path):
        """Export all CVs in the database."""
        # Create test data
        for name in ["person_a", "person_b"]:
            json_path = tmp_path / f"{name}.json"
            cv_data = {
                "config": {"lang": "en", "ID": name},
                "basics": [
                    {
                        "fname": name.replace("_", " ").title(),
                        "lname": "Test",
                        "label": [],
                        "email": f"{name}@example.com",
                        "phone": {"countryCode": None, "number": None, "formatted": None},
                        "birthDate": None,
                        "summary": None,
                        "location": [],
                        "Pictures": [],
                    }
                ],
                "profiles": [],
                "education": [],
                "languages": [],
                "workshop_and_certifications": [],
                "skills": {},
                "experiences": [],
                "projects": [],
                "publications": [],
                "references": [],
            }

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(cv_data, f)

            importer = CVImporter(fresh_db)
            importer.import_file(json_path)

        # Batch export
        output_dir = tmp_path / "exports"
        output_dir.mkdir()

        exporter = CVExporter(fresh_db)
        result = exporter.export_all(output_dir)

        # Verify results
        assert result.total_files == 2
        assert result.successful == 2
        assert result.failed == 0

        # Verify files created
        exported_files = list(output_dir.glob("*.json"))
        assert len(exported_files) == 2


# ==============================================================================
# Dry Run Workflow Tests
# ==============================================================================


class TestDryRunWorkflow:
    """Tests for dry-run mode workflows."""

    def test_workflow_dry_run_import(self, fresh_db, tmp_path):
        """Dry-run import validates without committing."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "dry_run_test"},
            "basics": [
                {
                    "fname": "Test",
                    "lname": "Person",
                    "label": [],
                    "email": "test@example.com",
                    "phone": {"countryCode": None, "number": None, "formatted": None},
                    "birthDate": None,
                    "summary": None,
                    "location": [],
                    "Pictures": [],
                }
            ],
            "profiles": [],
            "education": [],
            "languages": [],
            "workshop_and_certifications": [],
            "skills": {},
            "experiences": [],
            "projects": [],
            "publications": [],
            "references": [],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cv_data, f)

        # Dry-run import
        importer = CVImporter(fresh_db)
        result = importer.import_file(json_path, dry_run=True)

        # Should succeed (validation passes)
        assert result.success

        # But nothing should be in DB
        conn = sqlite3.connect(fresh_db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM resume_sets")
            assert cursor.fetchone()[0] == 0
        finally:
            conn.close()

    def test_workflow_dry_run_with_errors(self, fresh_db, tmp_path):
        """Dry-run import catches errors without side effects."""
        json_path = tmp_path / "invalid.json"
        json_path.write_text("{invalid json")

        importer = CVImporter(fresh_db)
        result = importer.import_file(json_path, dry_run=True)

        # Should fail
        assert not result.success

        # Nothing in DB
        conn = sqlite3.connect(fresh_db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM resume_sets")
            assert cursor.fetchone()[0] == 0
        finally:
            conn.close()
