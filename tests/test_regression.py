"""
Regression tests for known issues and fixed bugs.

These tests ensure that previously identified and fixed issues
do not reoccur in future updates.
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
    db_path = tmp_path / "test_regression.db"
    init_db_v2(db_path, force=True)
    return db_path


# ==============================================================================
# Known Issues Regression Tests
# ==============================================================================


class TestKnownIssues:
    """Tests for previously reported issues."""

    def test_issue_pictures_lowercase(self, fresh_db, tmp_path):
        """
        Regression: Export used 'pictures' instead of 'Pictures'.

        The JSON schema uses 'Pictures' (capital P) and LaTeX templates
        expect this exact casing. Export must preserve the capital P.
        """
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "pictures_case"},
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
        importer.import_file(json_path)

        exporter = CVExporter(fresh_db)
        exported = exporter.export("pictures_case", "en")

        # Must be 'Pictures' not 'pictures'
        assert "Pictures" in exported["basics"][0]
        assert "pictures" not in exported["basics"][0]

    def test_issue_phone_flattened(self, fresh_db, tmp_path):
        """
        Regression: Phone exported as flat fields, not nested object.

        Phone must be exported as:
        {"countryCode": "+1", "number": "123", "formatted": "+1 123"}

        Not as flat fields phone_country_code, phone_number.
        """
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "phone_nested"},
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
        importer.import_file(json_path)

        exporter = CVExporter(fresh_db)
        exported = exporter.export("phone_nested", "en")

        phone = exported["basics"][0]["phone"]

        # Must be nested object
        assert isinstance(phone, dict)
        assert phone["countryCode"] == "+49"
        assert phone["number"] == "17612345678"
        assert phone["formatted"] == "+49 176 12345678"

        # Must NOT have flat fields
        assert "phone_country_code" not in exported["basics"][0]
        assert "phone_number" not in exported["basics"][0]

    def test_issue_skills_order_scrambled(self, fresh_db, tmp_path):
        """
        Regression: Skills items exported in wrong order.

        Skills items must maintain their original array order,
        as defined by sort_order columns in the database.
        """
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "skills_order"},
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
                "Category": {
                    "Subcategory": [
                        {"long_name": "Alpha", "short_name": "A"},
                        {"long_name": "Beta", "short_name": "B"},
                        {"long_name": "Gamma", "short_name": "G"},
                        {"long_name": "Delta", "short_name": "D"},
                        {"long_name": "Epsilon", "short_name": "E"},
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
        importer.import_file(json_path)

        exporter = CVExporter(fresh_db)
        exported = exporter.export("skills_order", "en")

        items = exported["skills"]["Category"]["Subcategory"]

        # Must be in original order: Alpha, Beta, Gamma, Delta, Epsilon
        assert items[0]["long_name"] == "Alpha"
        assert items[1]["long_name"] == "Beta"
        assert items[2]["long_name"] == "Gamma"
        assert items[3]["long_name"] == "Delta"
        assert items[4]["long_name"] == "Epsilon"

    def test_issue_education_order_preserved(self, fresh_db, tmp_path):
        """
        Regression: Education items exported in wrong order.

        Education items must maintain their original order.
        """
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "edu_order"},
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
                    "institution": "First University",
                    "location": "City 1",
                    "area": "Area 1",
                    "studyType": "PhD",
                    "startDate": "2022-01-01",
                    "endDate": "present",
                    "gpa": "",
                    "logo_url": "",
                    "type_key": [],
                },
                {
                    "institution": "Second University",
                    "location": "City 2",
                    "area": "Area 2",
                    "studyType": "Master",
                    "startDate": "2019-01-01",
                    "endDate": "2021-12-31",
                    "gpa": "",
                    "logo_url": "",
                    "type_key": [],
                },
                {
                    "institution": "Third University",
                    "location": "City 3",
                    "area": "Area 3",
                    "studyType": "Bachelor",
                    "startDate": "2015-01-01",
                    "endDate": "2018-12-31",
                    "gpa": "",
                    "logo_url": "",
                    "type_key": [],
                },
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
        importer.import_file(json_path)

        exporter = CVExporter(fresh_db)
        exported = exporter.export("edu_order", "en")

        edu = exported["education"]
        assert len(edu) == 3
        assert edu[0]["institution"] == "First University"
        assert edu[1]["institution"] == "Second University"
        assert edu[2]["institution"] == "Third University"

    def test_issue_section_order_correct(self, fresh_db, tmp_path):
        """
        Regression: Sections in exported JSON were in wrong order.

        Sections must appear in the order:
        config, basics, profiles, education, languages,
        workshop_and_certifications, skills, experiences,
        projects, publications, references
        """
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "section_order"},
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
        importer.import_file(json_path)

        exporter = CVExporter(fresh_db)
        exported = exporter.export("section_order", "en")

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

        actual_keys = list(exported.keys())
        assert actual_keys == expected_order


# ==============================================================================
# Multi-Language Regression Tests
# ==============================================================================


class TestMultiLanguageRegression:
    """Regression tests for multi-language issues."""

    def test_issue_variants_linked_by_resume_key(self, fresh_db, tmp_path):
        """
        Regression: Language variants not correctly linked.

        All language variants for the same person must share
        the same resume_key via their config.ID field.
        """
        # Create English variant
        en_path = tmp_path / "person_en.json"
        en_data = {
            "config": {"lang": "en", "ID": "same_person"},
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

        # Create German variant with same ID
        de_path = tmp_path / "person_de.json"
        de_data = {
            "config": {"lang": "de", "ID": "same_person"},
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

        importer = CVImporter(fresh_db)
        importer.import_file(en_path)
        importer.import_file(de_path)

        # Verify both linked to same resume_key
        conn = sqlite3.connect(fresh_db)
        try:
            cursor = conn.cursor()

            # One resume_set
            cursor.execute("SELECT COUNT(*) FROM resume_sets")
            assert cursor.fetchone()[0] == 1

            # One person
            cursor.execute("SELECT COUNT(*) FROM persons")
            assert cursor.fetchone()[0] == 1

            # Two versions
            cursor.execute("SELECT lang_code FROM resume_versions WHERE resume_key = ?",
                          ("same_person",))
            langs = [row[0] for row in cursor.fetchall()]
            assert "en" in langs
            assert "de" in langs

        finally:
            conn.close()

    def test_issue_i18n_fields_per_language(self, fresh_db, tmp_path):
        """
        Regression: Translatable fields not correctly separated by language.

        Each language variant must have its own i18n data.
        """
        # Create English variant
        en_path = tmp_path / "person_en.json"
        en_data = {
            "config": {"lang": "en", "ID": "i18n_test"},
            "basics": [
                {
                    "fname": "John",
                    "lname": "Doe",
                    "label": [],
                    "email": "test@example.com",
                    "phone": {"countryCode": None, "number": None, "formatted": None},
                    "birthDate": None,
                    "summary": "English summary text",
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

        # Create German variant
        de_path = tmp_path / "person_de.json"
        de_data = {
            "config": {"lang": "de", "ID": "i18n_test"},
            "basics": [
                {
                    "fname": "Johann",
                    "lname": "Muster",
                    "label": [],
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

        importer = CVImporter(fresh_db)
        importer.import_file(en_path)
        importer.import_file(de_path)

        exporter = CVExporter(fresh_db)

        # English export must have English content
        en_export = exporter.export("i18n_test", "en")
        assert en_export["basics"][0]["fname"] == "John"
        assert en_export["basics"][0]["summary"] == "English summary text"

        # German export must have German content
        de_export = exporter.export("i18n_test", "de")
        assert de_export["basics"][0]["fname"] == "Johann"
        assert de_export["basics"][0]["summary"] == "Deutsche Zusammenfassung"


# ==============================================================================
# Tag System Regression Tests
# ==============================================================================


class TestTagSystemRegression:
    """Regression tests for the tag system."""

    def test_issue_tag_case_normalization(self, fresh_db, tmp_path):
        """
        Regression: Tags with different cases created duplicates.

        'Full CV' and 'full cv' must map to the same tag_code.
        """
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "tag_case"},
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
                    "institution": "Uni 1",
                    "location": "City",
                    "area": "Area",
                    "studyType": "Bachelor",
                    "startDate": "2020-01-01",
                    "endDate": "2024-01-01",
                    "gpa": "",
                    "logo_url": "",
                    "type_key": ["Full CV"],
                },
                {
                    "institution": "Uni 2",
                    "location": "City",
                    "area": "Area",
                    "studyType": "Master",
                    "startDate": "2024-01-01",
                    "endDate": "present",
                    "gpa": "",
                    "logo_url": "",
                    "type_key": ["full cv"],
                },
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
        importer.import_file(json_path)

        # Verify only one tag_code created
        conn = sqlite3.connect(fresh_db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT code FROM tag_codes WHERE code LIKE 'full%'")
            rows = cursor.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == "full_cv"
        finally:
            conn.close()


# ==============================================================================
# Import/Export Cycle Regression Tests
# ==============================================================================


class TestImportExportCycleRegression:
    """Regression tests for import/export cycles."""

    def test_issue_reimport_no_duplicates(self, fresh_db, tmp_path):
        """
        Regression: Re-importing same file created duplicate records.

        Re-importing the same file should not create duplicate records.
        """
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "reimport_test"},
            "basics": [
                {
                    "fname": "Test",
                    "lname": "Person",
                    "label": ["Developer"],
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
                    "area": "CS",
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

        # Import twice
        importer.import_file(json_path)
        importer.import_file(json_path)

        # Verify no duplicates
        conn = sqlite3.connect(fresh_db)
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM resume_sets")
            assert cursor.fetchone()[0] == 1

            cursor.execute("SELECT COUNT(*) FROM resume_versions")
            assert cursor.fetchone()[0] == 1

            cursor.execute("SELECT COUNT(*) FROM persons")
            assert cursor.fetchone()[0] == 1

            cursor.execute("SELECT COUNT(*) FROM education_items")
            assert cursor.fetchone()[0] == 1

        finally:
            conn.close()

    def test_issue_present_enddate_preserved(self, fresh_db, tmp_path):
        """
        Regression: 'present' end date converted to null.

        The string 'present' for end dates must survive round-trip.
        """
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "present_test"},
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
                    "institution": "Current University",
                    "location": "City",
                    "area": "CS",
                    "studyType": "PhD",
                    "startDate": "2024-01-01",
                    "endDate": "present",
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
        importer.import_file(json_path)

        exporter = CVExporter(fresh_db)
        exported = exporter.export("present_test", "en")

        assert exported["education"][0]["endDate"] == "present"
