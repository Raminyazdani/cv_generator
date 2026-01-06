"""
Edge case and boundary condition tests.

Tests cover:
- Null handling (explicit null vs missing keys)
- Empty handling (empty arrays, strings, objects)
- Type preservation (integers, floats, booleans)
- Unicode handling (Persian, German, mixed scripts)
- Large content handling (long text, many items)
"""

import json
import sqlite3
from pathlib import Path

import pytest

from cv_generator.exporter_v2 import CVExporter
from cv_generator.importer_v2 import CVImporter
from cv_generator.schema_v2 import init_db_v2


@pytest.fixture
def fresh_db(tmp_path):
    """Create a fresh database for each test."""
    db_path = tmp_path / "test_edge_cases.db"
    init_db_v2(db_path, force=True)
    return db_path


# ==============================================================================
# Null Handling Tests
# ==============================================================================


class TestNullHandling:
    """Tests for null value handling."""

    def test_explicit_null_preserved(self, fresh_db, tmp_path):
        """{"field": null} stays as null."""
        json_path = tmp_path / "test.json"
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
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("null_test", "en")

        # Verify null values are preserved
        basics = exported["basics"][0]
        assert basics["lname"] is None
        assert basics["email"] is None
        assert basics["birthDate"] is None
        assert basics["summary"] is None

    def test_phone_all_null_fields(self, fresh_db, tmp_path):
        """Phone object with all null fields."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "phone_null"},
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
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("phone_null", "en")

        phone = exported["basics"][0]["phone"]
        assert isinstance(phone, dict)
        assert phone["countryCode"] is None
        assert phone["number"] is None
        assert phone["formatted"] is None


# ==============================================================================
# Empty Handling Tests
# ==============================================================================


class TestEmptyHandling:
    """Tests for empty value handling."""

    def test_empty_array_preserved(self, fresh_db, tmp_path):
        """[] stays as []."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "empty_array"},
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
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("empty_array", "en")

        # Verify empty arrays are preserved
        assert exported["profiles"] == []
        assert exported["education"] == []
        assert exported["basics"][0]["label"] == []
        assert exported["basics"][0]["location"] == []

    def test_empty_string_preserved(self, fresh_db, tmp_path):
        """\"\" stays as \"\"."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "empty_string"},
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
            "education": [
                {
                    "institution": "University",
                    "location": "City",
                    "area": "Computer Science",
                    "studyType": "Bachelor",
                    "startDate": "2020-01-01",
                    "endDate": "2024-01-01",
                    "gpa": "",
                    "logo_url": "",
                    "type_key": [],
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

        importer = CVImporter(fresh_db)
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("empty_string", "en")

        edu = exported["education"][0]
        assert edu["gpa"] == ""
        assert edu["logo_url"] == ""

    def test_empty_skills_object(self, fresh_db, tmp_path):
        """{} stays as {} for skills."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "empty_skills"},
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
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("empty_skills", "en")

        assert exported["skills"] == {} or len(exported["skills"]) == 0


# ==============================================================================
# Type Preservation Tests
# ==============================================================================


class TestTypePreservation:
    """Tests for data type preservation."""

    def test_integer_stays_integer(self, fresh_db, tmp_path):
        """42 stays as 42, not \"42\"."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "int_test"},
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
            "publications": [
                {
                    "title": "Test Publication",
                    "type": "journal",
                    "year": 2023,
                    "month": 12,
                    "day": 25,
                }
            ],
            "references": [],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cv_data, f, indent=2)

        importer = CVImporter(fresh_db)
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("int_test", "en")

        pub = exported["publications"][0]
        assert pub["year"] == 2023
        assert isinstance(pub["year"], int)
        assert pub["month"] == 12
        assert isinstance(pub["month"], int)

    def test_float_stays_float(self, fresh_db, tmp_path):
        """8.5 stays as 8.5."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "float_test"},
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
            "languages": [
                {
                    "language": "English",
                    "proficiency": {"level": "Professional", "CEFR": "C1", "status": None},
                    "certifications": [
                        {
                            "test": "IELTS",
                            "organization": "British Council",
                            "overall": 7.5,
                            "reading": 8.0,
                            "writing": 7.0,
                            "listening": 8.5,
                            "speaking": 7.0,
                            "maxScore": 9.0,
                            "minScore": 0.0,
                            "examDate": None,
                            "URL": None,
                        }
                    ],
                }
            ],
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
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("float_test", "en")

        cert = exported["languages"][0]["certifications"][0]
        assert cert["overall"] == 7.5
        assert cert["listening"] == 8.5

    def test_boolean_stays_boolean(self, fresh_db, tmp_path):
        """true stays as true, not \"true\"."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "bool_test"},
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
            "workshop_and_certifications": [
                {
                    "issuer": "Test Issuer",
                    "certifications": [
                        {
                            "name": "With Certificate",
                            "date": "2023-01-01",
                            "duration": "10h",
                            "certificate": True,
                            "URL": None,
                        },
                        {
                            "name": "Without Certificate",
                            "date": "2023-02-01",
                            "duration": "5h",
                            "certificate": False,
                            "URL": None,
                        },
                    ],
                }
            ],
            "skills": {},
            "experiences": [],
            "projects": [],
            "publications": [],
            "references": [],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cv_data, f, indent=2)

        importer = CVImporter(fresh_db)
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("bool_test", "en")

        certs = exported["workshop_and_certifications"][0]["certifications"]
        assert certs[0]["certificate"] is True
        assert certs[1]["certificate"] is False


# ==============================================================================
# Unicode Handling Tests
# ==============================================================================


class TestUnicodeHandling:
    """Tests for Unicode content."""

    def test_persian_text_preserved(self, fresh_db, tmp_path):
        """Persian characters survive round-trip."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "fa", "ID": "persian_test"},
            "basics": [
                {
                    "fname": "رامین",
                    "lname": "یزدانی",
                    "label": ["مهندس نرم‌افزار", "توسعه‌دهنده"],
                    "email": "test@example.com",
                    "phone": {"countryCode": None, "number": None, "formatted": None},
                    "birthDate": None,
                    "summary": "خلاصه‌ای به زبان فارسی با نویسه‌های یونیکد مختلف: ‌آ، ﷽",
                    "location": [
                        {
                            "address": "خیابان ولیعصر",
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
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("persian_test", "fa")

        basics = exported["basics"][0]
        assert basics["fname"] == "رامین"
        assert basics["lname"] == "یزدانی"
        assert "مهندس" in basics["label"][0]
        assert basics["location"][0]["city"] == "تهران"

    def test_german_umlauts_preserved(self, fresh_db, tmp_path):
        """ä, ö, ü survive round-trip."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "de", "ID": "german_test"},
            "basics": [
                {
                    "fname": "Müller",
                    "lname": "Schäfer",
                    "label": ["Softwareentwickler", "Fähigkeiten"],
                    "email": "test@example.com",
                    "phone": {"countryCode": None, "number": None, "formatted": None},
                    "birthDate": None,
                    "summary": "Zusammenfassung mit Umlauten: äöüß ÄÖÜ",
                    "location": [
                        {
                            "address": "Königstraße 123",
                            "postalCode": "66121",
                            "city": "Saarbrücken",
                            "region": "Saarland",
                            "country": "Deutschland",
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
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("german_test", "de")

        basics = exported["basics"][0]
        assert basics["fname"] == "Müller"
        assert basics["lname"] == "Schäfer"
        assert "äöüß" in basics["summary"]

    def test_mixed_scripts_preserved(self, fresh_db, tmp_path):
        """Mixed Latin/Persian text."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "fa", "ID": "mixed_test"},
            "basics": [
                {
                    "fname": "رامین",
                    "lname": "Yazdani",
                    "label": ["Developer (توسعه‌دهنده)", "Python & R"],
                    "email": "test@example.com",
                    "phone": {"countryCode": None, "number": None, "formatted": None},
                    "birthDate": None,
                    "summary": "Mixed script: English text مخلوط با فارسی and symbols: → ← ↑ ↓",
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
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("mixed_test", "fa")

        basics = exported["basics"][0]
        assert basics["fname"] == "رامین"
        assert basics["lname"] == "Yazdani"
        assert "English text" in basics["summary"]
        assert "فارسی" in basics["summary"]


# ==============================================================================
# Large Content Tests
# ==============================================================================


class TestLargeContent:
    """Tests for large content handling."""

    def test_long_summary_preserved(self, fresh_db, tmp_path):
        """10KB summary text."""
        # Create ~10KB of text
        long_summary = "This is a paragraph of text. " * 400  # ~12KB

        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "long_summary"},
            "basics": [
                {
                    "fname": "Test",
                    "lname": "Person",
                    "label": [],
                    "email": "test@example.com",
                    "phone": {"countryCode": None, "number": None, "formatted": None},
                    "birthDate": None,
                    "summary": long_summary,
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
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("long_summary", "en")

        assert exported["basics"][0]["summary"] == long_summary

    def test_many_items_preserved(self, fresh_db, tmp_path):
        """50+ education items."""
        education = []
        for i in range(50):
            education.append({
                "institution": f"University {i+1}",
                "location": f"City {i+1}",
                "area": f"Area {i+1}",
                "studyType": "Bachelor",
                "startDate": f"20{i:02d}-01-01",
                "endDate": f"20{i+4:02d}-01-01",
                "gpa": "",
                "logo_url": "",
                "type_key": [],
            })

        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "many_items"},
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
            "education": education,
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
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("many_items", "en")

        assert len(exported["education"]) == 50
        assert exported["education"][0]["institution"] == "University 1"
        assert exported["education"][49]["institution"] == "University 50"

    def test_deep_skills_tree(self, fresh_db, tmp_path):
        """10 categories, 50 subcategories."""
        skills = {}
        for cat_i in range(10):
            cat_name = f"Category {cat_i + 1}"
            skills[cat_name] = {}
            for subcat_i in range(5):
                subcat_name = f"Subcategory {cat_i + 1}.{subcat_i + 1}"
                skills[cat_name][subcat_name] = [
                    {"long_name": f"Skill {j+1}", "short_name": f"S{j+1}"}
                    for j in range(3)
                ]

        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "deep_skills"},
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
            "skills": skills,
            "experiences": [],
            "projects": [],
            "publications": [],
            "references": [],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cv_data, f, indent=2)

        importer = CVImporter(fresh_db)
        result = importer.import_file(json_path)
        assert result.success
        assert result.stats["skill_categories"] == 10
        assert result.stats["skill_subcategories"] == 50
        assert result.stats["skill_items"] == 150

        exporter = CVExporter(fresh_db)
        exported = exporter.export("deep_skills", "en")

        assert len(exported["skills"]) == 10
        for cat_name in exported["skills"]:
            assert len(exported["skills"][cat_name]) == 5


# ==============================================================================
# Special Character Tests
# ==============================================================================


class TestSpecialCharacters:
    """Tests for special characters in content."""

    def test_html_entities_preserved(self, fresh_db, tmp_path):
        """HTML-like content preserved."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "html_test"},
            "basics": [
                {
                    "fname": "Test",
                    "lname": "Person",
                    "label": [],
                    "email": "test@example.com",
                    "phone": {"countryCode": None, "number": None, "formatted": None},
                    "birthDate": None,
                    "summary": "Contains <b>HTML</b> & special chars: 'quotes' \"double\" ©®™",
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
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("html_test", "en")

        summary = exported["basics"][0]["summary"]
        assert "<b>HTML</b>" in summary
        assert "&" in summary
        assert "©®™" in summary

    def test_latex_content_preserved(self, fresh_db, tmp_path):
        """LaTeX-like content preserved."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "latex_test"},
            "basics": [
                {
                    "fname": "Test",
                    "lname": "Person",
                    "label": [],
                    "email": "test@example.com",
                    "phone": {"countryCode": None, "number": None, "formatted": None},
                    "birthDate": None,
                    "summary": "LaTeX: $E = mc^2$, \\textbf{bold}, \\textit{italic}, {braces}",
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
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("latex_test", "en")

        summary = exported["basics"][0]["summary"]
        assert "$E = mc^2$" in summary
        assert "\\textbf" in summary
        assert "{braces}" in summary
