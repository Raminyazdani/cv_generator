"""
Round-trip tests proving lossless import/export.

These tests are the ULTIMATE proof that the system works correctly.
If these pass, we guarantee no data loss.

Tests:
- Individual file round-trips (ramin.json, ramin_de.json, ramin_fa.json, mahsa.json)
- Batch round-trip for all CV files
- Multi-language variant round-trips
- Edge case round-trips (empty sections, null values, unicode content, large text)
"""

import json
import tempfile
from pathlib import Path

import pytest

from cv_generator.export_verify import ExportVerifier, RoundTripResult, VerificationResult
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
    db_path = tmp_path / "test_roundtrip.db"
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


@pytest.fixture
def verifier():
    """Create verifier instance with sensible defaults.

    NOTE: We ignore_order=True because JSON objects are unordered by spec,
    and different serializers may output keys in different orders.
    The important thing is that all values are correct.
    """
    return ExportVerifier(
        ignore_order=True,  # JSON objects are unordered by spec
        ignore_whitespace=True,
        ignore_type_key_order=True,
    )


# ==============================================================================
# Helper functions
# ==============================================================================


def perform_roundtrip(
    json_path: Path,
    importer: CVImporter,
    exporter: CVExporter,
    verifier: ExportVerifier,
) -> VerificationResult:
    """
    Perform a full round-trip test on a single file.

    Steps:
    1. Import the JSON file to the database
    2. Export from the database
    3. Verify the exported data matches the original

    Args:
        json_path: Path to the original JSON file
        importer: CVImporter instance
        exporter: CVExporter instance
        verifier: ExportVerifier instance

    Returns:
        VerificationResult with match status and any differences
    """
    # Step 1: Import
    import_result = importer.import_file(json_path, overwrite=True)
    if not import_result.success:
        # Return a failed verification result
        result = VerificationResult(matches=False, original_path=json_path)
        result.value_diffs.append(
            type(
                "ValueDiff",
                (),
                {"path": "import", "original": "", "exported": import_result.error, "diff_type": "error"},
            )()
        )
        return result

    # Step 2: Export
    try:
        exported_data = exporter.export(
            resume_key=import_result.resume_key,
            lang_code=import_result.lang_code,
        )
    except Exception as e:
        result = VerificationResult(matches=False, original_path=json_path)
        result.value_diffs.append(
            type(
                "ValueDiff",
                (),
                {"path": "export", "original": "", "exported": str(e), "diff_type": "error"},
            )()
        )
        return result

    # Step 3: Verify
    verification = verifier.verify_export(json_path, exported_data)
    return verification


# ==============================================================================
# Individual file round-trip tests
# ==============================================================================


class TestRoundTripIndividualFiles:
    """Round-trip tests for individual CV files."""

    def test_roundtrip_ramin_en(self, fresh_db, verifier):
        """Round-trip test for English CV."""
        json_path = CVS_DIR / "ramin.json"
        if not json_path.exists():
            pytest.skip("ramin.json not found in data/cvs/")

        importer = CVImporter(fresh_db)
        exporter = CVExporter(fresh_db)

        verification = perform_roundtrip(json_path, importer, exporter, verifier)

        assert verification.matches, (
            f"Round-trip failed for ramin.json:\n{verification.get_summary()}"
        )

    def test_roundtrip_ramin_de(self, fresh_db, verifier):
        """Round-trip test for German CV."""
        json_path = CVS_DIR / "ramin_de.json"
        if not json_path.exists():
            pytest.skip("ramin_de.json not found in data/cvs/")

        importer = CVImporter(fresh_db)
        exporter = CVExporter(fresh_db)

        verification = perform_roundtrip(json_path, importer, exporter, verifier)

        assert verification.matches, (
            f"Round-trip failed for ramin_de.json:\n{verification.get_summary()}"
        )

    def test_roundtrip_ramin_fa(self, fresh_db, verifier):
        """Round-trip test for Persian CV."""
        json_path = CVS_DIR / "ramin_fa.json"
        if not json_path.exists():
            pytest.skip("ramin_fa.json not found in data/cvs/")

        importer = CVImporter(fresh_db)
        exporter = CVExporter(fresh_db)

        verification = perform_roundtrip(json_path, importer, exporter, verifier)

        assert verification.matches, (
            f"Round-trip failed for ramin_fa.json:\n{verification.get_summary()}"
        )

    def test_roundtrip_mahsa(self, fresh_db, verifier):
        """Round-trip test for second person."""
        json_path = CVS_DIR / "mahsa.json"
        if not json_path.exists():
            pytest.skip("mahsa.json not found in data/cvs/")

        importer = CVImporter(fresh_db)
        exporter = CVExporter(fresh_db)

        verification = perform_roundtrip(json_path, importer, exporter, verifier)

        assert verification.matches, (
            f"Round-trip failed for mahsa.json:\n{verification.get_summary()}"
        )


# ==============================================================================
# Batch round-trip tests
# ==============================================================================


class TestRoundTripBatch:
    """Batch round-trip tests for all CV files."""

    def test_roundtrip_all_files(self, tmp_path, verifier):
        """Round-trip all files in data/cvs/."""
        if not CVS_DIR.exists():
            pytest.skip("data/cvs/ directory not found")

        json_files = list(CVS_DIR.glob("*.json"))
        if not json_files:
            pytest.skip("No JSON files found in data/cvs/")

        failures = []

        for json_file in json_files:
            # Create fresh DB for each file to ensure isolation
            db_path = tmp_path / f"db_{json_file.stem}.db"
            init_db_v2(db_path, force=True)

            importer = CVImporter(db_path)
            exporter = CVExporter(db_path)

            verification = perform_roundtrip(json_file, importer, exporter, verifier)

            if not verification.matches:
                failures.append((json_file.name, verification.get_summary()))

        assert len(failures) == 0, (
            f"Round-trip failures in {len(failures)}/{len(json_files)} files:\n\n"
            + "\n\n".join(f"=== {name} ===\n{summary}" for name, summary in failures)
        )


# ==============================================================================
# Multi-language variant round-trip tests
# ==============================================================================


class TestRoundTripMultiLanguage:
    """Round-trip tests for multi-language variant scenarios."""

    def test_roundtrip_all_variants_together(self, fresh_db, verifier):
        """Import all 3 variants, verify they share the same resume_key.

        NOTE: When importing multiple language variants into a single database,
        translatable fields may get normalized/merged. This test verifies:
        1. All variants import successfully
        2. They share a common resume_key
        3. The number of resume versions matches the number of files imported

        For strict round-trip verification of individual files, use the
        TestRoundTripIndividualFiles tests which use fresh databases per file.
        """
        files = [
            CVS_DIR / "ramin.json",
            CVS_DIR / "ramin_de.json",
            CVS_DIR / "ramin_fa.json",
        ]

        # Skip if files don't exist
        existing_files = [f for f in files if f.exists()]
        if not existing_files:
            pytest.skip("No ramin variant files found")

        importer = CVImporter(fresh_db)

        # Import all variants
        for f in existing_files:
            result = importer.import_file(f, overwrite=True)
            assert result.success, f"Import failed for {f.name}: {result.error}"

        # Verify single resume_set created
        import sqlite3

        conn = sqlite3.connect(fresh_db)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(DISTINCT resume_key) FROM resume_versions"
            )
            count = cursor.fetchone()[0]
            # All variants should share the same resume_key
            assert count == 1, f"Expected 1 resume_key, got {count}"

            # Verify we have the expected number of resume versions
            cursor.execute("SELECT COUNT(*) FROM resume_versions")
            version_count = cursor.fetchone()[0]
            assert version_count == len(existing_files), (
                f"Expected {len(existing_files)} versions, got {version_count}"
            )
        finally:
            conn.close()

        # Verify each variant can be exported (basic structure check)
        for f in existing_files:
            with open(f, encoding="utf-8") as fp:
                original_data = json.load(fp)

            config = original_data.get("config", {})
            lang_code = config.get("lang", "en")
            resume_key = config.get("ID", f.stem)

            exporter = CVExporter(fresh_db)
            exported_data = exporter.export(resume_key, lang_code)

            # Basic structure checks
            assert "config" in exported_data
            assert "basics" in exported_data
            assert exported_data["config"]["lang"] == lang_code
            assert exported_data["config"]["ID"] == resume_key

    def test_variants_share_resume_key(self, fresh_db):
        """Verify that all language variants link to the same resume_key."""
        files = [
            CVS_DIR / "ramin.json",
            CVS_DIR / "ramin_de.json",
            CVS_DIR / "ramin_fa.json",
        ]

        existing_files = [f for f in files if f.exists()]
        if len(existing_files) < 2:
            pytest.skip("Need at least 2 variant files for this test")

        importer = CVImporter(fresh_db)

        # Import all variants
        for f in existing_files:
            result = importer.import_file(f, overwrite=True)
            assert result.success, f"Import failed: {result.error}"

        # Verify they all share the same resume_key
        import sqlite3

        conn = sqlite3.connect(fresh_db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT resume_key, lang_code FROM resume_versions")
            rows = cursor.fetchall()

            resume_keys = set(r[0] for r in rows)
            assert len(resume_keys) == 1, (
                f"Expected all variants to share one resume_key, got {resume_keys}"
            )

            # Verify we have the expected number of language variants
            assert len(rows) == len(existing_files), (
                f"Expected {len(existing_files)} variants, got {len(rows)}"
            )
        finally:
            conn.close()


# ==============================================================================
# Edge case round-trip tests
# ==============================================================================


class TestRoundTripEdgeCases:
    """Round-trip tests for edge cases and boundary conditions."""

    def test_roundtrip_empty_sections(self, fresh_db, verifier, tmp_path):
        """File with empty arrays survives round-trip."""
        json_path = tmp_path / "empty_sections.json"
        cv_data = {
            "config": {"lang": "en", "ID": "empty_test"},
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
            json.dump(cv_data, f, indent=2)

        importer = CVImporter(fresh_db)
        exporter = CVExporter(fresh_db)

        verification = perform_roundtrip(json_path, importer, exporter, verifier)

        assert verification.matches, (
            f"Round-trip failed for empty sections:\n{verification.get_summary()}"
        )

    def test_roundtrip_null_values(self, fresh_db, verifier, tmp_path):
        """Explicit nulls survive round-trip."""
        json_path = tmp_path / "null_values.json"
        cv_data = {
            "config": {"lang": "en", "ID": "null_test"},
            "basics": [
                {
                    "fname": "Test",
                    "lname": None,
                    "label": [],
                    "email": None,
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
        exporter = CVExporter(fresh_db)

        verification = perform_roundtrip(json_path, importer, exporter, verifier)

        assert verification.matches, (
            f"Round-trip failed for null values:\n{verification.get_summary()}"
        )

    def test_roundtrip_unicode_content(self, fresh_db, verifier, tmp_path):
        """Persian/German text survives round-trip."""
        json_path = tmp_path / "unicode_content.json"
        cv_data = {
            "config": {"lang": "fa", "ID": "unicode_test"},
            "basics": [
                {
                    "fname": "رامین",
                    "lname": "یزدانی",
                    "label": ["مهندس نرم‌افزار", "Entwickler"],
                    "email": "test@example.com",
                    "phone": {"countryCode": "+49", "number": "12345", "formatted": "+49 12345"},
                    "birthDate": "1990-01-01",
                    "summary": "این یک خلاصه به زبان فارسی است. Mit deutschen Umlauten: äöüß",
                    "location": [
                        {
                            "address": "آدرس فارسی",
                            "postalCode": "12345",
                            "city": "تهران",
                            "region": "تهران",
                            "country": "ایران",
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

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cv_data, f, indent=2, ensure_ascii=False)

        importer = CVImporter(fresh_db)
        exporter = CVExporter(fresh_db)

        verification = perform_roundtrip(json_path, importer, exporter, verifier)

        assert verification.matches, (
            f"Round-trip failed for unicode content:\n{verification.get_summary()}"
        )

    def test_roundtrip_large_text(self, fresh_db, verifier, tmp_path):
        """Long summary text survives round-trip."""
        # Create a large summary (10KB)
        large_summary = "This is a test paragraph. " * 500

        json_path = tmp_path / "large_text.json"
        cv_data = {
            "config": {"lang": "en", "ID": "large_test"},
            "basics": [
                {
                    "fname": "Test",
                    "lname": "Person",
                    "label": ["Developer"],
                    "email": "test@example.com",
                    "phone": {"countryCode": "+1", "number": "12345", "formatted": "+1 12345"},
                    "birthDate": "1990-01-01",
                    "summary": large_summary,
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
        exporter = CVExporter(fresh_db)

        verification = perform_roundtrip(json_path, importer, exporter, verifier)

        assert verification.matches, (
            f"Round-trip failed for large text:\n{verification.get_summary()}"
        )


# ==============================================================================
# Round-trip verification using the built-in verifier
# ==============================================================================


class TestRoundTripWithVerifier:
    """Tests using the ExportVerifier.verify_round_trip method."""

    def test_verify_round_trip_ramin_en(self, tmp_path):
        """Test full round-trip verification for ramin.json."""
        json_path = CVS_DIR / "ramin.json"
        if not json_path.exists():
            pytest.skip("ramin.json not found")

        db_path = tmp_path / "roundtrip_test.db"
        verifier = ExportVerifier()

        result = verifier.verify_round_trip(json_path, db_path)

        assert result.import_success, f"Import failed: {result.import_error}"
        assert result.export_success, f"Export failed: {result.export_error}"
        assert result.verification is not None, "Verification not performed"
        assert result.success, (
            f"Round-trip verification failed:\n{result.verification.get_summary()}"
        )

    def test_verify_round_trip_all_files(self, tmp_path):
        """Test round-trip verification for all CV files."""
        if not CVS_DIR.exists():
            pytest.skip("data/cvs/ directory not found")

        json_files = list(CVS_DIR.glob("*.json"))
        if not json_files:
            pytest.skip("No JSON files found")

        verifier = ExportVerifier(ignore_type_key_order=True)
        failures = []

        for json_file in json_files:
            db_path = tmp_path / f"rt_{json_file.stem}.db"
            result = verifier.verify_round_trip(json_file, db_path)

            if not result.success:
                if result.verification:
                    failures.append((json_file.name, result.verification.get_summary()))
                else:
                    failures.append(
                        (json_file.name, result.import_error or result.export_error or "Unknown")
                    )

        assert len(failures) == 0, (
            "Round-trip failures:\n\n"
            + "\n\n".join(f"=== {name} ===\n{summary}" for name, summary in failures)
        )


# ==============================================================================
# Regression tests for specific issues
# ==============================================================================


class TestRoundTripRegressions:
    """Regression tests for previously identified round-trip issues."""

    def test_pictures_key_capitalization(self, fresh_db, tmp_path):
        """
        Regression: 'Pictures' key must stay capitalized.

        The original JSON uses 'Pictures' (capital P) while the database
        column might be lowercase. Export must restore the correct casing.
        """
        json_path = tmp_path / "pictures_test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "pictures_test"},
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
                    "Pictures": [
                        {"type_of": "profile", "URL": "https://example.com/photo.jpg"}
                    ],
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
        import_result = importer.import_file(json_path)
        assert import_result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("pictures_test", "en")

        # Verify Pictures key is capitalized
        assert "Pictures" in exported["basics"][0], (
            "Pictures key should be capitalized in exported data"
        )
        assert "pictures" not in exported["basics"][0], (
            "Lowercase 'pictures' should not be in exported data"
        )

    def test_phone_nested_structure(self, fresh_db, tmp_path):
        """
        Regression: Phone must export as nested object, not flat fields.

        The phone field should be exported as:
        {"countryCode": "+1", "number": "123", "formatted": "+1 123"}

        Not as flat fields like phone_country_code, phone_number.
        """
        json_path = tmp_path / "phone_test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "phone_test"},
            "basics": [
                {
                    "fname": "Test",
                    "lname": "Person",
                    "label": [],
                    "email": "test@example.com",
                    "phone": {
                        "countryCode": "+49",
                        "number": "17612345678",
                        "formatted": "+49 176 12345678",
                    },
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
        import_result = importer.import_file(json_path)
        assert import_result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("phone_test", "en")

        phone = exported["basics"][0]["phone"]
        assert isinstance(phone, dict), f"Phone should be dict, got {type(phone)}"
        assert phone["countryCode"] == "+49"
        assert phone["number"] == "17612345678"
        assert phone["formatted"] == "+49 176 12345678"

    def test_skills_order_preserved(self, fresh_db, tmp_path):
        """
        Regression: Skills items should maintain their original order.

        The sort_order column must be used to preserve array order.
        """
        json_path = tmp_path / "skills_order_test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "skills_order_test"},
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
            "skills": {
                "Programming": {
                    "Languages": [
                        {"long_name": "First Item", "short_name": "1"},
                        {"long_name": "Second Item", "short_name": "2"},
                        {"long_name": "Third Item", "short_name": "3"},
                    ]
                }
            },
            "experiences": [],
            "projects": [],
            "publications": [],
            "references": [],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cv_data, f, indent=2)

        importer = CVImporter(fresh_db)
        import_result = importer.import_file(json_path)
        assert import_result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("skills_order_test", "en")

        items = exported["skills"]["Programming"]["Languages"]
        assert len(items) == 3
        assert items[0]["long_name"] == "First Item"
        assert items[1]["long_name"] == "Second Item"
        assert items[2]["long_name"] == "Third Item"


# ==============================================================================
# Performance tests (optional, can be skipped in CI)
# ==============================================================================


class TestRoundTripPerformance:
    """Performance tests for round-trip operations."""

    @pytest.mark.slow
    def test_roundtrip_performance_all_files(self, tmp_path, verifier):
        """Verify all round-trips complete within reasonable time."""
        import time

        if not CVS_DIR.exists():
            pytest.skip("data/cvs/ directory not found")

        json_files = list(CVS_DIR.glob("*.json"))
        if not json_files:
            pytest.skip("No JSON files found")

        start = time.time()

        for json_file in json_files:
            db_path = tmp_path / f"perf_{json_file.stem}.db"
            init_db_v2(db_path, force=True)

            importer = CVImporter(db_path)
            exporter = CVExporter(db_path)

            perform_roundtrip(json_file, importer, exporter, verifier)

        total_time = time.time() - start

        # All files should complete within 30 seconds
        assert total_time < 30, (
            f"Round-trip for all files took {total_time:.2f}s, expected < 30s"
        )
