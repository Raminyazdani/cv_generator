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


class TestWebAuth:
    """Tests for HTTP Basic Auth functionality."""

    @pytest.fixture
    def app_with_auth(self, tmp_path, monkeypatch):
        """Create a test Flask app with authentication enabled."""
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Import some test data
        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [{"title": "Test Project"}]
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))
        import_cv(cv_path, db_path)

        # Enable auth via environment variable
        monkeypatch.setenv("CVGEN_WEB_AUTH", "testuser:testpass")

        app = create_app(db_path)
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def client_with_auth(self, app_with_auth):
        """Create a test client with auth enabled."""
        return app_with_auth.test_client()

    def test_requires_auth_returns_401_without_credentials(self, client_with_auth):
        """Test that routes return 401 when auth is required but not provided."""
        response = client_with_auth.get("/")
        assert response.status_code == 401
        assert b"Authentication required" in response.data

    def test_requires_auth_returns_401_with_wrong_credentials(self, client_with_auth):
        """Test that routes return 401 with invalid credentials."""
        from base64 import b64encode
        credentials = b64encode(b"wronguser:wrongpass").decode("utf-8")
        response = client_with_auth.get(
            "/",
            headers={"Authorization": f"Basic {credentials}"}
        )
        assert response.status_code == 401

    def test_requires_auth_returns_200_with_valid_credentials(self, client_with_auth):
        """Test that routes return 200 with valid credentials."""
        from base64 import b64encode
        credentials = b64encode(b"testuser:testpass").decode("utf-8")
        response = client_with_auth.get(
            "/",
            headers={"Authorization": f"Basic {credentials}"}
        )
        assert response.status_code == 200

    def test_auth_with_separate_env_vars(self, tmp_path, monkeypatch):
        """Test auth configured via separate CVGEN_WEB_USER and CVGEN_WEB_PASSWORD."""
        from base64 import b64encode

        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Enable auth via separate environment variables
        monkeypatch.setenv("CVGEN_WEB_USER", "admin")
        monkeypatch.setenv("CVGEN_WEB_PASSWORD", "secret123")

        app = create_app(db_path)
        app.config["TESTING"] = True
        client = app.test_client()

        # Test without credentials
        response = client.get("/")
        assert response.status_code == 401

        # Test with valid credentials
        credentials = b64encode(b"admin:secret123").decode("utf-8")
        response = client.get("/", headers={"Authorization": f"Basic {credentials}"})
        assert response.status_code == 200


class TestHostBindingSafety:
    """Tests for non-localhost binding warnings."""

    def test_is_localhost_returns_true_for_127_0_0_1(self):
        """Test is_localhost returns True for 127.0.0.1."""
        from cv_generator.web import is_localhost
        assert is_localhost("127.0.0.1") is True

    def test_is_localhost_returns_true_for_localhost(self):
        """Test is_localhost returns True for 'localhost'."""
        from cv_generator.web import is_localhost
        assert is_localhost("localhost") is True

    def test_is_localhost_returns_true_for_127_x_addresses(self):
        """Test is_localhost returns True for 127.x.x.x addresses."""
        from cv_generator.web import is_localhost
        assert is_localhost("127.0.0.2") is True
        assert is_localhost("127.1.2.3") is True

    def test_is_localhost_returns_true_for_ipv6_localhost(self):
        """Test is_localhost returns True for IPv6 localhost."""
        from cv_generator.web import is_localhost
        assert is_localhost("::1") is True

    def test_is_localhost_returns_false_for_0_0_0_0(self):
        """Test is_localhost returns False for 0.0.0.0."""
        from cv_generator.web import is_localhost
        assert is_localhost("0.0.0.0") is False

    def test_is_localhost_returns_false_for_external_ip(self):
        """Test is_localhost returns False for external IPs."""
        from cv_generator.web import is_localhost
        assert is_localhost("192.168.1.1") is False
        assert is_localhost("10.0.0.1") is False

    def test_run_server_exits_on_non_localhost_without_flag(self, tmp_path):
        """Test run_server raises SystemExit for non-localhost without flag."""
        from cv_generator.web import run_server

        db_path = tmp_path / "test.db"
        init_db(db_path)

        with pytest.raises(SystemExit) as exc_info:
            run_server(host="0.0.0.0", db_path=db_path, allow_unsafe_bind=False)

        assert exc_info.value.code == 1


class TestRateLimiting:
    """Tests for rate limiting / throttle functionality."""

    def test_check_throttle_allows_first_action(self):
        """Test check_throttle allows the first action."""
        from cv_generator.web import create_app

        app = create_app()
        app.config["TESTING"] = True

        with app.test_request_context():
            from flask import session

            from cv_generator.web import check_throttle

            # First action should be allowed
            result = check_throttle("test_action")
            assert result is None

    def test_check_throttle_blocks_rapid_successive_actions(self):
        """Test check_throttle blocks rapid successive actions."""
        from cv_generator.web import THROTTLE_SECONDS, create_app

        app = create_app()
        app.config["TESTING"] = True

        with app.test_request_context():
            from cv_generator.web import check_throttle

            # First action should be allowed
            result1 = check_throttle("test_action2")
            assert result1 is None

            # Second immediate action should be blocked
            result2 = check_throttle("test_action2")
            assert result2 is not None
            assert result2 > 0
            assert result2 <= THROTTLE_SECONDS + 1


class TestSafeExportBehavior:
    """Tests for safe export filename generation."""

    def test_generate_unique_filename_includes_timestamp(self):
        """Test generate_unique_filename includes timestamp."""
        from cv_generator.web import generate_unique_filename

        filename = generate_unique_filename("ramin")

        assert filename.startswith("ramin_")
        assert filename.endswith(".json")
        # Should be like ramin_20260104_082034.json
        assert len(filename) > len("ramin_.json")

    def test_generate_unique_filename_custom_extension(self):
        """Test generate_unique_filename with custom extension."""
        from cv_generator.web import generate_unique_filename

        filename = generate_unique_filename("test", ".csv")

        assert filename.startswith("test_")
        assert filename.endswith(".csv")

    def test_generate_unique_filename_produces_different_names(self):
        """Test generate_unique_filename produces different names over time."""
        import time

        from cv_generator.web import generate_unique_filename

        name1 = generate_unique_filename("person")
        time.sleep(1.1)  # Wait just over a second
        name2 = generate_unique_filename("person")

        assert name1 != name2


class TestAuthCredentialParsing:
    """Tests for credential parsing from environment variables."""

    def test_get_auth_credentials_returns_none_when_not_set(self, monkeypatch):
        """Test get_auth_credentials returns None when not configured."""
        from cv_generator.web import get_auth_credentials

        # Clear any existing env vars
        monkeypatch.delenv("CVGEN_WEB_AUTH", raising=False)
        monkeypatch.delenv("CVGEN_WEB_USER", raising=False)
        monkeypatch.delenv("CVGEN_WEB_PASSWORD", raising=False)

        result = get_auth_credentials()
        assert result is None

    def test_get_auth_credentials_parses_combined_format(self, monkeypatch):
        """Test get_auth_credentials parses CVGEN_WEB_AUTH=user:pass."""
        from cv_generator.web import get_auth_credentials

        monkeypatch.delenv("CVGEN_WEB_USER", raising=False)
        monkeypatch.delenv("CVGEN_WEB_PASSWORD", raising=False)
        monkeypatch.setenv("CVGEN_WEB_AUTH", "myuser:mypassword")

        result = get_auth_credentials()
        assert result == ("myuser", "mypassword")

    def test_get_auth_credentials_handles_password_with_colon(self, monkeypatch):
        """Test get_auth_credentials handles passwords containing colons."""
        from cv_generator.web import get_auth_credentials

        monkeypatch.delenv("CVGEN_WEB_USER", raising=False)
        monkeypatch.delenv("CVGEN_WEB_PASSWORD", raising=False)
        monkeypatch.setenv("CVGEN_WEB_AUTH", "user:pass:with:colons")

        result = get_auth_credentials()
        assert result == ("user", "pass:with:colons")

    def test_get_auth_credentials_parses_separate_vars(self, monkeypatch):
        """Test get_auth_credentials parses separate USER/PASSWORD vars."""
        from cv_generator.web import get_auth_credentials

        monkeypatch.delenv("CVGEN_WEB_AUTH", raising=False)
        monkeypatch.setenv("CVGEN_WEB_USER", "admin")
        monkeypatch.setenv("CVGEN_WEB_PASSWORD", "secret")

        result = get_auth_credentials()
        assert result == ("admin", "secret")

    def test_get_auth_credentials_ignores_empty_values(self, monkeypatch):
        """Test get_auth_credentials ignores empty/whitespace values."""
        from cv_generator.web import get_auth_credentials

        monkeypatch.setenv("CVGEN_WEB_AUTH", "")
        monkeypatch.setenv("CVGEN_WEB_USER", "")
        monkeypatch.setenv("CVGEN_WEB_PASSWORD", "")

        result = get_auth_credentials()
        assert result is None
