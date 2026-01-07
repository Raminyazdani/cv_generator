"""
Unit tests for cv_generator.io module.

Tests CV file discovery and JSON loading.
"""

import json
import tempfile
from pathlib import Path

import pytest

from cv_generator.errors import ConfigurationError, ValidationError

# Import with path setup from conftest
from cv_generator.io import (
    discover_cv_files,
    load_cv_json,
    parse_cv_filename,
    validate_cv_data,
)


class TestParseCVFilename:
    """Tests for parse_cv_filename function."""

    def test_simple_name(self):
        """Test parsing a simple filename without language suffix."""
        base_name, lang = parse_cv_filename("ramin.json")
        assert base_name == "ramin"
        assert lang == "en"

    def test_underscore_language(self):
        """Test parsing filename with underscore language suffix."""
        base_name, lang = parse_cv_filename("ramin_de.json")
        assert base_name == "ramin"
        assert lang == "de"

    def test_hyphen_language(self):
        """Test parsing filename with hyphen language suffix."""
        base_name, lang = parse_cv_filename("ramin-fa.json")
        assert base_name == "ramin"
        assert lang == "fa"

    def test_three_letter_language(self):
        """Test parsing filename with three-letter language code."""
        base_name, lang = parse_cv_filename("john_eng.json")
        assert base_name == "john"
        assert lang == "eng"

    def test_name_with_underscore(self):
        """Test parsing filename with underscore in the name.
        
        F-012 fix: 'doe' is not a valid ISO 639 language code,
        so 'john_doe' is treated as the full base name.
        """
        base_name, lang = parse_cv_filename("john_doe.json")
        # "doe" is NOT a valid language code, so full name is base_name
        assert base_name == "john_doe"
        assert lang == "en"

    def test_name_with_valid_language_suffix(self):
        """Test parsing filename with valid language suffix after underscore."""
        # "en" IS a valid language code
        base_name, lang = parse_cv_filename("john_doe_en.json")
        assert base_name == "john_doe"
        assert lang == "en"

        # "de" IS a valid language code
        base_name, lang = parse_cv_filename("john_doe_de.json")
        assert base_name == "john_doe"
        assert lang == "de"

    def test_invalid_suffix_treated_as_name(self):
        """Test that invalid language codes are treated as part of the name."""
        # "xyz" is not a valid ISO 639 code
        base_name, lang = parse_cv_filename("person_xyz.json")
        assert base_name == "person_xyz"
        assert lang == "en"


class TestDiscoverCVFiles:
    """Tests for discover_cv_files function."""

    def test_discover_files(self, tmp_path):
        """Test discovering CV files in a directory."""
        # Create test files
        (tmp_path / "person1.json").write_text('{}')
        (tmp_path / "person2.json").write_text('{}')
        (tmp_path / "readme.txt").write_text('')

        files = discover_cv_files(tmp_path)

        assert len(files) == 2
        assert all(f.suffix == ".json" for f in files)

    def test_discover_with_name_filter(self, tmp_path):
        """Test discovering CV files with name filter."""
        (tmp_path / "ramin.json").write_text('{}')
        (tmp_path / "ramin_de.json").write_text('{}')
        (tmp_path / "mahsa.json").write_text('{}')

        files = discover_cv_files(tmp_path, name_filter="ramin")

        assert len(files) == 2
        names = [f.stem for f in files]
        assert "ramin" in names
        assert "ramin_de" in names

    def test_discover_nonexistent_directory(self, tmp_path):
        """Test that discovering in nonexistent directory raises error."""
        with pytest.raises(ConfigurationError):
            discover_cv_files(tmp_path / "nonexistent")


class TestLoadCVJson:
    """Tests for load_cv_json function."""

    def test_load_valid_json(self, tmp_path):
        """Test loading valid JSON file."""
        data = {"basics": [{"fname": "Test", "lname": "User"}]}
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(data))

        loaded = load_cv_json(json_file)

        assert loaded == data

    def test_load_invalid_json(self, tmp_path):
        """Test that loading invalid JSON raises error."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("{invalid json")

        with pytest.raises(ValidationError):
            load_cv_json(json_file)

    def test_load_nonexistent_file(self, tmp_path):
        """Test that loading nonexistent file raises error."""
        with pytest.raises(ConfigurationError):
            load_cv_json(tmp_path / "nonexistent.json")


class TestValidateCVData:
    """Tests for validate_cv_data function."""

    def test_valid_cv_data(self):
        """Test validating CV data with required fields."""
        data = {"basics": [{"fname": "Test", "lname": "User"}]}
        assert validate_cv_data(data, "test.json") is True

    def test_missing_basics(self):
        """Test that CV without basics is invalid."""
        data = {"education": []}
        assert validate_cv_data(data, "test.json") is False

    def test_basics_not_list(self):
        """Test that CV with non-list basics is invalid (F-013)."""
        data = {"basics": {"fname": "Test"}}  # dict instead of list
        assert validate_cv_data(data, "test.json") is False

    def test_empty_basics(self):
        """Test that CV with empty basics list is invalid (F-013)."""
        data = {"basics": []}
        assert validate_cv_data(data, "test.json") is False

    def test_invalid_top_level_type(self):
        """Test that non-dict CV data is invalid (F-013)."""
        data = [{"basics": [{"fname": "Test"}]}]  # list instead of dict
        assert validate_cv_data(data, "test.json") is False

    def test_list_section_not_list(self):
        """Test that list sections must be lists (F-013)."""
        data = {
            "basics": [{"fname": "Test"}],
            "education": {"school": "Test"}  # dict instead of list
        }
        assert validate_cv_data(data, "test.json") is False

    def test_skills_must_be_dict(self):
        """Test that skills section must be a dict (F-013)."""
        data = {
            "basics": [{"fname": "Test"}],
            "skills": ["Python", "JavaScript"]  # list instead of dict
        }
        assert validate_cv_data(data, "test.json") is False

    def test_valid_complete_cv(self):
        """Test validation of a complete valid CV structure (F-013)."""
        data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "education": [{"institution": "University"}],
            "experiences": [{"role": "Developer"}],
            "skills": {"Technical": {"Programming": []}},
            "languages": [],
            "projects": []
        }
        assert validate_cv_data(data, "test.json") is True


class TestIsValidLanguageCode:
    """Tests for is_valid_language_code function (F-012)."""

    def test_valid_two_letter_codes(self):
        """Test valid ISO 639-1 two-letter codes."""
        from cv_generator.io import is_valid_language_code

        assert is_valid_language_code("en") is True
        assert is_valid_language_code("de") is True
        assert is_valid_language_code("fr") is True
        assert is_valid_language_code("fa") is True  # Persian
        assert is_valid_language_code("ar") is True  # Arabic

    def test_valid_three_letter_codes(self):
        """Test valid ISO 639-2 three-letter codes."""
        from cv_generator.io import is_valid_language_code

        assert is_valid_language_code("eng") is True
        assert is_valid_language_code("deu") is True
        assert is_valid_language_code("fra") is True

    def test_invalid_codes(self):
        """Test that invalid codes are rejected."""
        from cv_generator.io import is_valid_language_code

        assert is_valid_language_code("doe") is False  # not a lang code
        assert is_valid_language_code("xyz") is False
        assert is_valid_language_code("ab") is False  # not in list
        assert is_valid_language_code("abcd") is False  # 4 letters
        assert is_valid_language_code("") is False
        assert is_valid_language_code("1") is False

