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
        rows.append({
            "id": t.id,
            "slug": t.slug,
            "translations": translations,
            "aliases": aliases,
        })
    return rows
