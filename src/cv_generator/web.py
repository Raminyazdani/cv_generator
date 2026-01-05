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
"""

import functools
import json
import logging
import os
import secrets
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for

from .db import (
    create_tag,
    delete_tag,
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
from .paths import get_default_output_path
from .tags import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    get_tag_catalog,
    validate_tags,
)

logger = logging.getLogger(__name__)

# Rate limiting configuration
THROTTLE_SECONDS = 5  # Minimum seconds between export/write operations


def get_auth_credentials() -> Optional[Tuple[str, str]]:
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


def get_entry_summary(section: str, data: Dict[str, Any]) -> str:
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
    app.secret_key = "cvgen-web-local-only"

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

    def get_tag_display(tag: Dict[str, Any], language: Optional[str] = None) -> Dict[str, Any]:
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
        current_lang = get_current_language()
        return {
            "get_entry_summary": get_entry_summary,
            "get_tag_label": get_tag_label,
            "get_tag_display": get_tag_display,
            "current_language": current_lang,
            "supported_languages": SUPPORTED_LANGUAGES,
            "tag_catalog": catalog,
        }

    @app.route("/")
    @requires_auth
    def index():
        """Home page - person selector."""
        try:
            persons = list_persons(app.config["DB_PATH"])
        except ConfigurationError as e:
            flash(str(e), "error")
            persons = []
        return render_template("index.html", persons=persons)

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
                    flash(
                        f"Some tags lack translation for {current_lang}: "
                        f"{', '.join(validation['missing_translations'][:3])}",
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
                    f"{', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}",
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

    return app


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
