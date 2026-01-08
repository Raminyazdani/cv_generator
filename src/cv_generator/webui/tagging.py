from __future__ import annotations

import csv
import io
from typing import Dict, List, Optional, Tuple

from .models import db, Tag, TagAlias, TagTranslation, EntityTag
from .fields import slugify, SUPPORTED_LANGUAGES


def get_all_tags_for_autocomplete(lang_code: str) -> List[Dict[str, any]]:
    """
    Return all tags with their labels for autocomplete/selection.
    Each tag includes id, slug, and label in the specified language.
    """
    tags = Tag.query.order_by(Tag.slug.asc()).all()
    results = []
    for t in tags:
        tr = TagTranslation.query.filter_by(tag_id=t.id, lang_code=lang_code).first()
        label = tr.label if tr else t.slug
        results.append({
            "id": t.id,
            "slug": t.slug,
            "label": label,
        })
    return results


def get_tag_label(tag_id: int, lang_code: str) -> str:
    tr = TagTranslation.query.filter_by(tag_id=tag_id, lang_code=lang_code).first()
    if tr:
        return tr.label
    tag = Tag.query.get(tag_id)
    return tag.slug if tag else "tag"


def list_entity_tags(person_id: int, section: str, stable_id: str, lang_code: str) -> List[str]:
    links = EntityTag.query.filter_by(person_id=person_id, section=section, stable_id=stable_id).all()
    if not links:
        return []
    labels = []
    for l in links:
        labels.append(get_tag_label(l.tag_id, lang_code))
    # stable, readable order
    return sorted(labels, key=lambda x: x.lower())


def resolve_or_create_tag(input_text: str, lang_code: str) -> Tag:
    """
    input_text can be:
      - a slug
      - a localized label (via TagAlias)
      - an existing translation label
    If it doesn't exist, create a new Tag with translation + alias in that language.
    """
    raw = (input_text or "").strip()
    if not raw:
        raise ValueError("Empty tag input.")

    # 1) slug direct hit
    t = Tag.query.filter_by(slug=raw).first()
    if t:
        return t

    # 2) alias hit (lang-specific)
    alias = TagAlias.query.filter_by(lang_code=lang_code, alias_label=raw).first()
    if alias:
        t2 = Tag.query.get(alias.tag_id)
        if t2:
            return t2

    # 3) translation label hit (lang-specific) - prevents duplicate tag creation
    existing_translation = TagTranslation.query.filter_by(lang_code=lang_code, label=raw).first()
    if existing_translation:
        t3 = Tag.query.get(existing_translation.tag_id)
        if t3:
            return t3

    # 4) create
    slug = slugify(raw)
    # ensure uniqueness
    base = slug
    i = 2
    while Tag.query.filter_by(slug=slug).first() is not None:
        slug = f"{base}-{i}"
        i += 1

    t = Tag(slug=slug)
    db.session.add(t)
    db.session.flush()  # t.id available

    # translation
    db.session.add(TagTranslation(tag_id=t.id, lang_code=lang_code, label=raw))
    # alias
    db.session.add(TagAlias(tag_id=t.id, lang_code=lang_code, alias_label=raw))
    return t


def attach_tag(person_id: int, section: str, stable_id: str, tag_id: int) -> bool:
    exists = EntityTag.query.filter_by(person_id=person_id, section=section, stable_id=stable_id, tag_id=tag_id).first()
    if exists:
        return False
    db.session.add(EntityTag(person_id=person_id, section=section, stable_id=stable_id, tag_id=tag_id))
    return True


def detach_tag(person_id: int, section: str, stable_id: str, tag_id: int) -> bool:
    link = EntityTag.query.filter_by(person_id=person_id, section=section, stable_id=stable_id, tag_id=tag_id).first()
    if not link:
        return False
    db.session.delete(link)
    return True


def get_tag_table(lang_code: str) -> List[dict]:
    """
    For tags management page: return a list of tags with translations+aliases.
    """
    tags = Tag.query.order_by(Tag.slug.asc()).all()
    rows = []
    for t in tags:
        translations = {tr.lang_code: tr.label for tr in TagTranslation.query.filter_by(tag_id=t.id).all()}
        aliases = {al.lang_code: [] for al in TagAlias.query.with_entities(TagAlias.lang_code).distinct().all()}
        # normalize aliases
        alias_rows = TagAlias.query.filter_by(tag_id=t.id).all()
        for a in alias_rows:
            aliases.setdefault(a.lang_code, []).append(a.alias_label)
        # count how many entities use this tag
        usage_count = EntityTag.query.filter_by(tag_id=t.id).count()
        rows.append({
            "id": t.id,
            "slug": t.slug,
            "translations": translations,
            "aliases": aliases,
            "usage_count": usage_count,
        })
    return rows


def delete_tag(tag_id: int) -> bool:
    """
    Delete a tag entirely, including all translations, aliases, and entity associations.
    Returns True if the tag was deleted, False if the tag was not found.
    """
    tag = Tag.query.get(tag_id)
    if not tag:
        return False
    # Delete all associated entity tags (cascade should handle this, but be explicit)
    EntityTag.query.filter_by(tag_id=tag_id).delete(synchronize_session=False)
    # Delete all aliases
    TagAlias.query.filter_by(tag_id=tag_id).delete(synchronize_session=False)
    # Delete all translations
    TagTranslation.query.filter_by(tag_id=tag_id).delete(synchronize_session=False)
    # Delete the tag itself
    db.session.delete(tag)
    return True


def merge_tags(target_tag_id: int, source_tag_ids: List[int]) -> Tuple[bool, str]:
    """
    Merge one or more source tags into a target tag.
    This will:
    - Transfer all entity associations from source tags to target tag
    - Transfer all translations (if target doesn't have that language)
    - Transfer all aliases (if not conflicting)
    - Delete the source tags

    Returns (success, message).
    """
    target = Tag.query.get(target_tag_id)
    if not target:
        return False, "Target tag not found."

    if not source_tag_ids:
        return False, "No source tags provided."

    # Filter out target from source list and invalid IDs
    source_tag_ids = [s for s in source_tag_ids if s != target_tag_id]
    source_tags = [Tag.query.get(sid) for sid in source_tag_ids]
    source_tags = [s for s in source_tags if s is not None]

    if not source_tags:
        return False, "No valid source tags to merge."

    merged_count = 0
    for source in source_tags:
        # Transfer entity associations
        entity_links = EntityTag.query.filter_by(tag_id=source.id).all()
        for link in entity_links:
            # Check if target already has this association
            existing = EntityTag.query.filter_by(
                person_id=link.person_id,
                section=link.section,
                stable_id=link.stable_id,
                tag_id=target.id
            ).first()
            if not existing:
                # Update the link to point to target
                link.tag_id = target.id
            else:
                # Remove duplicate link
                db.session.delete(link)

        # Transfer translations (only if target doesn't have that language)
        for tr in TagTranslation.query.filter_by(tag_id=source.id).all():
            existing_tr = TagTranslation.query.filter_by(
                tag_id=target.id, lang_code=tr.lang_code
            ).first()
            if not existing_tr:
                tr.tag_id = target.id
            else:
                db.session.delete(tr)

        # Transfer aliases (only if no conflict)
        for alias in TagAlias.query.filter_by(tag_id=source.id).all():
            existing_alias = TagAlias.query.filter_by(
                lang_code=alias.lang_code, alias_label=alias.alias_label
            ).first()
            if existing_alias and existing_alias.tag_id != target.id:
                # Conflict with another tag - delete source alias to avoid uniqueness violation
                db.session.delete(alias)
            elif existing_alias and existing_alias.tag_id == target.id:
                # Already exists for target - delete source's duplicate
                db.session.delete(alias)
            else:
                # No conflict - transfer alias to target
                alias.tag_id = target.id

        # Delete the source tag
        db.session.delete(source)
        merged_count += 1

    return True, f"Merged {merged_count} tag(s) into '{target.slug}'."


def delete_all_tags() -> int:
    """
    Delete all tags from the database, including all translations, aliases, and entity associations.
    Returns the number of tags deleted.
    """
    # Get count before deletion
    count = Tag.query.count()
    if count == 0:
        return 0

    # Delete all entity tags first
    EntityTag.query.delete(synchronize_session=False)
    # Delete all aliases
    TagAlias.query.delete(synchronize_session=False)
    # Delete all translations
    TagTranslation.query.delete(synchronize_session=False)
    # Delete all tags
    Tag.query.delete(synchronize_session=False)

    return count


def import_tags_from_csv(csv_content: bytes, filename: str) -> Tuple[int, List[str]]:
    """
    Import tags from a CSV file.
    The CSV should have headers like 'en_tag', 'de_tag', 'fa_tag' for each supported language.
    Each row represents a tag set with translations in multiple languages.

    Returns (number of tags created, list of warnings/messages).
    """
    warnings: List[str] = []
    created_count = 0

    try:
        # Try to decode as UTF-8 first, then fall back to other encodings
        try:
            text = csv_content.decode("utf-8-sig")  # Handle BOM
        except UnicodeDecodeError:
            text = csv_content.decode("latin-1")

        reader = csv.DictReader(io.StringIO(text))
        headers = reader.fieldnames or []

        # Find language columns
        lang_columns: Dict[str, str] = {}
        for lang in SUPPORTED_LANGUAGES:
            possible_headers = [f"{lang}_tag", f"{lang.upper()}_tag", f"tag_{lang}", lang, lang.upper()]
            for h in headers:
                if h.strip().lower() in [p.lower() for p in possible_headers]:
                    lang_columns[lang] = h
                    break

        if not lang_columns:
            warnings.append(f"No valid language columns found. Expected headers like: en_tag, de_tag, fa_tag")
            return 0, warnings

        warnings.append(f"Found language columns: {lang_columns}")

        for row_num, row in enumerate(reader, start=2):  # Start at 2 because row 1 is header
            # Get the first non-empty label to use as base for slug
            first_label = None
            first_lang = None
            labels: Dict[str, str] = {}

            for lang, col in lang_columns.items():
                val = (row.get(col) or "").strip()
                if val:
                    labels[lang] = val
                    if first_label is None:
                        first_label = val
                        first_lang = lang

            if not first_label:
                warnings.append(f"Row {row_num}: skipped (no labels found)")
                continue

            # Check if tag with this label already exists
            existing_tag = None
            for lang, label in labels.items():
                # Check by translation
                existing_tr = TagTranslation.query.filter_by(lang_code=lang, label=label).first()
                if existing_tr:
                    existing_tag = Tag.query.get(existing_tr.tag_id)
                    break
                # Check by alias
                existing_alias = TagAlias.query.filter_by(lang_code=lang, alias_label=label).first()
                if existing_alias:
                    existing_tag = Tag.query.get(existing_alias.tag_id)
                    break
                # Check by slug
                slug_check = slugify(label)
                existing_tag = Tag.query.filter_by(slug=slug_check).first()
                if existing_tag:
                    break

            if existing_tag:
                # Update existing tag with any missing translations
                for lang, label in labels.items():
                    existing_tr = TagTranslation.query.filter_by(tag_id=existing_tag.id, lang_code=lang).first()
                    if not existing_tr:
                        db.session.add(TagTranslation(tag_id=existing_tag.id, lang_code=lang, label=label))
                        # Also add alias
                        existing_alias = TagAlias.query.filter_by(lang_code=lang, alias_label=label).first()
                        if not existing_alias:
                            db.session.add(TagAlias(tag_id=existing_tag.id, lang_code=lang, alias_label=label))
                warnings.append(f"Row {row_num}: updated existing tag '{existing_tag.slug}'")
            else:
                # Create new tag
                slug = slugify(first_label)
                base = slug
                i = 2
                while Tag.query.filter_by(slug=slug).first() is not None:
                    slug = f"{base}-{i}"
                    i += 1

                tag = Tag(slug=slug)
                db.session.add(tag)
                db.session.flush()

                for lang, label in labels.items():
                    db.session.add(TagTranslation(tag_id=tag.id, lang_code=lang, label=label))
                    # Also add alias for lookup
                    db.session.add(TagAlias(tag_id=tag.id, lang_code=lang, alias_label=label))

                created_count += 1
                warnings.append(f"Row {row_num}: created tag '{slug}'")

    except Exception as e:
        warnings.append(f"Error parsing CSV: {e}")
        return 0, warnings

    return created_count, warnings
