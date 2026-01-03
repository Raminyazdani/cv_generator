#!/usr/bin/env python3
"""
Unit tests for cv_generator.lang_engine.translate_cv_keys

Tests key translation, language detection, collision handling, and skills special handling.
"""

import json
import tempfile
from pathlib import Path

import pytest

from cv_generator.lang_engine.translate_cv_keys import (
    detect_language_from_filename,
    load_lang_map,
    process_cv_file,
    translate_cv,
    translate_dict_keys,
    translate_key,
)

# ============================================================================
# Tests for language detection
# ============================================================================

def test_detect_language_with_hyphen():
    """Test language detection from filename with hyphen separator."""
    assert detect_language_from_filename("ramin-de.json") == "de"
    assert detect_language_from_filename("cv-fa.json") == "fa"
    assert detect_language_from_filename("resume-en.json") == "en"


def test_detect_language_with_underscore():
    """Test language detection from filename with underscore separator."""
    assert detect_language_from_filename("ramin_de.json") == "de"
    assert detect_language_from_filename("cv_fa.json") == "fa"
    assert detect_language_from_filename("resume_en.json") == "en"


def test_detect_language_default():
    """Test that default language is 'en' when no suffix found."""
    assert detect_language_from_filename("ramin.json") == "en"
    assert detect_language_from_filename("cv.json") == "en"
    assert detect_language_from_filename("myresume.json") == "en"


def test_detect_language_three_char_codes():
    """Test detection of 3-character language codes."""
    assert detect_language_from_filename("ramin-deu.json") == "deu"
    assert detect_language_from_filename("cv_fas.json") == "fas"


def test_detect_language_case_insensitive():
    """Test that language detection is case-insensitive."""
    assert detect_language_from_filename("ramin-DE.json") == "de"
    assert detect_language_from_filename("cv_FA.json") == "fa"


# ============================================================================
# Tests for key translation
# ============================================================================

def test_translate_key_with_mapping():
    """Test key translation when mapping exists."""
    lang_map = {
        "education": {"en": "Education", "de": "Ausbildung", "fa": "تحصیلات"},
        "fname": {"en": "First Name", "de": "Vorname", "fa": "نام"},
    }

    assert translate_key("education", "de", lang_map) == "Ausbildung"
    assert translate_key("education", "en", lang_map) == "Education"
    assert translate_key("fname", "de", lang_map) == "Vorname"


def test_translate_key_no_mapping():
    """Test that key is preserved when no mapping exists."""
    lang_map = {
        "education": {"en": "Education", "de": "Ausbildung"},
    }

    # Key not in map at all
    assert translate_key("unknown_key", "de", lang_map) == "unknown_key"


def test_translate_key_empty_translation():
    """Test that key is preserved when translation is empty."""
    lang_map = {
        "education": {"en": "", "de": "Ausbildung"},
    }

    # Translation is empty for 'en'
    assert translate_key("education", "en", lang_map) == "education"
    # But not for 'de'
    assert translate_key("education", "de", lang_map) == "Ausbildung"


def test_translate_key_missing_language():
    """Test that key is preserved when language not in mapping."""
    lang_map = {
        "education": {"en": "Education", "de": "Ausbildung"},
    }

    # Italian not in mapping
    assert translate_key("education", "it", lang_map) == "education"


# ============================================================================
# Tests for CV translation
# ============================================================================

def test_translate_cv_simple():
    """Test translation of a simple CV structure."""
    cv_data = {
        "education": [
            {"institution": "Test University"}
        ],
        "experiences": []
    }

    lang_map = {
        "education": {"de": "Ausbildung"},
        "institution": {"de": "Institution"},
        "experiences": {"de": "Berufserfahrung"},
    }

    translated = translate_cv(cv_data, "de", lang_map)

    assert "Ausbildung" in translated
    assert "education" not in translated
    assert "Berufserfahrung" in translated
    assert "experiences" not in translated
    # Nested keys should also be translated
    assert "Institution" in translated["Ausbildung"][0]


def test_translate_cv_preserves_values():
    """Test that values are never modified during translation."""
    cv_data = {
        "basics": [
            {
                "fname": "Ramin",
                "lname": "Yazdani",
            }
        ]
    }

    lang_map = {
        "basics": {"de": "Grunddaten"},
        "fname": {"de": "Vorname"},
        "lname": {"de": "Nachname"},
    }

    translated = translate_cv(cv_data, "de", lang_map)

    # Values should be unchanged
    assert translated["Grunddaten"][0]["Vorname"] == "Ramin"
    assert translated["Grunddaten"][0]["Nachname"] == "Yazdani"


def test_translate_cv_nested_dicts():
    """Test translation of deeply nested structures."""
    cv_data = {
        "basics": [
            {
                "phone": {
                    "countryCode": "+49",
                    "number": "123456"
                }
            }
        ]
    }

    lang_map = {
        "basics": {"de": "Grunddaten"},
        "phone": {"de": "Telefon"},
        "countryCode": {"de": "Landesvorwahl"},
        "number": {"de": "Nummer"},
    }

    translated = translate_cv(cv_data, "de", lang_map)

    phone = translated["Grunddaten"][0]["Telefon"]
    assert phone["Landesvorwahl"] == "+49"
    assert phone["Nummer"] == "123456"


def test_translate_cv_with_lists():
    """Test translation handles lists correctly."""
    cv_data = {
        "education": [
            {"institution": "University A"},
            {"institution": "University B"},
        ]
    }

    lang_map = {
        "education": {"de": "Ausbildung"},
        "institution": {"de": "Institution"},
    }

    translated = translate_cv(cv_data, "de", lang_map)

    assert len(translated["Ausbildung"]) == 2
    assert translated["Ausbildung"][0]["Institution"] == "University A"
    assert translated["Ausbildung"][1]["Institution"] == "University B"


# ============================================================================
# Tests for skills special handling
# ============================================================================

def test_translate_skills_preserves_category_labels():
    """Test that category labels under skills are NOT translated."""
    cv_data = {
        "skills": {
            "Programming & Scripting": {
                "Programming Languages": [
                    {"long_name": "Python", "short_name": "Py"}
                ]
            }
        }
    }

    lang_map = {
        "skills": {"de": "Fähigkeiten"},
        "Programming & Scripting": {"de": "Programmierung und Skripting"},
        "Programming Languages": {"de": "Programmiersprachen"},
        "long_name": {"de": "Voller_Name"},
        "short_name": {"de": "Kurzer_Name"},
    }

    translated = translate_cv(cv_data, "de", lang_map)

    # "skills" key should be translated
    assert "Fähigkeiten" in translated
    assert "skills" not in translated

    # Category label should NOT be translated
    skills = translated["Fähigkeiten"]
    assert "Programming & Scripting" in skills
    assert "Programmierung und Skripting" not in skills

    # Subcategory label should NOT be translated
    category = skills["Programming & Scripting"]
    assert "Programming Languages" in category
    assert "Programmiersprachen" not in category

    # Skill item keys SHOULD be translated
    skill_item = category["Programming Languages"][0]
    assert "Voller_Name" in skill_item
    assert "Kurzer_Name" in skill_item
    assert "long_name" not in skill_item
    assert "short_name" not in skill_item


def test_translate_skills_nested_in_items():
    """Test that nested structures in skill items are fully translated."""
    cv_data = {
        "skills": {
            "Category": {
                "Subcategory": [
                    {
                        "name": "Skill",
                        "metadata": {
                            "level": "expert"
                        }
                    }
                ]
            }
        }
    }

    lang_map = {
        "skills": {"de": "Fähigkeiten"},
        "name": {"de": "Name"},
        "metadata": {"de": "Metadaten"},
        "level": {"de": "Niveau"},
    }

    translated = translate_cv(cv_data, "de", lang_map)

    item = translated["Fähigkeiten"]["Category"]["Subcategory"][0]
    assert "Name" in item
    assert "Metadaten" in item
    assert "Niveau" in item["Metadaten"]


def test_translate_non_skills_sections_fully():
    """Test that non-skills sections are fully translated at all depths."""
    cv_data = {
        "education": [
            {
                "institution": "University",
                "details": {
                    "gpa": "4.0"
                }
            }
        ]
    }

    lang_map = {
        "education": {"de": "Ausbildung"},
        "institution": {"de": "Institution"},
        "details": {"de": "Details"},
        "gpa": {"de": "Note"},
    }

    translated = translate_cv(cv_data, "de", lang_map)

    # All keys should be translated
    assert "Ausbildung" in translated
    item = translated["Ausbildung"][0]
    assert "Institution" in item
    assert "Details" in item
    assert "Note" in item["Details"]


# ============================================================================
# Tests for collision handling
# ============================================================================

def test_collision_error_mode():
    """Test that collision in error mode raises exception."""
    cv_data = {
        "key1": "value1",
        "key2": "value2",
    }

    # Both keys translate to the same value
    lang_map = {
        "key1": {"de": "Schlüssel"},
        "key2": {"de": "Schlüssel"},
    }

    with pytest.raises(ValueError, match="collision"):
        translate_cv(cv_data, "de", lang_map, on_collision="error")


def test_collision_suffix_mode():
    """Test that collision in suffix mode appends suffix."""
    cv_data = {
        "key1": "value1",
        "key2": "value2",
    }

    lang_map = {
        "key1": {"de": "Schlüssel"},
        "key2": {"de": "Schlüssel"},
    }

    translated = translate_cv(cv_data, "de", lang_map, on_collision="suffix")

    # Should have both keys with suffix on one
    assert "Schlüssel" in translated
    assert "Schlüssel_2" in translated


def test_collision_keep_first_mode():
    """Test that collision in keep-first mode drops later keys."""
    cv_data = {
        "key1": "value1",
        "key2": "value2",
    }

    lang_map = {
        "key1": {"de": "Schlüssel"},
        "key2": {"de": "Schlüssel"},
    }

    translated = translate_cv(cv_data, "de", lang_map, on_collision="keep-first")

    # Should have only one key
    assert "Schlüssel" in translated
    assert len(translated) == 1


# ============================================================================
# Tests for process_cv_file
# ============================================================================

def test_process_cv_file_creates_output():
    """Test that process_cv_file creates the output file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create input file
        in_path = Path(tmpdir) / "test_de.json"
        cv_data = {"education": [{"institution": "Test"}]}
        in_path.write_text(json.dumps(cv_data), encoding="utf-8")

        # Create lang map
        lang_map_path = Path(tmpdir) / "lang.json"
        lang_map = {"education": {"de": "Ausbildung"}, "institution": {"de": "Institution"}}
        lang_map_path.write_text(json.dumps(lang_map), encoding="utf-8")

        # Create output directory
        out_dir = Path(tmpdir) / "output"
        out_path = out_dir / "test_de.json"

        # Process
        lang_map_loaded = load_lang_map(lang_map_path)
        stats = process_cv_file(in_path, out_path, lang_map_loaded)

        # Verify
        assert out_path.exists()
        assert stats["success"]
        assert stats["lang"] == "de"

        # Check content
        result = json.loads(out_path.read_text(encoding="utf-8"))
        assert "Ausbildung" in result


def test_process_cv_file_with_forced_lang():
    """Test that --lang overrides auto-detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create input file with no language suffix
        in_path = Path(tmpdir) / "test.json"
        cv_data = {"education": []}
        in_path.write_text(json.dumps(cv_data), encoding="utf-8")

        # Create lang map
        lang_map = {"education": {"de": "Ausbildung", "fa": "تحصیلات"}}

        # Create output
        out_dir = Path(tmpdir) / "output"
        out_path = out_dir / "test.json"

        # Process with forced Persian
        stats = process_cv_file(in_path, out_path, lang_map, lang="fa")

        assert stats["lang"] == "fa"
        result = json.loads(out_path.read_text(encoding="utf-8"))
        assert "تحصیلات" in result


# ============================================================================
# Tests for idempotency
# ============================================================================

def test_idempotency_translated_keys_preserved():
    """Test that already-translated keys are preserved on re-translation."""
    # This simulates running translation on already-translated output
    cv_data = {
        "Ausbildung": [  # Already German
            {"Institution": "Test"}  # Already German
        ]
    }

    lang_map = {
        "education": {"de": "Ausbildung"},
        "institution": {"de": "Institution"},
    }

    # Translating again should preserve the keys (they're not in lang_map as source keys)
    translated = translate_cv(cv_data, "de", lang_map)

    # Keys should remain unchanged since "Ausbildung" is not a source key
    assert "Ausbildung" in translated
    assert "Institution" in translated["Ausbildung"][0]


