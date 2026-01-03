"""
Unit tests for cv_generator.io module.

Tests CV file discovery, JSON loading, and language map loading.
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
    load_lang_map,
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
        """Test parsing filename with underscore in the name."""
        base_name, lang = parse_cv_filename("john_doe.json")
        # This should treat "doe" as a language code (2-3 letters)
        assert base_name == "john"
        assert lang == "doe"


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


class TestLoadLangMap:
    """Tests for load_lang_map function."""

    def test_load_lang_map(self, tmp_path):
        """Test loading language map."""
        lang_data = {
            "education": {"en": "Education", "de": "Ausbildung"},
            "skills": {"en": "Skills", "de": "Fähigkeiten"}
        }
        lang_file = tmp_path / "lang.json"
        lang_file.write_text(json.dumps(lang_data))

        loaded = load_lang_map(tmp_path)

        assert loaded == lang_data

    def test_load_lang_map_missing(self, tmp_path):
        """Test that missing lang.json raises error."""
        with pytest.raises(ConfigurationError):
            load_lang_map(tmp_path)
