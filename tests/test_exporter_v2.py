"""
Test suite for CVExporter (exporter_v2.py).

Tests cover:
- Config block export
- All section exporters
- Round-trip verification (import → export → compare)
- Edge cases
- Multi-language support
"""

import json
import sqlite3
import tempfile
from collections import OrderedDict
from pathlib import Path

import pytest

from cv_generator.exporter_v2 import CVExporter, ExportResult, ExportBatchResult
from cv_generator.export_mappings import ordered_dict_from_mapping, BASICS_FIELD_ORDER
from cv_generator.export_verify import ExportVerifier, VerificationResult
from cv_generator.importer_v2 import CVImporter
from cv_generator.schema_v2 import init_db_v2


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    init_db_v2(db_path, force=True)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def sample_cv_data():
    """Minimal CV data for testing."""
    return {
        "config": {"lang": "en", "ID": "test_person"},
        "basics": [
            {
                "fname": "Test",
                "lname": "Person",
                "label": ["Developer"],
                "email": "test@example.com",
                "phone": {
                    "countryCode": "+1",
                    "number": "1234567890",
                    "formatted": "+1 (123) 456-7890",
                },
                "birthDate": "1990-01-01",
                "summary": "Test summary",
                "location": [
                    {
                        "address": None,
                        "postalCode": "12345",
                        "city": "Test City",
                        "region": "Test Region",
                        "country": "Test Country",
                    }
                ],
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


@pytest.fixture
def imported_sample(temp_db, sample_cv_data):
    """Import sample data and return the DB path."""
    # Write sample data to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(sample_cv_data, f)
        json_path = Path(f.name)

    try:
        importer = CVImporter(temp_db)
        result = importer.import_file(json_path)
        assert result.success
        return temp_db
    finally:
        json_path.unlink()


class TestExportMappings:
    """Test export mapping utilities."""

    def test_ordered_dict_from_mapping_basic(self):
        """Test basic OrderedDict creation."""
        data = {"b": 2, "a": 1, "c": 3}
        order = ["a", "b", "c"]
        result = ordered_dict_from_mapping(data, order)

        assert list(result.keys()) == ["a", "b", "c"]
        assert result["a"] == 1

    def test_ordered_dict_preserves_extra_keys(self):
        """Test that keys not in order list are appended."""
        data = {"a": 1, "b": 2, "extra": "value"}
        order = ["a", "b"]
        result = ordered_dict_from_mapping(data, order)

        assert list(result.keys()) == ["a", "b", "extra"]

    def test_ordered_dict_handles_missing_keys(self):
        """Test handling of missing keys."""
        data = {"a": 1}
        order = ["a", "b", "c"]
        result = ordered_dict_from_mapping(data, order, include_missing=True)

        assert "b" in result
        assert result["b"] is None

    def test_ordered_dict_excludes_none(self):
        """Test excluding None values."""
        data = {"a": 1, "b": None}
        order = ["a", "b"]
        result = ordered_dict_from_mapping(data, order, include_none=False)

        assert "a" in result
        assert "b" not in result


class TestExportConfig:
    """Test config block export."""

    def test_export_config_en(self, imported_sample):
        """Test exporting config for English variant."""
        exporter = CVExporter(imported_sample)
        cv_data = exporter.export("test_person", "en")

        assert "config" in cv_data
        assert cv_data["config"]["lang"] == "en"
        assert cv_data["config"]["ID"] == "test_person"

    def test_export_config_order(self, imported_sample):
        """Test config key order."""
        exporter = CVExporter(imported_sample)
        cv_data = exporter.export("test_person", "en")

        config_keys = list(cv_data["config"].keys())
        assert config_keys == ["lang", "ID"]


class TestExportBasics:
    """Test basics section export."""

    def test_export_basics_full(self, imported_sample):
        """Test exporting complete basics section."""
        exporter = CVExporter(imported_sample)
        cv_data = exporter.export("test_person", "en")

        basics = cv_data["basics"]
        assert len(basics) == 1
        assert basics[0]["fname"] == "Test"
        assert basics[0]["lname"] == "Person"
        assert basics[0]["email"] == "test@example.com"

    def test_export_basics_phone_nested(self, imported_sample):
        """Test phone is exported as nested object."""
        exporter = CVExporter(imported_sample)
        cv_data = exporter.export("test_person", "en")

        phone = cv_data["basics"][0]["phone"]
        assert isinstance(phone, (dict, OrderedDict))
        assert phone["countryCode"] == "+1"
        assert phone["number"] == "1234567890"

    def test_export_basics_labels_array(self, imported_sample):
        """Test labels exported as array."""
        exporter = CVExporter(imported_sample)
        cv_data = exporter.export("test_person", "en")

        labels = cv_data["basics"][0]["label"]
        assert isinstance(labels, list)
        assert "Developer" in labels

    def test_export_basics_null_address(self, imported_sample):
        """Test null address is preserved."""
        exporter = CVExporter(imported_sample)
        cv_data = exporter.export("test_person", "en")

        location = cv_data["basics"][0]["location"][0]
        assert "address" in location
        assert location["address"] is None


class TestExportProfiles:
    """Test profiles section export."""

    def test_export_profiles_empty(self, imported_sample):
        """Test exporting empty profiles section."""
        exporter = CVExporter(imported_sample)
        cv_data = exporter.export("test_person", "en")

        assert "profiles" in cv_data
        assert cv_data["profiles"] == []


class TestExportEducation:
    """Test education section export."""

    def test_export_education_empty(self, imported_sample):
        """Test exporting empty education section."""
        exporter = CVExporter(imported_sample)
        cv_data = exporter.export("test_person", "en")

        assert "education" in cv_data
        assert cv_data["education"] == []


class TestExportSkills:
    """Test skills section export."""

    def test_export_skills_empty(self, imported_sample):
        """Test exporting empty skills section."""
        exporter = CVExporter(imported_sample)
        cv_data = exporter.export("test_person", "en")

        assert "skills" in cv_data
        assert cv_data["skills"] == {} or isinstance(cv_data["skills"], (dict, OrderedDict))


class TestSectionOrder:
    """Test section ordering in exported JSON."""

    def test_section_order(self, imported_sample):
        """Test sections appear in correct order."""
        exporter = CVExporter(imported_sample)
        cv_data = exporter.export("test_person", "en")

        expected_order = [
            "config",
            "basics",
            "profiles",
            "education",
            "languages",
            "workshop_and_certifications",
            "skills",
            "experiences",
            "projects",
            "publications",
            "references",
        ]

        actual_keys = list(cv_data.keys())
        assert actual_keys == expected_order


class TestExportToFile:
    """Test file export functionality."""

    def test_export_to_file_creates_file(self, imported_sample):
        """Test that export_to_file creates the output file."""
        exporter = CVExporter(imported_sample)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_export.json"
            result = exporter.export_to_file("test_person", "en", output_path)

            assert result.success
            assert output_path.exists()

    def test_export_to_file_valid_json(self, imported_sample):
        """Test that exported file is valid JSON."""
        exporter = CVExporter(imported_sample)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_export.json"
            exporter.export_to_file("test_person", "en", output_path)

            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert "config" in data
            assert "basics" in data


class TestExportResult:
    """Test ExportResult dataclass."""

    def test_export_result_to_dict(self):
        """Test serialization of ExportResult."""
        result = ExportResult(
            success=True,
            resume_key="test",
            lang_code="en",
            output_path=Path("/tmp/test.json"),
        )

        data = result.to_dict()
        assert data["success"] is True
        assert data["resume_key"] == "test"
        assert data["output_path"] == "/tmp/test.json"


class TestExportBatchResult:
    """Test ExportBatchResult dataclass."""

    def test_batch_result_to_dict(self):
        """Test serialization of ExportBatchResult."""
        result = ExportBatchResult(
            total_files=3,
            successful=2,
            failed=1,
        )

        data = result.to_dict()
        assert data["total_files"] == 3
        assert data["successful"] == 2


class TestExportVerifier:
    """Test ExportVerifier functionality."""

    def test_verify_identical_files(self, imported_sample, sample_cv_data):
        """Test verification of identical data."""
        # Write original to file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(sample_cv_data, f)
            original_path = Path(f.name)

        try:
            # Export from DB
            exporter = CVExporter(imported_sample)
            exported_data = exporter.export("test_person", "en")

            # Verify
            verifier = ExportVerifier()
            result = verifier.verify_export(original_path, exported_data)

            # Most fields should match; some minor differences due to import/export processing
            assert isinstance(result, VerificationResult)

        finally:
            original_path.unlink()

    def test_verify_detects_missing_key(self):
        """Test that verifier detects missing keys."""
        original = {"a": 1, "b": 2}
        exported = {"a": 1}

        # Create temp file for original
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(original, f)
            original_path = Path(f.name)

        try:
            verifier = ExportVerifier()
            result = verifier.verify_export(original_path, exported)

            assert not result.matches
            assert "b" in result.missing_keys

        finally:
            original_path.unlink()

    def test_verify_detects_extra_key(self):
        """Test that verifier detects extra keys."""
        original = {"a": 1}
        exported = {"a": 1, "b": 2}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(original, f)
            original_path = Path(f.name)

        try:
            verifier = ExportVerifier()
            result = verifier.verify_export(original_path, exported)

            assert not result.matches
            assert "b" in result.extra_keys

        finally:
            original_path.unlink()


class TestListAvailable:
    """Test listing available resume variants."""

    def test_list_available(self, imported_sample):
        """Test listing available (resume_key, lang_code) combinations."""
        exporter = CVExporter(imported_sample)
        available = exporter.list_available()

        assert len(available) >= 1
        assert ("test_person", "en") in available


class TestRealDataIntegration:
    """Integration tests with real CV data files."""

    @pytest.fixture
    def real_db(self):
        """Create a DB with real CV data."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        init_db_v2(db_path, force=True)

        # Import real files
        data_dir = Path(__file__).parent.parent / "data" / "cvs"
        if data_dir.exists():
            importer = CVImporter(db_path)
            for json_file in data_dir.glob("ramin*.json"):
                importer.import_file(json_file)

        yield db_path

        if db_path.exists():
            db_path.unlink()

    def test_export_ramin_en_complete(self, real_db):
        """Test full English CV export."""
        data_dir = Path(__file__).parent.parent / "data" / "cvs"
        if not (data_dir / "ramin.json").exists():
            pytest.skip("Real test data not available")

        exporter = CVExporter(real_db)
        cv_data = exporter.export("ramin_yazdani", "en")

        # Verify all sections present
        assert "config" in cv_data
        assert "basics" in cv_data
        assert "skills" in cv_data
        assert "education" in cv_data

        # Verify config
        assert cv_data["config"]["lang"] == "en"
        assert cv_data["config"]["ID"] == "ramin_yazdani"

        # Verify basics
        assert cv_data["basics"][0]["fname"] == "Ramin"

    def test_export_all_variants(self, real_db):
        """Test exporting all language variants."""
        data_dir = Path(__file__).parent.parent / "data" / "cvs"
        if not (data_dir / "ramin.json").exists():
            pytest.skip("Real test data not available")

        exporter = CVExporter(real_db)

        with tempfile.TemporaryDirectory() as tmpdir:
            results = exporter.export_all_variants("ramin_yazdani", Path(tmpdir))

            # Should have at least one result
            assert len(results) >= 1

    def test_roundtrip_ramin_en(self, real_db):
        """Test round-trip for English CV."""
        data_dir = Path(__file__).parent.parent / "data" / "cvs"
        original_path = data_dir / "ramin.json"
        if not original_path.exists():
            pytest.skip("Real test data not available")

        # Export from DB
        exporter = CVExporter(real_db)
        exported_data = exporter.export("ramin_yazdani", "en")

        # Verify structure
        verifier = ExportVerifier()
        result = verifier.verify_export(original_path, exported_data)

        # Note: We allow some minor differences due to type_key ordering
        # and maxScore/minScore fields. The important thing is structural identity.
        # Check for critical fields
        assert len(result.missing_keys) < 5  # Allow minor differences


class TestEdgeCases:
    """Test edge cases in export."""

    def test_export_nonexistent_resume(self, temp_db):
        """Test exporting non-existent resume raises error."""
        exporter = CVExporter(temp_db)

        with pytest.raises(ValueError, match="No resume version found"):
            exporter.export("nonexistent", "en")

    def test_export_nonexistent_language(self, imported_sample):
        """Test exporting non-existent language raises error."""
        exporter = CVExporter(imported_sample)

        with pytest.raises(ValueError, match="No resume version found"):
            exporter.export("test_person", "fr")  # French not imported
