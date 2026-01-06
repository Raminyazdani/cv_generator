"""
Tests for skills tagging functionality.

Tests the entry path system, skills import/export,
and tag management for individual skill items.
"""

import json
from pathlib import Path

import pytest

from cv_generator.db import (
    export_cv,
    get_entry,
    get_section_entries,
    import_cv,
    init_db,
    update_entry_tags,
)
from cv_generator.entry_path import (
    enumerate_skills,
    generate_skill_entry_path,
    get_skill_display_name,
    parse_skill_entry_path,
    reconstruct_skills_from_entries,
)


class TestEntryPath:
    """Tests for entry path generation and parsing."""

    def test_generate_skill_entry_path(self):
        """Test generating entry path for a skill."""
        path = generate_skill_entry_path(
            "Programming & Scripting",
            "Programming Languages",
            "Python"
        )
        assert path.startswith("skills/")
        assert "Programming" in path
        assert "Python" in path

    def test_parse_skill_entry_path(self):
        """Test parsing a skill entry path."""
        path = generate_skill_entry_path(
            "Technical Skills",
            "Machine Learning",
            "PyTorch"
        )
        parsed = parse_skill_entry_path(path)

        assert parsed is not None
        assert parsed[0] == "Technical Skills"
        assert parsed[1] == "Machine Learning"
        assert parsed[2] == "PyTorch"

    def test_parse_non_skill_path_returns_none(self):
        """Test that non-skill paths return None."""
        result = parse_skill_entry_path("projects/title=My Project")
        assert result is None

        result = parse_skill_entry_path("invalid")
        assert result is None

    def test_path_handles_special_characters(self):
        """Test that paths handle special characters correctly."""
        path = generate_skill_entry_path(
            "C++ / C#",
            "Web/Mobile",
            "Node.js"
        )
        parsed = parse_skill_entry_path(path)

        assert parsed is not None
        assert parsed[0] == "C++ / C#"
        assert parsed[1] == "Web/Mobile"
        assert parsed[2] == "Node.js"


class TestEnumerateSkills:
    """Tests for skill enumeration."""

    def test_enumerate_simple_skills(self):
        """Test enumerating a simple skills structure."""
        skills_data = {
            "Technical Skills": {
                "Programming": [
                    {"short_name": "Python", "long_name": "Python Programming"},
                    {"short_name": "JavaScript", "long_name": "JavaScript"},
                ]
            }
        }

        results = list(enumerate_skills(skills_data))

        assert len(results) == 2
        # Each result is (entry_path, parent_cat, sub_cat, skill_key, skill_item)
        assert results[0][1] == "Technical Skills"
        assert results[0][2] == "Programming"
        assert results[0][4]["short_name"] == "Python"

    def test_enumerate_nested_categories(self):
        """Test enumerating skills with multiple categories."""
        skills_data = {
            "Programming": {
                "Languages": [
                    {"short_name": "Python"}
                ],
                "Frameworks": [
                    {"short_name": "Django"}
                ]
            },
            "Soft Skills": {
                "Communication": [
                    {"short_name": "Public Speaking"}
                ]
            }
        }

        results = list(enumerate_skills(skills_data))

        assert len(results) == 3
        parent_categories = set(r[1] for r in results)
        assert "Programming" in parent_categories
        assert "Soft Skills" in parent_categories

    def test_handles_collision_with_suffix(self):
        """Test that skill key collisions are handled."""
        skills_data = {
            "Category": {
                "SubCat": [
                    {"short_name": "Skill", "long_name": "First Skill"},
                    {"short_name": "Skill", "long_name": "Second Skill"},
                ]
            }
        }

        results = list(enumerate_skills(skills_data))

        assert len(results) == 2
        # Keys should be different
        keys = [r[3] for r in results]
        assert len(set(keys)) == 2  # Both should be unique

    def test_fallback_to_index_when_no_name(self):
        """Test fallback to index when skill has no name."""
        skills_data = {
            "Category": {
                "SubCat": [
                    {},  # No short_name or long_name
                ]
            }
        }

        results = list(enumerate_skills(skills_data))

        assert len(results) == 1
        assert "idx_0" in results[0][3]


class TestSkillDisplayName:
    """Tests for skill display name generation."""

    def test_display_name_with_both_names(self):
        """Test display name when both short and long names exist."""
        skill = {"short_name": "ML", "long_name": "Machine Learning"}
        name = get_skill_display_name(skill)
        assert name == "ML (Machine Learning)"

    def test_display_name_short_only(self):
        """Test display name with only short name."""
        skill = {"short_name": "Python"}
        name = get_skill_display_name(skill)
        assert name == "Python"

    def test_display_name_long_only(self):
        """Test display name with only long name."""
        skill = {"long_name": "Machine Learning"}
        name = get_skill_display_name(skill)
        assert name == "Machine Learning"

    def test_display_name_same_names(self):
        """Test display name when short and long are the same."""
        skill = {"short_name": "Python", "long_name": "Python"}
        name = get_skill_display_name(skill)
        assert name == "Python"

    def test_display_name_no_names(self):
        """Test display name fallback."""
        skill = {}
        name = get_skill_display_name(skill)
        assert name == "Unknown Skill"


class TestSkillsImportExport:
    """Tests for skills import and export in database."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test database."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        return db_path

    @pytest.fixture
    def cv_with_skills(self, tmp_path):
        """Create a CV JSON with skills section."""
        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "skills": {
                "Programming & Scripting": {
                    "Programming Languages": [
                        {
                            "long_name": "Python",
                            "short_name": "Python",
                            "type_key": ["Full CV", "Programming"]
                        },
                        {
                            "long_name": "R",
                            "short_name": "R",
                            "type_key": ["Full CV", "Programming"]
                        }
                    ],
                    "Machine Learning": [
                        {
                            "long_name": "TensorFlow",
                            "short_name": "TensorFlow",
                            "type_key": ["Full CV", "Programming"]
                        }
                    ]
                },
                "Soft Skills": {
                    "Core": [
                        {
                            "long_name": "Problem-Solving",
                            "short_name": "Problem-Solving",
                            "type_key": ["Full CV"]
                        }
                    ]
                }
            }
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))
        return cv_path, cv_data

    def test_import_creates_individual_skill_entries(self, cv_with_skills, db):
        """Test that skills are imported as individual entries."""
        cv_path, original = cv_with_skills

        stats = import_cv(cv_path, db)

        # Should have 4 skill entries (Python, R, TensorFlow, Problem-Solving)
        assert stats["sections"]["skills"] == 4

        # Verify entries exist
        entries = get_section_entries("testuser", "skills", db)
        assert len(entries) == 4

    def test_skill_entries_have_correct_identity_keys(self, cv_with_skills, db):
        """Test that skill entries have proper entry paths as identity keys."""
        cv_path, _ = cv_with_skills
        import_cv(cv_path, db)

        entries = get_section_entries("testuser", "skills", db)

        for entry in entries:
            assert entry["identity_key"].startswith("skills/")
            parsed = parse_skill_entry_path(entry["identity_key"])
            assert parsed is not None

    def test_skill_entries_preserve_type_keys(self, cv_with_skills, db):
        """Test that type_key tags are preserved on skill entries."""
        cv_path, _ = cv_with_skills
        import_cv(cv_path, db)

        entries = get_section_entries("testuser", "skills", db)

        # Find Python entry
        python_entry = next((e for e in entries if e["data"]["short_name"] == "Python"), None)
        assert python_entry is not None
        assert "Full CV" in python_entry["tags"]
        assert "Programming" in python_entry["tags"]

    def test_export_reconstructs_nested_skills(self, cv_with_skills, db):
        """Test that export reconstructs the nested skills structure."""
        cv_path, original = cv_with_skills
        import_cv(cv_path, db)

        exported = export_cv("testuser", db)

        # Skills should be a nested dict
        assert "skills" in exported
        assert isinstance(exported["skills"], dict)

        # Check structure
        assert "Programming & Scripting" in exported["skills"]
        assert "Programming Languages" in exported["skills"]["Programming & Scripting"]
        assert "Soft Skills" in exported["skills"]

    def test_round_trip_preserves_skills_structure(self, cv_with_skills, db):
        """Test that import/export round-trip preserves skills."""
        cv_path, original = cv_with_skills
        import_cv(cv_path, db)

        exported = export_cv("testuser", db)

        # Verify same number of skills in each category
        original_skills = original["skills"]
        exported_skills = exported["skills"]

        for parent_cat, sub_cats in original_skills.items():
            assert parent_cat in exported_skills
            for sub_cat, skills in sub_cats.items():
                assert sub_cat in exported_skills[parent_cat]
                assert len(exported_skills[parent_cat][sub_cat]) == len(skills)


class TestSkillTaggingWorkflow:
    """Tests for the full skill tagging workflow."""

    @pytest.fixture
    def populated_db(self, tmp_path):
        """Create a database with imported skills."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "skills": {
                "Programming": {
                    "Languages": [
                        {
                            "short_name": "Python",
                            "long_name": "Python Programming",
                            "type_key": ["Full CV", "Programming"]
                        },
                        {
                            "short_name": "JavaScript",
                            "long_name": "JavaScript",
                            "type_key": ["Full CV", "Web"]
                        }
                    ]
                }
            }
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))

        import_cv(cv_path, db_path)
        return db_path

    def test_can_update_skill_tags(self, populated_db):
        """Test that tags can be updated on individual skill entries."""
        entries = get_section_entries("testuser", "skills", populated_db)

        # Find Python entry
        python_entry = next((e for e in entries if e["data"]["short_name"] == "Python"), None)
        assert python_entry is not None

        # Update tags
        update_entry_tags(python_entry["id"], ["Academic", "Research"], populated_db)

        # Verify update
        updated = get_entry(python_entry["id"], populated_db)
        assert "Academic" in updated["tags"]
        assert "Research" in updated["tags"]
        # Old tags should be gone
        assert "Full CV" not in updated["tags"]
        assert "Programming" not in updated["tags"]

    def test_skill_tag_update_affects_export(self, populated_db):
        """Test that updating skill tags affects the exported JSON."""
        entries = get_section_entries("testuser", "skills", populated_db)

        # Find JavaScript entry and update its tags
        js_entry = next((e for e in entries if e["data"]["short_name"] == "JavaScript"), None)
        update_entry_tags(js_entry["id"], ["Frontend", "UI"], populated_db)

        # Export and verify
        exported = export_cv("testuser", populated_db, apply_tags=True)

        # Find JavaScript in exported data
        js_skills = exported["skills"]["Programming"]["Languages"]
        js_skill = next((s for s in js_skills if s["short_name"] == "JavaScript"), None)

        assert js_skill is not None
        assert js_skill["type_key"] == ["Frontend", "UI"]

    def test_other_skill_unaffected_by_update(self, populated_db):
        """Test that updating one skill doesn't affect others."""
        entries = get_section_entries("testuser", "skills", populated_db)

        # Find Python entry and update
        python_entry = next((e for e in entries if e["data"]["short_name"] == "Python"), None)
        update_entry_tags(python_entry["id"], ["NewTag"], populated_db)

        # Check JavaScript is unaffected
        js_entry = next((e for e in entries if e["data"]["short_name"] == "JavaScript"), None)
        js_updated = get_entry(js_entry["id"], populated_db)

        assert "Full CV" in js_updated["tags"]
        assert "Web" in js_updated["tags"]


class TestReconstructSkillsFromEntries:
    """Tests for reconstructing skills from entry dicts."""

    def test_reconstruct_simple(self):
        """Test reconstructing a simple skills structure."""
        entries = [
            {
                "identity_key": "skills/Category/SubCat/Python",
                "data": {"short_name": "Python"}
            },
            {
                "identity_key": "skills/Category/SubCat/JavaScript",
                "data": {"short_name": "JavaScript"}
            }
        ]

        result = reconstruct_skills_from_entries(entries)

        assert "Category" in result
        assert "SubCat" in result["Category"]
        assert len(result["Category"]["SubCat"]) == 2

    def test_reconstruct_multiple_categories(self):
        """Test reconstructing skills across multiple categories."""
        entries = [
            {
                "identity_key": "skills/Programming/Languages/Python",
                "data": {"short_name": "Python"}
            },
            {
                "identity_key": "skills/Soft Skills/Communication/Speaking",
                "data": {"short_name": "Speaking"}
            }
        ]

        result = reconstruct_skills_from_entries(entries)

        assert "Programming" in result
        assert "Soft Skills" in result
        assert len(result["Programming"]["Languages"]) == 1
        assert len(result["Soft Skills"]["Communication"]) == 1

    def test_reconstruct_ignores_non_skill_entries(self):
        """Test that non-skill entries are ignored.

        Non-skill entries use different identity_key formats (e.g., 'projects:title=X').
        The reconstruct function should only process entries with skills/ prefix.
        """
        entries = [
            {
                "identity_key": "skills/Category/SubCat/Python",
                "data": {"short_name": "Python"}
            },
            {
                # This uses the projects identity key format (section:field=value)
                "identity_key": "projects:title=Something",
                "data": {"title": "Something"}
            }
        ]

        result = reconstruct_skills_from_entries(entries)

        assert "Category" in result
        assert len(result) == 1  # Only skills category


class TestSkillsTagDeletionCascade:
    """Tests for tag deletion cascade in nested skills structure."""

    @pytest.fixture
    def populated_db(self, tmp_path):
        """Create a database with imported skills having tags."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "skills": {
                "Programming": {
                    "Languages": [
                        {
                            "short_name": "Python",
                            "long_name": "Python Programming",
                            "type_key": ["SkillTagX", "Full CV"]
                        },
                        {
                            "short_name": "JavaScript",
                            "long_name": "JavaScript",
                            "type_key": ["SkillTagX", "Web"]
                        }
                    ],
                    "Frameworks": [
                        {
                            "short_name": "Django",
                            "long_name": "Django Framework",
                            "type_key": ["SkillTagX"]
                        }
                    ]
                }
            }
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))

        import_cv(cv_path, db_path)
        return db_path

    def test_delete_tag_removes_from_all_skill_entries(self, populated_db):
        """Test that deleting a tag removes it from all skill entries."""
        from cv_generator.db import delete_tag, get_tag_by_name

        # Delete SkillTagX which appears in all skills
        delete_tag("SkillTagX", populated_db)

        # Verify SkillTagX is not in any skill entry
        entries = get_section_entries("testuser", "skills", populated_db)
        for entry in entries:
            assert "SkillTagX" not in entry["tags"]
            data = entry["data"]
            if "type_key" in data:
                assert "SkillTagX" not in data["type_key"]

    def test_delete_tag_preserves_other_skill_tags(self, populated_db):
        """Test that deleting one tag preserves other tags in skill entries."""
        from cv_generator.db import delete_tag

        delete_tag("SkillTagX", populated_db)

        entries = get_section_entries("testuser", "skills", populated_db)

        # Find Python entry - should still have "Full CV"
        python_entry = next((e for e in entries if e["data"]["short_name"] == "Python"), None)
        assert "Full CV" in python_entry["tags"]

        # Find JavaScript entry - should still have "Web"
        js_entry = next((e for e in entries if e["data"]["short_name"] == "JavaScript"), None)
        assert "Web" in js_entry["tags"]

    def test_delete_tag_removes_empty_type_key_from_skills(self, populated_db):
        """Test that type_key is removed if it becomes empty after tag deletion."""
        from cv_generator.db import delete_tag

        delete_tag("SkillTagX", populated_db)

        entries = get_section_entries("testuser", "skills", populated_db)

        # Django only had SkillTagX, so type_key should be removed entirely
        django_entry = next((e for e in entries if e["data"]["short_name"] == "Django"), None)
        assert "type_key" not in django_entry["data"]

    def test_delete_tag_reflects_in_exported_skills_json(self, populated_db):
        """Test that export JSON for skills doesn't contain deleted tags."""
        from cv_generator.db import delete_tag

        delete_tag("SkillTagX", populated_db)

        # Export and verify
        exported = export_cv("testuser", populated_db)
        skills = exported["skills"]

        # Check all skill items
        for parent_cat, sub_cats in skills.items():
            for sub_cat, skill_list in sub_cats.items():
                for skill in skill_list:
                    type_key = skill.get("type_key", [])
                    assert "SkillTagX" not in type_key
