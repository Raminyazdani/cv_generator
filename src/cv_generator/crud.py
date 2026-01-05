"""
Generalized JSON CRUD Engine for CV Generator.

Provides a CRUD layer for managing CV entries across multiple languages (EN/DE/FA):
- Create/update/delete entries in any list-like section (projects, experiences, etc.)
- Multi-language synchronization: when an entry is created/deleted, sync across languages
- Stable entry IDs that link EN/DE/FA variants together
- Section adapters for different data structures (list sections, nested skills)

Multi-Language Sync Rules:
=========================
- Create: Creates entry in ALL languages with same stable_id.
  Text fields use source language value with needs_translation marker.
  Shared fields (url, date, type_key) are synced across languages.
- Delete: Removes entry from ALL languages by stable_id.
- Update: By default, updates only current language for text fields.
  Optionally can sync shared fields (url, date, type_key) to all languages.

Data Folder LOCKED:
==================
This module does NOT modify files in data/. All changes are stored in the SQLite database.
Exports to output/ directory for use.
"""

import json
import logging
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .db import _get_or_create_tag, _utcnow, get_db_path
from .errors import ConfigurationError, ValidationError

logger = logging.getLogger(__name__)

# Languages supported for multi-language sync
SUPPORTED_LANGUAGES = ["en", "de", "fa"]
DEFAULT_LANGUAGE = "en"

# Fields that are shared across languages (not translated)
SHARED_FIELDS = {
    "projects": ["url", "type_key"],
    "experiences": ["type_key"],
    "publications": ["doi", "identifiers", "type_key", "year", "status"],
    "education": ["startDate", "endDate", "gpa", "logo_url", "type_key"],
    "references": ["email", "phone", "type_key"],
    "profiles": ["url", "username", "uuid"],
    "languages": ["type_key"],
    "workshop_and_certifications": ["type_key", "date", "issueDate", "expirationDate"],
}

# Extended schema for stable entry IDs
CRUD_SCHEMA_SQL = """
-- Stable entry ID table for multi-language linking
CREATE TABLE IF NOT EXISTS stable_entry (
    id TEXT PRIMARY KEY,
    section TEXT NOT NULL,
    base_person TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_stable_entry_section ON stable_entry(section);
CREATE INDEX IF NOT EXISTS idx_stable_entry_base_person ON stable_entry(base_person);

-- Link between stable_entry and actual entry records per language
CREATE TABLE IF NOT EXISTS entry_lang_link (
    stable_id TEXT NOT NULL,
    language TEXT NOT NULL,
    entry_id INTEGER NOT NULL,
    needs_translation INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    PRIMARY KEY (stable_id, language),
    FOREIGN KEY (stable_id) REFERENCES stable_entry(id) ON DELETE CASCADE,
    FOREIGN KEY (entry_id) REFERENCES entry(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_entry_lang_link_entry ON entry_lang_link(entry_id);
"""


def ensure_crud_schema(db_path: Optional[Path] = None) -> None:
    """
    Ensure the CRUD schema tables exist in the database.

    Args:
        db_path: Path to the database file. Uses default if None.
    """
    db_path = get_db_path(db_path)

    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.executescript(CRUD_SCHEMA_SQL)
        conn.commit()
        logger.debug("CRUD schema ensured")
    finally:
        conn.close()


def generate_stable_id() -> str:
    """Generate a new stable entry ID."""
    return str(uuid.uuid4())


def _get_base_person(person_slug: str) -> str:
    """
    Extract base person name from slug (removes language suffix).

    Args:
        person_slug: Full person slug (e.g., "ramin", "ramin_de", "ramin_fa")

    Returns:
        Base person name (e.g., "ramin")
    """
    for lang in SUPPORTED_LANGUAGES:
        if lang != DEFAULT_LANGUAGE and person_slug.endswith(f"_{lang}"):
            return person_slug[:-len(f"_{lang}")]
    return person_slug


def _get_person_slug_for_lang(base_person: str, language: str) -> str:
    """
    Get the person slug for a specific language.

    Args:
        base_person: Base person name (e.g., "ramin")
        language: Language code (e.g., "en", "de", "fa")

    Returns:
        Person slug for that language (e.g., "ramin" for en, "ramin_de" for de)
    """
    if language == DEFAULT_LANGUAGE:
        return base_person
    return f"{base_person}_{language}"


def _person_exists_for_lang(cursor: sqlite3.Cursor, base_person: str, language: str) -> bool:
    """Check if a person exists in the database for a given language."""
    slug = _get_person_slug_for_lang(base_person, language)
    cursor.execute("SELECT id FROM person WHERE slug = ?", (slug,))
    return cursor.fetchone() is not None


def _get_entry_by_stable_id_and_lang(
    cursor: sqlite3.Cursor,
    stable_id: str,
    language: str
) -> Optional[Dict[str, Any]]:
    """Get entry data by stable_id and language."""
    cursor.execute(
        """SELECT e.id, e.person_id, e.section, e.order_idx, e.data_json, e.identity_key
           FROM entry e
           JOIN entry_lang_link ell ON e.id = ell.entry_id
           WHERE ell.stable_id = ? AND ell.language = ?""",
        (stable_id, language)
    )
    row = cursor.fetchone()
    if not row:
        return None

    entry_id, person_id, section, order_idx, data_json, identity_key = row
    return {
        "id": entry_id,
        "person_id": person_id,
        "section": section,
        "order_idx": order_idx,
        "data": json.loads(data_json),
        "identity_key": identity_key,
        "stable_id": stable_id,
        "language": language
    }


def _create_entry_in_db(
    cursor: sqlite3.Cursor,
    person_slug: str,
    section: str,
    data: Dict[str, Any],
    identity_key: Optional[str] = None,
    order_idx: Optional[int] = None
) -> int:
    """
    Create an entry in the database and return its ID.

    Args:
        cursor: Database cursor
        person_slug: Person's slug
        section: Section name
        data: Entry data
        identity_key: Optional identity key
        order_idx: Optional order index

    Returns:
        Created entry ID
    """
    # Get or create person
    cursor.execute("SELECT id FROM person WHERE slug = ?", (person_slug,))
    row = cursor.fetchone()
    if not row:
        # Create the person
        now = _utcnow()
        cursor.execute(
            "INSERT INTO person (slug, display_name, created_at) VALUES (?, ?, ?)",
            (person_slug, None, now)
        )
        person_id = cursor.lastrowid
    else:
        person_id = row[0]

    # Determine order_idx if not provided
    if order_idx is None:
        cursor.execute(
            "SELECT COALESCE(MAX(order_idx), -1) + 1 FROM entry WHERE person_id = ? AND section = ?",
            (person_id, section)
        )
        order_idx = cursor.fetchone()[0]

    # Create entry
    data_json = json.dumps(data, ensure_ascii=False, sort_keys=True)
    now = _utcnow()

    cursor.execute(
        """INSERT INTO entry (person_id, section, order_idx, data_json, identity_key, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (person_id, section, order_idx, data_json, identity_key, now)
    )
    entry_id = cursor.lastrowid

    # Extract and link tags from type_key
    type_keys = data.get("type_key", [])
    if isinstance(type_keys, list):
        for tag_name in type_keys:
            if tag_name:
                tag_id = _get_or_create_tag(cursor, str(tag_name))
                cursor.execute(
                    "INSERT OR IGNORE INTO entry_tag (entry_id, tag_id) VALUES (?, ?)",
                    (entry_id, tag_id)
                )

    return entry_id


def _create_placeholder_entry(
    source_data: Dict[str, Any],
    section: str,
    source_lang: str,
    target_lang: str
) -> Dict[str, Any]:
    """
    Create a placeholder entry for a target language based on source data.

    For text fields, copies source language value as placeholder.
    Shared fields are copied as-is.

    Args:
        source_data: Source entry data
        section: Section name
        source_lang: Source language code
        target_lang: Target language code

    Returns:
        Placeholder entry data for target language
    """
    placeholder = {}
    shared = SHARED_FIELDS.get(section, [])

    for key, value in source_data.items():
        if key in shared:
            # Copy shared fields directly
            placeholder[key] = value
        else:
            # For text fields, copy value but mark as needing translation
            # We copy the value as a placeholder
            placeholder[key] = value

    return placeholder


# =============================================================================
# SECTION ADAPTERS
# =============================================================================

class SectionAdapter:
    """
    Base adapter for CV sections.

    Each section type (list, skills tree, etc.) needs specific handling
    for CRUD operations.
    """

    def __init__(self, section: str):
        self.section = section

    def list_entries(
        self,
        person_slug: str,
        db_path: Optional[Path] = None
    ) -> List[Dict[str, Any]]:
        """List all entries in the section for a person."""
        raise NotImplementedError

    def get_entry(
        self,
        entry_id: int,
        db_path: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a single entry by ID."""
        raise NotImplementedError

    def create_entry(
        self,
        person_slug: str,
        data: Dict[str, Any],
        db_path: Optional[Path] = None,
        sync_languages: bool = True
    ) -> Dict[str, Any]:
        """Create a new entry, optionally syncing to other languages."""
        raise NotImplementedError

    def update_entry(
        self,
        entry_id: int,
        data: Dict[str, Any],
        db_path: Optional[Path] = None,
        sync_shared_fields: bool = False
    ) -> Dict[str, Any]:
        """Update an entry, optionally syncing shared fields."""
        raise NotImplementedError

    def delete_entry(
        self,
        entry_id: int,
        db_path: Optional[Path] = None,
        sync_languages: bool = True
    ) -> bool:
        """Delete an entry, optionally deleting counterparts in other languages."""
        raise NotImplementedError


class ListSectionAdapter(SectionAdapter):
    """
    Adapter for list-based sections (projects, experiences, publications, etc.).
    """

    def list_entries(
        self,
        person_slug: str,
        db_path: Optional[Path] = None
    ) -> List[Dict[str, Any]]:
        """List all entries in the section for a person."""
        db_path = get_db_path(db_path)

        if not db_path.exists():
            raise ConfigurationError(f"Database not found: {db_path}")

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()

            # Get person ID
            cursor.execute("SELECT id FROM person WHERE slug = ?", (person_slug,))
            row = cursor.fetchone()
            if not row:
                return []
            person_id = row[0]

            # Get entries
            cursor.execute(
                """SELECT e.id, e.order_idx, e.data_json, e.identity_key,
                          ell.stable_id, ell.needs_translation
                   FROM entry e
                   LEFT JOIN entry_lang_link ell ON e.id = ell.entry_id
                   WHERE e.person_id = ? AND e.section = ?
                   ORDER BY e.order_idx""",
                (person_id, self.section)
            )

            entries = []
            for row in cursor.fetchall():
                entry_id, order_idx, data_json, identity_key, stable_id, needs_translation = row

                # Skip empty list markers
                if order_idx == -1 and data_json == "[]":
                    continue

                data = json.loads(data_json)

                # Get tags
                cursor.execute(
                    """SELECT t.name FROM tag t
                       JOIN entry_tag et ON t.id = et.tag_id
                       WHERE et.entry_id = ?
                       ORDER BY t.name""",
                    (entry_id,)
                )
                tags = [r[0] for r in cursor.fetchall()]

                entries.append({
                    "id": entry_id,
                    "order_idx": order_idx,
                    "data": data,
                    "identity_key": identity_key,
                    "stable_id": stable_id,
                    "needs_translation": bool(needs_translation),
                    "tags": tags
                })

            return entries
        finally:
            conn.close()

    def get_entry(
        self,
        entry_id: int,
        db_path: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a single entry by ID."""
        db_path = get_db_path(db_path)

        if not db_path.exists():
            raise ConfigurationError(f"Database not found: {db_path}")

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()

            cursor.execute(
                """SELECT e.id, e.person_id, e.section, e.order_idx, e.data_json,
                          e.identity_key, p.slug,
                          ell.stable_id, ell.needs_translation, ell.language
                   FROM entry e
                   JOIN person p ON e.person_id = p.id
                   LEFT JOIN entry_lang_link ell ON e.id = ell.entry_id
                   WHERE e.id = ?""",
                (entry_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            (entry_id, person_id, section, order_idx, data_json,
             identity_key, person_slug, stable_id, needs_translation, language) = row

            data = json.loads(data_json)

            # Get tags
            cursor.execute(
                """SELECT t.name FROM tag t
                   JOIN entry_tag et ON t.id = et.tag_id
                   WHERE et.entry_id = ?
                   ORDER BY t.name""",
                (entry_id,)
            )
            tags = [r[0] for r in cursor.fetchall()]

            return {
                "id": entry_id,
                "person_id": person_id,
                "person_slug": person_slug,
                "section": section,
                "order_idx": order_idx,
                "data": data,
                "identity_key": identity_key,
                "stable_id": stable_id,
                "needs_translation": bool(needs_translation) if needs_translation is not None else False,
                "language": language,
                "tags": tags
            }
        finally:
            conn.close()

    def create_entry(
        self,
        person_slug: str,
        data: Dict[str, Any],
        db_path: Optional[Path] = None,
        sync_languages: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new entry, optionally syncing to other languages.

        Args:
            person_slug: Person's slug (e.g., "ramin" for EN, "ramin_de" for DE)
            data: Entry data
            db_path: Path to database
            sync_languages: If True, create placeholders in other languages

        Returns:
            Created entry info with stable_id
        """
        db_path = get_db_path(db_path)
        ensure_crud_schema(db_path)

        if not db_path.exists():
            raise ConfigurationError(f"Database not found: {db_path}")

        # Determine base person and source language
        base_person = _get_base_person(person_slug)
        source_lang = DEFAULT_LANGUAGE
        for lang in SUPPORTED_LANGUAGES:
            if person_slug == _get_person_slug_for_lang(base_person, lang):
                source_lang = lang
                break

        # Generate stable ID
        stable_id = generate_stable_id()

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()

            # Create stable entry record
            now = _utcnow()
            cursor.execute(
                """INSERT INTO stable_entry (id, section, base_person, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (stable_id, self.section, base_person, now, now)
            )

            # Create entry in source language
            entry_id = _create_entry_in_db(
                cursor, person_slug, self.section, data
            )

            # Link entry to stable_id
            cursor.execute(
                """INSERT INTO entry_lang_link (stable_id, language, entry_id, needs_translation, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (stable_id, source_lang, entry_id, 0, now)
            )

            created_entries = {source_lang: entry_id}

            # Sync to other languages if requested
            if sync_languages:
                for lang in SUPPORTED_LANGUAGES:
                    if lang == source_lang:
                        continue

                    # Check if person exists for this language
                    lang_slug = _get_person_slug_for_lang(base_person, lang)
                    if not _person_exists_for_lang(cursor, base_person, lang):
                        logger.debug(f"Skipping sync for {lang}: person {lang_slug} not found")
                        continue

                    # Create placeholder entry
                    placeholder = _create_placeholder_entry(
                        data, self.section, source_lang, lang
                    )

                    lang_entry_id = _create_entry_in_db(
                        cursor, lang_slug, self.section, placeholder
                    )

                    # Link to stable_id with needs_translation flag
                    cursor.execute(
                        """INSERT INTO entry_lang_link (stable_id, language, entry_id, needs_translation, created_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (stable_id, lang, lang_entry_id, 1, now)
                    )

                    created_entries[lang] = lang_entry_id

            conn.commit()

            return {
                "stable_id": stable_id,
                "section": self.section,
                "source_language": source_lang,
                "entries": created_entries,
                "data": data
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_entry(
        self,
        entry_id: int,
        data: Dict[str, Any],
        db_path: Optional[Path] = None,
        sync_shared_fields: bool = False
    ) -> Dict[str, Any]:
        """
        Update an entry, optionally syncing shared fields to other languages.

        Args:
            entry_id: Entry ID to update
            data: New entry data
            db_path: Path to database
            sync_shared_fields: If True, sync shared fields to other language variants

        Returns:
            Updated entry info
        """
        db_path = get_db_path(db_path)
        ensure_crud_schema(db_path)

        if not db_path.exists():
            raise ConfigurationError(f"Database not found: {db_path}")

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()

            # Get current entry info
            cursor.execute(
                """SELECT e.section, e.person_id, p.slug,
                          ell.stable_id, ell.language
                   FROM entry e
                   JOIN person p ON e.person_id = p.id
                   LEFT JOIN entry_lang_link ell ON e.id = ell.entry_id
                   WHERE e.id = ?""",
                (entry_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ConfigurationError(f"Entry not found: {entry_id}")

            section, person_id, person_slug, stable_id, current_lang = row

            # Update the entry
            data_json = json.dumps(data, ensure_ascii=False, sort_keys=True)
            cursor.execute(
                "UPDATE entry SET data_json = ? WHERE id = ?",
                (data_json, entry_id)
            )

            # Update tags
            cursor.execute("DELETE FROM entry_tag WHERE entry_id = ?", (entry_id,))
            type_keys = data.get("type_key", [])
            if isinstance(type_keys, list):
                for tag_name in type_keys:
                    if tag_name:
                        tag_id = _get_or_create_tag(cursor, str(tag_name))
                        cursor.execute(
                            "INSERT OR IGNORE INTO entry_tag (entry_id, tag_id) VALUES (?, ?)",
                            (entry_id, tag_id)
                        )

            # Mark as no longer needing translation
            cursor.execute(
                "UPDATE entry_lang_link SET needs_translation = 0 WHERE entry_id = ?",
                (entry_id,)
            )

            # Update stable_entry timestamp
            if stable_id:
                now = _utcnow()
                cursor.execute(
                    "UPDATE stable_entry SET updated_at = ? WHERE id = ?",
                    (now, stable_id)
                )

            # Sync shared fields to other languages if requested
            synced_entries = {current_lang: entry_id}
            if sync_shared_fields and stable_id:
                shared = SHARED_FIELDS.get(section, [])
                shared_data = {k: v for k, v in data.items() if k in shared}

                if shared_data:
                    # Get other language entries with same stable_id
                    cursor.execute(
                        """SELECT ell.entry_id, ell.language
                           FROM entry_lang_link ell
                           WHERE ell.stable_id = ? AND ell.language != ?""",
                        (stable_id, current_lang)
                    )

                    for other_entry_id, other_lang in cursor.fetchall():
                        # Get current data for other entry
                        cursor.execute(
                            "SELECT data_json FROM entry WHERE id = ?",
                            (other_entry_id,)
                        )
                        other_row = cursor.fetchone()
                        if other_row:
                            other_data = json.loads(other_row[0])
                            # Update only shared fields
                            for key, value in shared_data.items():
                                other_data[key] = value

                            other_data_json = json.dumps(other_data, ensure_ascii=False, sort_keys=True)
                            cursor.execute(
                                "UPDATE entry SET data_json = ? WHERE id = ?",
                                (other_data_json, other_entry_id)
                            )

                            # Update tags for shared type_key
                            if "type_key" in shared_data:
                                cursor.execute("DELETE FROM entry_tag WHERE entry_id = ?", (other_entry_id,))
                                type_keys = shared_data.get("type_key", [])
                                if isinstance(type_keys, list):
                                    for tag_name in type_keys:
                                        if tag_name:
                                            tag_id = _get_or_create_tag(cursor, str(tag_name))
                                            cursor.execute(
                                                "INSERT OR IGNORE INTO entry_tag (entry_id, tag_id) VALUES (?, ?)",
                                                (other_entry_id, tag_id)
                                            )

                            synced_entries[other_lang] = other_entry_id

            conn.commit()

            return {
                "id": entry_id,
                "section": section,
                "data": data,
                "stable_id": stable_id,
                "synced_entries": synced_entries
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def delete_entry(
        self,
        entry_id: int,
        db_path: Optional[Path] = None,
        sync_languages: bool = True
    ) -> bool:
        """
        Delete an entry, optionally deleting counterparts in other languages.

        Args:
            entry_id: Entry ID to delete
            db_path: Path to database
            sync_languages: If True, delete all language variants with same stable_id

        Returns:
            True if deleted, False if not found
        """
        db_path = get_db_path(db_path)
        ensure_crud_schema(db_path)

        if not db_path.exists():
            raise ConfigurationError(f"Database not found: {db_path}")

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()

            # Get entry info
            cursor.execute(
                """SELECT ell.stable_id, ell.language
                   FROM entry_lang_link ell
                   WHERE ell.entry_id = ?""",
                (entry_id,)
            )
            row = cursor.fetchone()

            entries_to_delete = [entry_id]
            stable_id = None

            if row and sync_languages:
                stable_id, _ = row

                # Get all entries with same stable_id
                cursor.execute(
                    "SELECT entry_id FROM entry_lang_link WHERE stable_id = ?",
                    (stable_id,)
                )
                entries_to_delete = [r[0] for r in cursor.fetchall()]

            # Delete entries
            deleted_count = 0
            for eid in entries_to_delete:
                # Delete entry_tag relationships
                cursor.execute("DELETE FROM entry_tag WHERE entry_id = ?", (eid,))
                # Delete entry_lang_link
                cursor.execute("DELETE FROM entry_lang_link WHERE entry_id = ?", (eid,))
                # Delete entry
                cursor.execute("DELETE FROM entry WHERE id = ?", (eid,))
                deleted_count += cursor.rowcount

            # Delete stable_entry if all variants are deleted
            if stable_id:
                cursor.execute(
                    "SELECT COUNT(*) FROM entry_lang_link WHERE stable_id = ?",
                    (stable_id,)
                )
                remaining = cursor.fetchone()[0]
                if remaining == 0:
                    cursor.execute("DELETE FROM stable_entry WHERE id = ?", (stable_id,))

            conn.commit()

            logger.info(f"Deleted {deleted_count} entries (stable_id: {stable_id})")
            return deleted_count > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_linked_entries(
        self,
        entry_id: int,
        db_path: Optional[Path] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get all language variants of an entry.

        Args:
            entry_id: Entry ID
            db_path: Path to database

        Returns:
            Dict mapping language codes to entry info
        """
        db_path = get_db_path(db_path)

        if not db_path.exists():
            raise ConfigurationError(f"Database not found: {db_path}")

        # Ensure CRUD schema exists
        ensure_crud_schema(db_path)

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()

            # Get stable_id
            cursor.execute(
                "SELECT stable_id FROM entry_lang_link WHERE entry_id = ?",
                (entry_id,)
            )
            row = cursor.fetchone()
            if not row:
                # Entry not linked, return just this entry
                entry = self.get_entry(entry_id, db_path)
                if entry:
                    lang = entry.get("language") or DEFAULT_LANGUAGE
                    return {lang: entry}
                return {}

            stable_id = row[0]

            # Get all linked entries
            cursor.execute(
                """SELECT ell.entry_id, ell.language, ell.needs_translation
                   FROM entry_lang_link ell
                   WHERE ell.stable_id = ?""",
                (stable_id,)
            )

            result = {}
            for eid, lang, needs_trans in cursor.fetchall():
                entry = self.get_entry(eid, db_path)
                if entry:
                    entry["needs_translation"] = bool(needs_trans)
                    result[lang] = entry

            return result
        finally:
            conn.close()


# =============================================================================
# ADAPTER REGISTRY
# =============================================================================

# List of sections that use list adapters
LIST_SECTIONS = [
    "projects", "experiences", "publications", "references",
    "education", "languages", "profiles", "workshop_and_certifications"
]

# Adapter instances cache
_adapters: Dict[str, SectionAdapter] = {}


def get_section_adapter(section: str) -> SectionAdapter:
    """
    Get the appropriate adapter for a section.

    Args:
        section: Section name

    Returns:
        SectionAdapter instance for the section

    Raises:
        ValidationError: If section is not supported
    """
    if section not in _adapters:
        if section in LIST_SECTIONS:
            _adapters[section] = ListSectionAdapter(section)
        else:
            raise ValidationError(
                f"Section '{section}' is not supported for CRUD operations. "
                f"Supported: {', '.join(LIST_SECTIONS)}"
            )

    return _adapters[section]


# =============================================================================
# HIGH-LEVEL API
# =============================================================================

def create_entry(
    person_slug: str,
    section: str,
    data: Dict[str, Any],
    db_path: Optional[Path] = None,
    sync_languages: bool = True
) -> Dict[str, Any]:
    """
    Create a new entry with multi-language sync.

    Args:
        person_slug: Person's slug
        section: Section name
        data: Entry data
        db_path: Path to database
        sync_languages: If True, create placeholders in other languages

    Returns:
        Created entry info with stable_id
    """
    adapter = get_section_adapter(section)
    return adapter.create_entry(person_slug, data, db_path, sync_languages)


def update_entry(
    entry_id: int,
    data: Dict[str, Any],
    section: str,
    db_path: Optional[Path] = None,
    sync_shared_fields: bool = False
) -> Dict[str, Any]:
    """
    Update an entry with optional shared field sync.

    Args:
        entry_id: Entry ID to update
        data: New entry data
        section: Section name
        db_path: Path to database
        sync_shared_fields: If True, sync shared fields to other languages

    Returns:
        Updated entry info
    """
    adapter = get_section_adapter(section)
    return adapter.update_entry(entry_id, data, db_path, sync_shared_fields)


def delete_entry(
    entry_id: int,
    section: str,
    db_path: Optional[Path] = None,
    sync_languages: bool = True
) -> bool:
    """
    Delete an entry with multi-language sync.

    Args:
        entry_id: Entry ID to delete
        section: Section name
        db_path: Path to database
        sync_languages: If True, delete all language variants

    Returns:
        True if deleted
    """
    adapter = get_section_adapter(section)
    return adapter.delete_entry(entry_id, db_path, sync_languages)


def get_entry(
    entry_id: int,
    section: str,
    db_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """
    Get a single entry.

    Args:
        entry_id: Entry ID
        section: Section name
        db_path: Path to database

    Returns:
        Entry info or None
    """
    adapter = get_section_adapter(section)
    return adapter.get_entry(entry_id, db_path)


def list_entries(
    person_slug: str,
    section: str,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    List all entries in a section.

    Args:
        person_slug: Person's slug
        section: Section name
        db_path: Path to database

    Returns:
        List of entries
    """
    adapter = get_section_adapter(section)
    return adapter.list_entries(person_slug, db_path)


def get_linked_entries(
    entry_id: int,
    section: str,
    db_path: Optional[Path] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Get all language variants of an entry.

    Args:
        entry_id: Entry ID
        section: Section name
        db_path: Path to database

    Returns:
        Dict mapping language codes to entry info
    """
    adapter = get_section_adapter(section)
    return adapter.get_linked_entries(entry_id, db_path)


def link_existing_entries(
    entry_ids: Dict[str, int],
    section: str,
    db_path: Optional[Path] = None
) -> str:
    """
    Link existing entries from different languages together with a stable ID.

    This is useful for linking entries that were imported separately.

    Args:
        entry_ids: Dict mapping language codes to entry IDs
        section: Section name
        db_path: Path to database

    Returns:
        Generated stable_id
    """
    db_path = get_db_path(db_path)
    ensure_crud_schema(db_path)

    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")

    if len(entry_ids) < 1:
        raise ValidationError("At least one entry ID is required")

    # Get base person from first entry
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        first_entry_id = list(entry_ids.values())[0]
        cursor.execute(
            """SELECT p.slug FROM entry e
               JOIN person p ON e.person_id = p.id
               WHERE e.id = ?""",
            (first_entry_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ConfigurationError(f"Entry not found: {first_entry_id}")

        base_person = _get_base_person(row[0])

        # Generate stable ID
        stable_id = generate_stable_id()
        now = _utcnow()

        # Create stable entry record
        cursor.execute(
            """INSERT INTO stable_entry (id, section, base_person, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (stable_id, section, base_person, now, now)
        )

        # Link each entry
        for lang, entry_id in entry_ids.items():
            cursor.execute(
                """INSERT INTO entry_lang_link (stable_id, language, entry_id, needs_translation, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (stable_id, lang, entry_id, 0, now)
            )

        conn.commit()

        logger.info(f"Linked {len(entry_ids)} entries with stable_id: {stable_id}")
        return stable_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
