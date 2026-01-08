from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_wtf.csrf import CSRFProtect, generate_csrf

from .models import db, PersonEntity, CVVariant, Entry, Tag, TagTranslation, TagAlias, EntityTag, ImportHistory, ExportHistory
from .fields import (
    SUPPORTED_LANGUAGES,
    SECTION_ORDER,
    SECTION_LABELS,
    get_section_label,
    get_section_icon,
    SECTION_FIELDS,
    summarize_entry,
    default_entry_data,
    skills_group,
)
from .cv_io import import_cv_json_bytes, export_variant_to_json, write_export_file
from .tagging import resolve_or_create_tag, attach_tag, detach_tag, list_entity_tags, get_tag_table


def create_app(*, repo_root: Path) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Config
    db_path = repo_root / "data" / "db" / "cv_database.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    app.config["SECRET_KEY"] = "dev-local-only-change-me"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path.as_posix()}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["REPO_ROOT"] = str(repo_root)
    app.config["SUPPORTED_LANGUAGES"] = SUPPORTED_LANGUAGES

    # Extensions
    db.init_app(app)
    csrf = CSRFProtect(app)
    app.jinja_env.globals["csrf_token"] = generate_csrf

    # Template globals
    app.jinja_env.globals["supported_languages"] = SUPPORTED_LANGUAGES
    app.jinja_env.globals["get_section_label"] = get_section_label
    app.jinja_env.globals["get_section_icon"] = get_section_icon

    @app.before_request
    def _ensure_db() -> None:
        # create tables on first request
        if getattr(app, "_db_ready", False):
            return
        with app.app_context():
            db.create_all()
            app._db_ready = True  # type: ignore[attr-defined]

    def current_language() -> str:
        lang = session.get("current_language") or "en"
        if lang not in SUPPORTED_LANGUAGES:
            lang = "en"
        return lang

    def show_canonical_keys() -> bool:
        return bool(session.get("show_canonical_keys", False))

    @app.context_processor
    def inject_globals():
        return {
            "current_language": current_language(),
            "show_canonical_keys": show_canonical_keys(),
        }

    # -------------------------
    # Home
    # -------------------------
    @app.route("/")
    def index():
        persons = PersonEntity.query.order_by(PersonEntity.display_name.asc()).all()
        person_entities = []
        for p in persons:
            variants = {}
            for lang in SUPPORTED_LANGUAGES:
                v = CVVariant.query.filter_by(person_id=p.id, lang_code=lang).first()
                if v:
                    variants[lang] = {"entry_count": v.entry_count}
            person_entities.append({
                "id": p.id,
                "slug": p.slug,
                "display_name": p.display_name or p.slug,
                "variants": variants,
            })

        # keep template-compatible names
        return render_template(
            "index.html",
            person_entities=person_entities,
            unlinked_variants=[],
            resume_sets_v2=[],
            supported_languages=SUPPORTED_LANGUAGES,
        )

    @app.route("/toggle-canonical-keys")
    def toggle_canonical_keys():
        session["show_canonical_keys"] = not bool(session.get("show_canonical_keys", False))
        return redirect(request.referrer or url_for("index"))

    @app.route("/set-language/<lang>")
    def set_language(lang: str):
        if lang not in SUPPORTED_LANGUAGES:
            abort(404)
        session["current_language"] = lang
        return redirect(request.referrer or url_for("index"))

    # -------------------------
    # Person pages
    # -------------------------
    @app.route("/person/<person>")
    def person_dashboard(person: str):
        p = PersonEntity.query.filter_by(slug=person).first_or_404()
        lang = current_language()

        # compute section counts
        section_cards = []
        for sec in SECTION_ORDER:
            count = Entry.query.filter_by(person_id=p.id, lang_code=lang, section=sec).count()
            section_cards.append({
                "key": sec,
                "label": get_section_label(sec),
                "icon": get_section_icon(sec),
                "count": count,
            })

        # variants summary
        variants = {l: (CVVariant.query.filter_by(person_id=p.id, lang_code=l).first() is not None) for l in SUPPORTED_LANGUAGES}

        return render_template(
            "person_dashboard.html",
            person=p,
            section_cards=section_cards,
            variants=variants,
        )

    @app.route("/person-entity/<int:person_entity_id>")
    def person_entity_detail(person_entity_id: int):
        p = PersonEntity.query.get_or_404(person_entity_id)
        return redirect(url_for("person_dashboard", person=p.slug))

    @app.route("/variant/<resume_key>")
    def variant_status_route(resume_key: str):
        p = PersonEntity.query.filter_by(slug=resume_key).first_or_404()
        variants = []
        for lang in SUPPORTED_LANGUAGES:
            v = CVVariant.query.filter_by(person_id=p.id, lang_code=lang).first()
            variants.append({"lang": lang, "exists": v is not None, "entry_count": v.entry_count if v else 0})
        return render_template("variant_status.html", person=p, variants=variants)

    @app.route("/create-person", methods=["GET", "POST"])
    def create_person_route():
        if request.method == "POST":
            slug = (request.form.get("slug") or "").strip()
            display_name = (request.form.get("display_name") or "").strip() or None
            if not slug:
                flash("slug is required.", "error")
                return redirect(url_for("create_person_route"))
            if PersonEntity.query.filter_by(slug=slug).first():
                flash("A person with this slug already exists.", "error")
                return redirect(url_for("create_person_route"))
            p = PersonEntity(slug=slug, display_name=display_name)
            db.session.add(p)
            db.session.commit()
            flash("Person created.", "success")
            return redirect(url_for("person_dashboard", person=slug))
        return render_template("person_entity_detail.html", create_mode=True, person=None)

    @app.route("/auto-group", methods=["POST"])
    def auto_group_route():
        # In this simplified local UI, variants are always grouped by resume_key during import.
        flash("Auto-group is not needed here (variants are grouped on import).", "success")
        return redirect(url_for("index"))

    # -------------------------
    # Section listing
    # -------------------------
    @app.route("/person/<person>/section/<section>")
    def section_entries(person: str, section: str):
        p = PersonEntity.query.filter_by(slug=person).first_or_404()
        if section not in SECTION_LABELS:
            abort(404)
        lang = current_language()

        entries = Entry.query.filter_by(person_id=p.id, lang_code=lang, section=section).order_by(Entry.sort_order.asc(), Entry.id.asc()).all()

        # decorate with tags (in UI language)
        for e in entries:
            e.tags = list_entity_tags(p.id, section, e.stable_id, lang)  # type: ignore[attr-defined]

        skills_by_category = None
        if section == "skills":
            skills_by_category = skills_group(entries)

        return render_template(
            "section.html",
            person=p,
            section=section,
            entries=entries,
            skills_by_category=skills_by_category,
        )

    @app.route("/person/<person>/section/<section>/new", methods=["GET", "POST"])
    def create_entry_route(person: str, section: str):
        p = PersonEntity.query.filter_by(slug=person).first_or_404()
        if section not in SECTION_LABELS:
            abort(404)
        lang = current_language()

        # create a new stable group id
        stable_id = str(__import__("uuid").uuid4())
        sort_order = Entry.query.filter_by(person_id=p.id, lang_code=lang, section=section).count()

        payload = default_entry_data(section)
        e = Entry(
            person_id=p.id,
            resume_key=p.slug,
            lang_code=lang,
            section=section,
            stable_id=stable_id,
            sort_order=sort_order,
            data=payload,
            summary=summarize_entry(section, payload),
            needs_translation=True,
        )
        db.session.add(e)
        db.session.commit()
        flash("Entry created.", "success")
        return redirect(url_for("edit_entry_route", entry_id=e.id))

    # -------------------------
    # Entry pages (detail, tags, raw edit, cross-language)
    # -------------------------
    @app.route("/entry/<int:entry_id>", methods=["GET", "POST"])
    def entry_detail(entry_id: int):
        e = Entry.query.get_or_404(entry_id)
        p = PersonEntity.query.get_or_404(e.person_id)
        lang = current_language()

        if request.method == "POST":
            action = request.form.get("action")
            if action == "add_tag":
                tag_input = (request.form.get("tag_input") or "").strip()
                if not tag_input:
                    flash("Tag input is empty.", "warning")
                    return redirect(url_for("entry_detail", entry_id=entry_id))
                try:
                    t = resolve_or_create_tag(tag_input, lang)
                    changed = attach_tag(p.id, e.section, e.stable_id, t.id)
                    db.session.commit()
                    flash("Tag added." if changed else "Tag already exists.", "success")
                except Exception as ex:
                    db.session.rollback()
                    flash(f"Failed to add tag: {ex}", "error")
                return redirect(url_for("entry_detail", entry_id=entry_id))

            if action == "remove_tag":
                tag_id = int(request.form.get("tag_id") or "0")
                try:
                    changed = detach_tag(p.id, e.section, e.stable_id, tag_id)
                    db.session.commit()
                    flash("Tag removed." if changed else "Tag not found.", "success")
                except Exception as ex:
                    db.session.rollback()
                    flash(f"Failed to remove tag: {ex}", "error")
                return redirect(url_for("entry_detail", entry_id=entry_id))

        tags = []
        links = EntityTag.query.filter_by(person_id=p.id, section=e.section, stable_id=e.stable_id).all()
        for link in links:
            label = TagTranslation.query.filter_by(tag_id=link.tag_id, lang_code=lang).first()
            slug = Tag.query.get(link.tag_id).slug if Tag.query.get(link.tag_id) else "tag"
            tags.append({
                "id": link.tag_id,
                "label": label.label if label else slug,
                "slug": slug,
            })
        tags = sorted(tags, key=lambda x: x["label"].lower())

        return render_template(
            "entry_detail.html",
            entry=e,
            person=p,
            tags=tags,
            json_pretty=json.dumps(e.data, ensure_ascii=False, indent=2),
        )

    @app.route("/entry/<int:entry_id>/edit", methods=["GET", "POST"])
    def edit_entry_route(entry_id: int):
        e = Entry.query.get_or_404(entry_id)
        p = PersonEntity.query.get_or_404(e.person_id)

        if request.method == "POST":
            raw = request.form.get("raw_json") or ""
            try:
                parsed = json.loads(raw)
                if not isinstance(parsed, dict):
                    raise ValueError("JSON must be an object (dict).")
                e.data = parsed
                e.summary = summarize_entry(e.section, e.data)
                db.session.commit()
                flash("Entry updated.", "success")
                return redirect(url_for("entry_detail", entry_id=e.id))
            except Exception as ex:
                db.session.rollback()
                flash(f"Invalid JSON: {ex}", "error")

        return render_template(
            "entry_edit.html",
            entry=e,
            person=p,
            raw_json=json.dumps(e.data, ensure_ascii=False, indent=2),
        )

    @app.route("/entry/<int:entry_id>/cross-language", methods=["GET", "POST"])
    def cross_language_editor(entry_id: int):
        base_entry = Entry.query.get_or_404(entry_id)
        p = PersonEntity.query.get_or_404(base_entry.person_id)

        # collect linked entries (by stable_id + section + person)
        linked = {}
        for lang in SUPPORTED_LANGUAGES:
            le = Entry.query.filter_by(person_id=p.id, section=base_entry.section, stable_id=base_entry.stable_id, lang_code=lang).first()
            if le:
                linked[lang] = le

        fields = SECTION_FIELDS.get(base_entry.section)
        if not fields:
            # fallback: show all keys from any available entry
            union_keys = set()
            for le in linked.values():
                union_keys |= set((le.data or {}).keys())
            fields = {k: SECTION_FIELDS.get("projects", {}).get("title") or type("X", (), {}) for k in union_keys}  # placeholder

        # normalize canonical_key
        normalized_fields = {}
        for k, fi in (fields or {}).items():
            # fi may not be FieldInfo if fallback
            try:
                fi.canonical_key = k
                normalized_fields[k] = fi
            except Exception:
                pass

        if request.method == "POST":
            # update each present language entry
            for lang, le in linked.items():
                # Update only fields we know
                new_data = dict(le.data or {})
                for field_name in normalized_fields.keys():
                    form_key = f"field_{lang}_{field_name}"
                    if form_key in request.form:
                        val = request.form.get(form_key)
                        new_data[field_name] = val
                le.data = new_data
                le.summary = summarize_entry(le.section, le.data)
                if request.form.get("mark_translated"):
                    le.needs_translation = False

            db.session.commit()
            flash("Saved cross-language changes.", "success")
            return redirect(url_for("entry_detail", entry_id=entry_id))

        # prepare fields map
        fields_map = {}
        for k, fi in normalized_fields.items():
            fields_map[k] = {
                "label": getattr(fi, "label", k),
                "input_type": getattr(fi, "input_type", "text"),
                "multiline": getattr(fi, "multiline", False),
                "shared": getattr(fi, "shared", False),
                "placeholder": getattr(fi, "placeholder", ""),
                "canonical_key": k,
                "localized_label": getattr(fi, "localized_label", None),
            }

        # entry "view model" for template
        class _EntryVM:
            def __init__(self, entry: Entry):
                self.id = entry.id
                self.section = entry.section
                self.person_slug = p.slug
                self.summary = entry.summary
                self.data = entry.data or {}
                self.needs_translation = entry.needs_translation

        linked_entries = {lang: _EntryVM(le) for lang, le in linked.items()}

        return render_template(
            "cross_language_editor.html",
            entry=_EntryVM(base_entry),
            linked_entries=linked_entries,
            fields=fields_map,
            stable_id=base_entry.stable_id,
            fields_by_lang=None,
        )

    @app.route("/entry/<int:entry_id>/create-missing/<target_lang>")
    def create_missing_lang_entry_route(entry_id: int, target_lang: str):
        if target_lang not in SUPPORTED_LANGUAGES:
            abort(404)
        base_entry = Entry.query.get_or_404(entry_id)
        p = PersonEntity.query.get_or_404(base_entry.person_id)

        exists = Entry.query.filter_by(person_id=p.id, section=base_entry.section, stable_id=base_entry.stable_id, lang_code=target_lang).first()
        if exists:
            flash("That language entry already exists.", "warning")
            return redirect(url_for("cross_language_editor", entry_id=entry_id))

        # copy shared fields from an available source (prefer EN)
        source = Entry.query.filter_by(person_id=p.id, section=base_entry.section, stable_id=base_entry.stable_id, lang_code="en").first() or base_entry
        new_data = dict(source.data or {})

        # wipe non-shared fields if we have schema
        fields = SECTION_FIELDS.get(base_entry.section)
        if fields:
            for k, fi in fields.items():
                if not getattr(fi, "shared", False):
                    new_data[k] = ""

        # insert
        sort_order = base_entry.sort_order
        e = Entry(
            person_id=p.id,
            resume_key=p.slug,
            lang_code=target_lang,
            section=base_entry.section,
            stable_id=base_entry.stable_id,
            sort_order=sort_order,
            data=new_data,
            summary=summarize_entry(base_entry.section, new_data),
            needs_translation=True,
        )
        db.session.add(e)
        # ensure variant record exists
        v = CVVariant.query.filter_by(person_id=p.id, lang_code=target_lang).first()
        if v is None:
            v = CVVariant(person_id=p.id, resume_key=p.slug, lang_code=target_lang)
            db.session.add(v)
        db.session.commit()
        flash(f"Created {target_lang.upper()} entry.", "success")
        return redirect(url_for("cross_language_editor", entry_id=base_entry.id))

    # -------------------------
    # Import
    # -------------------------
    @app.route("/import")
    def import_page():
        persons = PersonEntity.query.order_by(PersonEntity.slug.asc()).all()
        history = ImportHistory.query.order_by(ImportHistory.timestamp.desc()).limit(10).all()
        return render_template("import.html", existing_persons=persons, import_history=history)

    @app.route("/import/upload", methods=["POST"])
    def import_upload():
        files = request.files.getlist("files")
        mode = request.form.get("import_mode") or "merge"
        overwrite = (mode == "overwrite")

        if not files:
            flash("No files selected.", "error")
            return redirect(url_for("import_page"))

        success = 0
        errors = 0
        logs: List[str] = []
        for f in files:
            try:
                resume_key, lang, count, warnings = import_cv_json_bytes(f.read(), f.filename, import_mode=mode)
                success += 1
                logs.append(f"Imported {f.filename} as {resume_key} [{lang}] ({count} entries).")
                for w in warnings:
                    logs.append(f"  WARN: {w}")
            except Exception as ex:
                errors += 1
                logs.append(f"ERROR importing {f.filename}: {ex}")

        h = ImportHistory(
            files_count=len(files),
            overwrite=overwrite,
            success_count=success,
            error_count=errors,
            log="\n".join(logs),
        )
        db.session.add(h)
        db.session.commit()

        if errors == 0:
            flash(f"Imported {success} file(s) successfully.", "success")
        else:
            flash(f"Imported {success} file(s), {errors} failed. See history.", "warning")
        return redirect(url_for("import_page"))

    @app.route("/import/from-disk", methods=["POST"])
    def import_from_disk():
        repo_root = Path(app.config["REPO_ROOT"])
        cvs_dir = repo_root / "data" / "cvs"
        if not cvs_dir.exists():
            flash("data/cvs folder not found.", "error")
            return redirect(url_for("import_page"))

        json_files = sorted([p for p in cvs_dir.glob("*.json")])
        if not json_files:
            flash("No JSON files found in data/cvs.", "warning")
            return redirect(url_for("import_page"))

        success = 0
        errors = 0
        logs: List[str] = []
        for p in json_files:
            try:
                b = p.read_bytes()
                resume_key, lang, count, warnings = import_cv_json_bytes(b, p.name, import_mode="merge")
                success += 1
                logs.append(f"Imported {p.name} as {resume_key} [{lang}] ({count} entries).")
                for w in warnings:
                    logs.append(f"  WARN: {w}")
            except Exception as ex:
                errors += 1
                logs.append(f"ERROR importing {p.name}: {ex}")

        h = ImportHistory(
            files_count=len(json_files),
            overwrite=False,
            success_count=success,
            error_count=errors,
            log="\n".join(logs),
        )
        db.session.add(h)
        db.session.commit()

        flash(f"Imported from disk: {success} succeeded, {errors} failed.", "success" if errors == 0 else "warning")
        return redirect(url_for("import_page"))

    # -------------------------
    # Export + Preview
    # -------------------------
    @app.route("/export")
    def export_page():
        persons = PersonEntity.query.order_by(PersonEntity.slug.asc()).all()
        export_history = ExportHistory.query.order_by(ExportHistory.timestamp.desc()).limit(15).all()

        # available variants
        available_variants = []
        for p in persons:
            for lang in SUPPORTED_LANGUAGES:
                v = CVVariant.query.filter_by(person_id=p.id, lang_code=lang).first()
                if v:
                    available_variants.append((p.slug, lang))

        return render_template(
            "export.html",
            persons=persons,
            export_history=export_history,
            available_variants=available_variants,
            current_language=current_language(),
        )

    @app.route("/export/preview", methods=["POST"])
    def export_preview_v2():
        resume_key = request.form.get("person") or ""
        lang_code = request.form.get("language") or current_language()
        if not resume_key:
            flash("Select a person first.", "warning")
            return redirect(url_for("export_page"))
        return redirect(url_for("preview_export", person=resume_key, language=lang_code))

    @app.route("/preview/<person>")
    def preview_export(person: str):
        export_language = request.args.get("language") or current_language()
        if export_language not in SUPPORTED_LANGUAGES:
            export_language = "en"

        # Here, 'person' is resume_key/slug, and we preview exporting tags in export_language.
        try:
            json_payload = export_variant_to_json(person, export_language, export_language)
        except Exception as ex:
            flash(f"Preview failed: {ex}", "error")
            return redirect(url_for("export_page"))

        # lightweight summary object for template
        cv_data = type("CVD", (), {})()
        cv_data.name = person
        for sec in ["projects", "experiences", "publications", "education", "skills"]:
            setattr(cv_data, sec, json_payload.get(sec))

        return render_template(
            "preview.html",
            person=person,
            export_language=export_language,
            json_preview=json.dumps(json_payload, ensure_ascii=False, indent=2),
            cv_data=cv_data,
            supported_languages=SUPPORTED_LANGUAGES,
        )

    @app.route("/export/person/<person>", methods=["POST"])
    def export_person(person: str):
        export_language = request.form.get("language") or current_language()
        if export_language not in SUPPORTED_LANGUAGES:
            export_language = "en"
        repo_root = Path(app.config["REPO_ROOT"])

        try:
            out_path = write_export_file(repo_root, person, export_language, export_language)
            h = ExportHistory(
                batch=False,
                resume_key=person,
                persons_count=1,
                language=export_language,
                output_dir=str(out_path.parent),
                output_path=str(out_path),
                success=True,
                success_count=1,
                failed_count=0,
            )
            db.session.add(h)
            db.session.commit()
            flash(f"Exported to {out_path}", "success")
        except Exception as ex:
            db.session.rollback()
            flash(f"Export failed: {ex}", "error")
        return redirect(url_for("export_page"))

    @app.route("/export/single", methods=["POST"])
    def export_single():
        resume_key = request.form.get("person") or ""
        lang_code = request.form.get("language") or current_language()
        if not resume_key:
            flash("Select a person first.", "warning")
            return redirect(url_for("export_page"))

        if lang_code not in SUPPORTED_LANGUAGES:
            lang_code = "en"

        repo_root = Path(app.config["REPO_ROOT"])
        try:
            out_path = write_export_file(repo_root, resume_key, lang_code, lang_code)
            h = ExportHistory(
                batch=False,
                resume_key=resume_key,
                persons_count=1,
                language=lang_code,
                output_dir=str(out_path.parent),
                output_path=str(out_path),
                success=True,
                success_count=1,
                failed_count=0,
            )
            db.session.add(h)
            db.session.commit()
            flash(f"Exported to {out_path}", "success")
        except Exception as ex:
            db.session.rollback()
            flash(f"Export failed: {ex}", "error")
        return redirect(url_for("export_page"))

    @app.route("/export/batch", methods=["POST"])
    def export_batch():
        persons = request.form.getlist("persons")
        if not persons:
            flash("Select at least one person.", "warning")
            return redirect(url_for("export_page"))

        repo_root = Path(app.config["REPO_ROOT"])
        success = 0
        failed = 0
        for resume_key in persons:
            for lang in SUPPORTED_LANGUAGES:
                v = PersonEntity.query.filter_by(slug=resume_key).first()
                if not v:
                    continue
                if CVVariant.query.filter_by(person_id=v.id, lang_code=lang).first() is None:
                    continue
                try:
                    write_export_file(repo_root, resume_key, lang, lang)
                    success += 1
                except Exception:
                    failed += 1

        h = ExportHistory(
            batch=True,
            resume_key=None,
            persons_count=len(persons),
            language=None,
            output_dir=str((repo_root / "output" / "json")),
            output_path=None,
            success=(failed == 0),
            success_count=success,
            failed_count=failed,
        )
        db.session.add(h)
        db.session.commit()

        flash(f"Batch export done: {success} succeeded, {failed} failed.", "success" if failed == 0 else "warning")
        return redirect(url_for("export_page"))

    # -------------------------
    # Tags management
    # -------------------------
    @app.route("/tags", methods=["GET", "POST"])
    def tags_list():
        lang = current_language()

        if request.method == "POST":
            action = request.form.get("action")
            try:
                if action == "create_tag":
                    label = (request.form.get("label") or "").strip()
                    if not label:
                        flash("Label is required.", "warning")
                        return redirect(url_for("tags_list"))
                    t = resolve_or_create_tag(label, lang)
                    db.session.commit()
                    flash("Tag created.", "success")
                    return redirect(url_for("tags_list"))

                if action == "add_translation":
                    tag_id = int(request.form.get("tag_id") or "0")
                    tr_lang = request.form.get("tr_lang") or lang
                    tr_label = (request.form.get("tr_label") or "").strip()
                    if tr_lang not in SUPPORTED_LANGUAGES:
                        raise ValueError("Invalid language.")
                    if not tr_label:
                        raise ValueError("Translation label required.")
                    existing = TagTranslation.query.filter_by(tag_id=tag_id, lang_code=tr_lang).first()
                    if existing:
                        existing.label = tr_label
                    else:
                        db.session.add(TagTranslation(tag_id=tag_id, lang_code=tr_lang, label=tr_label))
                    db.session.commit()
                    flash("Translation saved.", "success")
                    return redirect(url_for("tags_list"))

                if action == "add_alias":
                    tag_id = int(request.form.get("tag_id") or "0")
                    al_lang = request.form.get("al_lang") or lang
                    al_label = (request.form.get("al_label") or "").strip()
                    if al_lang not in SUPPORTED_LANGUAGES:
                        raise ValueError("Invalid language.")
                    if not al_label:
                        raise ValueError("Alias label required.")
                    # unique constraint (lang, label) enforced; handle gracefully
                    existing = TagAlias.query.filter_by(lang_code=al_lang, alias_label=al_label).first()
                    if existing and existing.tag_id != tag_id:
                        raise ValueError("This alias already points to another tag.")
                    if existing is None:
                        db.session.add(TagAlias(tag_id=tag_id, lang_code=al_lang, alias_label=al_label))
                    db.session.commit()
                    flash("Alias added.", "success")
                    return redirect(url_for("tags_list"))

            except Exception as ex:
                db.session.rollback()
                flash(f"Tag update failed: {ex}", "error")
                return redirect(url_for("tags_list"))

        tags = get_tag_table(lang)
        return render_template("tags.html", tags=tags)

    # -------------------------
    # Diagnostics
    # -------------------------
    @app.route("/diagnostics")
    def diagnostics():
        # Translation coverage per person/section/stable_id
        persons = PersonEntity.query.order_by(PersonEntity.slug.asc()).all()
        rows = []
        for p in persons:
            # group entries by (section, stable_id)
            groups: Dict[Tuple[str, str], Dict[str, int]] = {}
            ents = Entry.query.filter_by(person_id=p.id).all()
            for e in ents:
                groups.setdefault((e.section, e.stable_id), {})[e.lang_code] = e.id

            for (section, stable_id), lang_map in groups.items():
                missing = [l for l in SUPPORTED_LANGUAGES if l not in lang_map]
                if missing:
                    # choose an existing entry id to link
                    any_id = next(iter(lang_map.values()))
                    rows.append({
                        "person": p.slug,
                        "section": section,
                        "stable_id": stable_id,
                        "missing": missing,
                        "entry_id": any_id,
                    })

        # Tags without translations in some languages
        tag_rows = []
        for t in Tag.query.order_by(Tag.slug.asc()).all():
            tr = {x.lang_code for x in TagTranslation.query.filter_by(tag_id=t.id).all()}
            missing_tr = [l for l in SUPPORTED_LANGUAGES if l not in tr]
            if missing_tr:
                tag_rows.append({"slug": t.slug, "tag_id": t.id, "missing": missing_tr})

        return render_template("diagnostics.html", missing_translations=rows, tags_missing_translations=tag_rows)

    return app
