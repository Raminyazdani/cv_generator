from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .models import db, Tag, TagAlias, TagTranslation, EntityTag
from .fields import slugify, SUPPORTED_LANGUAGES


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

    # 3) create
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
                # Conflict with another tag - skip but keep the alias pointing to target
                db.session.delete(alias)
            elif existing_alias and existing_alias.tag_id == target.id:
                # Already exists for target - delete source's
                db.session.delete(alias)
            else:
                # No conflict - transfer
                alias.tag_id = target.id

        # Delete the source tag
        db.session.delete(source)
        merged_count += 1

    return True, f"Merged {merged_count} tag(s) into '{target.slug}'."
