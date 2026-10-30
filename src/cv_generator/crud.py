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
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from .db import _get_or_create_tag, _utcnow, get_db_path
from .errors import ConfigurationError, ValidationError
logger = logging.getLogger(__name__)

class SyncResult:
    """
    Result of a sync operation with detailed status for observability.

    Provides structured feedback for UI display including:
    - Success/failure status
    - Languages synced/skipped
    - Conflicts detected
    - Timing information
    """

    def __init__(self, operation: str, stable_id: Optional[str]=None):
        self.operation = operation
        self.stable_id = stable_id
        self.success = True
        self.error_message: Optional[str] = None
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.synced_languages: List[str] = []
        self.skipped_languages: Dict[str, str] = {}
        self.failed_languages: Dict[str, str] = {}
        self.conflicts: List[Dict[str, Any]] = []
        self.entry_ids: Dict[str, int] = {}

    def mark_complete(self) -> None:
        """Mark the operation as complete and record end time."""
        self.end_time = time.time()

    def mark_failed(self, error: str) -> None:
        """Mark the operation as failed with an error message."""
        self.success = False
        self.error_message = error
        self.end_time = time.time()

    def add_synced(self, lang: str, entry_id: int) -> None:
        """Record a successfully synced language."""
        self.synced_languages.append(lang)
        self.entry_ids[lang] = entry_id

    def add_skipped(self, lang: str, reason: str) -> None:
        """Record a skipped language with reason."""
        self.skipped_languages[lang] = reason

    def add_failed(self, lang: str, error: str) -> None:
        """Record a failed sync for a language."""
        self.failed_languages[lang] = error

    def add_conflict(self, lang: str, existing_id: int, details: str) -> None:
        """Record a conflict detected during sync."""
        self.conflicts.append({'language': lang, 'existing_entry_id': existing_id, 'details': details})

    @property
    def duration_ms(self) -> float:
        """Get operation duration in milliseconds."""
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {'operation': self.operation, 'stable_id': self.stable_id, 'success': self.success, 'error_message': self.error_message, 'duration_ms': round(self.duration_ms, 2), 'synced_languages': self.synced_languages, 'skipped_languages': self.skipped_languages, 'failed_languages': self.failed_languages, 'conflicts': self.conflicts, 'entry_ids': self.entry_ids}

    def get_summary(self) -> str:
        """Get human-readable summary for flash messages."""
        if not self.success:
            return f'Failed: {self.error_message}'
        parts = []
        if self.synced_languages:
            parts.append(f"Synced to {len(self.synced_languages)} language(s): {', '.join(self.synced_languages).upper()}")
        if self.skipped_languages:
            parts.append(f"Skipped: {', '.join((f'{k} ({v})' for k, v in self.skipped_languages.items()))}")
        if self.conflicts:
            parts.append(f'⚠️ {len(self.conflicts)} conflict(s) detected')
        if not parts:
            parts.append('No sync performed')
        return ' | '.join(parts)
SUPPORTED_LANGUAGES = ['en', 'de', 'fa']
DEFAULT_LANGUAGE = 'en'
SHARED_FIELDS = {'basics': ['email', 'phone', 'urls', 'nationality', 'linkedin', 'github', 'website', 'type_key'], 'projects': ['url', 'type_key'], 'experiences': ['type_key'], 'publications': ['doi', 'identifiers', 'type_key', 'year', 'status'], 'education': ['startDate', 'endDate', 'gpa', 'logo_url', 'type_key'], 'references': ['email', 'phone', 'type_key'], 'profiles': ['url', 'username', 'uuid'], 'languages': ['type_key'], 'workshop_and_certifications': ['type_key', 'date', 'issueDate', 'expirationDate']}
CRUD_SCHEMA_SQL = '\n-- Stable entry ID table for multi-language linking\nCREATE TABLE IF NOT EXISTS stable_entry (\n    id TEXT PRIMARY KEY,\n    section TEXT NOT NULL,\n    base_person TEXT NOT NULL,\n    created_at TEXT NOT NULL,\n    updated_at TEXT NOT NULL\n);\n\nCREATE INDEX IF NOT EXISTS idx_stable_entry_section ON stable_entry(section);\nCREATE INDEX IF NOT EXISTS idx_stable_entry_base_person ON stable_entry(base_person);\n\n-- Link between stable_entry and actual entry records per language\nCREATE TABLE IF NOT EXISTS entry_lang_link (\n    stable_id TEXT NOT NULL,\n    language TEXT NOT NULL,\n    entry_id INTEGER NOT NULL,\n    needs_translation INTEGER DEFAULT 0,\n    created_at TEXT NOT NULL,\n    PRIMARY KEY (stable_id, language),\n    FOREIGN KEY (stable_id) REFERENCES stable_entry(id) ON DELETE CASCADE,\n    FOREIGN KEY (entry_id) REFERENCES entry(id) ON DELETE CASCADE\n);\n\nCREATE INDEX IF NOT EXISTS idx_entry_lang_link_entry ON entry_lang_link(entry_id);\n'

def ensure_crud_schema(db_path: Optional[Path]=None) -> None:
    """
    Ensure the CRUD schema tables exist in the database.

    Args:
        db_path: Path to the database file. Uses default if None.
    """
    db_path = get_db_path(db_path)
    if not db_path.exists():
        raise ConfigurationError(f'Database not found: {db_path}')
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.executescript(CRUD_SCHEMA_SQL)
        conn.commit()
        logger.debug('CRUD schema ensured')
    finally:
        conn.close()

def generate_stable_id() -> str:
    """Generate a new stable entry ID."""
    return str(uuid.uuid4())

def _get_base_person(person_slug: str) -> str:
    """
    Extract base person name from slug (removes language suffix).

    Args:
        person_slug: Full person slug (e.g., "example", "example_de", "example_fa")

    Returns:
        Base person name (e.g., "example")
    """
    for lang in SUPPORTED_LANGUAGES:
        if lang != DEFAULT_LANGUAGE and person_slug.endswith(f'_{lang}'):
            return person_slug[:-len(f'_{lang}')]
    return person_slug

def _get_person_slug_for_lang(base_person: str, language: str) -> str:
    """
    Get the person slug for a specific language.

    Args:
        base_person: Base person name (e.g., "example")
        language: Language code (e.g., "en", "de", "fa")

    Returns:
        Person slug for that language (e.g., "example" for en, "example_de" for de)
    """
    if language == DEFAULT_LANGUAGE:
        return base_person
    return f'{base_person}_{language}'

def _person_exists_for_lang(cursor: sqlite3.Cursor, base_person: str, language: str) -> bool:
    """Check if a person exists in the database for a given language."""
    slug = _get_person_slug_for_lang(base_person, language)
    cursor.execute('SELECT id FROM person WHERE slug = ?', (slug,))
    return cursor.fetchone() is not None

def _get_entry_by_stable_id_and_lang(cursor: sqlite3.Cursor, stable_id: str, language: str) -> Optional[Dict[str, Any]]:
    """Get entry data by stable_id and language."""
    cursor.execute('SELECT e.id, e.person_id, e.section, e.order_idx, e.data_json, e.identity_key\n           FROM entry e\n           JOIN entry_lang_link ell ON e.id = ell.entry_id\n           WHERE ell.stable_id = ? AND ell.language = ?', (stable_id, language))
    row = cursor.fetchone()
    if not row:
        return None
    entry_id, person_id, section, order_idx, data_json, identity_key = row
    return {'id': entry_id, 'person_id': person_id, 'section': section, 'order_idx': order_idx, 'data': json.loads(data_json), 'identity_key': identity_key, 'stable_id': stable_id, 'language': language}

def _create_entry_in_db(cursor: sqlite3.Cursor, person_slug: str, section: str, data: Dict[str, Any], identity_key: Optional[str]=None, order_idx: Optional[int]=None) -> int:
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
    cursor.execute('SELECT id FROM person WHERE slug = ?', (person_slug,))
    row = cursor.fetchone()
    if not row:
        now = _utcnow()
        cursor.execute('INSERT INTO person (slug, display_name, created_at) VALUES (?, ?, ?)', (person_slug, None, now))
        person_id = cursor.lastrowid
    else:
        person_id = row[0]
    if order_idx is None:
        cursor.execute('SELECT COALESCE(MAX(order_idx), -1) + 1 FROM entry WHERE person_id = ? AND section = ?', (person_id, section))
        order_idx = cursor.fetchone()[0]
    data_json = json.dumps(data, ensure_ascii=False, sort_keys=True)
    now = _utcnow()
    cursor.execute('INSERT INTO entry (person_id, section, order_idx, data_json, identity_key, created_at)\n           VALUES (?, ?, ?, ?, ?, ?)', (person_id, section, order_idx, data_json, identity_key, now))
    entry_id = cursor.lastrowid
    type_keys = data.get('type_key', [])
    if isinstance(type_keys, list):
        for tag_name in type_keys:
            if tag_name:
                tag_id = _get_or_create_tag(cursor, str(tag_name))
                cursor.execute('INSERT OR IGNORE INTO entry_tag (entry_id, tag_id) VALUES (?, ?)', (entry_id, tag_id))
    return entry_id

def _create_placeholder_entry(source_data: Dict[str, Any], section: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
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
            placeholder[key] = value
        else:
            placeholder[key] = value
    return placeholder

class SectionAdapter:
    """
    Base adapter for CV sections.

    Each section type (list, skills tree, etc.) needs specific handling
    for CRUD operations.
    """

    def __init__(self, section: str):
        self.section = section

    def list_entries(self, person_slug: str, db_path: Optional[Path]=None) -> List[Dict[str, Any]]:
        """List all entries in the section for a person."""
        raise NotImplementedError

    def get_entry(self, entry_id: int, db_path: Optional[Path]=None) -> Optional[Dict[str, Any]]:
        """Get a single entry by ID."""
        raise NotImplementedError

    def create_entry(self, person_slug: str, data: Dict[str, Any], db_path: Optional[Path]=None, sync_languages: bool=True) -> Dict[str, Any]:
        """Create a new entry, optionally syncing to other languages."""
        raise NotImplementedError

    def update_entry(self, entry_id: int, data: Dict[str, Any], db_path: Optional[Path]=None, sync_shared_fields: bool=False) -> Dict[str, Any]:
        """Update an entry, optionally syncing shared fields."""
        raise NotImplementedError

    def delete_entry(self, entry_id: int, db_path: Optional[Path]=None, sync_languages: bool=True) -> bool:
        """Delete an entry, optionally deleting counterparts in other languages."""
        raise NotImplementedError

class ListSectionAdapter(SectionAdapter):
    """
    Adapter for list-based sections (projects, experiences, publications, etc.).
    """

    def list_entries(self, person_slug: str, db_path: Optional[Path]=None) -> List[Dict[str, Any]]:
        """List all entries in the section for a person."""
        db_path = get_db_path(db_path)
        if not db_path.exists():
            raise ConfigurationError(f'Database not found: {db_path}')
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM person WHERE slug = ?', (person_slug,))
            row = cursor.fetchone()
            if not row:
                return []
            person_id = row[0]
            cursor.execute('SELECT e.id, e.order_idx, e.data_json, e.identity_key,\n                          ell.stable_id, ell.needs_translation\n                   FROM entry e\n                   LEFT JOIN entry_lang_link ell ON e.id = ell.entry_id\n                   WHERE e.person_id = ? AND e.section = ?\n                   ORDER BY e.order_idx', (person_id, self.section))
            entries = []
            for row in cursor.fetchall():
                entry_id, order_idx, data_json, identity_key, stable_id, needs_translation = row
                if order_idx == -1 and data_json == '[]':
                    continue
                data = json.loads(data_json)
                cursor.execute('SELECT t.name FROM tag t\n                       JOIN entry_tag et ON t.id = et.tag_id\n                       WHERE et.entry_id = ?\n                       ORDER BY t.name', (entry_id,))
                tags = [r[0] for r in cursor.fetchall()]
                entries.append({'id': entry_id, 'order_idx': order_idx, 'data': data, 'identity_key': identity_key, 'stable_id': stable_id, 'needs_translation': bool(needs_translation), 'tags': tags})
            return entries
        finally:
            conn.close()

    def get_entry(self, entry_id: int, db_path: Optional[Path]=None) -> Optional[Dict[str, Any]]:
        """Get a single entry by ID."""
        db_path = get_db_path(db_path)
        if not db_path.exists():
            raise ConfigurationError(f'Database not found: {db_path}')
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT e.id, e.person_id, e.section, e.order_idx, e.data_json,\n                          e.identity_key, p.slug,\n                          ell.stable_id, ell.needs_translation, ell.language\n                   FROM entry e\n                   JOIN person p ON e.person_id = p.id\n                   LEFT JOIN entry_lang_link ell ON e.id = ell.entry_id\n                   WHERE e.id = ?', (entry_id,))
            row = cursor.fetchone()
            if not row:
                return None
            entry_id, person_id, section, order_idx, data_json, identity_key, person_slug, stable_id, needs_translation, language = row
            data = json.loads(data_json)
            cursor.execute('SELECT t.name FROM tag t\n                   JOIN entry_tag et ON t.id = et.tag_id\n                   WHERE et.entry_id = ?\n                   ORDER BY t.name', (entry_id,))
            tags = [r[0] for r in cursor.fetchall()]
            return {'id': entry_id, 'person_id': person_id, 'person_slug': person_slug, 'section': section, 'order_idx': order_idx, 'data': data, 'identity_key': identity_key, 'stable_id': stable_id, 'needs_translation': bool(needs_translation) if needs_translation is not None else False, 'language': language, 'tags': tags}
        finally:
            conn.close()

    def create_entry(self, person_slug: str, data: Dict[str, Any], db_path: Optional[Path]=None, sync_languages: bool=True) -> Dict[str, Any]:
        """
        Create a new entry, optionally syncing to other languages.

        This operation is atomic - either all entries are created, or none.
        Uses a single transaction to ensure consistency across languages.

        Args:
            person_slug: Person's slug (e.g., "example" for EN, "example_de" for DE)
            data: Entry data
            db_path: Path to database
            sync_languages: If True, create placeholders in other languages

        Returns:
            Created entry info with stable_id and sync_result for observability
        """
        db_path = get_db_path(db_path)
        ensure_crud_schema(db_path)
        if not db_path.exists():
            raise ConfigurationError(f'Database not found: {db_path}')
        stable_id = generate_stable_id()
        sync_result = SyncResult('create', stable_id)
        base_person = _get_base_person(person_slug)
        source_lang = DEFAULT_LANGUAGE
        for lang in SUPPORTED_LANGUAGES:
            if person_slug == _get_person_slug_for_lang(base_person, lang):
                source_lang = lang
                break
        logger.info(f'[SYNC CREATE] Starting entry creation: section={self.section}, person={person_slug}, source_lang={source_lang}, sync={sync_languages}')
        conn = sqlite3.connect(db_path, timeout=30)
        try:
            cursor = conn.cursor()
            now = _utcnow()
            cursor.execute('INSERT INTO stable_entry (id, section, base_person, created_at, updated_at)\n                   VALUES (?, ?, ?, ?, ?)', (stable_id, self.section, base_person, now, now))
            logger.debug(f'[SYNC CREATE] Created stable_entry: {stable_id[:8]}...')
            entry_id = _create_entry_in_db(cursor, person_slug, self.section, data)
            logger.debug(f'[SYNC CREATE] Created source entry: id={entry_id}, lang={source_lang}')
            cursor.execute('INSERT INTO entry_lang_link (stable_id, language, entry_id, needs_translation, created_at)\n                   VALUES (?, ?, ?, ?, ?)', (stable_id, source_lang, entry_id, 0, now))
            created_entries = {source_lang: entry_id}
            sync_result.add_synced(source_lang, entry_id)
            if sync_languages:
                for lang in SUPPORTED_LANGUAGES:
                    if lang == source_lang:
                        continue
                    lang_slug = _get_person_slug_for_lang(base_person, lang)
                    if not _person_exists_for_lang(cursor, base_person, lang):
                        reason = f"person '{lang_slug}' not found"
                        logger.info(f'[SYNC CREATE] Skipping {lang}: {reason}')
                        sync_result.add_skipped(lang, reason)
                        continue
                    try:
                        placeholder = _create_placeholder_entry(data, self.section, source_lang, lang)
                        lang_entry_id = _create_entry_in_db(cursor, lang_slug, self.section, placeholder)
                        cursor.execute('INSERT INTO entry_lang_link (stable_id, language, entry_id, needs_translation, created_at)\n                               VALUES (?, ?, ?, ?, ?)', (stable_id, lang, lang_entry_id, 1, now))
                        created_entries[lang] = lang_entry_id
                        sync_result.add_synced(lang, lang_entry_id)
                        logger.debug(f'[SYNC CREATE] Created {lang} entry: id={lang_entry_id}')
                    except Exception as lang_err:
                        error_msg = str(lang_err)
                        logger.warning(f'[SYNC CREATE] Failed to create {lang} entry: {error_msg}')
                        sync_result.add_failed(lang, error_msg)
            conn.commit()
            sync_result.mark_complete()
            logger.info(f'[SYNC CREATE] Completed: stable_id={stable_id[:8]}..., synced={sync_result.synced_languages}, skipped={list(sync_result.skipped_languages.keys())}, duration={sync_result.duration_ms:.1f}ms')
            return {'stable_id': stable_id, 'section': self.section, 'source_language': source_lang, 'entries': created_entries, 'data': data, 'sync_result': sync_result.to_dict()}
        except Exception as e:
            conn.rollback()
            sync_result.mark_failed(str(e))
            logger.error(f'[SYNC CREATE] Failed: {e}, duration={sync_result.duration_ms:.1f}ms')
            raise
        finally:
            conn.close()

    def update_entry(self, entry_id: int, data: Dict[str, Any], db_path: Optional[Path]=None, sync_shared_fields: bool=False) -> Dict[str, Any]:
        """
        Update an entry, optionally syncing shared fields to other languages.

        This operation is atomic - the update and any shared field syncs
        occur in a single transaction.

        Args:
            entry_id: Entry ID to update
            data: New entry data
            db_path: Path to database
            sync_shared_fields: If True, sync shared fields to other language variants

        Returns:
            Updated entry info with sync_result for observability
        """
        db_path = get_db_path(db_path)
        ensure_crud_schema(db_path)
        if not db_path.exists():
            raise ConfigurationError(f'Database not found: {db_path}')
        sync_result = SyncResult('update')
        logger.info(f'[SYNC UPDATE] Starting entry update: entry_id={entry_id}, sync_shared={sync_shared_fields}')
        conn = sqlite3.connect(db_path, timeout=30)
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT e.section, e.person_id, p.slug,\n                          ell.stable_id, ell.language\n                   FROM entry e\n                   JOIN person p ON e.person_id = p.id\n                   LEFT JOIN entry_lang_link ell ON e.id = ell.entry_id\n                   WHERE e.id = ?', (entry_id,))
            row = cursor.fetchone()
            if not row:
                raise ConfigurationError(f'Entry not found: {entry_id}')
            section, person_id, person_slug, stable_id, current_lang = row
            sync_result.stable_id = stable_id
            current_lang = current_lang or DEFAULT_LANGUAGE
            logger.debug(f"[SYNC UPDATE] Entry info: section={section}, lang={current_lang}, stable_id={(stable_id[:8] if stable_id else 'None')}...")
            data_json = json.dumps(data, ensure_ascii=False, sort_keys=True)
            cursor.execute('UPDATE entry SET data_json = ? WHERE id = ?', (data_json, entry_id))
            cursor.execute('DELETE FROM entry_tag WHERE entry_id = ?', (entry_id,))
            type_keys = data.get('type_key', [])
            if isinstance(type_keys, list):
                for tag_name in type_keys:
                    if tag_name:
                        tag_id = _get_or_create_tag(cursor, str(tag_name))
                        cursor.execute('INSERT OR IGNORE INTO entry_tag (entry_id, tag_id) VALUES (?, ?)', (entry_id, tag_id))
            cursor.execute('UPDATE entry_lang_link SET needs_translation = 0 WHERE entry_id = ?', (entry_id,))
            if stable_id:
                now = _utcnow()
                cursor.execute('UPDATE stable_entry SET updated_at = ? WHERE id = ?', (now, stable_id))
            sync_result.add_synced(current_lang, entry_id)
            synced_entries = {current_lang: entry_id}
            if sync_shared_fields and stable_id:
                shared = SHARED_FIELDS.get(section, [])
                shared_data = {k: v for k, v in data.items() if k in shared}
                if shared_data:
                    logger.debug(f'[SYNC UPDATE] Syncing shared fields: {list(shared_data.keys())}')
                    cursor.execute('SELECT ell.entry_id, ell.language\n                           FROM entry_lang_link ell\n                           WHERE ell.stable_id = ? AND ell.language != ?', (stable_id, current_lang))
                    for other_entry_id, other_lang in cursor.fetchall():
                        try:
                            cursor.execute('SELECT data_json FROM entry WHERE id = ?', (other_entry_id,))
                            other_row = cursor.fetchone()
                            if other_row:
                                other_data = json.loads(other_row[0])
                                for key, value in shared_data.items():
                                    other_data[key] = value
                                other_data_json = json.dumps(other_data, ensure_ascii=False, sort_keys=True)
                                cursor.execute('UPDATE entry SET data_json = ? WHERE id = ?', (other_data_json, other_entry_id))
                                if 'type_key' in shared_data:
                                    cursor.execute('DELETE FROM entry_tag WHERE entry_id = ?', (other_entry_id,))
                                    type_keys = shared_data.get('type_key', [])
                                    if isinstance(type_keys, list):
                                        for tag_name in type_keys:
                                            if tag_name:
                                                tag_id = _get_or_create_tag(cursor, str(tag_name))
                                                cursor.execute('INSERT OR IGNORE INTO entry_tag (entry_id, tag_id) VALUES (?, ?)', (other_entry_id, tag_id))
                                synced_entries[other_lang] = other_entry_id
                                sync_result.add_synced(other_lang, other_entry_id)
                                logger.debug(f'[SYNC UPDATE] Synced shared fields to {other_lang}')
                        except Exception as lang_err:
                            error_msg = str(lang_err)
                            logger.warning(f'[SYNC UPDATE] Failed to sync {other_lang}: {error_msg}')
                            sync_result.add_failed(other_lang, error_msg)
                else:
                    logger.debug('[SYNC UPDATE] No shared fields to sync')
            conn.commit()
            sync_result.mark_complete()
            logger.info(f'[SYNC UPDATE] Completed: entry_id={entry_id}, synced={sync_result.synced_languages}, duration={sync_result.duration_ms:.1f}ms')
            return {'id': entry_id, 'section': section, 'data': data, 'stable_id': stable_id, 'synced_entries': synced_entries, 'sync_result': sync_result.to_dict()}
        except Exception as e:
            conn.rollback()
            sync_result.mark_failed(str(e))
            logger.error(f'[SYNC UPDATE] Failed: {e}, duration={sync_result.duration_ms:.1f}ms')
            raise
        finally:
            conn.close()

    def delete_entry(self, entry_id: int, db_path: Optional[Path]=None, sync_languages: bool=True) -> Dict[str, Any]:
        """
        Delete an entry, optionally deleting counterparts in other languages.

        This operation is atomic - either all deletions succeed, or none.
        Uses a single transaction to ensure consistency.

        Args:
            entry_id: Entry ID to delete
            db_path: Path to database
            sync_languages: If True, delete all language variants with same stable_id

        Returns:
            Dict with deletion result including sync_result for observability
        """
        db_path = get_db_path(db_path)
        ensure_crud_schema(db_path)
        if not db_path.exists():
            raise ConfigurationError(f'Database not found: {db_path}')
        sync_result = SyncResult('delete')
        logger.info(f'[SYNC DELETE] Starting entry deletion: entry_id={entry_id}, sync={sync_languages}')
        conn = sqlite3.connect(db_path, timeout=30)
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT ell.stable_id, ell.language\n                   FROM entry_lang_link ell\n                   WHERE ell.entry_id = ?', (entry_id,))
            row = cursor.fetchone()
            entries_to_delete = [entry_id]
            stable_id = None
            if row and sync_languages:
                stable_id, source_lang = row
                sync_result.stable_id = stable_id
                cursor.execute('SELECT entry_id, language FROM entry_lang_link WHERE stable_id = ?', (stable_id,))
                entries_info = cursor.fetchall()
                entries_to_delete = [r[0] for r in entries_info]
                logger.debug(f'[SYNC DELETE] Will delete {len(entries_to_delete)} linked entries for stable_id={stable_id[:8]}...')
            elif row:
                stable_id, source_lang = row
                sync_result.stable_id = stable_id
                logger.debug(f'[SYNC DELETE] Deleting only {source_lang} variant')
            deleted_count = 0
            for eid in entries_to_delete:
                cursor.execute('SELECT language FROM entry_lang_link WHERE entry_id = ?', (eid,))
                lang_row = cursor.fetchone()
                lang = lang_row[0] if lang_row else DEFAULT_LANGUAGE
                cursor.execute('DELETE FROM entry_tag WHERE entry_id = ?', (eid,))
                cursor.execute('DELETE FROM entry_lang_link WHERE entry_id = ?', (eid,))
                cursor.execute('DELETE FROM entry WHERE id = ?', (eid,))
                if cursor.rowcount > 0:
                    deleted_count += 1
                    sync_result.add_synced(lang, eid)
                    logger.debug(f'[SYNC DELETE] Deleted {lang} entry: id={eid}')
            if stable_id:
                cursor.execute('SELECT COUNT(*) FROM entry_lang_link WHERE stable_id = ?', (stable_id,))
                remaining = cursor.fetchone()[0]
                if remaining == 0:
                    cursor.execute('DELETE FROM stable_entry WHERE id = ?', (stable_id,))
                    logger.debug(f'[SYNC DELETE] Deleted stable_entry: {stable_id[:8]}...')
            conn.commit()
            sync_result.mark_complete()
            logger.info(f"[SYNC DELETE] Completed: deleted {deleted_count} entries, stable_id={(stable_id[:8] if stable_id else 'None')}..., duration={sync_result.duration_ms:.1f}ms")
            return {'success': deleted_count > 0, 'deleted_count': deleted_count, 'stable_id': stable_id, 'sync_result': sync_result.to_dict()}
        except Exception as e:
            conn.rollback()
            sync_result.mark_failed(str(e))
            logger.error(f'[SYNC DELETE] Failed: {e}, duration={sync_result.duration_ms:.1f}ms')
            raise
        finally:
            conn.close()

    def get_linked_entries(self, entry_id: int, db_path: Optional[Path]=None) -> Dict[str, Dict[str, Any]]:
        """
        Get all language variants of an entry.

        Uses two strategies:
        1. Primary: Find entries linked via stable_id in entry_lang_link table
        2. Fallback: Find corresponding entries via person_entity (config.ID grouping)
           by matching order_idx (position) and section across language variants

        This ensures multilingual entries are shown together even when they were
        imported separately without explicit stable_id linking.

        Args:
            entry_id: Entry ID
            db_path: Path to database

        Returns:
            Dict mapping language codes to entry info
        """
        db_path = get_db_path(db_path)
        if not db_path.exists():
            raise ConfigurationError(f'Database not found: {db_path}')
        ensure_crud_schema(db_path)
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT stable_id FROM entry_lang_link WHERE entry_id = ?', (entry_id,))
            row = cursor.fetchone()
            if row and row[0]:
                stable_id = row[0]
                cursor.execute('SELECT ell.entry_id, ell.language, ell.needs_translation\n                       FROM entry_lang_link ell\n                       WHERE ell.stable_id = ?', (stable_id,))
                result = {}
                for eid, lang, needs_trans in cursor.fetchall():
                    entry = self.get_entry(eid, db_path)
                    if entry:
                        entry['needs_translation'] = bool(needs_trans)
                        result[lang] = entry
                return result
            entry = self.get_entry(entry_id, db_path)
            if not entry:
                return {}
            order_idx = entry.get('order_idx')
            person_id = entry.get('person_id')
            person_slug = entry.get('person_slug', '')
            current_lang = DEFAULT_LANGUAGE
            for lang in SUPPORTED_LANGUAGES:
                if lang != DEFAULT_LANGUAGE and person_slug.endswith(f'_{lang}'):
                    current_lang = lang
                    break
            result = {current_lang: entry}
            if order_idx is None or not person_id:
                return result
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='person_entity_variant'")
            if not cursor.fetchone():
                return result
            cursor.execute('SELECT person_entity_id FROM person_entity_variant\n                   WHERE person_id = ?', (person_id,))
            pe_row = cursor.fetchone()
            if not pe_row:
                return result
            person_entity_id = pe_row[0]
            cursor.execute('SELECT person_id, language FROM person_entity_variant\n                   WHERE person_entity_id = ?', (person_entity_id,))
            person_variants = cursor.fetchall()
            for variant_person_id, variant_lang in person_variants:
                if variant_person_id == person_id:
                    continue
                cursor.execute('SELECT id FROM entry\n                       WHERE person_id = ? AND section = ? AND order_idx = ?', (variant_person_id, self.section, order_idx))
                variant_entry_row = cursor.fetchone()
                if variant_entry_row:
                    variant_entry = self.get_entry(variant_entry_row[0], db_path)
                    if variant_entry:
                        variant_entry['needs_translation'] = False
                        result[variant_lang] = variant_entry
            return result
        finally:
            conn.close()
LIST_SECTIONS = ['basics', 'projects', 'experiences', 'publications', 'references', 'education', 'languages', 'profiles', 'workshop_and_certifications']
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
            raise ValidationError(f"Section '{section}' is not supported for CRUD operations. Supported: {', '.join(LIST_SECTIONS)}")
    return _adapters[section]

def create_entry(person_slug: str, section: str, data: Dict[str, Any], db_path: Optional[Path]=None, sync_languages: bool=True) -> Dict[str, Any]:
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

def update_entry(entry_id: int, data: Dict[str, Any], section: str, db_path: Optional[Path]=None, sync_shared_fields: bool=False) -> Dict[str, Any]:
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

def delete_entry(entry_id: int, section: str, db_path: Optional[Path]=None, sync_languages: bool=True) -> Dict[str, Any]:
    """
    Delete an entry with multi-language sync.

    Args:
        entry_id: Entry ID to delete
        section: Section name
        db_path: Path to database
        sync_languages: If True, delete all language variants

    Returns:
        Dict with deletion result including sync_result for observability.
        Contains 'success' key to check if deletion occurred.
    """
    adapter = get_section_adapter(section)
    return adapter.delete_entry(entry_id, db_path, sync_languages)

def get_entry(entry_id: int, section: str, db_path: Optional[Path]=None) -> Optional[Dict[str, Any]]:
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

def list_entries(person_slug: str, section: str, db_path: Optional[Path]=None) -> List[Dict[str, Any]]:
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

def get_linked_entries(entry_id: int, section: str, db_path: Optional[Path]=None) -> Dict[str, Dict[str, Any]]:
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

def link_existing_entries(entry_ids: Dict[str, int], section: str, db_path: Optional[Path]=None) -> str:
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
        raise ConfigurationError(f'Database not found: {db_path}')
    if len(entry_ids) < 1:
        raise ValidationError('At least one entry ID is required')
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        first_entry_id = list(entry_ids.values())[0]
        cursor.execute('SELECT p.slug FROM entry e\n               JOIN person p ON e.person_id = p.id\n               WHERE e.id = ?', (first_entry_id,))
        row = cursor.fetchone()
        if not row:
            raise ConfigurationError(f'Entry not found: {first_entry_id}')
        base_person = _get_base_person(row[0])
        stable_id = generate_stable_id()
        now = _utcnow()
        cursor.execute('INSERT INTO stable_entry (id, section, base_person, created_at, updated_at)\n               VALUES (?, ?, ?, ?, ?)', (stable_id, section, base_person, now, now))
        for lang, entry_id in entry_ids.items():
            cursor.execute('INSERT INTO entry_lang_link (stable_id, language, entry_id, needs_translation, created_at)\n                   VALUES (?, ?, ?, ?, ?)', (stable_id, lang, entry_id, 0, now))
        conn.commit()
        logger.info(f'Linked {len(entry_ids)} entries with stable_id: {stable_id}')
        return stable_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_entries_without_stable_ids(db_path: Optional[Path]=None, section: Optional[str]=None, person_slug: Optional[str]=None) -> List[Dict[str, Any]]:
    """
    Get all entries that don't have stable IDs assigned.

    These are typically entries imported before the CRUD schema was introduced.

    Args:
        db_path: Path to database
        section: Optional section filter
        person_slug: Optional person filter

    Returns:
        List of entries without stable IDs
    """
    db_path = get_db_path(db_path)
    ensure_crud_schema(db_path)
    if not db_path.exists():
        raise ConfigurationError(f'Database not found: {db_path}')
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        query = '\n            SELECT e.id, e.section, e.order_idx, e.data_json, e.identity_key, p.slug\n            FROM entry e\n            JOIN person p ON e.person_id = p.id\n            LEFT JOIN entry_lang_link ell ON e.id = ell.entry_id\n            WHERE ell.entry_id IS NULL\n            AND e.order_idx >= 0\n        '
        params = []
        if section:
            query += ' AND e.section = ?'
            params.append(section)
        if person_slug:
            query += ' AND p.slug = ?'
            params.append(person_slug)
        query += ' ORDER BY p.slug, e.section, e.order_idx'
        cursor.execute(query, params)
        entries = []
        for row in cursor.fetchall():
            entry_id, section_name, order_idx, data_json, identity_key, slug = row
            data = json.loads(data_json) if data_json else {}
            cursor.execute('SELECT t.name FROM tag t\n                   JOIN entry_tag et ON t.id = et.tag_id\n                   WHERE et.entry_id = ?\n                   ORDER BY t.name', (entry_id,))
            tags = [r[0] for r in cursor.fetchall()]
            entries.append({'id': entry_id, 'section': section_name, 'order_idx': order_idx, 'data': data, 'identity_key': identity_key, 'person_slug': slug, 'tags': tags, 'stable_id': None})
        return entries
    finally:
        conn.close()

def assign_stable_id(entry_id: int, db_path: Optional[Path]=None, custom_stable_id: Optional[str]=None) -> Dict[str, Any]:
    """
    Assign a stable ID to an entry that doesn't have one.

    This creates a new stable_entry record and links it to the entry.

    Args:
        entry_id: Entry ID to assign stable ID to
        db_path: Path to database
        custom_stable_id: Optional custom stable ID to use (for merging)

    Returns:
        Dict with stable_id and entry info

    Raises:
        ValidationError: If entry already has a stable ID
        ConfigurationError: If entry not found
    """
    db_path = get_db_path(db_path)
    ensure_crud_schema(db_path)
    if not db_path.exists():
        raise ConfigurationError(f'Database not found: {db_path}')
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT e.section, p.slug\n               FROM entry e\n               JOIN person p ON e.person_id = p.id\n               WHERE e.id = ?', (entry_id,))
        row = cursor.fetchone()
        if not row:
            raise ConfigurationError(f'Entry not found: {entry_id}')
        section, person_slug = row
        cursor.execute('SELECT stable_id FROM entry_lang_link WHERE entry_id = ?', (entry_id,))
        existing = cursor.fetchone()
        if existing:
            raise ValidationError(f'Entry {entry_id} already has stable ID: {existing[0]}')
        base_person = _get_base_person(person_slug)
        language = DEFAULT_LANGUAGE
        for lang in SUPPORTED_LANGUAGES:
            if person_slug == _get_person_slug_for_lang(base_person, lang):
                language = lang
                break
        stable_id = custom_stable_id or generate_stable_id()
        now = _utcnow()
        if custom_stable_id:
            cursor.execute('SELECT id FROM stable_entry WHERE id = ?', (stable_id,))
            if not cursor.fetchone():
                cursor.execute('INSERT INTO stable_entry (id, section, base_person, created_at, updated_at)\n                       VALUES (?, ?, ?, ?, ?)', (stable_id, section, base_person, now, now))
        else:
            cursor.execute('INSERT INTO stable_entry (id, section, base_person, created_at, updated_at)\n                   VALUES (?, ?, ?, ?, ?)', (stable_id, section, base_person, now, now))
        cursor.execute('INSERT INTO entry_lang_link (stable_id, language, entry_id, needs_translation, created_at)\n               VALUES (?, ?, ?, ?, ?)', (stable_id, language, entry_id, 0, now))
        conn.commit()
        logger.info(f'Assigned stable_id {stable_id[:8]}... to entry {entry_id}')
        return {'entry_id': entry_id, 'stable_id': stable_id, 'section': section, 'language': language, 'person_slug': person_slug}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def merge_entries_to_stable_id(target_stable_id: str, entry_ids: Dict[str, int], db_path: Optional[Path]=None) -> Dict[str, Any]:
    """
    Merge entries from different languages into an existing stable ID group.

    This is used to link entries that belong together but were imported
    separately without stable ID linking.

    Args:
        target_stable_id: The stable ID to merge entries into
        entry_ids: Dict mapping language codes to entry IDs to merge
        db_path: Path to database

    Returns:
        Dict with merge result info

    Raises:
        ValidationError: If stable_id doesn't exist or entry already linked
        ConfigurationError: If entry not found
    """
    db_path = get_db_path(db_path)
    ensure_crud_schema(db_path)
    if not db_path.exists():
        raise ConfigurationError(f'Database not found: {db_path}')
    if not entry_ids:
        raise ValidationError('At least one entry must be provided')
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT section, base_person FROM stable_entry WHERE id = ?', (target_stable_id,))
        row = cursor.fetchone()
        if not row:
            raise ValidationError(f'Stable ID not found: {target_stable_id}')
        expected_section, base_person = row
        now = _utcnow()
        merged_languages = []
        skipped_languages = {}
        for lang, entry_id in entry_ids.items():
            cursor.execute('SELECT e.section, p.slug\n                   FROM entry e\n                   JOIN person p ON e.person_id = p.id\n                   WHERE e.id = ?', (entry_id,))
            entry_row = cursor.fetchone()
            if not entry_row:
                skipped_languages[lang] = f'Entry {entry_id} not found'
                continue
            entry_section, person_slug = entry_row
            if entry_section != expected_section:
                skipped_languages[lang] = f'Section mismatch: entry is {entry_section}, stable_id is {expected_section}'
                continue
            cursor.execute('SELECT stable_id FROM entry_lang_link WHERE entry_id = ?', (entry_id,))
            existing = cursor.fetchone()
            if existing:
                if existing[0] == target_stable_id:
                    skipped_languages[lang] = 'Already linked to this stable ID'
                else:
                    skipped_languages[lang] = f'Already linked to {existing[0][:8]}...'
                continue
            cursor.execute('SELECT entry_id FROM entry_lang_link WHERE stable_id = ? AND language = ?', (target_stable_id, lang))
            if cursor.fetchone():
                skipped_languages[lang] = 'Language already exists in group'
                continue
            cursor.execute('INSERT INTO entry_lang_link (stable_id, language, entry_id, needs_translation, created_at)\n                   VALUES (?, ?, ?, ?, ?)', (target_stable_id, lang, entry_id, 0, now))
            merged_languages.append(lang)
        cursor.execute('UPDATE stable_entry SET updated_at = ? WHERE id = ?', (now, target_stable_id))
        conn.commit()
        logger.info(f'Merged {len(merged_languages)} entries to stable_id {target_stable_id[:8]}...')
        return {'stable_id': target_stable_id, 'merged_languages': merged_languages, 'skipped_languages': skipped_languages, 'success': len(merged_languages) > 0}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def update_entry_stable_id(entry_id: int, new_stable_id: str, db_path: Optional[Path]=None) -> Dict[str, Any]:
    """
    Update the stable ID for an entry, moving it to a different group.

    This can be used to manually correct stable ID assignments.

    Args:
        entry_id: Entry ID to update
        new_stable_id: New stable ID to assign
        db_path: Path to database

    Returns:
        Dict with update result info

    Raises:
        ValidationError: If new stable_id doesn't exist
        ConfigurationError: If entry not found
    """
    db_path = get_db_path(db_path)
    ensure_crud_schema(db_path)
    if not db_path.exists():
        raise ConfigurationError(f'Database not found: {db_path}')
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT e.section, p.slug\n               FROM entry e\n               JOIN person p ON e.person_id = p.id\n               WHERE e.id = ?', (entry_id,))
        row = cursor.fetchone()
        if not row:
            raise ConfigurationError(f'Entry not found: {entry_id}')
        section, person_slug = row
        cursor.execute('SELECT section FROM stable_entry WHERE id = ?', (new_stable_id,))
        stable_row = cursor.fetchone()
        if not stable_row:
            raise ValidationError(f'Stable ID not found: {new_stable_id}')
        if stable_row[0] != section:
            raise ValidationError(f'Section mismatch: entry is {section}, stable_id is {stable_row[0]}')
        base_person = _get_base_person(person_slug)
        language = DEFAULT_LANGUAGE
        for lang in SUPPORTED_LANGUAGES:
            if person_slug == _get_person_slug_for_lang(base_person, lang):
                language = lang
                break
        cursor.execute('SELECT entry_id FROM entry_lang_link WHERE stable_id = ? AND language = ?', (new_stable_id, language))
        existing_in_target = cursor.fetchone()
        if existing_in_target and existing_in_target[0] != entry_id:
            raise ValidationError(f'Language {language} already exists in stable ID group (entry {existing_in_target[0]})')
        cursor.execute('SELECT stable_id FROM entry_lang_link WHERE entry_id = ?', (entry_id,))
        current = cursor.fetchone()
        old_stable_id = current[0] if current else None
        now = _utcnow()
        if current:
            cursor.execute('UPDATE entry_lang_link SET stable_id = ? WHERE entry_id = ?', (new_stable_id, entry_id))
        else:
            cursor.execute('INSERT INTO entry_lang_link (stable_id, language, entry_id, needs_translation, created_at)\n                   VALUES (?, ?, ?, ?, ?)', (new_stable_id, language, entry_id, 0, now))
        cursor.execute('UPDATE stable_entry SET updated_at = ? WHERE id = ?', (now, new_stable_id))
        if old_stable_id and old_stable_id != new_stable_id:
            cursor.execute('SELECT COUNT(*) FROM entry_lang_link WHERE stable_id = ?', (old_stable_id,))
            remaining = cursor.fetchone()[0]
            if remaining == 0:
                cursor.execute('DELETE FROM stable_entry WHERE id = ?', (old_stable_id,))
                logger.debug(f'Deleted empty stable_entry: {old_stable_id[:8]}...')
        conn.commit()
        logger.info(f"Updated entry {entry_id} stable_id: {(old_stable_id[:8] if old_stable_id else 'None')}... -> {new_stable_id[:8]}...")
        return {'entry_id': entry_id, 'old_stable_id': old_stable_id, 'new_stable_id': new_stable_id, 'language': language, 'section': section}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
