from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import db, PersonEntity, CVVariant, Entry, Tag, TagTranslation, TagAlias, EntityTag
from .fields import (
    SUPPORTED_LANGUAGES,
    SECTION_ORDER,
    stable_uuid,
    infer_lang_from_filename,
    infer_resume_key_from_filename,
    summarize_entry,
    skills_flatten,
    skills_group,
)
from .tagging import resolve_or_create_tag, attach_tag

logger = logging.getLogger(__name__)


def ensure_person(resume_key: str) -> PersonEntity:
    p = PersonEntity.query.filter_by(slug=resume_key).first()
    if p:
        return p
    p = PersonEntity(slug=resume_key, display_name=resume_key.replace("_", " ").title())
    db.session.add(p)
    db.session.flush()
    return p


def upsert_variant(person: PersonEntity, resume_key: str, lang_code: str, source_filename: Optional[str], config: Optional[dict]) -> CVVariant:
    v = CVVariant.query.filter_by(person_id=person.id, lang_code=lang_code).first()
    if v is None:
        v = CVVariant(person_id=person.id, resume_key=resume_key, lang_code=lang_code)
        db.session.add(v)
    v.source_filename = source_filename
    v.imported_at = datetime.utcnow()
    v.config = config
    return v


def cleanup_orphaned_entity_tags(person_id: int, section: str, stable_id: str) -> bool:
    """
    Clean up EntityTag links for a (person, section, stable_id) if no entries remain.
    Returns True if EntityTags were deleted, False otherwise.
    """
    # Check if any entries with this stable_id still exist
    remaining = Entry.query.filter_by(
        person_id=person_id, section=section, stable_id=stable_id
    ).first()
    if remaining is None:
        # No entries with this stable_id remain; delete associated EntityTag links
        count = EntityTag.query.filter_by(
            person_id=person_id, section=section, stable_id=stable_id
        ).delete(synchronize_session=False)
        return count > 0
    return False


def _wipe_variant_entries(person_id: int, lang_code: str) -> None:
    # Collect stable_ids being deleted in this language
    entries_to_delete = Entry.query.filter_by(person_id=person_id, lang_code=lang_code).all()
    stable_ids_to_check = {(e.section, e.stable_id) for e in entries_to_delete}
    
    # Delete the entries
    Entry.query.filter_by(person_id=person_id, lang_code=lang_code).delete(synchronize_session=False)
    
    # Clean up orphaned EntityTag links for stable_ids that no longer exist in ANY language
    for section, stable_id in stable_ids_to_check:
        cleanup_orphaned_entity_tags(person_id, section, stable_id)


def import_cv_json_bytes(
    file_bytes: bytes,
    filename: str,
    *,
    import_mode: str = "merge",
) -> Tuple[str, str, int, List[str]]:
    """
    Import one CV JSON file into DB.
    Returns: (resume_key, lang_code, entry_count, warnings)
    """
    warnings: List[str] = []
    cv = json.loads(file_bytes.decode("utf-8"))

    lang = infer_lang_from_filename(filename)
    resume_key = infer_resume_key_from_filename(filename)

    person = ensure_person(resume_key)

    # overwrite mode wipes entries for that language variant
    if import_mode == "overwrite":
        _wipe_variant_entries(person.id, lang)

    variant = upsert_variant(person, resume_key, lang, filename, cv.get("config"))

    entry_count = 0

    # Helper to create/update entry row
    def upsert_entry(section: str, stable_id: str, sort_order: int, payload: Dict[str, Any]) -> Entry:
        nonlocal entry_count
        e = Entry.query.filter_by(person_id=person.id, lang_code=lang, section=section, stable_id=stable_id).first()
        if e is None:
            e = Entry(
                person_id=person.id,
                resume_key=resume_key,
                lang_code=lang,
                section=section,
                stable_id=stable_id,
                sort_order=sort_order,
                data={},
            )
            db.session.add(e)
            entry_count += 1
        e.sort_order = sort_order
        # Strip type_key from stored data - tags are managed via EntityTag links
        clean_payload = {k: v for k, v in (payload or {}).items() if k != "type_key"}
        e.data = clean_payload
        e.summary = summarize_entry(section, e.data)
        return e

    # Import each section
    for section in SECTION_ORDER:
        if section not in cv:
            continue

        if section == "skills":
            flat = skills_flatten(cv.get("skills") or {})
            for i, item in enumerate(flat):
                # stable key by category + skill name
                key = f"{item.get('parent_category','')}|{item.get('sub_category','')}|{item.get('short_name') or item.get('long_name') or i}"
                sid = stable_uuid(resume_key, "skills", key)
                e = upsert_entry("skills", sid, i, item)
                _import_tags_from_payload(person.id, "skills", sid, item, lang, warnings)
            continue

        if section == "workshop_and_certifications":
            # flatten issuer->certifications
            ws_list = cv.get(section) or []
            idx = 0
            for issuer_i, block in enumerate(ws_list):
                issuer = ""
                if isinstance(block, dict):
                    issuer = block.get("issuer") or ""
                    certs = block.get("certifications") or []
                else:
                    certs = []
                for cert_i, cert in enumerate(certs):
                    if not isinstance(cert, dict):
                        continue
                    payload = dict(cert)
                    payload["issuer"] = issuer
                    key = f"{issuer_i}:{cert_i}:{payload.get('name') or cert_i}"
                    sid = stable_uuid(resume_key, section, key)
                    e = upsert_entry(section, sid, idx, payload)
                    _import_tags_from_payload(person.id, section, sid, payload, lang, warnings)
                    idx += 1
            continue

        # list-like sections
        sec_val = cv.get(section)
        if isinstance(sec_val, list):
            for i, item in enumerate(sec_val):
                if not isinstance(item, dict):
                    continue
                sid = stable_uuid(resume_key, section, str(i))
                e = upsert_entry(section, sid, i, item)
                _import_tags_from_payload(person.id, section, sid, item, lang, warnings)
        elif isinstance(sec_val, dict):
            sid = stable_uuid(resume_key, section, "0")
            e = upsert_entry(section, sid, 0, sec_val)
            _import_tags_from_payload(person.id, section, sid, sec_val, lang, warnings)
        else:
            warnings.append(f"Section {section}: unsupported type {type(sec_val)}")

    variant.entry_count = Entry.query.filter_by(person_id=person.id, lang_code=lang).count()
    db.session.commit()
    return resume_key, lang, variant.entry_count, warnings


def _import_tags_from_payload(person_id: int, section: str, stable_id: str, payload: Dict[str, Any], lang_code: str, warnings: List[str]) -> None:
    """
    Reads payload['type_key'] if present and attaches those tags to (person, section, stable_id).
    """
    type_key = payload.get("type_key")
    if not type_key:
        return
    if not isinstance(type_key, list):
        warnings.append(f"type_key is not a list in {section}/{stable_id}")
        return
    for label in type_key:
        if not isinstance(label, str) or not label.strip():
            continue
        try:
            t = resolve_or_create_tag(label.strip(), lang_code)
            attach_tag(person_id, section, stable_id, t.id)
        except Exception as ex:
            warnings.append(f"Failed to import tag '{label}': {ex}")


def export_variant_to_json(resume_key: str, lang_code: str, export_language: str) -> Dict[str, Any]:
    """
    Reconstruct the original CV JSON shape for a person+lang from the database.
    Tags are exported into 'type_key' in export_language (fallback: slug).
    """
    person = PersonEntity.query.filter_by(slug=resume_key).first()
    if not person:
        raise ValueError(f"Unknown person: {resume_key}")

    variant = CVVariant.query.filter_by(person_id=person.id, lang_code=lang_code).first()
    config = variant.config if variant else None

    out: Dict[str, Any] = {}
    if config is not None:
        out["config"] = config

    # Build tag map for stable groups
    tag_map = _tag_map_for_person(person.id, export_language)

    # basics etc
    for section in SECTION_ORDER:
        entries = Entry.query.filter_by(person_id=person.id, lang_code=lang_code, section=section).order_by(Entry.sort_order.asc(), Entry.id.asc()).all()
        if not entries:
            continue

        if section == "skills":
            # rebuild nested
            skills_obj: Dict[str, Dict[str, List[dict]]] = {}
            for e in entries:
                d = dict(e.data or {})
                # inject exported tags - always use tag_map, never fallback to raw type_key
                d["type_key"] = tag_map.get((section, e.stable_id), [])
                parent = d.pop("parent_category", "Other")
                sub = d.pop("sub_category", "Other")
                skills_obj.setdefault(parent, {}).setdefault(sub, []).append(d)
            out["skills"] = skills_obj
            continue

        if section == "workshop_and_certifications":
            # rebuild issuer blocks
            blocks: Dict[str, List[dict]] = {}
            order: List[str] = []
            for e in entries:
                d = dict(e.data or {})
                # always use tag_map, never fallback to raw type_key
                d["type_key"] = tag_map.get((section, e.stable_id), [])
                issuer = d.pop("issuer", "") or "Unknown"
                if issuer not in blocks:
                    blocks[issuer] = []
                    order.append(issuer)
                blocks[issuer].append(d)
            out_list: List[dict] = []
            for issuer in order:
                out_list.append({"issuer": issuer, "certifications": blocks[issuer]})
            out[section] = out_list
            continue

        # list-like in JSON: basics is list in your files, even if 1 item
        if section == "basics":
            items = []
            for e in entries:
                d = dict(e.data or {})
                # basics doesn't have type_key typically, but keep consistent
                items.append(d)
            out["basics"] = items
            continue

        # all other sections are list
        items = []
        for e in entries:
            d = dict(e.data or {})
            # always use tag_map, never fallback to raw type_key
            d["type_key"] = tag_map.get((section, e.stable_id), [])
            items.append(d)
        out[section] = items

    return out


def _tag_map_for_person(person_id: int, export_language: str) -> Dict[Tuple[str, str], List[str]]:
    """
    Returns {(section, stable_id): [labels...]} for the given person.
    """
    # Collect all links in one go
    links = EntityTag.query.filter_by(person_id=person_id).all()
    if not links:
        return {}

    # tag translations cache
    tr_cache: Dict[Tuple[int, str], str] = {}
    def label_for(tag_id: int) -> str:
        key = (tag_id, export_language)
        if key in tr_cache:
            return tr_cache[key]
        tr = TagTranslation.query.filter_by(tag_id=tag_id, lang_code=export_language).first()
        if tr:
            tr_cache[key] = tr.label
            return tr.label
        t = Tag.query.get(tag_id)
        if t:
            logger.debug(f"Missing translation for tag '{t.slug}' (id={tag_id}) in language '{export_language}', using slug as fallback")
            tr_cache[key] = t.slug
            return t.slug
        logger.warning(f"Tag with id={tag_id} not found during export, returning generic fallback 'tag'")
        tr_cache[key] = "tag"
        return "tag"

    tag_map: Dict[Tuple[str, str], List[str]] = {}
    for l in links:
        k = (l.section, l.stable_id)
        tag_map.setdefault(k, []).append(label_for(l.tag_id))

    # normalize ordering
    for k in list(tag_map.keys()):
        tag_map[k] = sorted(set(tag_map[k]), key=lambda x: x.lower())
    return tag_map


def write_export_file(repo_root: Path, resume_key: str, lang_code: str, export_language: str, *, out_dir: Optional[Path] = None) -> Path:
    """
    Write an exported JSON file to output/json/.
    """
    out_dir = out_dir or (repo_root / "output" / "json")
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = export_variant_to_json(resume_key, lang_code, export_language)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"{resume_key}_{lang_code}_export_{export_language}_{ts}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
