"""
Web UI for CV Generator Tag Manager.

Provides a local-first web interface for:
- Creating and managing tags
- Browsing CV entries by person and section
- Assigning/unassigning tags to entries
- Exporting updated CVs to JSON
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask, flash, redirect, render_template, request, url_for

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
from .paths import get_default_cvs_path

logger = logging.getLogger(__name__)


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
        # Skills section is typically a dict of categories
        return "Skills Overview"

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

    @app.context_processor
    def inject_helpers():
        """Inject helper functions into templates."""
        return {
            "get_entry_summary": get_entry_summary
        }

    @app.route("/")
    def index():
        """Home page - person selector."""
        try:
            persons = list_persons(app.config["DB_PATH"])
        except ConfigurationError as e:
            flash(str(e), "error")
            persons = []
        return render_template("index.html", persons=persons)

    @app.route("/p/<person>")
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
    def section_entries(person: str, section: str):
        """Section entries list."""
        try:
            entries = get_section_entries(person, section, app.config["DB_PATH"])
            persons = list_persons(app.config["DB_PATH"])
            person_info = next((p for p in persons if p["slug"] == person), None)
        except ConfigurationError as e:
            flash(str(e), "error")
            return redirect(url_for("person_dashboard", person=person))

        # Add summaries
        for entry in entries:
            entry["summary"] = get_entry_summary(section, entry["data"])

        return render_template(
            "section.html",
            person=person_info,
            section=section,
            entries=entries
        )

    @app.route("/entry/<int:entry_id>")
    def entry_detail(entry_id: int):
        """Entry detail view with tag assignment."""
        try:
            entry = get_entry(entry_id, app.config["DB_PATH"])
            if not entry:
                flash(f"Entry {entry_id} not found", "error")
                return redirect(url_for("index"))

            all_tags = list_tags(app.config["DB_PATH"])
            entry["summary"] = get_entry_summary(entry["section"], entry["data"])
        except ConfigurationError as e:
            flash(str(e), "error")
            return redirect(url_for("index"))

        return render_template(
            "entry.html",
            entry=entry,
            all_tags=all_tags,
            data_json=json.dumps(entry["data"], indent=2, ensure_ascii=False)
        )

    @app.route("/entry/<int:entry_id>/tags", methods=["POST"])
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
    def tags_list():
        """List all tags."""
        try:
            tags = list_tags(app.config["DB_PATH"])
        except ConfigurationError as e:
            flash(str(e), "error")
            tags = []

        return render_template("tags.html", tags=tags)

    @app.route("/tags/create", methods=["GET", "POST"])
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
    def export_person(person: str):
        """Export a person's CV to JSON."""
        try:
            output_dir = get_default_cvs_path()
            output_path = output_dir / f"{person}.json"
            # Use force=True for web exports (user action implies consent)
            export_cv_to_file(person, output_path, app.config["DB_PATH"], force=True)
            flash(f"Exported CV to {output_path}", "success")
        except (ConfigurationError, ValidationError) as e:
            flash(str(e), "error")

        return redirect(url_for("person_dashboard", person=person))

    return app


def run_server(
    host: str = "127.0.0.1",
    port: int = 5000,
    debug: bool = False,
    db_path: Optional[Path] = None
) -> None:
    """
    Run the web server.

    Args:
        host: Host to bind to.
        port: Port to listen on.
        debug: Enable debug mode.
        db_path: Path to the database file.
    """
    app = create_app(db_path)
    logger.info(f"Starting Tag Manager web server at http://{host}:{port}")
    print(f"\n🏷️  Tag Manager running at http://{host}:{port}")
    print("   Press Ctrl+C to stop\n")
    app.run(host=host, port=port, debug=debug)
