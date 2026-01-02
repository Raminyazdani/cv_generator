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
    assert _is_translation_dict({"en": "", "de": "", "fa": ""}) == True
    assert _is_translation_dict({"en": "Hello", "de": "Hallo"}) == True
    assert _is_translation_dict({"it": "Ciao"}) == True


def test_is_translation_dict_invalid():
    """Test detection of invalid translation dictionaries."""
    # Not a dict
    assert _is_translation_dict("string") == False
    assert _is_translation_dict([]) == False
    
    # Empty dict
    assert _is_translation_dict({}) == False
    
    # Keys that are not language codes
    assert _is_translation_dict({"english": ""}) == False
    assert _is_translation_dict({"EN": ""}) == False  # uppercase
    assert _is_translation_dict({"a": ""}) == False  # too short
    
    # Values that are not strings
    assert _is_translation_dict({"en": 123}) == False
    assert _is_translation_dict({"en": None}) == False


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
