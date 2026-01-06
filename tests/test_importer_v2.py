"""
Tests for cv_generator importer_v2 (Lossless JSON to DB import engine).

Tests the complete import engine:
- Config parsing with and without config block
- All section importers (basics, profiles, education, etc.)
- Tag normalization and i18n
- Idempotent imports
- Dry-run mode
- Batch imports
"""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from cv_generator.importer_v2 import (
    BatchImportResult,
    CVImporter,
    ImportResult,
    _parse_date,
    _slugify,
)
from cv_generator.schema_v2 import init_db_v2


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_slugify_basic(self):
        """Test basic slugification."""
        assert _slugify("Full CV") == "full_cv"
        assert _slugify("Biotechnology") == "biotechnology"
        assert _slugify("Programming & Scripting") == "programming_scripting"

    def test_slugify_special_chars(self):
        """Test slugification with special characters."""
        assert _slugify("C++") == "c"
        assert _slugify("Node.js") == "nodejs"
        assert _slugify("  Spaces  ") == "spaces"

    def test_parse_date_valid(self):
        """Test date parsing with valid dates."""
        assert _parse_date("2024-10-20") == "2024-10-20"
        assert _parse_date("2024-10") == "2024-10-01"
        assert _parse_date("2024") == "2024-01-01"

    def test_parse_date_present(self):
        """Test date parsing with 'present' values."""
        assert _parse_date("present") is None
        assert _parse_date("Present") is None
        assert _parse_date("Recent") is None

    def test_parse_date_invalid(self):
        """Test date parsing with invalid dates."""
        # Should try to fix invalid day
        result = _parse_date("2020-9-31")
        assert result == "2020-09-28"

    def test_parse_date_none(self):
        """Test date parsing with None."""
        assert _parse_date(None) is None


class TestImportResultDataclasses:
    """Tests for ImportResult and BatchImportResult dataclasses."""

    def test_import_result_to_dict(self, tmp_path):
        """Test ImportResult serialization."""
        result = ImportResult(
            success=True,
            resume_key="test_person",
            lang_code="en",
            file_path=tmp_path / "test.json",
            stats={"basics": 1, "education": 5},
            warnings=["Warning 1"],
            duration_ms=100.5,
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["resume_key"] == "test_person"
        assert d["lang_code"] == "en"
        assert "test.json" in d["file_path"]
        assert d["stats"]["basics"] == 1

    def test_batch_import_result_to_dict(self, tmp_path):
        """Test BatchImportResult serialization."""
        result = BatchImportResult(
            total_files=3,
            successful=2,
            failed=1,
            results=[],
            duration_ms=500.0,
        )

        d = result.to_dict()

        assert d["total_files"] == 3
        assert d["successful"] == 2
        assert d["failed"] == 1


class TestConfigParsing:
    """Tests for config block parsing."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test v2 database."""
        db_path = tmp_path / "test_v2.db"
        init_db_v2(db_path)
        return db_path

    def test_parse_config_normal(self, db, tmp_path):
        """Test parsing config with both ID and lang."""
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps({
            "config": {"lang": "en", "ID": "ramin_yazdani"},
            "basics": []
        }))

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert result.success
        assert result.resume_key == "ramin_yazdani"
        assert result.lang_code == "en"

    def test_parse_config_missing(self, db, tmp_path):
        """Test parsing without config block - infer from filename."""
        json_path = tmp_path / "ramin.json"
        json_path.write_text(json.dumps({"basics": []}))

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert result.success
        assert result.resume_key == "ramin"
        assert result.lang_code == "en"

    def test_parse_config_partial_no_id(self, db, tmp_path):
        """Test parsing with config but no ID - infer from filename."""
        json_path = tmp_path / "test_person.json"
        json_path.write_text(json.dumps({
            "config": {"lang": "de"},
            "basics": []
        }))

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert result.success
        assert result.resume_key == "test_person"
        assert result.lang_code == "de"

    def test_parse_config_invalid_lang(self, db, tmp_path):
        """Test parsing with unsupported language code."""
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps({
            "config": {"lang": "xx", "ID": "test"},
            "basics": []
        }))

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert not result.success
        assert "Unsupported language code" in result.error

    def test_parse_config_from_filename_de(self, db, tmp_path):
        """Test inferring German language from filename."""
        json_path = tmp_path / "ramin_de.json"
        json_path.write_text(json.dumps({"basics": []}))

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert result.success
        assert result.resume_key == "ramin"
        assert result.lang_code == "de"

    def test_parse_config_from_filename_fa(self, db, tmp_path):
        """Test inferring Persian language from filename."""
        json_path = tmp_path / "ramin_fa.json"
        json_path.write_text(json.dumps({"basics": []}))

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert result.success
        assert result.resume_key == "ramin"
        assert result.lang_code == "fa"


class TestBasicsImport:
    """Tests for basics section import."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test v2 database."""
        db_path = tmp_path / "test_v2.db"
        init_db_v2(db_path)
        return db_path

    def test_import_basics_full(self, db, tmp_path):
        """Test importing complete basics with all fields."""
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps({
            "config": {"lang": "en", "ID": "test_person"},
            "basics": [{
                "fname": "John",
                "lname": "Doe",
                "email": "john@example.com",
                "birthDate": "1990-01-15",
                "summary": "Test summary",
                "phone": {
                    "countryCode": "+1",
                    "number": "5551234567",
                    "formatted": "+1 (555) 123-4567"
                },
                "location": [{
                    "postalCode": "12345",
                    "city": "New York",
                    "region": "NY",
                    "country": "USA"
                }],
                "Pictures": [
                    {"type_of": "profile", "URL": "http://example.com/photo.jpg"}
                ],
                "label": ["Developer", "Engineer"]
            }]
        }))

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert result.success
        assert result.stats["basics"] == 1

        # Verify database records
        conn = sqlite3.connect(db)
        try:
            cursor = conn.cursor()

            # Check persons table
            cursor.execute("SELECT email, birth_date, phone_country_code FROM persons")
            row = cursor.fetchone()
            assert row[0] == "john@example.com"
            assert row[1] == "1990-01-15"
            assert row[2] == "+1"

            # Check person_i18n
            cursor.execute("SELECT fname, lname, summary FROM person_i18n")
            row = cursor.fetchone()
            assert row[0] == "John"
            assert row[1] == "Doe"

            # Check locations
            cursor.execute("SELECT city FROM person_location_i18n")
            row = cursor.fetchone()
            assert row[0] == "New York"

            # Check pictures
            cursor.execute("SELECT type_of, url FROM person_pictures")
            row = cursor.fetchone()
            assert row[0] == "profile"

            # Check labels
            cursor.execute("SELECT label_text FROM person_label_i18n ORDER BY label_id")
            rows = cursor.fetchall()
            assert len(rows) == 2
            assert rows[0][0] == "Developer"
            assert rows[1][0] == "Engineer"

        finally:
            conn.close()

    def test_import_basics_minimal(self, db, tmp_path):
        """Test importing basics with only fname/lname."""
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps({
            "config": {"lang": "en", "ID": "test_person"},
            "basics": [{"fname": "Jane", "lname": "Doe"}]
        }))

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert result.success

        conn = sqlite3.connect(db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT fname, lname FROM person_i18n")
            row = cursor.fetchone()
            assert row[0] == "Jane"
            assert row[1] == "Doe"
        finally:
            conn.close()


class TestEducationImport:
    """Tests for education section import."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test v2 database."""
        db_path = tmp_path / "test_v2.db"
        init_db_v2(db_path)
        return db_path

    def test_import_education_with_tags(self, db, tmp_path):
        """Test importing education with tags."""
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps({
            "config": {"lang": "en", "ID": "test_person"},
            "education": [{
                "institution": "Test University",
                "location": "Berlin, Germany",
                "area": "Computer Science",
                "studyType": "Bachelor",
                "startDate": "2020-09-01",
                "endDate": "2024-06-15",
                "gpa": "3.8/4.0",
                "type_key": ["Full CV", "Academic"]
            }]
        }))

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert result.success
        assert result.stats["education"] == 1

        conn = sqlite3.connect(db)
        try:
            cursor = conn.cursor()

            # Check education item
            cursor.execute("SELECT start_date, end_date, gpa FROM education_items")
            row = cursor.fetchone()
            assert row[0] == "2020-09-01"
            assert row[2] == "3.8/4.0"

            # Check education i18n
            cursor.execute("SELECT institution, area FROM education_i18n")
            row = cursor.fetchone()
            assert row[0] == "Test University"
            assert row[1] == "Computer Science"

            # Check tags
            cursor.execute("SELECT tag_code FROM education_item_tags ORDER BY tag_code")
            rows = cursor.fetchall()
            assert len(rows) == 2
            assert rows[0][0] == "academic"
            assert rows[1][0] == "full_cv"

        finally:
            conn.close()

    def test_import_education_present_enddate(self, db, tmp_path):
        """Test importing education with 'present' end date."""
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps({
            "config": {"lang": "en", "ID": "test_person"},
            "education": [{
                "institution": "Current University",
                "startDate": "2024-10-01",
                "endDate": "present"
            }]
        }))

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert result.success

        conn = sqlite3.connect(db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT end_date, end_date_text FROM education_items")
            row = cursor.fetchone()
            assert row[0] is None
            assert row[1] == "present"
        finally:
            conn.close()


class TestSkillsImport:
    """Tests for skills section import (3-level nested structure)."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test v2 database."""
        db_path = tmp_path / "test_v2.db"
        init_db_v2(db_path)
        return db_path

    def test_import_skills_full_tree(self, db, tmp_path):
        """Test importing 3-level nested skills structure."""
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps({
            "config": {"lang": "en", "ID": "test_person"},
            "skills": {
                "Programming": {
                    "Languages": [
                        {"long_name": "Python", "short_name": "Python", "type_key": ["Full CV"]},
                        {"long_name": "JavaScript", "short_name": "JS"}
                    ],
                    "Frameworks": [
                        {"long_name": "Flask", "short_name": "Flask"}
                    ]
                },
                "Data Science": {
                    "Tools": [
                        {"long_name": "Pandas", "short_name": "Pandas"}
                    ]
                }
            }
        }))

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert result.success
        assert result.stats["skill_categories"] == 2
        assert result.stats["skill_subcategories"] == 3
        assert result.stats["skill_items"] == 4

        conn = sqlite3.connect(db)
        try:
            cursor = conn.cursor()

            # Check categories
            cursor.execute("SELECT name FROM skill_category_i18n ORDER BY name")
            rows = cursor.fetchall()
            assert len(rows) == 2

            # Check items
            cursor.execute("SELECT long_name FROM skill_item_i18n ORDER BY long_name")
            rows = cursor.fetchall()
            assert len(rows) == 4
            assert rows[0][0] == "Flask"
            assert rows[3][0] == "Python"

            # Check tags
            cursor.execute("SELECT tag_code FROM skill_item_tags")
            rows = cursor.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == "full_cv"

        finally:
            conn.close()

    def test_import_skills_preserves_order(self, db, tmp_path):
        """Test that skills import preserves order."""
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps({
            "config": {"lang": "en", "ID": "test_person"},
            "skills": {
                "Category": {
                    "SubCat": [
                        {"long_name": "First", "short_name": "1st"},
                        {"long_name": "Second", "short_name": "2nd"},
                        {"long_name": "Third", "short_name": "3rd"}
                    ]
                }
            }
        }))

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert result.success

        conn = sqlite3.connect(db)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT si.sort_order, sii.long_name
                FROM skill_items si
                JOIN skill_item_i18n sii ON si.id = sii.skill_item_id
                ORDER BY si.sort_order
            """)
            rows = cursor.fetchall()
            assert rows[0] == (0, "First")
            assert rows[1] == (1, "Second")
            assert rows[2] == (2, "Third")
        finally:
            conn.close()


class TestIdempotentImport:
    """Tests for idempotent imports."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test v2 database."""
        db_path = tmp_path / "test_v2.db"
        init_db_v2(db_path)
        return db_path

    def test_reimport_same_file(self, db, tmp_path):
        """Test that re-importing same file doesn't create duplicates."""
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps({
            "config": {"lang": "en", "ID": "test_person"},
            "basics": [{"fname": "John", "lname": "Doe"}],
            "education": [{
                "institution": "Test University",
                "startDate": "2020-01-01"
            }]
        }))

        importer = CVImporter(db)

        # First import
        result1 = importer.import_file(json_path)
        assert result1.success

        # Second import
        result2 = importer.import_file(json_path)
        assert result2.success

        # Verify no duplicates
        conn = sqlite3.connect(db)
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM resume_sets")
            assert cursor.fetchone()[0] == 1

            cursor.execute("SELECT COUNT(*) FROM resume_versions")
            assert cursor.fetchone()[0] == 1

            cursor.execute("SELECT COUNT(*) FROM persons")
            assert cursor.fetchone()[0] == 1

            cursor.execute("SELECT COUNT(*) FROM person_i18n")
            assert cursor.fetchone()[0] == 1

            cursor.execute("SELECT COUNT(*) FROM education_items")
            assert cursor.fetchone()[0] == 1

        finally:
            conn.close()


class TestMultiLanguageImport:
    """Tests for multi-language imports."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test v2 database."""
        db_path = tmp_path / "test_v2.db"
        init_db_v2(db_path)
        return db_path

    def test_import_three_language_variants(self, db, tmp_path):
        """Test importing EN, DE, FA for same person."""
        # Create three JSON files
        for lang, fname, lname in [
            ("en", "Ramin", "Yazdani"),
            ("de", "Ramin", "Yazdani"),
            ("fa", "رامین", "یزدانی")
        ]:
            json_path = tmp_path / f"ramin_{lang}.json"
            json_path.write_text(json.dumps({
                "config": {"lang": lang, "ID": "ramin_yazdani"},
                "basics": [{"fname": fname, "lname": lname}]
            }), encoding="utf-8")

        importer = CVImporter(db)

        # Import all three
        for lang in ["en", "de", "fa"]:
            json_path = tmp_path / f"ramin_{lang}.json"
            result = importer.import_file(json_path)
            assert result.success, f"Failed for {lang}: {result.error}"

        # Verify database state
        conn = sqlite3.connect(db)
        try:
            cursor = conn.cursor()

            # One resume_set
            cursor.execute("SELECT COUNT(*) FROM resume_sets")
            assert cursor.fetchone()[0] == 1

            # Three resume_versions
            cursor.execute("SELECT COUNT(*) FROM resume_versions")
            assert cursor.fetchone()[0] == 3

            # One person
            cursor.execute("SELECT COUNT(*) FROM persons")
            assert cursor.fetchone()[0] == 1

            # Three person_i18n (one per language)
            cursor.execute("SELECT COUNT(*) FROM person_i18n")
            assert cursor.fetchone()[0] == 3

            # Verify Persian name is correctly stored
            cursor.execute("""
                SELECT pi.fname, pi.lname
                FROM person_i18n pi
                JOIN resume_versions rv ON pi.resume_version_id = rv.id
                WHERE rv.lang_code = 'fa'
            """)
            row = cursor.fetchone()
            assert row[0] == "رامین"
            assert row[1] == "یزدانی"

        finally:
            conn.close()


class TestDryRunMode:
    """Tests for dry-run mode."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test v2 database."""
        db_path = tmp_path / "test_v2.db"
        init_db_v2(db_path)
        return db_path

    def test_dry_run_no_commit(self, db, tmp_path):
        """Test that dry-run mode doesn't commit changes."""
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps({
            "config": {"lang": "en", "ID": "test_person"},
            "basics": [{"fname": "John", "lname": "Doe"}]
        }))

        importer = CVImporter(db)
        result = importer.import_file(json_path, dry_run=True)

        assert result.success

        # Verify nothing was committed
        conn = sqlite3.connect(db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM resume_sets")
            assert cursor.fetchone()[0] == 0

            cursor.execute("SELECT COUNT(*) FROM persons")
            assert cursor.fetchone()[0] == 0
        finally:
            conn.close()


class TestBatchImport:
    """Tests for batch directory import."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test v2 database."""
        db_path = tmp_path / "test_v2.db"
        init_db_v2(db_path)
        return db_path

    def test_import_directory(self, db, tmp_path):
        """Test importing all JSON files from a directory."""
        # Create test files
        for name in ["alice", "bob", "charlie"]:
            json_path = tmp_path / f"{name}.json"
            json_path.write_text(json.dumps({
                "config": {"lang": "en", "ID": name},
                "basics": [{"fname": name.title(), "lname": "Test"}]
            }))

        importer = CVImporter(db)
        result = importer.import_directory(tmp_path)

        assert result.total_files == 3
        assert result.successful == 3
        assert result.failed == 0

        # Verify database
        conn = sqlite3.connect(db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM resume_sets")
            assert cursor.fetchone()[0] == 3
        finally:
            conn.close()


class TestTagNormalization:
    """Tests for tag normalization."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test v2 database."""
        db_path = tmp_path / "test_v2.db"
        init_db_v2(db_path)
        return db_path

    def test_tag_case_normalization(self, db, tmp_path):
        """Test that 'Full CV' and 'full cv' map to same tag_code."""
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps({
            "config": {"lang": "en", "ID": "test_person"},
            "education": [
                {"institution": "Uni A", "startDate": "2020-01-01", "type_key": ["Full CV"]},
                {"institution": "Uni B", "startDate": "2021-01-01", "type_key": ["full cv"]}
            ]
        }))

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert result.success

        conn = sqlite3.connect(db)
        try:
            cursor = conn.cursor()

            # Should only have one tag code
            cursor.execute("SELECT COUNT(*) FROM tag_codes WHERE code = 'full_cv'")
            assert cursor.fetchone()[0] == 1

            # Both education items should reference same tag
            cursor.execute("SELECT COUNT(*) FROM education_item_tags WHERE tag_code = 'full_cv'")
            assert cursor.fetchone()[0] == 2

        finally:
            conn.close()


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test v2 database."""
        db_path = tmp_path / "test_v2.db"
        init_db_v2(db_path)
        return db_path

    def test_import_empty_sections(self, db, tmp_path):
        """Test importing JSON with empty arrays."""
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps({
            "config": {"lang": "en", "ID": "test_person"},
            "basics": [],
            "education": [],
            "skills": {}
        }))

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert result.success

    def test_import_malformed_json(self, db, tmp_path):
        """Test importing invalid JSON."""
        json_path = tmp_path / "test.json"
        json_path.write_text("{invalid json")

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert not result.success
        assert "Invalid JSON" in result.error

    def test_import_missing_file(self, db, tmp_path):
        """Test importing non-existent file."""
        json_path = tmp_path / "nonexistent.json"

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert not result.success
        assert "File not found" in result.error

    def test_import_null_values(self, db, tmp_path):
        """Test importing with explicit null values."""
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps({
            "config": {"lang": "en", "ID": "test_person"},
            "basics": [{
                "fname": "John",
                "lname": None,
                "email": None,
                "summary": None
            }]
        }))

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert result.success

        conn = sqlite3.connect(db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT fname, lname, summary FROM person_i18n")
            row = cursor.fetchone()
            assert row[0] == "John"
            assert row[1] is None
            assert row[2] is None
        finally:
            conn.close()

    def test_import_unicode_content(self, db, tmp_path):
        """Test importing with Unicode content (Persian, German)."""
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps({
            "config": {"lang": "fa", "ID": "test_person"},
            "basics": [{
                "fname": "رامین",
                "lname": "یزدانی",
                "summary": "خلاصه فارسی mit Umlauten: äöü"
            }]
        }, ensure_ascii=False), encoding="utf-8")

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert result.success

        conn = sqlite3.connect(db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT fname, lname, summary FROM person_i18n")
            row = cursor.fetchone()
            assert row[0] == "رامین"
            assert row[1] == "یزدانی"
            assert "Umlauten" in row[2]
        finally:
            conn.close()


class TestIntegrationWithRealFiles:
    """Integration tests with real CV JSON files."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test v2 database."""
        db_path = tmp_path / "test_v2.db"
        init_db_v2(db_path)
        return db_path

    def test_import_ramin_en(self, db):
        """Test importing real ramin.json file."""
        json_path = Path("/home/runner/work/cv_generator/cv_generator/data/cvs/ramin.json")
        if not json_path.exists():
            pytest.skip("Real CV file not found")

        importer = CVImporter(db)
        result = importer.import_file(json_path)

        assert result.success, f"Failed: {result.error}"
        assert result.resume_key == "ramin_yazdani"
        assert result.lang_code == "en"

        # Verify all sections were imported
        assert result.stats.get("basics", 0) > 0
        assert result.stats.get("education", 0) > 0
        assert result.stats.get("skill_items", 0) > 0

    def test_import_all_three_variants(self, db):
        """Test importing EN, DE, FA variants of the same CV."""
        cvs_dir = Path("/home/runner/work/cv_generator/cv_generator/data/cvs")
        if not cvs_dir.exists():
            pytest.skip("CVs directory not found")

        importer = CVImporter(db)

        for filename in ["ramin.json", "ramin_de.json", "ramin_fa.json"]:
            json_path = cvs_dir / filename
            if not json_path.exists():
                continue

            result = importer.import_file(json_path)
            assert result.success, f"Failed for {filename}: {result.error}"

        # Verify database state
        conn = sqlite3.connect(db)
        try:
            cursor = conn.cursor()

            # Should have one resume_set
            cursor.execute("SELECT COUNT(*) FROM resume_sets WHERE resume_key = 'ramin_yazdani'")
            assert cursor.fetchone()[0] == 1

            # Should have up to 3 versions (depending on which files exist)
            cursor.execute("SELECT COUNT(*) FROM resume_versions WHERE resume_key = 'ramin_yazdani'")
            count = cursor.fetchone()[0]
            assert count >= 1

        finally:
            conn.close()
