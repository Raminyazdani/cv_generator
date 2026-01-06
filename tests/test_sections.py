"""
Section-specific tests for CV import/export.

Tests each CV section ensuring correct import/export handling:
- Basics section (phone, location, pictures, labels)
- Skills section (3-level nesting)
- Certifications section (issuer grouping)
- Publications section (complex structure with authors)
- Languages section (proficiency, certifications)
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
    db_path = tmp_path / "test_sections.db"
    init_db_v2(db_path, force=True)
    return db_path


# ==============================================================================
# Basics Section Tests
# ==============================================================================


class TestBasicsSection:
    """Tests for basics section handling."""

    def test_basics_phone_nested_structure(self, fresh_db, tmp_path):
        """Phone object with countryCode, number, formatted."""
        json_path = tmp_path / "test.json"
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
        result = importer.import_file(json_path)
        assert result.success

        # Verify phone is stored correctly
        conn = sqlite3.connect(fresh_db)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT phone_country_code, phone_number, phone_formatted FROM persons"
            )
            row = cursor.fetchone()
            assert row[0] == "+49"
            assert row[1] == "17612345678"
            assert row[2] == "+49 176 12345678"
        finally:
            conn.close()

        # Verify phone is exported as nested object
        exporter = CVExporter(fresh_db)
        exported = exporter.export("phone_test", "en")

        phone = exported["basics"][0]["phone"]
        assert isinstance(phone, dict)
        assert phone["countryCode"] == "+49"
        assert phone["number"] == "17612345678"
        assert phone["formatted"] == "+49 176 12345678"

    def test_basics_location_array(self, fresh_db, tmp_path):
        """Multiple locations array."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "location_test"},
            "basics": [
                {
                    "fname": "Test",
                    "lname": "Person",
                    "label": [],
                    "email": "test@example.com",
                    "phone": {"countryCode": None, "number": None, "formatted": None},
                    "birthDate": None,
                    "summary": None,
                    "location": [
                        {
                            "address": "123 Main St",
                            "postalCode": "12345",
                            "city": "Berlin",
                            "region": "Berlin",
                            "country": "Germany",
                        },
                        {
                            "address": "456 Oak Ave",
                            "postalCode": "67890",
                            "city": "Munich",
                            "region": "Bavaria",
                            "country": "Germany",
                        },
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
            json.dump(cv_data, f, indent=2)

        importer = CVImporter(fresh_db)
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("location_test", "en")

        locations = exported["basics"][0]["location"]
        assert len(locations) == 2
        assert locations[0]["city"] == "Berlin"
        assert locations[1]["city"] == "Munich"

    def test_basics_pictures_capitalization(self, fresh_db, tmp_path):
        """Pictures key must be capitalized."""
        json_path = tmp_path / "test.json"
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
                        {"type_of": "profile", "URL": "https://example.com/profile.jpg"},
                        {"type_of": "cover", "URL": "https://example.com/cover.jpg"},
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
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("pictures_test", "en")

        # Verify capital P in Pictures
        assert "Pictures" in exported["basics"][0]
        assert "pictures" not in exported["basics"][0]

        pictures = exported["basics"][0]["Pictures"]
        assert len(pictures) == 2
        assert pictures[0]["type_of"] == "profile"
        assert pictures[1]["type_of"] == "cover"

    def test_basics_labels_array(self, fresh_db, tmp_path):
        """Label array handling."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "labels_test"},
            "basics": [
                {
                    "fname": "Test",
                    "lname": "Person",
                    "label": ["Developer", "Data Scientist", "Engineer"],
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
        exported = exporter.export("labels_test", "en")

        labels = exported["basics"][0]["label"]
        assert len(labels) == 3
        assert labels[0] == "Developer"
        assert labels[1] == "Data Scientist"
        assert labels[2] == "Engineer"


# ==============================================================================
# Skills Section Tests
# ==============================================================================


class TestSkillsSection:
    """Tests for skills nested structure."""

    def test_skills_three_level_nesting(self, fresh_db, tmp_path):
        """Category > Subcategory > Items structure."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "skills_test"},
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
                        {"long_name": "Python", "short_name": "Python"},
                        {"long_name": "JavaScript", "short_name": "JS"},
                    ],
                    "Frameworks": [
                        {"long_name": "Flask", "short_name": "Flask"},
                        {"long_name": "React", "short_name": "React"},
                    ],
                },
                "Data Science": {
                    "Tools": [
                        {"long_name": "Pandas", "short_name": "Pandas"},
                    ],
                },
            },
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
        assert result.stats["skill_categories"] == 2
        assert result.stats["skill_subcategories"] == 3
        assert result.stats["skill_items"] == 5

        exporter = CVExporter(fresh_db)
        exported = exporter.export("skills_test", "en")

        skills = exported["skills"]
        assert "Programming" in skills
        assert "Languages" in skills["Programming"]
        assert len(skills["Programming"]["Languages"]) == 2

    def test_skills_order_preserved(self, fresh_db, tmp_path):
        """Item order matches original."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "order_test"},
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
                        {"long_name": "First", "short_name": "1st"},
                        {"long_name": "Second", "short_name": "2nd"},
                        {"long_name": "Third", "short_name": "3rd"},
                        {"long_name": "Fourth", "short_name": "4th"},
                        {"long_name": "Fifth", "short_name": "5th"},
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
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("order_test", "en")

        items = exported["skills"]["Category"]["Subcategory"]
        assert items[0]["long_name"] == "First"
        assert items[1]["long_name"] == "Second"
        assert items[2]["long_name"] == "Third"
        assert items[3]["long_name"] == "Fourth"
        assert items[4]["long_name"] == "Fifth"

    def test_skills_tags_per_item(self, fresh_db, tmp_path):
        """type_key arrays on items."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "tags_test"},
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
                        {
                            "long_name": "Python",
                            "short_name": "Python",
                            "type_key": ["Full CV", "Programming"],
                        },
                        {
                            "long_name": "SQL",
                            "short_name": "SQL",
                            "type_key": ["Full CV"],
                        },
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
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("tags_test", "en")

        items = exported["skills"]["Category"]["Subcategory"]
        # Note: type_key order may differ due to set semantics in tags
        assert "type_key" in items[0]
        assert len(items[0]["type_key"]) == 2


# ==============================================================================
# Certifications Section Tests
# ==============================================================================


class TestCertificationsSection:
    """Tests for workshop_and_certifications."""

    def test_certs_grouped_by_issuer(self, fresh_db, tmp_path):
        """Issuer grouping structure."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "certs_test"},
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
                    "issuer": "Coursera",
                    "certifications": [
                        {
                            "name": "Machine Learning",
                            "date": "2023-01-15",
                            "duration": "40 hours",
                            "certificate": True,
                            "URL": "https://example.com/cert1",
                        }
                    ],
                },
                {
                    "issuer": "Udemy",
                    "certifications": [
                        {
                            "name": "Python Masterclass",
                            "date": "2023-06-20",
                            "duration": "60 hours",
                            "certificate": True,
                            "URL": "https://example.com/cert2",
                        }
                    ],
                },
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
        exported = exporter.export("certs_test", "en")

        certs = exported["workshop_and_certifications"]
        assert len(certs) == 2
        assert certs[0]["issuer"] == "Coursera"
        assert certs[1]["issuer"] == "Udemy"

    def test_certs_nested_certifications(self, fresh_db, tmp_path):
        """Certifications array under issuer."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "nested_certs"},
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
                    "issuer": "Training Institute",
                    "certifications": [
                        {
                            "name": "Course A",
                            "date": "2023-01-01",
                            "duration": "10 hours",
                            "certificate": True,
                            "URL": None,
                        },
                        {
                            "name": "Course B",
                            "date": "2023-02-01",
                            "duration": "20 hours",
                            "certificate": False,
                            "URL": None,
                        },
                        {
                            "name": "Course C",
                            "date": "2023-03-01",
                            "duration": "30 hours",
                            "certificate": True,
                            "URL": "https://example.com/c",
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
        exported = exporter.export("nested_certs", "en")

        issuer = exported["workshop_and_certifications"][0]
        assert len(issuer["certifications"]) == 3
        assert issuer["certifications"][0]["name"] == "Course A"
        assert issuer["certifications"][1]["certificate"] is False


# ==============================================================================
# Publications Section Tests
# ==============================================================================


class TestPublicationsSection:
    """Tests for publications with complex structure."""

    def test_publications_authors_array(self, fresh_db, tmp_path):
        """Authors as array of strings."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "pub_test"},
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
                    "authors": ["Author One", "Author Two", "Author Three"],
                    "authors_structured": [
                        {"literal": "Author One"},
                        {"literal": "Author Two"},
                        {"literal": "Author Three"},
                    ],
                    "type": "journal",
                    "status": "published",
                    "year": 2023,
                    "journal": "Test Journal",
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
        exported = exporter.export("pub_test", "en")

        pub = exported["publications"][0]
        assert len(pub["authors"]) == 3
        assert pub["authors"][0] == "Author One"

    def test_publications_identifiers(self, fresh_db, tmp_path):
        """DOI, ISBN, ISSN fields."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "id_test"},
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
                    "title": "Publication with IDs",
                    "type": "journal",
                    "doi": "10.1234/test.doi",
                    "isbn": "978-3-16-148410-0",
                    "issn": "1234-5678",
                    "identifiers": {
                        "doi": "10.1234/test.doi",
                        "isbn": "978-3-16-148410-0",
                        "issn": "1234-5678",
                        "pmid": None,
                        "pmcid": None,
                        "arxiv": None,
                    },
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
        exported = exporter.export("id_test", "en")

        pub = exported["publications"][0]
        assert pub["doi"] == "10.1234/test.doi"
        assert "identifiers" in pub


# ==============================================================================
# Languages Section Tests
# ==============================================================================


class TestLanguagesSection:
    """Tests for spoken languages with certifications."""

    def test_languages_proficiency_nested(self, fresh_db, tmp_path):
        """Proficiency object structure."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "lang_test"},
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
                    "proficiency": {
                        "level": "Professional",
                        "CEFR": "C1",
                        "status": "Fluent",
                    },
                    "certifications": [],
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
        exported = exporter.export("lang_test", "en")

        lang = exported["languages"][0]
        assert lang["language"] == "English"
        assert isinstance(lang["proficiency"], dict)
        assert lang["proficiency"]["level"] == "Professional"
        assert lang["proficiency"]["CEFR"] == "C1"

    def test_languages_certifications_nested(self, fresh_db, tmp_path):
        """Certifications array with scores."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "cert_lang_test"},
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
                    "proficiency": {
                        "level": "Professional",
                        "CEFR": "C1",
                        "status": "Certified",
                    },
                    "certifications": [
                        {
                            "test": "IELTS Academic",
                            "organization": "British Council",
                            "overall": 7.5,
                            "reading": 8.0,
                            "writing": 7.0,
                            "listening": 8.0,
                            "speaking": 7.0,
                            "maxScore": 9.0,
                            "minScore": 0.0,
                            "examDate": "2023-05-15",
                            "URL": "https://example.com/cert",
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
        exported = exporter.export("cert_lang_test", "en")

        cert = exported["languages"][0]["certifications"][0]
        assert cert["test"] == "IELTS Academic"
        assert cert["overall"] == 7.5
        assert cert["reading"] == 8.0
        assert cert["maxScore"] == 9.0


# ==============================================================================
# Education Section Tests
# ==============================================================================


class TestEducationSection:
    """Tests for education section handling."""

    def test_education_with_present_enddate(self, fresh_db, tmp_path):
        """Education with 'present' end date."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "edu_present"},
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
                    "location": "Test City",
                    "area": "Computer Science",
                    "studyType": "Master",
                    "startDate": "2023-10-01",
                    "endDate": "present",
                    "gpa": "",
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

        importer = CVImporter(fresh_db)
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("edu_present", "en")

        edu = exported["education"][0]
        assert edu["endDate"] == "present"

    def test_education_with_tags(self, fresh_db, tmp_path):
        """Education items with type_key tags."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "edu_tags"},
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
                    "institution": "University A",
                    "location": "City A",
                    "area": "Computer Science",
                    "studyType": "Bachelor",
                    "startDate": "2018-09-01",
                    "endDate": "2022-06-15",
                    "gpa": "3.8",
                    "logo_url": "",
                    "type_key": ["Full CV", "Academic", "Programming"],
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
        exported = exporter.export("edu_tags", "en")

        edu = exported["education"][0]
        assert "type_key" in edu
        assert len(edu["type_key"]) == 3


# ==============================================================================
# Experiences Section Tests
# ==============================================================================


class TestExperiencesSection:
    """Tests for experiences section handling."""

    def test_experiences_with_duration(self, fresh_db, tmp_path):
        """Experience with duration text."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "exp_test"},
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
            "experiences": [
                {
                    "role": "Software Developer",
                    "institution": "Tech Company",
                    "duration": "2022-01 - present",
                    "primaryFocus": "Backend development",
                    "description": "Working on distributed systems.",
                }
            ],
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
        exported = exporter.export("exp_test", "en")

        exp = exported["experiences"][0]
        assert exp["role"] == "Software Developer"
        assert exp["duration"] == "2022-01 - present"
        assert exp["primaryFocus"] == "Backend development"


# ==============================================================================
# References Section Tests
# ==============================================================================


class TestReferencesSection:
    """Tests for references section handling."""

    def test_references_with_emails(self, fresh_db, tmp_path):
        """Reference with multiple email addresses."""
        json_path = tmp_path / "test.json"
        cv_data = {
            "config": {"lang": "en", "ID": "ref_test"},
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
            "references": [
                {
                    "name": "Dr. John Smith",
                    "position": "Professor",
                    "department": "Computer Science",
                    "institution": "University",
                    "location": "City, Country",
                    "email": ["john.smith@university.edu", "j.smith@personal.com"],
                    "phone": "+1 234 567 8901",
                    "URL": "https://university.edu/jsmith",
                }
            ],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cv_data, f, indent=2)

        importer = CVImporter(fresh_db)
        result = importer.import_file(json_path)
        assert result.success

        exporter = CVExporter(fresh_db)
        exported = exporter.export("ref_test", "en")

        ref = exported["references"][0]
        assert ref["name"] == "Dr. John Smith"
        assert isinstance(ref["email"], list)
        assert len(ref["email"]) == 2
