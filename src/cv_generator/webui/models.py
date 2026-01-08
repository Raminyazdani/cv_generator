from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class PersonEntity(db.Model):
    __tablename__ = "person_entities"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    variants = db.relationship("CVVariant", back_populates="person", cascade="all, delete-orphan")
    entries = db.relationship("Entry", back_populates="person", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<PersonEntity {self.slug}>"


class CVVariant(db.Model):
    """
    A language variant for a person (resume_key == person.slug for now).
    Stores imported CV config and some metadata.
    """
    __tablename__ = "cv_variants"

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("person_entities.id", ondelete="CASCADE"), nullable=False, index=True)

    resume_key = db.Column(db.String(120), nullable=False, index=True)
    lang_code = db.Column(db.String(8), nullable=False, index=True)

    source_filename = db.Column(db.String(400), nullable=True)
    imported_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    entry_count = db.Column(db.Integer, nullable=False, default=0)

    # Optional: store the "config" object from CV JSON
    config = db.Column(db.JSON, nullable=True)

    person = db.relationship("PersonEntity", back_populates="variants")

    __table_args__ = (
        db.UniqueConstraint("person_id", "lang_code", name="uq_variant_person_lang"),
    )


class Entry(db.Model):
    """
    Generic per-language entry record. Grouping across languages is done with stable_id.
    Tags are attached to stable_id (via EntityTag), so tags are shared across languages.
    """
    __tablename__ = "entries"

    id = db.Column(db.Integer, primary_key=True)

    person_id = db.Column(db.Integer, db.ForeignKey("person_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_key = db.Column(db.String(120), nullable=False, index=True)
    lang_code = db.Column(db.String(8), nullable=False, index=True)

    section = db.Column(db.String(64), nullable=False, index=True)
    stable_id = db.Column(db.String(64), nullable=False, index=True)  # UUID string
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    summary = db.Column(db.String(600), nullable=False, default="")
    needs_translation = db.Column(db.Boolean, nullable=False, default=False)

    data = db.Column(db.JSON, nullable=False, default=dict)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    person = db.relationship("PersonEntity", back_populates="entries")

    __table_args__ = (
        db.UniqueConstraint("person_id", "lang_code", "section", "stable_id", name="uq_entry_person_lang_section_stable"),
    )


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    translations = db.relationship("TagTranslation", back_populates="tag", cascade="all, delete-orphan")
    aliases = db.relationship("TagAlias", back_populates="tag", cascade="all, delete-orphan")


class TagTranslation(db.Model):
    __tablename__ = "tag_translations"

    id = db.Column(db.Integer, primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True)
    lang_code = db.Column(db.String(8), nullable=False, index=True)
    label = db.Column(db.String(220), nullable=False)

    tag = db.relationship("Tag", back_populates="translations")

    __table_args__ = (
        db.UniqueConstraint("tag_id", "lang_code", name="uq_tag_translation"),
    )


class TagAlias(db.Model):
    __tablename__ = "tag_aliases"

    id = db.Column(db.Integer, primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True)
    lang_code = db.Column(db.String(8), nullable=False, index=True)
    alias_label = db.Column(db.String(220), nullable=False)

    tag = db.relationship("Tag", back_populates="aliases")

    __table_args__ = (
        db.UniqueConstraint("lang_code", "alias_label", name="uq_tag_alias_lang_label"),
    )


class EntityTag(db.Model):
    """
    Attach tags to an entity group (person + section + stable_id).
    This makes tags shared across languages.
    """
    __tablename__ = "entity_tags"

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("person_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    section = db.Column(db.String(64), nullable=False, index=True)
    stable_id = db.Column(db.String(64), nullable=False, index=True)

    tag_id = db.Column(db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("person_id", "section", "stable_id", "tag_id", name="uq_entity_tag"),
    )


class ImportHistory(db.Model):
    __tablename__ = "import_history"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    files_count = db.Column(db.Integer, nullable=False, default=0)
    overwrite = db.Column(db.Boolean, nullable=False, default=False)
    success_count = db.Column(db.Integer, nullable=False, default=0)
    error_count = db.Column(db.Integer, nullable=False, default=0)
    log = db.Column(db.Text, nullable=True)


class ExportHistory(db.Model):
    __tablename__ = "export_history"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    batch = db.Column(db.Boolean, nullable=False, default=False)

    resume_key = db.Column(db.String(120), nullable=True)
    persons_count = db.Column(db.Integer, nullable=False, default=0)
    language = db.Column(db.String(8), nullable=True)

    output_dir = db.Column(db.String(500), nullable=True)
    output_path = db.Column(db.String(800), nullable=True)

    success = db.Column(db.Boolean, nullable=False, default=True)
    success_count = db.Column(db.Integer, nullable=False, default=0)
    failed_count = db.Column(db.Integer, nullable=False, default=0)
