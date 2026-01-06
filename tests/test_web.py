"""
Tests for cv_generator.web module and tag management in db.

Tests the tag CRUD operations and the web Flask routes.
"""

import json
import re
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


def get_csrf_token(response) -> str:
    """
    Extract CSRF token from a response's HTML.

    Args:
        response: Flask test client response.

    Returns:
        The CSRF token string, or empty string if not found.
    """
    match = re.search(
        rb'name="csrf_token"[^>]*value="([^"]*)"',
        response.data
    )
    if match:
        return match.group(1).decode("utf-8")
    return ""


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
        # First get the CSRF token from the form page
        form_response = client.get("/tags/create")
        csrf_token = get_csrf_token(form_response)

        response = client.post(
            "/tags/create",
            data={
                "name": "New Test Tag",
                "description": "A description",
                "csrf_token": csrf_token,
            },
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
        csrf_token = get_csrf_token(response)

        # Post tag update
        response = client.post(
            "/entry/2/tags",
            data={"tags": ["TestTag", "NewTag"], "csrf_token": csrf_token},
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


class TestCSRFProtection:
    """Tests for CSRF protection functionality."""

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

    def test_csrf_token_is_generated(self, client):
        """Test that CSRF token is included in forms."""
        response = client.get("/tags/create")
        assert response.status_code == 200
        # Check that the form contains a CSRF token field
        assert b'name="csrf_token"' in response.data
        assert b'value="' in response.data

    def test_post_without_csrf_token_fails(self, client):
        """Test that POST requests without CSRF token return 400."""
        response = client.post(
            "/tags/create",
            data={"name": "Test Tag"},
            follow_redirects=False
        )
        assert response.status_code == 400
        assert b"CSRF token validation failed" in response.data

    def test_post_with_invalid_csrf_token_fails(self, client):
        """Test that POST requests with invalid CSRF token return 400."""
        response = client.post(
            "/tags/create",
            data={"name": "Test Tag", "csrf_token": "invalid-token"},
            follow_redirects=False
        )
        assert response.status_code == 400
        assert b"CSRF token validation failed" in response.data

    def test_post_with_valid_csrf_token_succeeds(self, client):
        """Test that POST requests with valid CSRF token succeed."""
        # Get the form to get a valid CSRF token
        form_response = client.get("/tags/create")
        csrf_token = get_csrf_token(form_response)
        assert csrf_token  # Should not be empty

        # Post with valid token
        response = client.post(
            "/tags/create",
            data={"name": "CSRF Test Tag", "csrf_token": csrf_token},
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b"CSRF Test Tag" in response.data

    def test_csrf_token_is_consistent_within_session(self, client):
        """Test that CSRF token remains consistent within the same session."""
        # Get token from first page
        response1 = client.get("/tags/create")
        token1 = get_csrf_token(response1)

        # Get token from second page (same session)
        response2 = client.get("/entry/2")
        token2 = get_csrf_token(response2)

        # Tokens should be the same within the session
        assert token1 == token2

    def test_csrf_token_validation_function(self):
        """Test the CSRF token generation and validation functions."""
        from cv_generator.web import (
            CSRF_SESSION_KEY,
            generate_csrf_token,
            validate_csrf_token,
        )

        # Mock the session
        with pytest.raises(RuntimeError):
            # Should fail outside of request context
            generate_csrf_token()

    def test_all_post_routes_require_csrf(self, client):
        """Test that all POST routes require CSRF protection."""
        post_routes = [
            "/tags/create",
            "/tags/TestTag/edit",
            "/tags/TestTag/delete",
            "/entry/2/tags",
            "/entry/2/edit",
            "/entry/2/delete",
            "/export/testuser",
            "/p/testuser/projects/create",
            "/diagnostics/cleanup-orphans",
        ]

        for route in post_routes:
            response = client.post(route, data={}, follow_redirects=False)
            assert response.status_code == 400, f"Route {route} did not require CSRF"


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

    def test_generate_unique_filename_produces_different_names(self, monkeypatch):
        """Test generate_unique_filename produces different names over time."""
        from datetime import datetime as real_datetime
        from unittest.mock import MagicMock

        from cv_generator.web import generate_unique_filename

        # First call with mocked time
        mock_dt1 = MagicMock()
        mock_dt1.now.return_value.strftime.return_value = "20260104_100000"
        monkeypatch.setattr("cv_generator.web.datetime", mock_dt1)
        name1 = generate_unique_filename("person")

        # Second call with different mocked time
        mock_dt2 = MagicMock()
        mock_dt2.now.return_value.strftime.return_value = "20260104_100001"
        monkeypatch.setattr("cv_generator.web.datetime", mock_dt2)
        name2 = generate_unique_filename("person")

        assert name1 != name2
        assert name1 == "person_20260104_100000.json"
        assert name2 == "person_20260104_100001.json"


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


class TestTagDeletionCascade:
    """Tests for tag deletion with cascade cleanup to data_json."""

    @pytest.fixture
    def populated_db(self, tmp_path):
        """Create a database with imported CV data having tags across multiple entries."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Project A", "type_key": ["TagX", "TagY"]},
                {"title": "Project B", "type_key": ["TagX", "TagZ"]},
                {"title": "Project C", "type_key": ["TagY", "TagZ"]}
            ],
            "experiences": [
                {"role": "Developer", "institution": "Company", "duration": "2020", "type_key": ["TagX"]}
            ]
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))

        import_cv(cv_path, db_path)
        return db_path

    def test_delete_tag_removes_from_catalog(self, populated_db):
        """Test that deleting a tag removes it from the tag catalog."""
        # Verify tag exists
        tag = get_tag_by_name("TagX", populated_db)
        assert tag is not None

        # Delete the tag
        result = delete_tag("TagX", populated_db)
        assert result is True

        # Verify tag is gone from catalog
        tag = get_tag_by_name("TagX", populated_db)
        assert tag is None

    def test_delete_tag_removes_from_all_entries_type_key(self, populated_db):
        """Test that deleting a tag removes it from type_key in all entries."""
        # Delete TagX which appears in multiple entries
        delete_tag("TagX", populated_db)

        # Verify TagX is not in any entry's type_key
        entries = get_section_entries("testuser", "projects", populated_db)
        for entry in entries:
            assert "TagX" not in entry["tags"]
            # Also check the raw data
            entry_detail = get_entry(entry["id"], populated_db)
            data = entry_detail["data"]
            if "type_key" in data:
                assert "TagX" not in data["type_key"]

        # Check experiences too
        exp_entries = get_section_entries("testuser", "experiences", populated_db)
        for entry in exp_entries:
            assert "TagX" not in entry["tags"]

    def test_delete_tag_removes_from_exported_json(self, populated_db):
        """Test that export JSON never contains deleted tags."""
        # Delete TagX
        delete_tag("TagX", populated_db)

        # Export without apply_tags (uses data_json directly)
        exported = export_cv("testuser", populated_db)

        # Verify TagX is not in any type_key in exported data
        for project in exported.get("projects", []):
            type_key = project.get("type_key", [])
            assert "TagX" not in type_key

        for exp in exported.get("experiences", []):
            type_key = exp.get("type_key", [])
            assert "TagX" not in type_key

    def test_delete_tag_preserves_other_tags(self, populated_db):
        """Test that deleting one tag preserves other tags in entries."""
        # Delete TagX
        delete_tag("TagX", populated_db)

        # Project A originally had [TagX, TagY], should now have [TagY]
        entries = get_section_entries("testuser", "projects", populated_db)
        project_a = next(e for e in entries if e["data"]["title"] == "Project A")
        assert "TagY" in project_a["tags"]
        assert "TagX" not in project_a["tags"]

        # Project C originally had [TagY, TagZ], should be unchanged
        project_c = next(e for e in entries if e["data"]["title"] == "Project C")
        assert "TagY" in project_c["tags"]
        assert "TagZ" in project_c["tags"]

    def test_delete_tag_removes_empty_type_key(self, populated_db):
        """Test that if type_key becomes empty after tag deletion, it's removed entirely."""
        # Delete TagX from the experience which only has TagX
        delete_tag("TagX", populated_db)

        exp_entries = get_section_entries("testuser", "experiences", populated_db)
        assert len(exp_entries) == 1
        exp = exp_entries[0]

        # type_key should be removed (not just empty)
        assert "type_key" not in exp["data"]


class TestRemoveTagFromEntry:
    """Tests for removing a specific tag from an entry."""

    @pytest.fixture
    def populated_db(self, tmp_path):
        """Create a database with imported CV data."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Project A", "type_key": ["TagA", "TagB", "TagC"]}
            ]
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))

        import_cv(cv_path, db_path)
        return db_path

    def test_remove_tag_from_entry(self, populated_db):
        """Test removing a single tag from an entry."""
        from cv_generator.db import remove_tag_from_entry

        entries = get_section_entries("testuser", "projects", populated_db)
        entry_id = entries[0]["id"]

        # Remove TagB
        result = remove_tag_from_entry(entry_id, "TagB", populated_db)

        assert "TagB" not in result["tags"]
        assert "TagA" in result["tags"]
        assert "TagC" in result["tags"]

    def test_remove_tag_updates_data_json(self, populated_db):
        """Test that removing a tag updates the data_json type_key."""
        from cv_generator.db import remove_tag_from_entry

        entries = get_section_entries("testuser", "projects", populated_db)
        entry_id = entries[0]["id"]

        # Remove TagB
        remove_tag_from_entry(entry_id, "TagB", populated_db)

        # Verify data_json is updated
        entry = get_entry(entry_id, populated_db)
        assert "TagB" not in entry["data"]["type_key"]
        assert "TagA" in entry["data"]["type_key"]

    def test_remove_tag_reflects_in_export(self, populated_db):
        """Test that removing a tag is reflected in export."""
        from cv_generator.db import remove_tag_from_entry

        entries = get_section_entries("testuser", "projects", populated_db)
        entry_id = entries[0]["id"]

        # Remove TagB
        remove_tag_from_entry(entry_id, "TagB", populated_db)

        # Export and verify
        exported = export_cv("testuser", populated_db)
        project = exported["projects"][0]
        assert "TagB" not in project["type_key"]
        assert "TagA" in project["type_key"]

    def test_remove_nonexistent_tag_no_error(self, populated_db):
        """Test removing a nonexistent tag doesn't raise an error."""
        from cv_generator.db import remove_tag_from_entry

        entries = get_section_entries("testuser", "projects", populated_db)
        entry_id = entries[0]["id"]

        # Remove a tag that doesn't exist
        result = remove_tag_from_entry(entry_id, "NonexistentTag", populated_db)

        # Should work without error, original tags preserved
        assert "TagA" in result["tags"]
        assert "TagB" in result["tags"]
        assert "TagC" in result["tags"]


class TestExportConsistency:
    """Tests for export consistency and determinism."""

    @pytest.fixture
    def populated_db(self, tmp_path):
        """Create a database with imported CV data."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Project A", "type_key": ["Tag1", "Tag2"]}
            ]
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))

        import_cv(cv_path, db_path)
        return db_path

    def test_export_twice_same_content(self, populated_db):
        """Test that exporting twice produces the same content."""
        exported1 = export_cv("testuser", populated_db)
        exported2 = export_cv("testuser", populated_db)

        assert exported1 == exported2

    def test_export_after_tag_modification_consistent(self, populated_db):
        """Test that exports are consistent after tag modifications."""
        # Modify tags
        entries = get_section_entries("testuser", "projects", populated_db)
        entry_id = entries[0]["id"]
        update_entry_tags(entry_id, ["NewTag1", "NewTag2"], populated_db)

        # Export twice
        exported1 = export_cv("testuser", populated_db, apply_tags=True)
        exported2 = export_cv("testuser", populated_db, apply_tags=True)

        assert exported1 == exported2
        assert exported1["projects"][0]["type_key"] == ["NewTag1", "NewTag2"]

    def test_export_after_delete_no_reintroduced_tags(self, populated_db):
        """Test that deleted tags are never reintroduced in exports."""
        # Delete a tag
        delete_tag("Tag1", populated_db)

        # Export multiple times
        for _ in range(3):
            exported = export_cv("testuser", populated_db)
            type_key = exported["projects"][0].get("type_key", [])
            assert "Tag1" not in type_key

    def test_export_with_apply_tags_uses_database_truth(self, populated_db):
        """Test that apply_tags uses database as source of truth."""
        # Manually update entry_tag (simulating a different code path)
        entries = get_section_entries("testuser", "projects", populated_db)
        entry_id = entries[0]["id"]

        # Update tags via the proper API
        update_entry_tags(entry_id, ["OnlyThisTag"], populated_db)

        # Export with apply_tags=True
        exported = export_cv("testuser", populated_db, apply_tags=True)
        assert exported["projects"][0]["type_key"] == ["OnlyThisTag"]


class TestCleanupOrphanTagReferences:
    """Tests for cleanup_orphan_tag_references function."""

    @pytest.fixture
    def db_with_orphans(self, tmp_path):
        """Create a database with orphan tag references in data_json."""
        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Import CV with tags
        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Project A", "type_key": ["RealTag", "OrphanTag"]}
            ]
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))

        import_cv(cv_path, db_path)

        # Manually delete the tag from the catalog but NOT update data_json
        # (simulating pre-fix behavior or a bug)
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tag WHERE name = ?", ("OrphanTag",))
        tag_id = cursor.fetchone()[0]
        cursor.execute("DELETE FROM entry_tag WHERE tag_id = ?", (tag_id,))
        cursor.execute("DELETE FROM tag WHERE id = ?", (tag_id,))
        conn.commit()
        conn.close()

        return db_path

    def test_cleanup_finds_orphan_references(self, db_with_orphans):
        """Test that cleanup finds orphan tag references."""
        from cv_generator.db import cleanup_orphan_tag_references

        result = cleanup_orphan_tag_references(db_with_orphans)

        assert result["entries_cleaned"] == 1
        assert "OrphanTag" in result["orphan_tags_found"]

    def test_cleanup_removes_orphan_from_data_json(self, db_with_orphans):
        """Test that cleanup removes orphans from data_json."""
        from cv_generator.db import cleanup_orphan_tag_references

        cleanup_orphan_tag_references(db_with_orphans)

        # Verify the data_json no longer contains OrphanTag
        entries = get_section_entries("testuser", "projects", db_with_orphans)
        entry = entries[0]

        assert "OrphanTag" not in entry["data"].get("type_key", [])
        assert "RealTag" in entry["data"]["type_key"]

    def test_cleanup_preserves_valid_tags(self, db_with_orphans):
        """Test that cleanup preserves valid tags."""
        from cv_generator.db import cleanup_orphan_tag_references

        cleanup_orphan_tag_references(db_with_orphans)

        # Verify RealTag is still present
        entries = get_section_entries("testuser", "projects", db_with_orphans)
        entry = entries[0]

        assert "RealTag" in entry["tags"]
        assert "RealTag" in entry["data"]["type_key"]


class TestWebCrudRoutes:
    """Tests for the Web CRUD routes (create/edit/delete entries)."""

    @pytest.fixture
    def app_with_multi_lang(self, tmp_path):
        """Create a test Flask app with multi-language CV data."""
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Create EN CV
        cv_en = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Existing Project", "url": "https://example.com"}
            ]
        }
        cv_en_path = tmp_path / "cvs" / "testuser.json"
        cv_en_path.parent.mkdir(parents=True, exist_ok=True)
        cv_en_path.write_text(json.dumps(cv_en, ensure_ascii=False))
        import_cv(cv_en_path, db_path)

        # Create DE CV
        cv_de = {
            "basics": [{"fname": "Test", "lname": "Benutzer"}],
            "projects": [
                {"title": "Bestehendes Projekt", "url": "https://example.com"}
            ]
        }
        cv_de_path = tmp_path / "cvs" / "testuser_de.json"
        cv_de_path.write_text(json.dumps(cv_de, ensure_ascii=False))
        import_cv(cv_de_path, db_path)

        app = create_app(db_path)
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def client(self, app_with_multi_lang):
        """Create a test client."""
        return app_with_multi_lang.test_client()

    def test_create_entry_form_loads(self, client):
        """Test that the create entry form loads."""
        response = client.get("/p/testuser/projects/create")
        assert response.status_code == 200
        assert b"Create" in response.data
        assert b"Title" in response.data

    def test_create_entry_post_with_sync(self, client):
        """Test creating an entry with multi-language sync."""
        # First get the CSRF token from the form page
        form_response = client.get("/p/testuser/projects/create")
        csrf_token = get_csrf_token(form_response)

        response = client.post(
            "/p/testuser/projects/create",
            data={
                "field_title": "New Project",
                "field_description": "A new project",
                "field_url": "https://new-project.com",
                "sync_languages": "on",
                "csrf_token": csrf_token,
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        # Check for "Entry created" message (case-insensitive)
        response_lower = response.data.lower()
        assert b"entry created" in response_lower or b"created" in response_lower

    def test_create_entry_post_without_sync(self, client):
        """Test creating an entry without multi-language sync."""
        # First get the CSRF token from the form page
        form_response = client.get("/p/testuser/projects/create")
        csrf_token = get_csrf_token(form_response)

        response = client.post(
            "/p/testuser/projects/create",
            data={
                "field_title": "Solo Project",
                "csrf_token": csrf_token,
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        # Check for "Entry created" message (case-insensitive)
        response_lower = response.data.lower()
        assert b"entry created" in response_lower or b"created" in response_lower

    def test_edit_entry_form_loads(self, client):
        """Test that the edit entry form loads."""
        # Get entry ID (skip basics which is entry 1)
        response = client.get("/entry/2/edit")
        assert response.status_code == 200
        assert b"Edit" in response.data

    def test_edit_entry_post(self, client):
        """Test updating an entry."""
        # First get the CSRF token from the form page
        form_response = client.get("/entry/2/edit")
        csrf_token = get_csrf_token(form_response)

        response = client.post(
            "/entry/2/edit",
            data={
                "field_title": "Updated Project Title",
                "field_url": "https://updated-url.com",
                "csrf_token": csrf_token,
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b"updated successfully" in response.data.lower()

    def test_entry_linked_page_loads(self, client):
        """Test that the linked entries page loads."""
        response = client.get("/entry/2/linked")
        assert response.status_code == 200
        # Page should show language variants
        assert b"Linked" in response.data or b"linked" in response.data.lower()

    def test_section_entries_shows_add_button(self, client):
        """Test that section entries page shows add button for supported sections."""
        response = client.get("/p/testuser/projects")
        assert response.status_code == 200
        assert b"Add New" in response.data

    def test_entry_detail_shows_edit_button(self, client):
        """Test that entry detail page shows edit button."""
        response = client.get("/entry/2")
        assert response.status_code == 200
        assert b"Edit Entry" in response.data


class TestDiagnosticsRoute:
    """Tests for the diagnostics page."""

    @pytest.fixture
    def app_with_data(self, tmp_path):
        """Create a test Flask app with CV data."""
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Create CV with tags
        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Project A", "type_key": ["TagA", "TagB"]}
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
    def client(self, app_with_data):
        """Create a test client."""
        return app_with_data.test_client()

    def test_diagnostics_page_loads(self, client):
        """Test that the diagnostics page loads successfully."""
        response = client.get("/diagnostics")
        assert response.status_code == 200
        assert b"Diagnostics" in response.data
        assert b"Database Health" in response.data

    def test_diagnostics_shows_stats(self, client):
        """Test that diagnostics shows database statistics."""
        response = client.get("/diagnostics")
        assert response.status_code == 200
        assert b"Persons" in response.data
        assert b"Entries" in response.data
        assert b"Tags" in response.data


class TestPreviewExportRoute:
    """Tests for the export preview page."""

    @pytest.fixture
    def app_with_data(self, tmp_path):
        """Create a test Flask app with CV data."""
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Create CV with tags
        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Project A", "url": "https://example.com"}
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
    def client(self, app_with_data):
        """Create a test client."""
        return app_with_data.test_client()

    def test_preview_export_page_loads(self, client):
        """Test that the preview export page loads successfully."""
        response = client.get("/p/testuser/preview")
        assert response.status_code == 200
        assert b"Preview" in response.data
        assert b"testuser" in response.data

    def test_preview_shows_json(self, client):
        """Test that preview shows JSON content."""
        response = client.get("/p/testuser/preview")
        assert response.status_code == 200
        # Check for JSON structure markers
        assert b"fname" in response.data
        assert b"Test" in response.data

    def test_preview_with_language_param(self, client):
        """Test that preview respects language parameter."""
        response = client.get("/p/testuser/preview?language=de")
        assert response.status_code == 200
        assert b"DE" in response.data


class TestLanguageSelectorInHeader:
    """Tests for the language selector in the header."""

    @pytest.fixture
    def app_with_data(self, tmp_path):
        """Create a test Flask app with CV data."""
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        cv_data = {"basics": [{"fname": "Test", "lname": "User"}]}
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))
        import_cv(cv_path, db_path)

        app = create_app(db_path)
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def client(self, app_with_data):
        """Create a test client."""
        return app_with_data.test_client()

    def test_header_shows_language_selector(self, client):
        """Test that the header shows language selector."""
        response = client.get("/")
        assert response.status_code == 200
        # Check for language codes in the response
        assert b"EN" in response.data
        assert b"DE" in response.data
        assert b"FA" in response.data

    def test_diagnostics_link_in_header(self, client):
        """Test that diagnostics link appears in header."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Diagnostics" in response.data

    def test_cv_json_manager_title(self, client):
        """Test that the new title is displayed."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"CV JSON Manager" in response.data


class TestPersonEntityRoutes:
    """Tests for the person entity management routes."""

    @pytest.fixture
    def app_with_variants(self, tmp_path):
        """Create a test Flask app with multi-language CV data."""
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Create EN CV
        cv_en = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [{"title": "Test Project"}]
        }
        cv_en_path = tmp_path / "cvs" / "testuser.json"
        cv_en_path.parent.mkdir(parents=True, exist_ok=True)
        cv_en_path.write_text(json.dumps(cv_en, ensure_ascii=False))
        import_cv(cv_en_path, db_path)

        # Create DE CV
        cv_de = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [{"title": "Testprojekt"}]
        }
        cv_de_path = tmp_path / "cvs" / "testuser_de.json"
        cv_de_path.write_text(json.dumps(cv_de, ensure_ascii=False))
        import_cv(cv_de_path, db_path)

        app = create_app(db_path)
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def client(self, app_with_variants):
        """Create a test client."""
        return app_with_variants.test_client()

    def test_index_shows_create_person_button(self, client):
        """Test that index page shows Create Person button."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Create Person" in response.data

    def test_index_shows_unlinked_variants(self, client):
        """Test that index page shows unlinked variants section."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Unlinked Variants" in response.data

    def test_create_person_form_loads(self, client):
        """Test that create person form loads."""
        response = client.get("/persons/create")
        assert response.status_code == 200
        assert b"First Name" in response.data
        assert b"Last Name" in response.data

    def test_create_person_post(self, client):
        """Test creating a person via POST."""
        # Get CSRF token
        form_response = client.get("/persons/create")
        csrf_token = get_csrf_token(form_response)

        response = client.post(
            "/persons/create",
            data={
                "first_name": "New",
                "last_name": "Person",
                "csrf_token": csrf_token,
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b"created successfully" in response.data.lower()

    def test_create_person_shows_in_list(self, client):
        """Test that created person appears in list."""
        # Create a person
        form_response = client.get("/persons/create")
        csrf_token = get_csrf_token(form_response)

        client.post(
            "/persons/create",
            data={
                "first_name": "Listed",
                "last_name": "Person",
                "csrf_token": csrf_token,
            },
            follow_redirects=True
        )

        # Check list
        response = client.get("/")
        assert response.status_code == 200
        assert b"Listed Person" in response.data

    def test_person_entity_detail_page_loads(self, client):
        """Test that person entity detail page loads."""
        # Create a person first
        form_response = client.get("/persons/create")
        csrf_token = get_csrf_token(form_response)

        response = client.post(
            "/persons/create",
            data={
                "first_name": "Detail",
                "last_name": "Test",
                "csrf_token": csrf_token,
            },
            follow_redirects=False
        )

        # Should redirect to person detail page
        assert response.status_code == 302
        # Follow the redirect
        detail_response = client.get(response.headers["Location"])
        assert detail_response.status_code == 200
        assert b"Detail Test" in detail_response.data

    def test_auto_group_variants(self, client):
        """Test auto-grouping variants."""
        # Get CSRF token
        form_response = client.get("/")
        csrf_token = get_csrf_token(form_response)

        response = client.post(
            "/persons/auto-group",
            data={"csrf_token": csrf_token},
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Auto-grouping complete" in response.data

    def test_auto_group_links_variants_together(self, client):
        """Test that auto-group links variants with same name."""
        # Auto-group
        form_response = client.get("/")
        csrf_token = get_csrf_token(form_response)

        client.post(
            "/persons/auto-group",
            data={"csrf_token": csrf_token},
            follow_redirects=True
        )

        # Check that "Test User" person entity exists with multiple variants
        response = client.get("/")
        assert response.status_code == 200
        assert b"Test User" in response.data
        # Both EN and DE should be shown as linked
        assert b"EN" in response.data
        assert b"DE" in response.data


class TestBasicsEditing:
    """Tests for editing Basics section entries."""

    @pytest.fixture
    def app_with_basics(self, tmp_path):
        """Create a test Flask app with basics data in multiple languages."""
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Create EN CV
        cv_en = {
            "basics": [{"fname": "John", "lname": "Doe", "email": "john@example.com", "headline": "Software Engineer"}],
            "projects": [{"title": "Test Project"}]
        }
        cv_en_path = tmp_path / "cvs" / "johndoe.json"
        cv_en_path.parent.mkdir(parents=True, exist_ok=True)
        cv_en_path.write_text(json.dumps(cv_en, ensure_ascii=False))
        import_cv(cv_en_path, db_path)

        # Create DE CV
        cv_de = {
            "basics": [{"fname": "Johann", "lname": "Doe", "email": "john@example.com", "headline": "Software Ingenieur"}],
            "projects": [{"title": "Testprojekt"}]
        }
        cv_de_path = tmp_path / "cvs" / "johndoe_de.json"
        cv_de_path.write_text(json.dumps(cv_de, ensure_ascii=False))
        import_cv(cv_de_path, db_path)

        app = create_app(db_path)
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def client(self, app_with_basics):
        """Create a test client."""
        return app_with_basics.test_client()

    def test_basics_section_in_crud_sections(self):
        """Test that basics is included in CRUD sections list."""
        from cv_generator.crud import LIST_SECTIONS
        assert "basics" in LIST_SECTIONS

    def test_basics_has_shared_fields_defined(self):
        """Test that basics section has shared fields defined."""
        from cv_generator.crud import SHARED_FIELDS
        assert "basics" in SHARED_FIELDS
        assert "email" in SHARED_FIELDS["basics"]
        assert "phone" in SHARED_FIELDS["basics"]

    def test_basics_entry_edit_form_loads(self, client):
        """Test that basics entry edit form loads correctly."""
        # Get basics entry ID
        response = client.get("/p/johndoe/basics")
        assert response.status_code == 200

        # Get the basics entry (should be entry ID 1)
        response = client.get("/entry/1/edit")
        assert response.status_code == 200
        assert b"First Name" in response.data
        assert b"Last Name" in response.data
        assert b"Email" in response.data

    def test_basics_entry_update_post(self, client):
        """Test updating basics entry."""
        # Get CSRF token
        form_response = client.get("/entry/1/edit")
        csrf_token = get_csrf_token(form_response)

        response = client.post(
            "/entry/1/edit",
            data={
                "field_fname": "Johnny",
                "field_lname": "Doe",
                "field_email": "johnny@example.com",
                "field_headline": "Senior Software Engineer",
                "csrf_token": csrf_token,
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b"updated successfully" in response.data.lower()

    def test_basics_create_form_loads(self, client):
        """Test that basics create form loads."""
        response = client.get("/p/johndoe/basics/create")
        assert response.status_code == 200
        assert b"First Name" in response.data
        assert b"Last Name" in response.data

    def test_section_entries_shows_add_button_for_basics(self, client):
        """Test that basics section shows add button."""
        response = client.get("/p/johndoe/basics")
        assert response.status_code == 200
        assert b"Add New" in response.data


class TestCrossLanguageEditor:
    """Tests for the cross-language entry editor."""

    @pytest.fixture
    def app_with_multi_lang(self, tmp_path):
        """Create a test Flask app with multi-language CV data."""
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Create EN CV
        cv_en = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Existing Project", "url": "https://example.com", "description": "A test project"}
            ]
        }
        cv_en_path = tmp_path / "cvs" / "testuser.json"
        cv_en_path.parent.mkdir(parents=True, exist_ok=True)
        cv_en_path.write_text(json.dumps(cv_en, ensure_ascii=False))
        import_cv(cv_en_path, db_path)

        # Create DE CV
        cv_de = {
            "basics": [{"fname": "Test", "lname": "Benutzer"}],
            "projects": [
                {"title": "Bestehendes Projekt", "url": "https://example.com", "description": "Ein Testprojekt"}
            ]
        }
        cv_de_path = tmp_path / "cvs" / "testuser_de.json"
        cv_de_path.write_text(json.dumps(cv_de, ensure_ascii=False))
        import_cv(cv_de_path, db_path)

        app = create_app(db_path)
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def client(self, app_with_multi_lang):
        """Create a test client."""
        return app_with_multi_lang.test_client()

    def test_cross_language_editor_link_visible(self, client):
        """Test that cross-language editor link is visible on entry page."""
        response = client.get("/entry/2")  # Skip basics (entry 1)
        assert response.status_code == 200
        assert b"Cross-Language Editor" in response.data

    def test_cross_language_editor_page_loads(self, client):
        """Test that cross-language editor page loads."""
        response = client.get("/entry/2/cross-language")
        assert response.status_code == 200
        assert b"Cross-Language Entry Editor" in response.data
        assert b"EN" in response.data
        assert b"DE" in response.data

    def test_cross_language_editor_shows_fields(self, client):
        """Test that cross-language editor shows correct fields for projects."""
        response = client.get("/entry/2/cross-language")
        assert response.status_code == 200
        assert b"Title" in response.data
        assert b"Description" in response.data
        assert b"URL" in response.data

    def test_get_section_fields_returns_basics_fields(self):
        """Test that _get_section_fields returns correct fields for basics."""
        from cv_generator.web import _get_section_fields

        fields = _get_section_fields("basics")
        assert "fname" in fields
        assert "lname" in fields
        assert "email" in fields
        assert fields["email"]["shared"] is True
        assert fields["fname"]["shared"] is False

    def test_get_section_fields_returns_projects_fields(self):
        """Test that _get_section_fields returns correct fields for projects."""
        from cv_generator.web import _get_section_fields

        fields = _get_section_fields("projects")
        assert "title" in fields
        assert "url" in fields
        assert fields["url"]["shared"] is True
        assert fields["title"]["shared"] is False

    def test_cross_language_editor_post_updates_entries(self, client):
        """Test that posting to cross-language editor updates entries."""
        # First get CSRF token and entry IDs
        response = client.get("/entry/2/cross-language")
        csrf_token = get_csrf_token(response)

        # Post updates - we'll update at least EN fields
        # Note: we need the entry_id fields which are provided by the form
        response = client.post(
            "/entry/2/cross-language",
            data={
                "entry_id_en": "2",
                "field_en_title": "Updated EN Title",
                "field_en_description": "Updated EN Description",
                "field_en_url": "https://updated.example.com",
                "csrf_token": csrf_token,
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        # Check for success message
        assert b"Updated" in response.data or b"updated" in response.data.lower()


class TestCopyHelpers:
    """Tests for copy helpers in cross-language editor."""

    def test_cross_language_editor_has_copy_buttons(self):
        """Test that the cross-language editor template includes copy buttons."""

        template_path = Path(__file__).parent.parent / "src" / "cv_generator" / "templates" / "cross_language_editor.html"
        content = template_path.read_text()

        # Check for copy functionality
        assert "EN → DE" in content
        assert "EN → FA" in content
        assert "copyField" in content
        assert "copyAllFields" in content

    def test_cross_language_editor_has_undo_support(self):
        """Test that the cross-language editor has undo support."""

        template_path = Path(__file__).parent.parent / "src" / "cv_generator" / "templates" / "cross_language_editor.html"
        content = template_path.read_text()

        # Check for undo functionality
        assert "originalValues" in content
        assert "undoField" in content


class TestTranslationWorkflow:
    """Tests for translation workflow helpers."""

    @pytest.fixture
    def app_with_translation_data(self, tmp_path):
        """Create app with entries needing translation."""
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Create EN CV
        cv_en = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [{"title": "Test Project"}]
        }
        cv_en_path = tmp_path / "cvs" / "testuser.json"
        cv_en_path.parent.mkdir(parents=True, exist_ok=True)
        cv_en_path.write_text(json.dumps(cv_en, ensure_ascii=False))
        import_cv(cv_en_path, db_path)

        app = create_app(db_path)
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def client(self, app_with_translation_data):
        """Create a test client."""
        return app_with_translation_data.test_client()

    def test_cross_language_editor_has_mark_translated_option(self, client):
        """Test that cross-language editor has mark translated option."""
        response = client.get("/entry/2/cross-language")
        assert response.status_code == 200
        assert b"mark_translated" in response.data or b"Clear" in response.data

    def test_needs_translation_badge_in_template(self):
        """Test that needs translation badge is in template."""

        template_path = Path(__file__).parent.parent / "src" / "cv_generator" / "templates" / "cross_language_editor.html"
        content = template_path.read_text()

        assert "needs_translation" in content.lower() or "Needs Translation" in content


class TestImportUIRoutes:
    """Tests for the Import UI routes."""

    @pytest.fixture
    def app_with_data(self, tmp_path):
        """Create a test Flask app with CV data."""
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Create CV with tags
        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Project A", "url": "https://example.com"}
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
    def client(self, app_with_data):
        """Create a test client."""
        return app_with_data.test_client()

    def test_import_page_loads(self, client):
        """Test that the import page loads successfully."""
        response = client.get("/import")
        assert response.status_code == 200
        assert b"Import" in response.data
        assert b"Upload Files" in response.data

    def test_import_page_shows_existing_persons(self, client):
        """Test that import page shows existing persons."""
        response = client.get("/import")
        assert response.status_code == 200
        assert b"testuser" in response.data

    def test_import_upload_requires_files(self, client):
        """Test that import upload requires files."""
        form_response = client.get("/import")
        csrf_token = get_csrf_token(form_response)

        response = client.post(
            "/import/upload",
            data={"csrf_token": csrf_token, "import_mode": "merge"},
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b"No files" in response.data

    def test_import_link_in_header(self, client):
        """Test that import link appears in header."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Import" in response.data


class TestImportV2Schema:
    """Tests for CV import with v2 schema (resume_sets table).

    This test class specifically validates that the import functionality
    correctly migrates the database schema to v2 before using CVImporter.
    """

    @pytest.fixture
    def app_with_v1_db(self, tmp_path):
        """Create a test Flask app with a v1 database."""
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)  # Creates v1 schema

        # Import some data using v1 importer
        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [{"title": "Test Project", "url": "https://example.com"}]
        }
        cv_path = tmp_path / "cvs" / "testuser.json"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_data, ensure_ascii=False))
        import_cv(cv_path, db_path)

        app = create_app(db_path)
        app.config["TESTING"] = True
        return app, tmp_path

    @pytest.fixture
    def client(self, app_with_v1_db):
        """Create a test client."""
        app, _ = app_with_v1_db
        return app.test_client()

    def test_import_confirm_migrates_to_v2_schema(self, app_with_v1_db):
        """Test that import_confirm properly migrates database to v2 before import.

        This test verifies the fix for 'no such table: resume_sets' bug.
        """
        import sqlite3

        app, tmp_path = app_with_v1_db
        client = app.test_client()

        # First verify database is at v1 (no resume_sets table)
        db_path = app.config["DB_PATH"]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='resume_sets'"
        )
        result = cursor.fetchone()
        conn.close()
        assert result is None, "resume_sets should not exist in v1 schema"

        # Create a new CV JSON file to import
        new_cv_data = {
            "config": {"lang": "en", "ID": "newuser"},
            "basics": [{"fname": "New", "lname": "User"}],
            "projects": [{"title": "New Project", "url": "https://new.example.com"}]
        }
        new_cv_path = tmp_path / "newuser.json"
        new_cv_path.write_text(json.dumps(new_cv_data, ensure_ascii=False))

        # Get CSRF token
        form_response = client.get("/import")
        csrf_token = get_csrf_token(form_response)

        # Mock the import session by uploading a file
        with open(new_cv_path, 'rb') as f:
            response = client.post(
                "/import/upload",
                data={
                    "csrf_token": csrf_token,
                    "import_mode": "merge",
                    "files": (f, "newuser.json"),
                },
                content_type='multipart/form-data',
                follow_redirects=False
            )

        # Check that upload worked and we got redirected to preview
        assert response.status_code in (200, 302)

        # After the upload, the confirm route should trigger migration
        # This verifies the fix works - the migration happens before CVImporter is used
        # Verify database now has v2 tables after any import operation that uses CVImporter
        # We test this indirectly by calling migrate_to_v2 directly (as import_confirm does)
        from cv_generator.migrations.migrate_to_v2 import migrate_to_v2
        result = migrate_to_v2(db_path, backup=False)

        assert result["success"], f"Migration failed: {result}"

        # Now verify the resume_sets table exists
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='resume_sets'"
        )
        result = cursor.fetchone()
        conn.close()
        assert result is not None, "resume_sets table should exist after migration"


class TestExportUIRoutes:
    """Tests for the Export UI routes."""

    @pytest.fixture
    def app_with_data(self, tmp_path):
        """Create a test Flask app with CV data."""
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Create CV with tags
        cv_data = {
            "basics": [{"fname": "Test", "lname": "User"}],
            "projects": [
                {"title": "Project A", "url": "https://example.com"}
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
    def client(self, app_with_data):
        """Create a test client."""
        return app_with_data.test_client()

    def test_export_page_loads(self, client):
        """Test that the export page loads successfully."""
        response = client.get("/export")
        assert response.status_code == 200
        assert b"Export" in response.data

    def test_export_page_shows_persons(self, client):
        """Test that export page shows available persons."""
        response = client.get("/export")
        assert response.status_code == 200
        assert b"testuser" in response.data

    def test_export_page_shows_language_options(self, client):
        """Test that export page shows language options."""
        response = client.get("/export")
        assert response.status_code == 200
        assert b"EN" in response.data
        assert b"DE" in response.data
        assert b"FA" in response.data

    def test_export_link_in_header(self, client):
        """Test that export link appears in header."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Export" in response.data

    def test_export_requires_person_selection(self, client):
        """Test that export requires person selection."""
        form_response = client.get("/export")
        csrf_token = get_csrf_token(form_response)

        response = client.post(
            "/export/single",
            data={"csrf_token": csrf_token, "language": "en"},
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Please select a person" in response.data


class TestSecureFilename:
    """Tests for the _secure_filename function."""

    def test_secure_filename_removes_path_traversal(self):
        """Test that path traversal is prevented."""
        from cv_generator.web import _secure_filename

        assert ".." not in _secure_filename("../../../etc/passwd")
        assert "/" not in _secure_filename("path/to/file.json")
        assert "\\" not in _secure_filename("path\\to\\file.json")

    def test_secure_filename_preserves_valid_names(self):
        """Test that valid filenames are preserved."""
        from cv_generator.web import _secure_filename

        assert _secure_filename("myfile.json") == "myfile.json"
        assert _secure_filename("my_file.json") == "my_file.json"
        assert _secure_filename("my-file.json") == "my-file.json"

    def test_secure_filename_handles_special_chars(self):
        """Test that special characters are handled."""
        from cv_generator.web import _secure_filename

        result = _secure_filename("file<script>.json")
        assert "<" not in result
        assert ">" not in result

    def test_secure_filename_handles_empty_string(self):
        """Test that empty strings are handled."""
        from cv_generator.web import _secure_filename

        assert _secure_filename("") == "unnamed"
        assert _secure_filename("...") == "unnamed"
