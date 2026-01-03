"""
Tests for cv_generator.web module and tag management in db.

Tests the tag CRUD operations and the web Flask routes.
"""

import json
import tempfile
from pathlib import Path

import pytest

from cv_generator.db import (
    create_tag,
    delete_tag,
    export_cv,
    get_entry,
    get_person_sections,
    get_section_entries,
    get_tag_by_name,
    import_cv,
    init_db,
    list_persons,
    list_tags,
    update_entry_tags,
    update_tag,
)
from cv_generator.errors import ConfigurationError, ValidationError


class TestTagCRUD:
    """Tests for tag CRUD operations."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test database."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        return db_path

    def test_create_tag(self, db):
        """Test creating a new tag."""
        tag = create_tag("Test Tag", "A test tag description", db)

        assert tag["name"] == "Test Tag"
        assert tag["description"] == "A test tag description"
        assert tag["usage_count"] == 0
        assert "id" in tag

    def test_create_tag_no_description(self, db):
        """Test creating a tag without description."""
        tag = create_tag("Simple Tag", None, db)

        assert tag["name"] == "Simple Tag"
        assert tag["description"] is None

    def test_create_duplicate_tag_raises_error(self, db):
        """Test that creating a duplicate tag raises error."""
        create_tag("Duplicate", None, db)

        with pytest.raises(ValidationError) as exc_info:
            create_tag("Duplicate", None, db)

        assert "already exists" in str(exc_info.value)

    def test_create_empty_tag_name_raises_error(self, db):
        """Test that empty tag name raises error."""
        with pytest.raises(ValidationError):
            create_tag("", None, db)

        with pytest.raises(ValidationError):
            create_tag("   ", None, db)

    def test_get_tag_by_name(self, db):
        """Test getting a tag by name."""
        create_tag("Find Me", "Description here", db)

        tag = get_tag_by_name("Find Me", db)

        assert tag is not None
        assert tag["name"] == "Find Me"
        assert tag["description"] == "Description here"

    def test_get_nonexistent_tag(self, db):
        """Test getting a nonexistent tag returns None."""
        tag = get_tag_by_name("Nonexistent", db)
        assert tag is None

    def test_update_tag_name(self, db):
        """Test renaming a tag."""
        create_tag("Old Name", None, db)

        updated = update_tag("Old Name", new_name="New Name", db_path=db)

        assert updated["name"] == "New Name"
        assert get_tag_by_name("Old Name", db) is None
        assert get_tag_by_name("New Name", db) is not None

    def test_update_tag_description(self, db):
        """Test updating tag description."""
        create_tag("My Tag", "Old description", db)

        updated = update_tag("My Tag", description="New description", db_path=db)

        assert updated["description"] == "New description"

    def test_update_nonexistent_tag_raises_error(self, db):
        """Test updating nonexistent tag raises error."""
        with pytest.raises(ConfigurationError):
            update_tag("Nonexistent", new_name="Whatever", db_path=db)

    def test_update_tag_to_existing_name_raises_error(self, db):
        """Test renaming to an existing name raises error."""
        create_tag("Tag A", None, db)
        create_tag("Tag B", None, db)

        with pytest.raises(ValidationError):
            update_tag("Tag A", new_name="Tag B", db_path=db)

    def test_delete_tag(self, db):
        """Test deleting a tag."""
        create_tag("To Delete", None, db)

        result = delete_tag("To Delete", db)

        assert result is True
        assert get_tag_by_name("To Delete", db) is None

    def test_delete_nonexistent_tag(self, db):
        """Test deleting nonexistent tag returns False."""
        result = delete_tag("Nonexistent", db)
        assert result is False


class TestEntryTagManagement:
    """Tests for managing tags on entries."""

    @pytest.fixture
    def populated_db(self, tmp_path):
        """Create a database with imported CV data."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Project A", "type_key": ["Tag1", "Tag2"]},
                {"title": "Project B", "type_key": ["Tag2"]}
            ],
            "experiences": [
                {"role": "Developer", "institution": "Company", "duration": "2020-2022"}
            ]
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))

        import_cv(cv_path, db_path)
        return db_path

    def test_get_person_sections(self, populated_db):
        """Test listing sections for a person."""
        sections = get_person_sections("testuser", populated_db)

        assert "projects" in sections
        assert "experiences" in sections
        assert "basics" in sections

    def test_get_section_entries(self, populated_db):
        """Test getting entries for a section."""
        entries = get_section_entries("testuser", "projects", populated_db)

        assert len(entries) == 2
        assert entries[0]["data"]["title"] == "Project A"
        assert "Tag1" in entries[0]["tags"]
        assert "Tag2" in entries[0]["tags"]

    def test_get_entry(self, populated_db):
        """Test getting a single entry."""
        entries = get_section_entries("testuser", "projects", populated_db)
        entry_id = entries[0]["id"]

        entry = get_entry(entry_id, populated_db)

        assert entry is not None
        assert entry["section"] == "projects"
        assert entry["data"]["title"] == "Project A"
        assert entry["person_slug"] == "testuser"

    def test_get_nonexistent_entry(self, populated_db):
        """Test getting a nonexistent entry."""
        entry = get_entry(9999, populated_db)
        assert entry is None

    def test_update_entry_tags(self, populated_db):
        """Test updating tags on an entry."""
        entries = get_section_entries("testuser", "projects", populated_db)
        entry_id = entries[0]["id"]

        # Update to new set of tags
        result = update_entry_tags(entry_id, ["NewTag1", "NewTag2"], populated_db)

        assert "NewTag1" in result["tags"]
        assert "NewTag2" in result["tags"]

        # Verify in database
        entry = get_entry(entry_id, populated_db)
        assert "NewTag1" in entry["tags"]
        assert "NewTag2" in entry["tags"]
        # Old tags should be gone
        assert "Tag1" not in entry["tags"]

    def test_update_entry_tags_updates_data_json(self, populated_db):
        """Test that updating tags also updates the data_json type_key."""
        entries = get_section_entries("testuser", "projects", populated_db)
        entry_id = entries[0]["id"]

        update_entry_tags(entry_id, ["Export1", "Export2"], populated_db)

        # Export and check type_key is updated
        exported = export_cv("testuser", populated_db)
        project = exported["projects"][0]

        assert project["type_key"] == ["Export1", "Export2"]

    def test_clear_entry_tags(self, populated_db):
        """Test clearing all tags from an entry."""
        entries = get_section_entries("testuser", "projects", populated_db)
        entry_id = entries[0]["id"]

        update_entry_tags(entry_id, [], populated_db)

        entry = get_entry(entry_id, populated_db)
        assert entry["tags"] == []

        # Verify type_key is removed from data
        assert "type_key" not in entry["data"]


class TestWebApp:
    """Tests for the Flask web application."""

    @pytest.fixture
    def app(self, tmp_path):
        """Create a test Flask app with a test database."""
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Import some test data
        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Test Project", "type_key": ["TestTag"]}
            ]
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))
        import_cv(cv_path, db_path)

        app = create_app(db_path)
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return app.test_client()

    def test_index_page(self, client):
        """Test the home page loads."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"testuser" in response.data.lower() or b"Test User" in response.data

    def test_person_dashboard(self, client):
        """Test the person dashboard loads."""
        response = client.get("/p/testuser")
        assert response.status_code == 200
        assert b"projects" in response.data.lower()

    def test_section_entries(self, client):
        """Test the section entries page loads."""
        response = client.get("/p/testuser/projects")
        assert response.status_code == 200
        assert b"Test Project" in response.data

    def test_tags_page(self, client):
        """Test the tags list page loads."""
        response = client.get("/tags")
        assert response.status_code == 200
        # Should show the imported tag
        assert b"TestTag" in response.data

    def test_create_tag_form(self, client):
        """Test the create tag form loads."""
        response = client.get("/tags/create")
        assert response.status_code == 200
        assert b"Create Tag" in response.data

    def test_create_tag_post(self, client):
        """Test creating a tag via POST."""
        response = client.post(
            "/tags/create",
            data={"name": "New Test Tag", "description": "A description"},
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b"New Test Tag" in response.data

    def test_update_entry_tags_post(self, client):
        """Test updating entry tags via POST."""
        # First get entry ID from section page
        response = client.get("/p/testuser/projects")

        # Entry detail page should work with entry ID 1 or 2 (depending on import order)
        response = client.get("/entry/2")  # Skip basics entry
        assert response.status_code == 200

        # Post tag update
        response = client.post(
            "/entry/2/tags",
            data={"tags": ["TestTag", "NewTag"]},
            follow_redirects=True
        )
        assert response.status_code == 200
