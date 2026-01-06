"""
Web UI for CV Generator Tag Manager.

Provides a local-first web interface for:
- Creating and managing tags
- Browsing CV entries by person and section
- Assigning/unassigning tags to entries
- Exporting updated CVs to JSON
- Language-aware tag display and filtering

Language-Aware Tagging Strategy:
================================
This module implements Option A from the tagging strategy design:
- Canonical ID: English key (e.g., "Full CV")
- Display: Localized name per active language
- Storage: Database stores canonical IDs
- Export: Writes language-specific tag strings based on export language

Security Features (opt-in):
- Basic auth: Set CVGEN_WEB_AUTH=user:pass or CVGEN_WEB_USER + CVGEN_WEB_PASSWORD
- Host binding safety: Warns when binding to non-localhost
- Rate limiting: Simple time-based throttle for export/write operations
- CSRF protection: Automatic token validation for all POST requests
"""

from __future__ import annotations

import functools
import json
import logging
import os
import secrets
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for

from .crud import (
    LIST_SECTIONS as CRUD_SECTIONS,
)
from .crud import (
    create_entry as crud_create_entry,
)
from .crud import (
    delete_entry as crud_delete_entry,
)
from .crud import (
    get_linked_entries,
)
from .crud import (
    update_entry as crud_update_entry,
)
from .db import (
    cleanup_orphan_tag_references,
    create_tag,
    delete_tag,
    doctor,
    export_cv,
    export_cv_to_file,
    get_db_path,
    get_entry,
    get_person_sections,
    get_section_entries,
    get_tag_by_name,
    list_persons,
    list_tags,
    update_entry_tags,
    update_tag,
)
from .errors import ConfigurationError, ValidationError
from .integrity import run_integrity_check
from .paths import get_default_output_path
from .person import (
    auto_group_variants,
    create_person_entity,
    ensure_person_entity_schema,
    get_person_entity,
    get_unlinked_variants,
    link_variant_to_person,
    list_person_entities,
)
from .tags import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    get_tag_catalog,
    validate_tags,
)
from .vocabulary import (
    get_vocabulary,
)

logger = logging.getLogger(__name__)

# Maximum number of items to show in warning messages
MAX_WARNING_ITEMS = 5

# Rate limiting configuration
THROTTLE_SECONDS = 5  # Minimum seconds between export/write operations

# CSRF token configuration
CSRF_TOKEN_LENGTH = 32  # Length of CSRF token in bytes (produces 43-character URL-safe string)
CSRF_SESSION_KEY = "_csrf_token"
CSRF_FORM_FIELD = "csrf_token"


def generate_csrf_token() -> str:
    """
    Generate or retrieve a CSRF token from the session.

    The token is generated once per session and reused for all requests
    within that session. This provides CSRF protection while maintaining
    a good user experience (no token expiration during a session).

    Returns:
        A URL-safe CSRF token string.
    """
    if CSRF_SESSION_KEY not in session:
        session[CSRF_SESSION_KEY] = secrets.token_urlsafe(CSRF_TOKEN_LENGTH)
    return session[CSRF_SESSION_KEY]


def validate_csrf_token(token: Optional[str]) -> bool:
    """
    Validate a CSRF token against the one stored in the session.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        token: The CSRF token from the form submission.

    Returns:
        True if the token is valid, False otherwise.
    """
    if token is None:
        return False
    expected = session.get(CSRF_SESSION_KEY)
    if expected is None:
        return False
    return secrets.compare_digest(token, expected)


def get_auth_credentials() -> Optional[tuple[str, str]]:
    """
    Get authentication credentials from environment variables.

    Credentials can be set via:
    - CVGEN_WEB_AUTH=user:pass (combined format)
    - CVGEN_WEB_USER + CVGEN_WEB_PASSWORD (separate vars)

    Returns:
        Tuple of (username, password) if auth is configured, None otherwise.
        Credentials are never logged in plaintext.
    """
    # Try combined format first
    auth_combined = os.environ.get("CVGEN_WEB_AUTH", "").strip()
    if auth_combined and ":" in auth_combined:
        parts = auth_combined.split(":", 1)
        if len(parts) == 2 and parts[0] and parts[1]:
            logger.debug("Auth configured via CVGEN_WEB_AUTH")
            return (parts[0], parts[1])

    # Try separate vars
    user = os.environ.get("CVGEN_WEB_USER", "").strip()
    password = os.environ.get("CVGEN_WEB_PASSWORD", "").strip()
    if user and password:
        logger.debug("Auth configured via CVGEN_WEB_USER/CVGEN_WEB_PASSWORD")
        return (user, password)

    return None


def check_auth(username: str, password: str) -> bool:
    """
    Verify credentials against configured auth.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        username: Provided username.
        password: Provided password.

    Returns:
        True if credentials match, False otherwise.
    """
    creds = get_auth_credentials()
    if creds is None:
        return True  # No auth configured = allow all

    expected_user, expected_pass = creds
    # Use constant-time comparison to prevent timing attacks
    user_ok = secrets.compare_digest(username, expected_user)
    pass_ok = secrets.compare_digest(password, expected_pass)
    return user_ok and pass_ok


def requires_auth(f: Callable) -> Callable:
    """
    Decorator that requires HTTP Basic Auth if configured.

    If no auth is configured (no env vars set), requests pass through.
    If auth is configured but credentials are wrong, returns 401.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        creds = get_auth_credentials()
        if creds is None:
            # No auth configured, allow through
            return f(*args, **kwargs)

        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return Response(
                "Authentication required.\n"
                "Configure via CVGEN_WEB_AUTH=user:pass or "
                "CVGEN_WEB_USER + CVGEN_WEB_PASSWORD environment variables.",
                401,
                {"WWW-Authenticate": 'Basic realm="CV Generator Web UI"'}
            )
        return f(*args, **kwargs)
    return decorated


def check_throttle(action_key: str) -> Optional[int]:
    """
    Check if an action is being performed too frequently.

    Args:
        action_key: Unique key for the action (e.g., "export_ramin").

    Returns:
        Seconds to wait if throttled, None if action is allowed.
    """
    throttle_key = f"throttle_{action_key}"
    last_action = session.get(throttle_key, 0)
    now = time.time()
    elapsed = now - last_action

    if elapsed < THROTTLE_SECONDS:
        return int(THROTTLE_SECONDS - elapsed) + 1

    # Update last action time
    session[throttle_key] = now
    return None


def generate_unique_filename(base_name: str, extension: str = ".json") -> str:
    """
    Generate a unique filename with timestamp.

    Args:
        base_name: Base name for the file (e.g., "ramin").
        extension: File extension (default: ".json").

    Returns:
        Unique filename like "ramin_20260104_082034.json".
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}{extension}"


def _secure_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal attacks.

    This function removes or replaces potentially dangerous characters
    from filenames to prevent security vulnerabilities like path traversal.

    Args:
        filename: The original filename from user upload.

    Returns:
        A sanitized filename safe for filesystem operations.
    """
    import re

    # Normalize unicode characters
    import unicodedata
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")

    # Remove any path components (directory traversal protection)
    filename = filename.replace("/", "_").replace("\\", "_")

    # Remove potentially dangerous characters, keep only alphanumeric, dots, underscores, hyphens
    filename = re.sub(r"[^\w.\-]", "_", filename)

    # Remove leading/trailing dots and underscores
    filename = filename.strip("._")

    # Collapse multiple underscores
    filename = re.sub(r"_+", "_", filename)

    # Default filename if empty
    if not filename:
        filename = "unnamed"

    return filename


def format_sync_result_message(
    operation: str,
    sync_result: dict,
    stable_id: Optional[str] = None
) -> str:
    """
    Format a user-friendly message from a sync result.

    Args:
        operation: Operation type ("create", "update", "delete")
        sync_result: Sync result dictionary from CRUD operations
        stable_id: Optional stable ID to include in message

    Returns:
        Formatted message string suitable for flash()
    """
    synced_langs = sync_result.get("synced_languages", [])
    skipped_langs = sync_result.get("skipped_languages", {})

    if operation == "create":
        if synced_langs:
            msg = f"✓ Entry created in {len(synced_langs)} language(s): {', '.join(lang.upper() for lang in synced_langs)}."
        else:
            msg = "✓ Entry created successfully."
        if skipped_langs:
            msg += f" (Skipped: {', '.join(f'{k.upper()} - {v}' for k, v in skipped_langs.items())})"
        if stable_id:
            msg += f" ID: {stable_id[:8]}..."

    elif operation == "update":
        msg = "✓ Entry updated successfully."
        if len(synced_langs) > 1:
            msg += f" Shared fields synced to: {', '.join(lang.upper() for lang in synced_langs)}."

    elif operation == "delete":
        if len(synced_langs) > 1:
            msg = f"Entry deleted successfully from {len(synced_langs)} language(s): {', '.join(lang.upper() for lang in synced_langs)}."
        else:
            msg = "Entry deleted successfully."

    else:
        msg = f"Operation {operation} completed successfully."

    return msg


def is_localhost(host: str) -> bool:
    """
    Check if a host string represents localhost.

    Args:
        host: Host string to check.

    Returns:
        True if host is localhost (127.x.x.x or "localhost"), False otherwise.
    """
    if host == "localhost":
        return True
    if host.startswith("127."):
        return True
    if host == "::1":
        return True
    return False


def get_secret_key() -> str:
    """
    Get Flask secret key with the following precedence:
    1. Environment variable CVGEN_WEB_SECRET
    2. State file .cvgen/web_secret
    3. Generate new random key and save to state file

    Returns:
        A secret key string for Flask session management.
    """
    # Try environment variable first (highest precedence)
    secret = os.environ.get('CVGEN_WEB_SECRET')
    if secret and secret.strip():
        logger.info("Using secret key from environment variable")
        return secret.strip()

    # Try state file
    state_dir = Path.cwd() / '.cvgen'
    secret_file = state_dir / 'web_secret'

    if secret_file.exists():
        try:
            saved_secret = secret_file.read_text().strip()
            if saved_secret:
                logger.info("Using secret key from state file")
                return saved_secret
        except Exception as e:
            logger.warning(f"Could not read secret key file: {e}")

    # Generate new secret
    logger.info("Generating new secret key")
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        new_secret = secrets.token_urlsafe(32)
        secret_file.write_text(new_secret)

        # Restrict file permissions (Unix only, ignored on Windows)
        try:
            secret_file.chmod(0o600)
            logger.debug(f"Set restricted permissions on {secret_file}")
        except Exception:
            pass  # chmod may fail on Windows, which is acceptable

        return new_secret
    except Exception as e:
        # If we can't write to disk, generate an ephemeral secret
        logger.warning(f"Could not save secret key to disk: {e}")
        logger.warning("Using ephemeral secret key (sessions won't persist)")
        return secrets.token_urlsafe(32)


def get_entry_summary(section: str, data: dict[str, Any]) -> str:
    """
    Get a human-readable summary of an entry based on section type.

    Args:
        section: The section name.
        data: The entry data.

    Returns:
        A summary string for display.
    """
    if section == "projects":
        title = data.get("title", "Untitled Project")
        url = data.get("url", "")
        return f"{title}" + (f" ({url})" if url else "")

    elif section == "experiences":
        role = data.get("role", "Unknown Role")
        institution = data.get("institution", "")
        duration = data.get("duration", "")
        parts = [role]
        if institution:
            parts.append(f"@ {institution}")
        if duration:
            parts.append(f"({duration})")
        return " ".join(parts)

    elif section == "publications":
        title = data.get("title", "Untitled Publication")
        status = data.get("status", "")
        year = data.get("year", "")
        parts = [title]
        if status:
            parts.append(f"[{status}]")
        if year:
            parts.append(f"({year})")
        return " ".join(parts)

    elif section == "references":
        name = data.get("name", "Unknown")
        institution = data.get("institution", "")
        return f"{name}" + (f" ({institution})" if institution else "")

    elif section == "education":
        institution = data.get("institution", "Unknown Institution")
        area = data.get("area", "")
        study_type = data.get("studyType", "")
        parts = [institution]
        if area:
            parts.append(f"- {area}")
        if study_type:
            parts.append(f"({study_type})")
        return " ".join(parts)

    elif section == "languages":
        language = data.get("language", "Unknown")
        fluency = data.get("fluency", "")
        return f"{language}" + (f" ({fluency})" if fluency else "")

    elif section == "profiles":
        network = data.get("network", "Unknown")
        username = data.get("username", "")
        return f"{network}" + (f": {username}" if username else "")

    elif section == "basics":
        fname = data.get("fname", "")
        lname = data.get("lname", "")
        return f"{fname} {lname}".strip() or "Basic Info"

    elif section == "skills":
        # Skills entries are now individual skill items
        short_name = data.get("short_name", "")
        long_name = data.get("long_name", "")
        if short_name and long_name and short_name != long_name:
            return f"{short_name} ({long_name})"
        elif short_name:
            return short_name
        elif long_name:
            return long_name
        else:
            return "Unknown Skill"

    elif section == "workshop_and_certifications":
        issuer = data.get("issuer", "Unknown Issuer")
        title = data.get("title", data.get("name", ""))
        return f"{title}" + (f" ({issuer})" if issuer and title else issuer)

    else:
        # Generic fallback: try common fields
        for key in ["title", "name", "role", "institution", "network"]:
            if key in data:
                return str(data[key])
        return f"{section} entry"


def create_app(db_path: Optional[Path] = None) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        db_path: Path to the database file. Uses default if None.

    Returns:
        Configured Flask application.
    """
    # Get the templates directory
    templates_dir = Path(__file__).parent / "templates"
    static_dir = Path(__file__).parent / "static"

    app = Flask(
        __name__,
        template_folder=str(templates_dir),
        static_folder=str(static_dir)
    )
    app.secret_key = get_secret_key()

    # Store db_path in app config
    if db_path is None:
        db_path = get_db_path()
    app.config["DB_PATH"] = db_path

    def get_current_language() -> str:
        """Get current language from session, defaulting to English."""
        return session.get("language", DEFAULT_LANGUAGE)

    def get_tag_label(tag_name: str, language: Optional[str] = None) -> str:
        """Get localized label for a tag."""
        lang = language or get_current_language()
        catalog = get_tag_catalog()
        return catalog.get_tag_label(tag_name, lang)

    def get_tag_display(tag: dict[str, Any], language: Optional[str] = None) -> dict[str, Any]:
        """Add display_label to a tag dict for the current language."""
        lang = language or get_current_language()
        catalog = get_tag_catalog()
        tag_copy = tag.copy()
        tag_copy["display_label"] = catalog.get_tag_label(tag["name"], lang)
        tag_copy["has_translation"] = catalog.has_translation(tag["name"], lang)
        return tag_copy

    @app.context_processor
    def inject_helpers():
        """Inject helper functions into templates."""
        catalog = get_tag_catalog()
        vocab = get_vocabulary()
        current_lang = get_current_language()
        # Debug mode shows canonical keys under labels (controlled via session)
        show_canonical = session.get("show_canonical_keys", False)

        def get_localized_field_label(field_key: str, lang: Optional[str] = None) -> str:
            """Get localized label for a field key."""
            return vocab.get_label(field_key, lang or current_lang)

        def get_localized_section_label(section_key: str, lang: Optional[str] = None) -> str:
            """Get localized label for a section name."""
            return vocab.get_section_label(section_key, lang or current_lang)

        return {
            "get_entry_summary": get_entry_summary,
            "get_tag_label": get_tag_label,
            "get_tag_display": get_tag_display,
            "get_field_label": get_localized_field_label,
            "get_section_label": get_localized_section_label,
            "current_language": current_lang,
            "supported_languages": SUPPORTED_LANGUAGES,
            "tag_catalog": catalog,
            "vocabulary": vocab,
            "csrf_token": generate_csrf_token,
            "show_canonical_keys": show_canonical,
        }

    @app.before_request
    def validate_csrf():
        """Validate CSRF token on all POST requests."""
        if request.method == "POST":
            token = request.form.get(CSRF_FORM_FIELD)
            if not validate_csrf_token(token):
                logger.warning("CSRF token validation failed for %s", request.path)
                return Response(
                    "CSRF token validation failed. Please reload the page and try again.",
                    400,
                )

    @app.route("/")
    @requires_auth
    def index():
        """Home page - person entity selector with grouped variants."""
        try:
            # Ensure person entity schema exists and auto-group variants
            ensure_person_entity_schema(app.config["DB_PATH"])

            # Get grouped person entities
            person_entities = list_person_entities(app.config["DB_PATH"])

            # Get unlinked variants for display
            unlinked = get_unlinked_variants(app.config["DB_PATH"])

            # Also get legacy persons list for backward compatibility
            persons = list_persons(app.config["DB_PATH"])
        except ConfigurationError as e:
            flash(str(e), "error")
            person_entities = []
            unlinked = []
            persons = []

        return render_template(
            "index.html",
            person_entities=person_entities,
            unlinked_variants=unlinked,
            persons=persons,
            supported_languages=SUPPORTED_LANGUAGES
        )

    @app.route("/persons/create", methods=["GET", "POST"])
    @requires_auth
    def create_person_route():
        """Create a new person entity."""
        if request.method == "POST":
            first_name = request.form.get("first_name", "").strip()
            last_name = request.form.get("last_name", "").strip()
            display_name = request.form.get("display_name", "").strip() or None
            notes = request.form.get("notes", "").strip() or None

            try:
                person = create_person_entity(
                    first_name=first_name,
                    last_name=last_name,
                    display_name=display_name,
                    notes=notes,
                    db_path=app.config["DB_PATH"]
                )
                flash(f"Person '{person['display_name']}' created successfully", "success")
                return redirect(url_for("person_entity_detail", person_entity_id=person["id"]))
            except (ConfigurationError, ValidationError) as e:
                flash(str(e), "error")

        return render_template("person_form.html", action="Create", person=None)

    @app.route("/persons/<person_entity_id>")
    @requires_auth
    def person_entity_detail(person_entity_id: str):
        """Person entity detail page - shows all language variants."""
        try:
            person = get_person_entity(person_entity_id, app.config["DB_PATH"])
            if not person:
                flash("Person not found", "error")
                return redirect(url_for("index"))

            # Get missing languages
            existing_langs = set(person["variants"].keys())
            missing_langs = [lang for lang in SUPPORTED_LANGUAGES if lang not in existing_langs]

            # Get unlinked variants that could be linked to this person
            unlinked = get_unlinked_variants(app.config["DB_PATH"])

        except ConfigurationError as e:
            flash(str(e), "error")
            return redirect(url_for("index"))

        return render_template(
            "person_entity.html",
            person=person,
            missing_languages=missing_langs,
            unlinked_variants=unlinked,
            supported_languages=SUPPORTED_LANGUAGES
        )

    @app.route("/persons/<person_entity_id>/link", methods=["POST"])
    @requires_auth
    def link_variant_route(person_entity_id: str):
        """Link a CV variant to a person entity."""
        variant_person_id = request.form.get("person_id")
        language = request.form.get("language", "en")

        if not variant_person_id:
            flash("Please select a variant to link", "error")
            return redirect(url_for("person_entity_detail", person_entity_id=person_entity_id))

        try:
            link_variant_to_person(
                person_entity_id=person_entity_id,
                person_id=int(variant_person_id),
                language=language,
                db_path=app.config["DB_PATH"]
            )
            flash(f"Variant linked successfully ({language.upper()})", "success")
        except (ConfigurationError, ValidationError) as e:
            flash(str(e), "error")

        return redirect(url_for("person_entity_detail", person_entity_id=person_entity_id))

    @app.route("/persons/auto-group", methods=["POST"])
    @requires_auth
    def auto_group_route():
        """Automatically group CV variants into person entities based on basics names."""
        try:
            stats = auto_group_variants(app.config["DB_PATH"], dry_run=False)
            flash(
                f"Auto-grouping complete: {stats['persons_created']} persons created, "
                f"{stats['variants_linked']} variants linked",
                "success"
            )
        except (ConfigurationError, ValidationError) as e:
            flash(str(e), "error")

        return redirect(url_for("index"))

    @app.route("/p/<person>")
    @requires_auth
    def person_dashboard(person: str):
        """Person dashboard - section selector."""
        try:
            persons = list_persons(app.config["DB_PATH"])
            person_info = next((p for p in persons if p["slug"] == person), None)
            if not person_info:
                flash(f"Person '{person}' not found", "error")
                return redirect(url_for("index"))

            sections = get_person_sections(person, app.config["DB_PATH"])
        except ConfigurationError as e:
            flash(str(e), "error")
            return redirect(url_for("index"))

        return render_template(
            "person.html",
            person=person_info,
            sections=sections
        )

    @app.route("/p/<person>/<section>")
    @requires_auth
    def section_entries(person: str, section: str):
        """Section entries list."""
        try:
            entries = get_section_entries(person, section, app.config["DB_PATH"])
            persons = list_persons(app.config["DB_PATH"])
            person_info = next((p for p in persons if p["slug"] == person), None)
        except ConfigurationError as e:
            flash(str(e), "error")
            return redirect(url_for("person_dashboard", person=person))

        # Add summaries and skill category info
        skills_by_category = {}  # For skills section grouping
        for entry in entries:
            entry["summary"] = get_entry_summary(section, entry["data"])

            # For skills, extract category info from identity_key
            if section == "skills" and entry.get("identity_key", "").startswith("skills/"):
                from .entry_path import parse_skill_entry_path
                parsed = parse_skill_entry_path(entry["identity_key"])
                if parsed:
                    parent_cat, sub_cat, skill_key = parsed
                    entry["parent_category"] = parent_cat
                    entry["sub_category"] = sub_cat

                    # Group for tree display
                    if parent_cat not in skills_by_category:
                        skills_by_category[parent_cat] = {}
                    if sub_cat not in skills_by_category[parent_cat]:
                        skills_by_category[parent_cat][sub_cat] = []
                    skills_by_category[parent_cat][sub_cat].append(entry)

        return render_template(
            "section.html",
            person=person_info,
            section=section,
            entries=entries,
            skills_by_category=skills_by_category if section == "skills" else None
        )

    @app.route("/entry/<int:entry_id>")
    @requires_auth
    def entry_detail(entry_id: int):
        """Entry detail view with tag assignment and language-aware display."""
        try:
            entry = get_entry(entry_id, app.config["DB_PATH"])
            if not entry:
                flash(f"Entry {entry_id} not found", "error")
                return redirect(url_for("index"))

            all_tags = list_tags(app.config["DB_PATH"])
            # Add localized display labels to tags
            all_tags_with_labels = [get_tag_display(tag) for tag in all_tags]
            entry["summary"] = get_entry_summary(entry["section"], entry["data"])

            # Validate tags on this entry
            current_lang = get_current_language()
            if entry["tags"] and current_lang != DEFAULT_LANGUAGE:
                validation = validate_tags(entry["tags"], current_lang)
                if validation["missing_translations"]:
                    missing = validation["missing_translations"]
                    flash(
                        f"Some tags lack translation for {current_lang}: "
                        f"{', '.join(missing[:MAX_WARNING_ITEMS])}"
                        f"{'...' if len(missing) > MAX_WARNING_ITEMS else ''}",
                        "warning"
                    )
        except ConfigurationError as e:
            flash(str(e), "error")
            return redirect(url_for("index"))

        return render_template(
            "entry.html",
            entry=entry,
            all_tags=all_tags_with_labels,
            data_json=json.dumps(entry["data"], indent=2, ensure_ascii=False)
        )

    @app.route("/entry/<int:entry_id>/tags", methods=["POST"])
    @requires_auth
    def update_entry_tags_route(entry_id: int):
        """Update tags for an entry."""
        try:
            entry = get_entry(entry_id, app.config["DB_PATH"])
            if not entry:
                flash(f"Entry {entry_id} not found", "error")
                return redirect(url_for("index"))

            # Get selected tags from form
            selected_tags = request.form.getlist("tags")

            # Update tags
            update_entry_tags(entry_id, selected_tags, app.config["DB_PATH"])
            flash("Tags updated successfully", "success")

        except (ConfigurationError, ValidationError) as e:
            flash(str(e), "error")

        return redirect(url_for("entry_detail", entry_id=entry_id))

    @app.route("/tags")
    @requires_auth
    def tags_list():
        """List all tags with language-aware display."""
        try:
            tags = list_tags(app.config["DB_PATH"])
            # Add localized display labels to tags
            tags_with_labels = [get_tag_display(tag) for tag in tags]
        except ConfigurationError as e:
            flash(str(e), "error")
            tags_with_labels = []

        # Get validation warnings for missing translations
        current_lang = get_current_language()
        if current_lang != DEFAULT_LANGUAGE:
            catalog = get_tag_catalog()
            missing = catalog.get_missing_translations(current_lang)
            if missing:
                flash(
                    f"Warning: {len(missing)} tag(s) lack translation for {current_lang}: "
                    f"{', '.join(missing[:MAX_WARNING_ITEMS])}"
                    f"{'...' if len(missing) > MAX_WARNING_ITEMS else ''}",
                    "warning"
                )

        return render_template("tags.html", tags=tags_with_labels)

    @app.route("/language/<lang>")
    @requires_auth
    def set_language(lang: str):
        """Set the current language for tag display."""
        if lang not in SUPPORTED_LANGUAGES:
            flash(f"Unsupported language: {lang}. Supported: {', '.join(SUPPORTED_LANGUAGES)}", "error")
        else:
            session["language"] = lang
            flash(f"Language set to: {lang}", "success")
        return redirect(request.referrer or url_for("index"))

    @app.route("/debug/toggle-canonical-keys")
    @requires_auth
    def toggle_canonical_keys():
        """Toggle debug mode to show/hide canonical keys under labels."""
        current = session.get("show_canonical_keys", False)
        session["show_canonical_keys"] = not current
        if session["show_canonical_keys"]:
            flash("Developer mode: Showing canonical keys under labels", "success")
        else:
            flash("Developer mode: Hiding canonical keys", "success")
        return redirect(request.referrer or url_for("index"))

    @app.route("/tags/create", methods=["GET", "POST"])
    @requires_auth
    def create_tag_route():
        """Create a new tag."""
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            description = request.form.get("description", "").strip() or None

            try:
                create_tag(name, description, app.config["DB_PATH"])
                flash(f"Tag '{name}' created successfully", "success")
                return redirect(url_for("tags_list"))
            except (ConfigurationError, ValidationError) as e:
                flash(str(e), "error")

        return render_template("tag_form.html", tag=None, action="Create")

    @app.route("/tags/<name>/edit", methods=["GET", "POST"])
    @requires_auth
    def edit_tag_route(name: str):
        """Edit a tag."""
        try:
            tag = get_tag_by_name(name, app.config["DB_PATH"])
            if not tag:
                flash(f"Tag '{name}' not found", "error")
                return redirect(url_for("tags_list"))
        except ConfigurationError as e:
            flash(str(e), "error")
            return redirect(url_for("tags_list"))

        if request.method == "POST":
            new_name = request.form.get("name", "").strip()
            description = request.form.get("description", "").strip() or None

            try:
                update_tag(name, new_name=new_name, description=description, db_path=app.config["DB_PATH"])
                flash("Tag updated successfully", "success")
                return redirect(url_for("tags_list"))
            except (ConfigurationError, ValidationError) as e:
                flash(str(e), "error")

        return render_template("tag_form.html", tag=tag, action="Edit")

    @app.route("/tags/<name>/delete", methods=["POST"])
    @requires_auth
    def delete_tag_route(name: str):
        """Delete a tag."""
        try:
            if delete_tag(name, app.config["DB_PATH"]):
                flash(f"Tag '{name}' deleted successfully", "success")
            else:
                flash(f"Tag '{name}' not found", "error")
        except ConfigurationError as e:
            flash(str(e), "error")

        return redirect(url_for("tags_list"))

    @app.route("/export/<person>", methods=["POST"])
    @requires_auth
    def export_person(person: str):
        """Export a person's CV to JSON with rate limiting, safe filenames, and language-aware tags."""
        # Check throttle
        wait_time = check_throttle(f"export_{person}")
        if wait_time is not None:
            flash(
                f"Please wait {wait_time} seconds before exporting again.",
                "warning"
            )
            return redirect(url_for("person_dashboard", person=person))

        try:
            # Get export language from form or session
            export_lang = request.form.get("language") or get_current_language()

            # Use output directory instead of data/cvs for safety
            output_dir = get_default_output_path() / "json" / person
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique filename with language suffix
            lang_suffix = f"_{export_lang}" if export_lang != DEFAULT_LANGUAGE else ""
            filename = generate_unique_filename(f"{person}{lang_suffix}", ".json")
            output_path = output_dir / filename

            # Export with language-specific tags
            export_cv_to_file(
                person, output_path, app.config["DB_PATH"],
                apply_tags=True, force=False, tag_language=export_lang
            )
            flash(f"Exported CV to {output_path} (tags in {export_lang})", "success")
        except (ConfigurationError, ValidationError) as e:
            flash(str(e), "error")

        return redirect(url_for("person_dashboard", person=person))

    @app.route("/p/<person>/<section>/create", methods=["GET", "POST"])
    @requires_auth
    def create_entry_route(person: str, section: str):
        """Create a new entry in a section with multi-language sync."""
        if section not in CRUD_SECTIONS:
            flash(f"Section '{section}' does not support CRUD operations.", "error")
            return redirect(url_for("section_entries", person=person, section=section))

        try:
            persons = list_persons(app.config["DB_PATH"])
            person_info = next((p for p in persons if p["slug"] == person), None)
            if not person_info:
                flash(f"Person '{person}' not found", "error")
                return redirect(url_for("index"))
        except ConfigurationError as e:
            flash(str(e), "error")
            return redirect(url_for("index"))

        if request.method == "POST":
            try:
                # Build entry data from form
                data = {}
                for key in request.form:
                    if key.startswith("field_"):
                        field_name = key[6:]  # Remove 'field_' prefix
                        value = request.form[key].strip()
                        if value:
                            data[field_name] = value

                # Handle type_key as list
                type_keys = request.form.getlist("type_key")
                if type_keys:
                    data["type_key"] = type_keys

                # Handle sync option
                sync_languages = request.form.get("sync_languages") == "on"

                if not data:
                    flash("Please fill in at least one field.", "error")
                    return render_template(
                        "entry_form.html",
                        person=person_info,
                        section=section,
                        action="Create",
                        entry=None,
                        all_tags=[get_tag_display(tag) for tag in list_tags(app.config["DB_PATH"])]
                    )

                result = crud_create_entry(
                    person_slug=person,
                    section=section,
                    data=data,
                    db_path=app.config["DB_PATH"],
                    sync_languages=sync_languages
                )

                # Build detailed success message with sync info
                sync_result = result.get("sync_result", {})
                msg = format_sync_result_message("create", sync_result, result.get("stable_id"))
                flash(msg, "success")
                return redirect(url_for("section_entries", person=person, section=section))

            except (ConfigurationError, ValidationError) as e:
                flash(str(e), "error")

        # GET request - show form
        all_tags = list_tags(app.config["DB_PATH"])
        return render_template(
            "entry_form.html",
            person=person_info,
            section=section,
            action="Create",
            entry=None,
            all_tags=[get_tag_display(tag) for tag in all_tags]
        )

    @app.route("/entry/<int:entry_id>/edit", methods=["GET", "POST"])
    @requires_auth
    def edit_entry_route(entry_id: int):
        """Edit an existing entry."""
        try:
            entry = get_entry(entry_id, app.config["DB_PATH"])
            if not entry:
                flash(f"Entry {entry_id} not found", "error")
                return redirect(url_for("index"))

            section = entry["section"]
            if section not in CRUD_SECTIONS:
                flash(f"Section '{section}' does not support CRUD operations.", "error")
                return redirect(url_for("entry_detail", entry_id=entry_id))

            persons = list_persons(app.config["DB_PATH"])
            person_info = next((p for p in persons if p["slug"] == entry["person_slug"]), None)

        except ConfigurationError as e:
            flash(str(e), "error")
            return redirect(url_for("index"))

        if request.method == "POST":
            try:
                # Build entry data from form
                data = {}
                for key in request.form:
                    if key.startswith("field_"):
                        field_name = key[6:]
                        value = request.form[key].strip()
                        if value:
                            data[field_name] = value

                # Handle type_key as list
                type_keys = request.form.getlist("type_key")
                if type_keys:
                    data["type_key"] = type_keys

                # Handle sync option for shared fields
                sync_shared_fields = request.form.get("sync_shared_fields") == "on"

                result = crud_update_entry(
                    entry_id=entry_id,
                    data=data,
                    section=section,
                    db_path=app.config["DB_PATH"],
                    sync_shared_fields=sync_shared_fields
                )

                # Build detailed success message with sync info
                sync_result = result.get("sync_result", {})
                msg = format_sync_result_message("update", sync_result)
                flash(msg, "success")
                return redirect(url_for("entry_detail", entry_id=entry_id))

            except (ConfigurationError, ValidationError) as e:
                flash(str(e), "error")

        # GET request - show form with current data
        all_tags = list_tags(app.config["DB_PATH"])

        # Get linked entries for display
        linked_entries = {}
        try:
            linked_entries = get_linked_entries(entry_id, section, app.config["DB_PATH"])
        except Exception:
            pass  # May not be linked

        return render_template(
            "entry_form.html",
            person=person_info,
            section=section,
            action="Edit",
            entry=entry,
            all_tags=[get_tag_display(tag) for tag in all_tags],
            linked_entries=linked_entries
        )

    @app.route("/entry/<int:entry_id>/delete", methods=["POST"])
    @requires_auth
    def delete_entry_route(entry_id: int):
        """Delete an entry with optional multi-language sync."""
        try:
            entry = get_entry(entry_id, app.config["DB_PATH"])
            if not entry:
                flash(f"Entry {entry_id} not found", "error")
                return redirect(url_for("index"))

            section = entry["section"]
            person_slug = entry["person_slug"]

            if section not in CRUD_SECTIONS:
                flash(f"Section '{section}' does not support CRUD operations.", "error")
                return redirect(url_for("entry_detail", entry_id=entry_id))

            # Handle sync option
            sync_languages = request.form.get("sync_languages") == "on"

            result = crud_delete_entry(
                entry_id=entry_id,
                section=section,
                db_path=app.config["DB_PATH"],
                sync_languages=sync_languages
            )

            if result.get("success"):
                sync_result = result.get("sync_result", {})
                msg = format_sync_result_message("delete", sync_result)
                flash(msg, "success")
            else:
                flash("Entry not found or already deleted.", "warning")

        except (ConfigurationError, ValidationError) as e:
            flash(str(e), "error")
            return redirect(url_for("index"))

        return redirect(url_for("section_entries", person=person_slug, section=section))

    @app.route("/entry/<int:entry_id>/linked")
    @requires_auth
    def entry_linked_route(entry_id: int):
        """View linked language variants of an entry."""
        try:
            entry = get_entry(entry_id, app.config["DB_PATH"])
            if not entry:
                flash(f"Entry {entry_id} not found", "error")
                return redirect(url_for("index"))

            section = entry["section"]
            linked_entries = get_linked_entries(entry_id, section, app.config["DB_PATH"])

            persons = list_persons(app.config["DB_PATH"])
            person_info = next((p for p in persons if p["slug"] == entry["person_slug"]), None)

            entry["summary"] = get_entry_summary(section, entry["data"])

        except (ConfigurationError, ValidationError) as e:
            flash(str(e), "error")
            return redirect(url_for("index"))

        return render_template(
            "entry_linked.html",
            entry=entry,
            person=person_info,
            linked_entries=linked_entries,
            supported_languages=SUPPORTED_LANGUAGES
        )

    @app.route("/entry/<int:entry_id>/cross-language", methods=["GET", "POST"])
    @requires_auth
    def cross_language_editor_route(entry_id: int):
        """Cross-language entry editor - edit EN/DE/FA from one screen."""
        try:
            entry = get_entry(entry_id, app.config["DB_PATH"])
            if not entry:
                flash(f"Entry {entry_id} not found", "error")
                return redirect(url_for("index"))

            section = entry["section"]
            if section not in CRUD_SECTIONS:
                flash(f"Section '{section}' does not support cross-language editing.", "error")
                return redirect(url_for("entry_detail", entry_id=entry_id))

            linked_entries = get_linked_entries(entry_id, section, app.config["DB_PATH"])
            entry["summary"] = get_entry_summary(section, entry["data"])

            # Get stable_id
            stable_id = entry.get("stable_id")

            # Define field info for the section - we need per-language fields for labels
            # Pass fields for each language so the template can show localized labels
            fields_by_lang = {}
            for lang in SUPPORTED_LANGUAGES:
                fields_by_lang[lang] = _get_section_fields(section, lang)

            # Also get the default (English) fields for backward compatibility
            fields = _get_section_fields(section, DEFAULT_LANGUAGE)

        except (ConfigurationError, ValidationError) as e:
            flash(str(e), "error")
            return redirect(url_for("index"))

        if request.method == "POST":
            try:
                updated_count = 0
                mark_translated = request.form.get("mark_translated") == "1"

                # Process updates for each language
                for lang in SUPPORTED_LANGUAGES:
                    lang_entry_id = request.form.get(f"entry_id_{lang}")
                    if not lang_entry_id:
                        continue

                    lang_entry_id = int(lang_entry_id)

                    # Build data from form fields
                    data = {}
                    for field_name in fields.keys():
                        value = request.form.get(f"field_{lang}_{field_name}", "").strip()
                        if value:
                            data[field_name] = value

                    if data:
                        # Update the entry
                        crud_update_entry(
                            entry_id=lang_entry_id,
                            data=data,
                            section=section,
                            db_path=app.config["DB_PATH"],
                            sync_shared_fields=False  # We're manually updating all
                        )

                        # Clear needs_translation if requested
                        if mark_translated:
                            _clear_needs_translation(lang_entry_id, app.config["DB_PATH"])

                        updated_count += 1

                if updated_count > 0:
                    flash(f"✓ Updated {updated_count} language variant(s) successfully.", "success")
                else:
                    flash("No changes were made.", "warning")

                return redirect(url_for("cross_language_editor_route", entry_id=entry_id))

            except (ConfigurationError, ValidationError) as e:
                flash(str(e), "error")

        return render_template(
            "cross_language_editor.html",
            entry=entry,
            linked_entries=linked_entries,
            fields=fields,
            fields_by_lang=fields_by_lang,
            stable_id=stable_id,
            supported_languages=SUPPORTED_LANGUAGES
        )

    @app.route("/entry/<int:entry_id>/create-lang", methods=["POST"])
    @requires_auth
    def create_missing_lang_entry_route(entry_id: int):
        """Create a missing language variant for an entry."""
        try:
            entry = get_entry(entry_id, app.config["DB_PATH"])
            if not entry:
                flash(f"Entry {entry_id} not found", "error")
                return redirect(url_for("index"))

            section = entry["section"]
            if section not in CRUD_SECTIONS:
                flash(f"Section '{section}' does not support this operation.", "error")
                return redirect(url_for("entry_detail", entry_id=entry_id))

            target_lang = request.form.get("target_lang")
            if not target_lang or target_lang not in SUPPORTED_LANGUAGES:
                flash("Invalid target language", "error")
                return redirect(url_for("entry_linked_route", entry_id=entry_id))

            # Get linked entries to find the stable_id
            linked_entries = get_linked_entries(entry_id, section, app.config["DB_PATH"])

            if target_lang in linked_entries:
                flash(f"Entry already exists in {target_lang.upper()}", "warning")
                return redirect(url_for("cross_language_editor_route", entry_id=entry_id))

            # Get base person from current entry
            person_slug = entry["person_slug"]
            # Compute base person and target slug
            from .crud import _get_base_person, _get_person_slug_for_lang

            base_person = _get_base_person(person_slug)
            target_slug = _get_person_slug_for_lang(base_person, target_lang)

            # Get source entry data (use English if available, else the current)
            source_entry = linked_entries.get("en", entry)
            source_data = source_entry["data"].copy()

            # Create placeholder entry (reuse the data structure)
            result = crud_create_entry(
                person_slug=target_slug,
                section=section,
                data=source_data,
                db_path=app.config["DB_PATH"],
                sync_languages=False  # Only create in target language
            )

            # Link to existing stable_id if we have one
            stable_id = entry.get("stable_id")
            if stable_id:
                _link_entry_to_stable(result["entries"].get(target_lang), stable_id, target_lang, app.config["DB_PATH"])
                flash(f"✓ Created {target_lang.upper()} entry and linked to existing stable ID.", "success")
            else:
                flash(f"✓ Created {target_lang.upper()} entry.", "success")

            return redirect(url_for("cross_language_editor_route", entry_id=entry_id))

        except (ConfigurationError, ValidationError) as e:
            flash(str(e), "error")
            return redirect(url_for("entry_detail", entry_id=entry_id))

    @app.route("/diagnostics")
    @requires_auth
    def diagnostics():
        """Diagnostics panel - show database health, orphan tags, and missing translations."""
        try:
            # Run doctor to get database health
            health = doctor(app.config["DB_PATH"])

            # Run integrity check
            integrity_report = None
            integrity_error = None
            try:
                integrity_report = run_integrity_check(app.config["DB_PATH"])
            except Exception as e:
                logger.warning(f"Integrity check failed: {e}")
                integrity_error = str(e)

            # Get missing translations for current language
            current_lang = get_current_language()
            catalog = get_tag_catalog()
            missing_translations = []
            if current_lang != DEFAULT_LANGUAGE:
                missing_translations = catalog.get_missing_translations(current_lang)

            # Get entries with needs_translation flag
            entries_needing_translation = _get_entries_needing_translation(app.config["DB_PATH"])

            # Get entries with missing language counterparts
            missing_counterparts = _get_missing_counterparts(app.config["DB_PATH"])

        except ConfigurationError as e:
            flash(str(e), "error")
            return redirect(url_for("index"))

        return render_template(
            "diagnostics.html",
            health=health,
            integrity=integrity_report,
            integrity_error=integrity_error,
            missing_translations=missing_translations,
            entries_needing_translation=entries_needing_translation,
            missing_counterparts=missing_counterparts,
            current_language=current_lang,
        )

    @app.route("/diagnostics/cleanup-orphans", methods=["POST"])
    @requires_auth
    def cleanup_orphans():
        """Clean up orphan tag references in entries."""
        try:
            result = cleanup_orphan_tag_references(app.config["DB_PATH"])
            if result["entries_cleaned"] > 0:
                flash(
                    f"Cleaned {result['entries_cleaned']} entries with orphan tag references.",
                    "success"
                )
            else:
                flash("No orphan tag references found.", "success")
        except (ConfigurationError, ValidationError) as e:
            flash(str(e), "error")

        return redirect(url_for("diagnostics"))

    @app.route("/p/<person>/preview")
    @requires_auth
    def preview_export(person: str):
        """Preview export JSON for a person without writing to disk."""
        try:
            export_lang = request.args.get("language") or get_current_language()

            # Export to dict (not file)
            cv_data = export_cv(
                person,
                app.config["DB_PATH"],
                apply_tags=True,
                tag_language=export_lang
            )

            return render_template(
                "preview.html",
                person=person,
                cv_data=cv_data,
                export_language=export_lang,
                json_preview=json.dumps(cv_data, indent=2, ensure_ascii=False)
            )
        except ConfigurationError as e:
            flash(str(e), "error")
            return redirect(url_for("person_dashboard", person=person))

    # =========================================================================
    # Import UI Routes
    # =========================================================================

    @app.route("/import")
    @requires_auth
    def import_page():
        """
        Import landing page with file upload form.

        Shows:
        - File upload dropzone (single or multiple)
        - Import options (overwrite vs merge)
        - Recent import history
        """
        # Get recent import history from session
        import_history = session.get("import_history", [])

        # Get list of existing persons for collision info
        try:
            persons = list_persons(app.config["DB_PATH"])
        except ConfigurationError:
            persons = []

        return render_template(
            "import.html",
            import_history=import_history,
            existing_persons=persons,
        )

    @app.route("/import/upload", methods=["POST"])
    @requires_auth
    def import_upload():
        """
        Handle file upload and return validation preview.

        1. Receive uploaded file(s)
        2. Validate JSON syntax
        3. Parse config block
        4. Check for collisions with existing data
        5. Return preview page with validation results
        """
        # Check if files were uploaded
        if "files" not in request.files:
            flash("No files were uploaded.", "error")
            return redirect(url_for("import_page"))

        files = request.files.getlist("files")
        if not files or all(f.filename == "" for f in files):
            flash("No files were selected.", "error")
            return redirect(url_for("import_page"))

        # Get import options
        import_mode = request.form.get("import_mode", "merge")
        overwrite = import_mode == "overwrite"

        # Create a temporary directory for uploaded files
        import tempfile
        import uuid
        session_id = str(uuid.uuid4())[:8]
        temp_dir = Path(tempfile.gettempdir()) / f"cvgen_import_{session_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Process each uploaded file
        validation_results = []
        valid_files = []

        for file in files:
            if not file.filename:
                continue

            # Security: validate filename
            filename = _secure_filename(file.filename)
            if not filename.endswith(".json"):
                validation_results.append({
                    "filename": file.filename,
                    "valid": False,
                    "error": "Only JSON files are allowed.",
                    "error_type": "invalid_extension",
                })
                continue

            # Save file temporarily
            file_path = temp_dir / filename
            try:
                file.save(str(file_path))
            except Exception as e:
                validation_results.append({
                    "filename": filename,
                    "valid": False,
                    "error": f"Failed to save file: {e}",
                    "error_type": "save_error",
                })
                continue

            # Validate JSON syntax
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                validation_results.append({
                    "filename": filename,
                    "valid": False,
                    "error": f"Invalid JSON: {e}",
                    "error_type": "json_error",
                    "error_details": {"line": e.lineno, "column": e.colno},
                })
                continue

            # Parse config block
            config = data.get("config", {})
            resume_key = config.get("ID")
            lang_code = config.get("lang")

            # Infer from filename if not in config
            if not resume_key or not lang_code:
                stem = file_path.stem
                parts = stem.rsplit("_", 1)
                if len(parts) == 2 and parts[1] in SUPPORTED_LANGUAGES:
                    if not resume_key:
                        resume_key = parts[0]
                    if not lang_code:
                        lang_code = parts[1]
                else:
                    if not resume_key:
                        resume_key = stem
                    if not lang_code:
                        lang_code = "en"

            # Check for collisions with existing data
            collision = None
            try:
                persons = list_persons(app.config["DB_PATH"])
                for p in persons:
                    if p["slug"] == resume_key or p["slug"] == f"{resume_key}_{lang_code}":
                        collision = {
                            "person_slug": p["slug"],
                            "display_name": p.get("display_name", p["slug"]),
                            "entry_count": p.get("entry_count", 0),
                        }
                        break
            except ConfigurationError:
                pass

            # Count sections in the import data
            section_counts = {}
            for section in ["basics", "profiles", "education", "languages",
                           "workshop_and_certifications", "skills", "experiences",
                           "projects", "publications", "references"]:
                if section in data:
                    section_data = data[section]
                    if isinstance(section_data, list):
                        section_counts[section] = len(section_data)
                    elif isinstance(section_data, dict):
                        # Skills is a nested dict
                        count = sum(
                            len(items)
                            for subcats in section_data.values()
                            for items in subcats.values()
                        ) if section == "skills" else 1
                        section_counts[section] = count

            validation_results.append({
                "filename": filename,
                "valid": True,
                "resume_key": resume_key,
                "lang_code": lang_code,
                "collision": collision,
                "section_counts": section_counts,
                "file_path": str(file_path),
            })
            valid_files.append(str(file_path))

        # Store session data for confirmation step
        session[f"import_session_{session_id}"] = {
            "temp_dir": str(temp_dir),
            "files": valid_files,
            "overwrite": overwrite,
            "created_at": _utcnow(),
        }

        return render_template(
            "import_preview.html",
            session_id=session_id,
            validation_results=validation_results,
            import_mode=import_mode,
            has_valid_files=len(valid_files) > 0,
            has_collisions=any(r.get("collision") for r in validation_results if r.get("valid")),
        )

    @app.route("/import/confirm/<session_id>", methods=["POST"])
    @requires_auth
    def import_confirm(session_id: str):
        """
        Commit import after user confirmation.

        This performs the actual import operation after the user has reviewed
        the preview and confirmed they want to proceed.
        """
        from .importer_v2 import CVImporter

        # Retrieve session data
        session_key = f"import_session_{session_id}"
        session_data = session.get(session_key)

        if not session_data:
            flash("Import session expired. Please upload files again.", "error")
            return redirect(url_for("import_page"))

        files = session_data.get("files", [])
        overwrite = session_data.get("overwrite", False)

        if not files:
            flash("No valid files to import.", "error")
            return redirect(url_for("import_page"))

        # Perform the import
        importer = CVImporter(app.config["DB_PATH"])
        results = []
        success_count = 0
        error_count = 0

        for file_path in files:
            try:
                result = importer.import_file(Path(file_path), dry_run=False, overwrite=overwrite)
                results.append(result.to_dict())
                if result.success:
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                results.append({
                    "success": False,
                    "file_path": file_path,
                    "error": str(e),
                })
                error_count += 1

        # Clean up temp directory
        temp_dir = session_data.get("temp_dir")
        if temp_dir and Path(temp_dir).exists():
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception:
                pass

        # Clear session data
        session.pop(session_key, None)

        # Update import history
        import_history = session.get("import_history", [])
        import_history.insert(0, {
            "timestamp": _utcnow(),
            "files_count": len(files),
            "success_count": success_count,
            "error_count": error_count,
            "overwrite": overwrite,
        })
        # Keep only last 10 entries
        session["import_history"] = import_history[:10]

        if error_count == 0:
            flash(f"Successfully imported {success_count} file(s).", "success")
        elif success_count > 0:
            flash(
                f"Imported {success_count} file(s) with {error_count} error(s). "
                "Check the results below.",
                "warning"
            )
        else:
            flash(f"Import failed for all {error_count} file(s).", "error")

        return render_template(
            "import_results.html",
            results=results,
            success_count=success_count,
            error_count=error_count,
        )

    @app.route("/import/cancel/<session_id>", methods=["POST"])
    @requires_auth
    def import_cancel(session_id: str):
        """Cancel an import session and clean up temporary files."""
        session_key = f"import_session_{session_id}"
        session_data = session.get(session_key)

        if session_data:
            # Clean up temp directory
            temp_dir = session_data.get("temp_dir")
            if temp_dir and Path(temp_dir).exists():
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass

            # Clear session data
            session.pop(session_key, None)

        flash("Import cancelled.", "success")
        return redirect(url_for("import_page"))

    # =========================================================================
    # Export UI Routes
    # =========================================================================

    @app.route("/export")
    @requires_auth
    def export_page():
        """
        Export landing page with person/language selection and batch options.
        """
        from .exporter_v2 import CVExporter

        try:
            # Get list of persons
            persons = list_persons(app.config["DB_PATH"])

            # Try to get available exports from v2 exporter
            available_variants = []
            try:
                exporter = CVExporter(app.config["DB_PATH"])
                available_variants = exporter.list_available()
            except Exception:
                pass

        except ConfigurationError as e:
            flash(str(e), "error")
            persons = []
            available_variants = []

        # Get recent export history
        export_history = session.get("export_history", [])

        return render_template(
            "export.html",
            persons=persons,
            available_variants=available_variants,
            export_history=export_history,
            supported_languages=SUPPORTED_LANGUAGES,
        )

    @app.route("/export/single", methods=["POST"])
    @requires_auth
    def export_single():
        """Export a single CV variant to a file."""
        from .exporter_v2 import CVExporter

        person = request.form.get("person")
        language = request.form.get("language", "en")

        if not person:
            flash("Please select a person to export.", "error")
            return redirect(url_for("export_page"))

        # Check throttle
        wait_time = check_throttle(f"export_single_{person}_{language}")
        if wait_time is not None:
            flash(f"Please wait {wait_time} seconds before exporting again.", "warning")
            return redirect(url_for("export_page"))

        try:
            # Determine resume_key from person slug
            # The person slug might be "ramin" or "ramin_de" etc.
            resume_key = person
            if "_" in person:
                parts = person.rsplit("_", 1)
                if parts[1] in SUPPORTED_LANGUAGES:
                    resume_key = parts[0]

            exporter = CVExporter(app.config["DB_PATH"])

            # Create output directory
            output_dir = get_default_output_path() / "json" / resume_key
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            lang_suffix = f"_{language}" if language != "en" else ""
            filename = generate_unique_filename(f"{resume_key}{lang_suffix}", ".json")
            output_path = output_dir / filename

            # Export
            result = exporter.export_to_file(resume_key, language, output_path)

            if result.success:
                flash(f"Exported CV to {output_path}", "success")

                # Update export history
                export_history = session.get("export_history", [])
                export_history.insert(0, {
                    "timestamp": _utcnow(),
                    "resume_key": resume_key,
                    "language": language,
                    "output_path": str(output_path),
                    "success": True,
                })
                session["export_history"] = export_history[:10]
            else:
                flash(f"Export failed: {result.error}", "error")

        except Exception as e:
            flash(f"Export failed: {e}", "error")

        return redirect(url_for("export_page"))

    @app.route("/export/batch", methods=["POST"])
    @requires_auth
    def export_batch():
        """
        Batch export all variants for selected persons.
        """
        from .exporter_v2 import CVExporter

        # Get selected persons (checkboxes)
        selected_persons = request.form.getlist("persons")

        if not selected_persons:
            flash("Please select at least one person to export.", "error")
            return redirect(url_for("export_page"))

        # Check throttle
        wait_time = check_throttle("export_batch")
        if wait_time is not None:
            flash(f"Please wait {wait_time} seconds before exporting again.", "warning")
            return redirect(url_for("export_page"))

        try:
            exporter = CVExporter(app.config["DB_PATH"])

            # Create output directory
            output_dir = get_default_output_path() / "json" / "batch"
            output_dir.mkdir(parents=True, exist_ok=True)

            total_success = 0
            total_failed = 0
            results = []

            for person in selected_persons:
                # Determine resume_key
                resume_key = person
                if "_" in person:
                    parts = person.rsplit("_", 1)
                    if parts[1] in SUPPORTED_LANGUAGES:
                        resume_key = parts[0]

                # Export all variants for this person
                variant_results = exporter.export_all_variants(resume_key, output_dir)

                for result in variant_results:
                    results.append(result.to_dict())
                    if result.success:
                        total_success += 1
                    else:
                        total_failed += 1

            # Update export history
            export_history = session.get("export_history", [])
            export_history.insert(0, {
                "timestamp": _utcnow(),
                "batch": True,
                "persons_count": len(selected_persons),
                "success_count": total_success,
                "failed_count": total_failed,
                "output_dir": str(output_dir),
            })
            session["export_history"] = export_history[:10]

            if total_failed == 0:
                flash(f"Successfully exported {total_success} file(s) to {output_dir}", "success")
            else:
                flash(
                    f"Exported {total_success} file(s), {total_failed} failed. "
                    f"Output directory: {output_dir}",
                    "warning"
                )

        except Exception as e:
            flash(f"Batch export failed: {e}", "error")

        return redirect(url_for("export_page"))

    @app.route("/export/preview", methods=["POST"])
    @requires_auth
    def export_preview_v2():
        """
        Preview export for a person/language combination using v2 exporter.
        """
        from .exporter_v2 import CVExporter

        person = request.form.get("person")
        language = request.form.get("language", "en")

        if not person:
            flash("Please select a person to preview.", "error")
            return redirect(url_for("export_page"))

        try:
            # Determine resume_key
            resume_key = person
            if "_" in person:
                parts = person.rsplit("_", 1)
                if parts[1] in SUPPORTED_LANGUAGES:
                    resume_key = parts[0]

            exporter = CVExporter(app.config["DB_PATH"])
            cv_data = exporter.export(resume_key, language)

            return render_template(
                "export_preview.html",
                person=person,
                resume_key=resume_key,
                language=language,
                cv_data=cv_data,
                json_preview=json.dumps(cv_data, indent=2, ensure_ascii=False),
            )

        except Exception as e:
            flash(f"Preview failed: {e}", "error")
            return redirect(url_for("export_page"))

    return app


def _get_entries_needing_translation(db_path: Path) -> list[dict[str, Any]]:
    """Get entries marked as needing translation."""
    import sqlite3

    entries = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if entry_lang_link table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entry_lang_link'"
        )
        if not cursor.fetchone():
            return entries

        cursor.execute(
            """SELECT e.id, e.section, p.slug, ell.language, e.data_json
               FROM entry_lang_link ell
               JOIN entry e ON ell.entry_id = e.id
               JOIN person p ON e.person_id = p.id
               WHERE ell.needs_translation = 1
               ORDER BY p.slug, e.section, e.id"""
        )

        for row in cursor.fetchall():
            entry_id, section, person_slug, language, data_json = row
            data = json.loads(data_json) if data_json else {}
            entries.append({
                "id": entry_id,
                "section": section,
                "person_slug": person_slug,
                "language": language,
                "summary": get_entry_summary(section, data),
            })

        conn.close()
    except Exception:
        pass  # Table may not exist yet

    return entries


def _get_missing_counterparts(db_path: Path) -> list[dict[str, Any]]:
    """Get entries that are missing language counterparts."""
    import sqlite3

    missing = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if entry_lang_link and stable_entry tables exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='stable_entry'"
        )
        if not cursor.fetchone():
            return missing

        # Find stable entries that don't have all 3 languages
        cursor.execute(
            """SELECT se.id, se.section, se.base_person,
                      GROUP_CONCAT(ell.language) as languages
               FROM stable_entry se
               LEFT JOIN entry_lang_link ell ON se.id = ell.stable_id
               GROUP BY se.id
               HAVING COUNT(DISTINCT ell.language) < 3"""
        )

        for row in cursor.fetchall():
            stable_id, section, base_person, languages_str = row
            existing_langs = set(languages_str.split(",")) if languages_str else set()
            missing_langs = set(SUPPORTED_LANGUAGES) - existing_langs

            missing.append({
                "stable_id": stable_id,
                "section": section,
                "base_person": base_person,
                "existing_languages": sorted(existing_langs),
                "missing_languages": sorted(missing_langs),
            })

        conn.close()
    except Exception:
        pass  # Tables may not exist yet

    return missing


def _get_section_fields(section: str, language: str = DEFAULT_LANGUAGE) -> dict[str, dict[str, Any]]:
    """
    Get field definitions for a section for the cross-language editor.

    Returns a dict mapping field names to field info:
    - label: Display label (English default for cross-language editor pane headers)
    - localized_label: Localized label for the given language (from vocabulary)
    - canonical_key: The canonical field key
    - shared: Whether this is a shared field (not translated)
    - multiline: Whether this is a multiline field
    - input_type: HTML input type
    - placeholder: Placeholder text
    """
    from .vocabulary import get_vocabulary
    vocab = get_vocabulary()

    # Define base field structures (with English labels as default)
    if section == "basics":
        fields = {
            "fname": {"label": "First Name", "shared": False, "multiline": False, "input_type": "text", "placeholder": "First name"},
            "lname": {"label": "Last Name", "shared": False, "multiline": False, "input_type": "text", "placeholder": "Last name"},
            "headline": {"label": "Headline", "shared": False, "multiline": False, "input_type": "text", "placeholder": "Professional title"},
            "location": {"label": "Location", "shared": False, "multiline": False, "input_type": "text", "placeholder": "City, Country"},
            "email": {"label": "Email", "shared": True, "multiline": False, "input_type": "email", "placeholder": "email@example.com"},
            "phone": {"label": "Phone", "shared": True, "multiline": False, "input_type": "text", "placeholder": "+49 123 456"},
            "website": {"label": "Website", "shared": True, "multiline": False, "input_type": "url", "placeholder": "https://example.com"},
            "linkedin": {"label": "LinkedIn", "shared": True, "multiline": False, "input_type": "url", "placeholder": "https://linkedin.com/in/..."},
            "github": {"label": "GitHub", "shared": True, "multiline": False, "input_type": "url", "placeholder": "https://github.com/..."},
            "summary": {"label": "Summary / Bio", "shared": False, "multiline": True, "input_type": "text", "placeholder": "Professional summary"},
        }
    elif section == "projects":
        fields = {
            "title": {"label": "Title", "shared": False, "multiline": False, "input_type": "text", "placeholder": "Project title"},
            "description": {"label": "Description", "shared": False, "multiline": True, "input_type": "text", "placeholder": "Project description"},
            "url": {"label": "URL", "shared": True, "multiline": False, "input_type": "url", "placeholder": "https://github.com/..."},
        }
    elif section == "experiences":
        fields = {
            "role": {"label": "Role", "shared": False, "multiline": False, "input_type": "text", "placeholder": "Job title"},
            "institution": {"label": "Institution", "shared": False, "multiline": False, "input_type": "text", "placeholder": "Company name"},
            "duration": {"label": "Duration", "shared": False, "multiline": False, "input_type": "text", "placeholder": "2020 - present"},
            "description": {"label": "Description", "shared": False, "multiline": True, "input_type": "text", "placeholder": "Responsibilities"},
        }
    elif section == "publications":
        fields = {
            "title": {"label": "Title", "shared": False, "multiline": False, "input_type": "text", "placeholder": "Publication title"},
            "authors": {"label": "Authors", "shared": False, "multiline": False, "input_type": "text", "placeholder": "Author names"},
            "journal": {"label": "Journal", "shared": False, "multiline": False, "input_type": "text", "placeholder": "Journal name"},
            "year": {"label": "Year", "shared": True, "multiline": False, "input_type": "text", "placeholder": "2024"},
            "doi": {"label": "DOI", "shared": True, "multiline": False, "input_type": "text", "placeholder": "10.1000/xyz123"},
            "status": {"label": "Status", "shared": True, "multiline": False, "input_type": "text", "placeholder": "Published"},
        }
    elif section == "references":
        fields = {
            "name": {"label": "Name", "shared": False, "multiline": False, "input_type": "text", "placeholder": "Reference name"},
            "institution": {"label": "Institution", "shared": False, "multiline": False, "input_type": "text", "placeholder": "Company"},
            "email": {"label": "Email", "shared": True, "multiline": False, "input_type": "email", "placeholder": "email@example.com"},
            "phone": {"label": "Phone", "shared": True, "multiline": False, "input_type": "text", "placeholder": "+49 123 456"},
        }
    elif section == "education":
        fields = {
            "institution": {"label": "Institution", "shared": False, "multiline": False, "input_type": "text", "placeholder": "University name"},
            "area": {"label": "Area / Major", "shared": False, "multiline": False, "input_type": "text", "placeholder": "Computer Science"},
            "studyType": {"label": "Degree Type", "shared": False, "multiline": False, "input_type": "text", "placeholder": "Master's"},
            "location": {"label": "Location", "shared": False, "multiline": False, "input_type": "text", "placeholder": "City, Country"},
            "startDate": {"label": "Start Date", "shared": True, "multiline": False, "input_type": "text", "placeholder": "2020-10"},
            "endDate": {"label": "End Date", "shared": True, "multiline": False, "input_type": "text", "placeholder": "2024-09"},
            "gpa": {"label": "GPA", "shared": True, "multiline": False, "input_type": "text", "placeholder": "3.5 / 4.0"},
        }
    else:
        # Generic fields
        fields = {
            "title": {"label": "Title", "shared": False, "multiline": False, "input_type": "text", "placeholder": "Title"},
            "description": {"label": "Description", "shared": False, "multiline": True, "input_type": "text", "placeholder": "Description"},
        }

    # Add localized labels from vocabulary for each field
    for field_name, field_info in fields.items():
        field_info["canonical_key"] = field_name
        field_info["localized_label"] = vocab.get_label(field_name, language)
        field_info["has_translation"] = vocab.has_translation(field_name, language)

    return fields


def _clear_needs_translation(entry_id: int, db_path: Path) -> None:
    """Clear the needs_translation flag for an entry."""
    import sqlite3

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE entry_lang_link SET needs_translation = 0 WHERE entry_id = ?",
            (entry_id,)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # Ignore errors


def _link_entry_to_stable(entry_id: int, stable_id: str, language: str, db_path: Path) -> None:
    """Link an entry to an existing stable_id."""
    import sqlite3

    if not entry_id or not stable_id:
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        now = _utcnow()

        # Check if link already exists
        cursor.execute(
            "SELECT 1 FROM entry_lang_link WHERE entry_id = ?",
            (entry_id,)
        )
        if cursor.fetchone():
            # Update existing link
            cursor.execute(
                "UPDATE entry_lang_link SET stable_id = ?, language = ? WHERE entry_id = ?",
                (stable_id, language, entry_id)
            )
        else:
            # Create new link
            cursor.execute(
                """INSERT INTO entry_lang_link (stable_id, language, entry_id, needs_translation, created_at)
                   VALUES (?, ?, ?, 1, ?)""",
                (stable_id, language, entry_id, now)
            )

        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Failed to link entry to stable_id: {e}")


def _utcnow() -> str:
    """Return current UTC time as ISO format string."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def run_server(
    host: str = "127.0.0.1",
    port: int = 5000,
    debug: bool = False,
    db_path: Optional[Path] = None,
    allow_unsafe_bind: bool = False
) -> None:
    """
    Run the web server.

    Args:
        host: Host to bind to. Defaults to 127.0.0.1 (localhost only).
        port: Port to listen on.
        debug: Enable debug mode.
        db_path: Path to the database file.
        allow_unsafe_bind: If True, suppress warning for non-localhost bindings.
    """
    # Safety check for non-localhost binding
    if not is_localhost(host) and not allow_unsafe_bind:
        print("\n" + "=" * 70)
        print("⚠️  WARNING: BINDING TO NON-LOCALHOST ADDRESS")
        print("=" * 70)
        print(f"   You are binding to '{host}' which may expose this server")
        print("   to other machines on your network or the internet.")
        print()
        print("   This web UI has minimal security features.")
        print("   Consider using authentication by setting:")
        print("     CVGEN_WEB_AUTH=username:password")
        print()
        print("   To proceed without this warning, use:")
        print("     --i-know-what-im-doing")
        print("=" * 70 + "\n")
        raise SystemExit(1)

    # Log auth status (never log actual credentials)
    if get_auth_credentials() is not None:
        logger.info("Authentication is ENABLED")
        print("🔐 Authentication: ENABLED")
    else:
        logger.info("Authentication is DISABLED (set CVGEN_WEB_AUTH to enable)")
        print("🔓 Authentication: DISABLED (set CVGEN_WEB_AUTH=user:pass to enable)")

    app = create_app(db_path)
    logger.info(f"Starting Tag Manager web server at http://{host}:{port}")
    print(f"\n🏷️  Tag Manager running at http://{host}:{port}")
    print("   Press Ctrl+C to stop\n")
    app.run(host=host, port=port, debug=debug)
