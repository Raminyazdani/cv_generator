#!/usr/bin/env python3
"""
Unit tests for create_lang.py

Tests key extraction, merge behavior, and new language addition.
"""

import json
import tempfile
from pathlib import Path
import sys

# Import from create_lang module
sys.path.insert(0, str(Path(__file__).parent))
from create_lang import collect_keys, merge_lang_data, update_lang_json, _is_translation_dict


def test_collect_keys_simple_dict():
    """Test key extraction from a simple dictionary."""
    data = {"name": "John", "age": 30}
    keys = collect_keys(data)
    assert keys == {"name", "age"}


def test_collect_keys_nested_dict():
    """Test key extraction from nested dictionaries."""
    data = {
        "basics": {
            "fname": "Ramin",
            "lname": "Yazdani",
            "phone": {
                "countryCode": "+49",
                "number": "123456789"
            }
        }
    }
    keys = collect_keys(data)
    assert "basics" in keys
    assert "fname" in keys
    assert "lname" in keys
    assert "phone" in keys
    assert "countryCode" in keys
    assert "number" in keys


def test_collect_keys_list_of_objects():
    """Test key extraction from lists containing objects."""
    data = {
        "education": [
            {"institution": "University A", "degree": "BSc"},
            {"institution": "University B", "degree": "MSc", "gpa": "3.8"}
        ]
    }
    keys = collect_keys(data)
    assert keys == {"education", "institution", "degree", "gpa"}


def test_collect_keys_case_sensitive():
    """Test that key names are case-sensitive."""
    data = {
        "pictures": [],
        "Pictures": []
    }
    keys = collect_keys(data)
    assert "pictures" in keys
    assert "Pictures" in keys
    assert len(keys) == 2


def test_collect_keys_no_values():
    """Test that scalar values are not collected as keys."""
    data = {
        "name": "John Doe",
        "count": 42,
        "active": True,
        "value": None
    }
    keys = collect_keys(data)
    # Only keys, not values like "John Doe" or 42
    assert keys == {"name", "count", "active", "value"}
    assert "John Doe" not in keys


def test_collect_keys_deeply_nested():
    """Test key extraction from deeply nested structures."""
    data = {
        "level1": {
            "level2": {
                "level3": {
                    "leaf": "value"
                }
            }
        }
    }
    keys = collect_keys(data)
    assert keys == {"level1", "level2", "level3", "leaf"}


def test_is_translation_dict_valid():
    """Test detection of valid translation dictionaries."""
    assert _is_translation_dict({"en": "", "de": "", "fa": ""})
    assert _is_translation_dict({"en": "Hello", "de": "Hallo"})
    assert _is_translation_dict({"it": "Ciao"})


def test_is_translation_dict_invalid():
    """Test detection of invalid translation dictionaries."""
    # Not a dict
    assert not _is_translation_dict("string")
    assert not _is_translation_dict([])
    
    # Empty dict
    assert not _is_translation_dict({})
    
    # Keys that are not language codes
    assert not _is_translation_dict({"english": ""})
    assert not _is_translation_dict({"EN": ""})  # uppercase
    assert not _is_translation_dict({"a": ""})  # too short
    
    # Values that are not strings
    assert not _is_translation_dict({"en": 123})
    assert not _is_translation_dict({"en": None})


def test_merge_preserves_existing_translations():
    """Test that merge preserves existing non-empty translations."""
    existing = {
        "fname": {"de": "Vorname", "en": "", "fa": ""}
    }
    discovered_keys = {"fname", "lname"}
    languages = ["de", "en", "fa"]
    
    merged, stats = merge_lang_data(existing, discovered_keys, languages)
    
    # Existing translation should be preserved
    assert merged["fname"]["de"] == "Vorname"
    assert merged["fname"]["en"] == ""
    
    # New key should be added
    assert "lname" in merged
    assert merged["lname"] == {"de": "", "en": "", "fa": ""}
    
    # Stats should reflect what happened
    assert stats["translations_preserved"] == 1  # "Vorname"
    assert stats["keys_added"] == 1  # "lname"


def test_merge_adds_new_language():
    """Test that adding a new language adds empty slots everywhere."""
    existing = {
        "fname": {"de": "Vorname", "en": "First Name"}
    }
    discovered_keys = {"fname"}
    languages = ["de", "en", "fa", "it"]  # Adding fa and it
    
    merged, stats = merge_lang_data(existing, discovered_keys, languages)
    
    # Existing translations preserved
    assert merged["fname"]["de"] == "Vorname"
    assert merged["fname"]["en"] == "First Name"
    
    # New languages added with empty string
    assert merged["fname"]["fa"] == ""
    assert merged["fname"]["it"] == ""


def test_merge_keeps_extra_languages():
    """Test that extra languages in existing file are kept."""
    existing = {
        "fname": {"de": "Vorname", "en": "First Name", "zh": "名"}
    }
    discovered_keys = {"fname"}
    languages = ["de", "en"]  # Not requesting zh, but it should be kept
    
    merged, stats = merge_lang_data(existing, discovered_keys, languages)
    
    # All existing languages should be kept
    assert merged["fname"]["de"] == "Vorname"
    assert merged["fname"]["en"] == "First Name"
    assert merged["fname"]["zh"] == "名"


def test_merge_non_destructive_keys():
    """Test that keys not in CV are still kept in output."""
    existing = {
        "old_key": {"en": "translation"}
    }
    discovered_keys = {"new_key"}  # old_key not discovered
    languages = ["en"]
    
    merged, stats = merge_lang_data(existing, discovered_keys, languages)
    
    # Both keys should exist
    assert "old_key" in merged
    assert "new_key" in merged
    assert merged["old_key"]["en"] == "translation"


def test_update_lang_json_creates_file():
    """Test that update_lang_json creates a new file correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cv_path = Path(tmpdir) / "test_cv.json"
        lang_path = Path(tmpdir) / "lang.json"
        
        # Create a simple CV
        cv_data = {
            "basics": {"fname": "John", "lname": "Doe"},
            "education": [{"institution": "Test U"}]
        }
        cv_path.write_text(json.dumps(cv_data), encoding="utf-8")
        
        # Run update
        stats = update_lang_json(
            cv_path=cv_path,
            lang_path=lang_path,
            languages=["en", "de"],
            dry_run=False,
            verbose=False,
        )
        
        # Check file was created
        assert lang_path.exists()
        
        # Load and verify content
        result = json.loads(lang_path.read_text(encoding="utf-8"))
        
        assert "basics" in result
        assert "fname" in result
        assert "lname" in result
        assert "education" in result
        assert "institution" in result
        
        # Each should have both languages
        assert result["fname"] == {"de": "", "en": ""}


def test_update_lang_json_idempotent():
    """Test that running twice produces no changes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cv_path = Path(tmpdir) / "test_cv.json"
        lang_path = Path(tmpdir) / "lang.json"
        
        cv_data = {"name": "value"}
        cv_path.write_text(json.dumps(cv_data), encoding="utf-8")
        
        # First run
        update_lang_json(cv_path, lang_path, ["en"], dry_run=False, verbose=False)
        first_content = lang_path.read_text(encoding="utf-8")
        
        # Second run
        update_lang_json(cv_path, lang_path, ["en"], dry_run=False, verbose=False)
        second_content = lang_path.read_text(encoding="utf-8")
        
        # Should be identical
        assert first_content == second_content


def test_update_lang_json_dry_run():
    """Test that dry run doesn't write file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cv_path = Path(tmpdir) / "test_cv.json"
        lang_path = Path(tmpdir) / "lang.json"
        
        cv_data = {"name": "value"}
        cv_path.write_text(json.dumps(cv_data), encoding="utf-8")
        
        # Dry run
        update_lang_json(cv_path, lang_path, ["en"], dry_run=True, verbose=False)
        
        # File should NOT exist
        assert not lang_path.exists()


# ============================================================================
# Tests for Feature A: --from-lang (auto-populate source language)
# ============================================================================

def test_from_lang_populates_empty_slots():
    """Test that --from-lang populates empty slots with key name."""
    existing = {
        "fname": {"de": "", "en": "", "fa": ""},
        "lname": {"de": "", "en": "", "fa": ""},
    }
    discovered_keys = {"fname", "lname"}
    languages = ["de", "en", "fa"]
    
    merged, stats = merge_lang_data(existing, discovered_keys, languages, from_lang="en")
    
    # en slots should be populated with key names
    assert merged["fname"]["en"] == "fname"
    assert merged["lname"]["en"] == "lname"
    
    # Other language slots should remain empty
    assert merged["fname"]["de"] == ""
    assert merged["fname"]["fa"] == ""
    
    # Stats should reflect from-lang population
    assert stats["from_lang_populated"] == 2


def test_from_lang_preserves_existing_translations():
    """Test that --from-lang does not overwrite non-empty translations."""
    existing = {
        "fname": {"de": "Vorname", "en": "First Name", "fa": ""},
    }
    discovered_keys = {"fname"}
    languages = ["de", "en", "fa"]
    
    merged, stats = merge_lang_data(existing, discovered_keys, languages, from_lang="en")
    
    # Existing non-empty "en" translation should be preserved, NOT overwritten
    assert merged["fname"]["en"] == "First Name"
    assert merged["fname"]["de"] == "Vorname"
    
    # from_lang_populated should be 0 since en slot was already filled
    assert stats["from_lang_populated"] == 0
    assert stats["translations_preserved"] == 2


def test_from_lang_different_language():
    """Test that --from-lang works with different languages (e.g., de, fa)."""
    existing = {
        "fname": {"de": "", "en": "", "fa": ""},
    }
    discovered_keys = {"fname"}
    languages = ["de", "en", "fa"]
    
    # Test with German
    merged, stats = merge_lang_data(existing, discovered_keys, languages, from_lang="de")
    assert merged["fname"]["de"] == "fname"
    assert merged["fname"]["en"] == ""
    assert stats["from_lang_populated"] == 1
    
    # Test with Persian
    merged2, stats2 = merge_lang_data(existing, discovered_keys, languages, from_lang="fa")
    assert merged2["fname"]["fa"] == "fname"
    assert merged2["fname"]["en"] == ""


def test_from_lang_with_new_keys():
    """Test that --from-lang works when adding new keys."""
    existing = {}
    discovered_keys = {"fname", "lname"}
    languages = ["en", "de"]
    
    merged, stats = merge_lang_data(existing, discovered_keys, languages, from_lang="en")
    
    assert merged["fname"]["en"] == "fname"
    assert merged["lname"]["en"] == "lname"
    assert merged["fname"]["de"] == ""
    assert stats["keys_added"] == 2
    assert stats["from_lang_populated"] == 2


# ============================================================================
# Tests for Feature B: Skills subtree exclusion
# ============================================================================

def test_collect_keys_excludes_skills_descendants():
    """Test that keys under 'skills' are excluded from discovery."""
    data = {
        "basics": {"fname": "John"},
        "skills": {
            "Programming": {
                "Languages": [
                    {"long_name": "Python", "short_name": "Py"}
                ]
            },
            "Soft Skills": {
                "Communication": []
            }
        },
        "education": []
    }
    
    keys = collect_keys(data, exclude_skills_descendants=True)
    
    # Top-level keys should be present
    assert "basics" in keys
    assert "fname" in keys
    assert "skills" in keys
    assert "education" in keys
    
    # Keys under skills should NOT be present
    assert "Programming" not in keys
    assert "Languages" not in keys
    assert "long_name" not in keys
    assert "short_name" not in keys
    assert "Soft Skills" not in keys
    assert "Communication" not in keys


def test_collect_keys_include_skills_descendants_when_disabled():
    """Test that skills descendants are included when exclusion is disabled."""
    data = {
        "basics": {"fname": "John"},
        "skills": {
            "Programming": {"Languages": []}
        }
    }
    
    keys = collect_keys(data, exclude_skills_descendants=False)
    
    # Skills descendants should be included
    assert "Programming" in keys
    assert "Languages" in keys


def test_collect_keys_skills_as_empty_object():
    """Test that skills exclusion works when skills is an empty object."""
    data = {
        "basics": {"fname": "John"},
        "skills": {}
    }
    
    keys = collect_keys(data, exclude_skills_descendants=True)
    
    assert "skills" in keys
    assert "basics" in keys
    assert "fname" in keys


def test_collect_keys_skills_as_list():
    """Test that skills exclusion works when skills is a list."""
    data = {
        "basics": {"fname": "John"},
        "skills": [
            {"category": "Programming", "items": ["Python"]}
        ]
    }
    
    keys = collect_keys(data, exclude_skills_descendants=True)
    
    # skills key should be present
    assert "skills" in keys
    # Keys inside the skills list should NOT be present
    assert "category" not in keys
    assert "items" not in keys


# ============================================================================
# Tests for idempotency with new features
# ============================================================================

def test_idempotency_with_from_lang():
    """Test that running with --from-lang twice produces identical output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cv_path = Path(tmpdir) / "test_cv.json"
        lang_path = Path(tmpdir) / "lang.json"
        
        cv_data = {"fname": "John", "lname": "Doe"}
        cv_path.write_text(json.dumps(cv_data), encoding="utf-8")
        
        # First run with from_lang
        update_lang_json(cv_path, lang_path, ["en", "de"], dry_run=False, verbose=False, from_lang="en")
        first_content = lang_path.read_text(encoding="utf-8")
        
        # Second run with same from_lang
        update_lang_json(cv_path, lang_path, ["en", "de"], dry_run=False, verbose=False, from_lang="en")
        second_content = lang_path.read_text(encoding="utf-8")
        
        # Should be identical
        assert first_content == second_content


def run_all_tests():
    """Run all tests and report results."""
    import traceback
    
    tests = [
        test_collect_keys_simple_dict,
        test_collect_keys_nested_dict,
        test_collect_keys_list_of_objects,
        test_collect_keys_case_sensitive,
        test_collect_keys_no_values,
        test_collect_keys_deeply_nested,
        test_is_translation_dict_valid,
        test_is_translation_dict_invalid,
        test_merge_preserves_existing_translations,
        test_merge_adds_new_language,
        test_merge_keeps_extra_languages,
        test_merge_non_destructive_keys,
        test_update_lang_json_creates_file,
        test_update_lang_json_idempotent,
        test_update_lang_json_dry_run,
        # New tests for Feature A (--from-lang)
        test_from_lang_populates_empty_slots,
        test_from_lang_preserves_existing_translations,
        test_from_lang_different_language,
        test_from_lang_with_new_keys,
        # New tests for Feature B (skills exclusion)
        test_collect_keys_excludes_skills_descendants,
        test_collect_keys_include_skills_descendants_when_disabled,
        test_collect_keys_skills_as_empty_object,
        test_collect_keys_skills_as_list,
        # Idempotency with new features
        test_idempotency_with_from_lang,
    ]
    
    passed = 0
    failed = 0
    
    print("=" * 60)
    print("Running create_lang.py unit tests")
    print("=" * 60)
    
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}")
            print(f"      Error: {e}")
            traceback.print_exc()
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed}/{len(tests)} passed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
