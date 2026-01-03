"""
SQLite3 storage module for CV Generator.

Provides functions for:
- Initializing the database with schema
- Importing CV JSON files into the database
- Exporting database entries back to JSON files
- Comparing JSON files with database exports (diff)

This module implements a hybrid storage approach where:
- Core tables store person, entry, and tag relationships
- Entry data is stored as JSON blobs for schema flexibility
- Tags are extracted from type_key fields and stored in a separate table
"""

import hashlib
import json
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .errors import ConfigurationError, ValidationError
from .io import load_cv_json, parse_cv_filename
from .paths import get_default_cvs_path

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    """Return current UTC time as ISO format string."""
    return datetime.now(timezone.utc).isoformat()

# Default database location
DEFAULT_DB_PATH = Path("data/db/cv.db")

# Schema version for migrations
SCHEMA_VERSION = 1

# Maximum number of errors to report in doctor command
MAX_DOCTOR_ERRORS = 5

# SQL schema for the database
SCHEMA_SQL = """
-- Meta table for schema version tracking
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Person table
CREATE TABLE IF NOT EXISTS person (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    display_name TEXT,
    created_at TEXT NOT NULL
);

-- Entry table for CV sections
CREATE TABLE IF NOT EXISTS entry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    section TEXT NOT NULL,
    order_idx INTEGER NOT NULL,
    data_json TEXT NOT NULL,
    identity_key TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (person_id) REFERENCES person(id) ON DELETE CASCADE
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_entry_person_section ON entry(person_id, section);
CREATE INDEX IF NOT EXISTS idx_entry_identity ON entry(identity_key);

-- Tag table for type_key values
CREATE TABLE IF NOT EXISTS tag (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL
);

-- Entry-Tag relationship table
CREATE TABLE IF NOT EXISTS entry_tag (
    entry_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (entry_id, tag_id),
    FOREIGN KEY (entry_id) REFERENCES entry(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tag(id) ON DELETE CASCADE
);

-- Index for faster tag lookups
CREATE INDEX IF NOT EXISTS idx_entry_tag_entry ON entry_tag(entry_id);
CREATE INDEX IF NOT EXISTS idx_entry_tag_tag ON entry_tag(tag_id);
"""

# Sections that are lists of objects
LIST_SECTIONS = [
    "basics", "profiles", "education", "experiences", "languages",
    "projects", "publications", "references", "workshop_and_certifications"
]

# Sections that are dict-of-dicts (stored as single entry)
DICT_SECTIONS = ["skills"]


def get_db_path(db_path: Optional[Path] = None, repo_root: Optional[Path] = None) -> Path:
    """
    Get the database path.
    
    Args:
        db_path: Explicit database path. If None, uses default.
        repo_root: Repository root path. Used for default path calculation.
        
    Returns:
        Path to the database file.
    """
    if db_path is not None:
        return Path(db_path)
    
    if repo_root is None:
        from .paths import get_repo_root
        repo_root = get_repo_root()
    
    return repo_root / DEFAULT_DB_PATH


def init_db(db_path: Optional[Path] = None, force: bool = False) -> Path:
    """
    Initialize the database with schema.
    
    Args:
        db_path: Path to the database file. Uses default if None.
        force: If True, recreate the database even if it exists.
        
    Returns:
        Path to the created database file.
        
    Raises:
        ConfigurationError: If database already exists and force is False.
    """
    db_path = get_db_path(db_path)
    
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    if db_path.exists():
        if force:
            logger.info(f"Removing existing database: {db_path}")
            db_path.unlink()
        else:
            logger.info(f"Database already exists: {db_path}")
            # Verify schema version
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM meta WHERE key = 'schema_version'")
                row = cursor.fetchone()
                if row:
                    existing_version = int(row[0])
                    if existing_version != SCHEMA_VERSION:
                        logger.warning(
                            f"Schema version mismatch: DB has v{existing_version}, "
                            f"expected v{SCHEMA_VERSION}"
                        )
            finally:
                conn.close()
            return db_path
    
    logger.info(f"Creating database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.executescript(SCHEMA_SQL)
        
        # Set schema version
        now = _utcnow()
        cursor.execute(
            "INSERT OR REPLACE INTO meta (key, value, updated_at) VALUES (?, ?, ?)",
            ("schema_version", str(SCHEMA_VERSION), now)
        )
        
        conn.commit()
        logger.info(f"Database initialized with schema version {SCHEMA_VERSION}")
    finally:
        conn.close()
    
    return db_path


def _compute_identity_key(section: str, item: Dict[str, Any]) -> Optional[str]:
    """
    Compute identity key for an entry based on section and item data.
    
    Args:
        section: The section name (e.g., "projects", "experiences").
        item: The entry data.
        
    Returns:
        Identity key string or None if cannot be computed.
    """
    if section == "projects":
        if item.get("url"):
            return f"projects:url={item['url']}"
        if item.get("title"):
            return f"projects:title={item['title']}"
    elif section == "experiences":
        parts = []
        if item.get("role"):
            parts.append(item["role"])
        if item.get("institution"):
            parts.append(item["institution"])
        if item.get("duration"):
            parts.append(item["duration"])
        if parts:
            return f"experiences:{'-'.join(parts)}"
    elif section == "publications":
        if item.get("doi"):
            return f"publications:doi={item['doi']}"
        if item.get("identifiers", {}).get("doi"):
            return f"publications:doi={item['identifiers']['doi']}"
        if item.get("title"):
            return f"publications:title={item['title']}"
    elif section == "references":
        if item.get("name"):
            return f"references:name={item['name']}"
        if item.get("email"):
            emails = item["email"]
            if isinstance(emails, list) and emails:
                return f"references:email={emails[0]}"
            elif isinstance(emails, str):
                return f"references:email={emails}"
    elif section == "education":
        parts = []
        if item.get("institution"):
            parts.append(item["institution"])
        if item.get("area"):
            parts.append(item["area"])
        if item.get("startDate"):
            parts.append(item["startDate"])
        if parts:
            return f"education:{'-'.join(parts)}"
    elif section == "profiles":
        if item.get("url"):
            return f"profiles:url={item['url']}"
        if item.get("network"):
            return f"profiles:network={item['network']}"
    elif section == "languages":
        if item.get("language"):
            return f"languages:language={item['language']}"
    elif section == "basics":
        if item.get("fname") and item.get("lname"):
            return f"basics:{item['fname']}-{item['lname']}"
    elif section == "workshop_and_certifications":
        if item.get("issuer"):
            return f"workshop_and_certifications:issuer={item['issuer']}"
    
    return None


def _extract_type_keys(item: Dict[str, Any]) -> List[str]:
    """
    Extract type_key tags from an entry.
    
    Args:
        item: The entry data.
        
    Returns:
        List of tag names.
    """
    type_key = item.get("type_key", [])
    if isinstance(type_key, list):
        return [str(t) for t in type_key if t]
    return []


def _get_or_create_tag(cursor: sqlite3.Cursor, tag_name: str) -> int:
    """
    Get or create a tag and return its ID.
    
    Args:
        cursor: Database cursor.
        tag_name: Name of the tag.
        
    Returns:
        Tag ID.
    """
    cursor.execute("SELECT id FROM tag WHERE name = ?", (tag_name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    now = _utcnow()
    cursor.execute(
        "INSERT INTO tag (name, created_at) VALUES (?, ?)",
        (tag_name, now)
    )
    return cursor.lastrowid


def _get_or_create_person(cursor: sqlite3.Cursor, slug: str, display_name: Optional[str] = None) -> int:
    """
    Get or create a person and return their ID.
    
    Args:
        cursor: Database cursor.
        slug: Person's slug (unique identifier).
        display_name: Optional display name.
        
    Returns:
        Person ID.
    """
    cursor.execute("SELECT id FROM person WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    now = _utcnow()
    cursor.execute(
        "INSERT INTO person (slug, display_name, created_at) VALUES (?, ?, ?)",
        (slug, display_name, now)
    )
    return cursor.lastrowid


def import_cv(
    cv_path: Path,
    db_path: Optional[Path] = None,
    overwrite: bool = False
) -> Dict[str, Any]:
    """
    Import a single CV JSON file into the database.
    
    Args:
        cv_path: Path to the CV JSON file.
        db_path: Path to the database file. Uses default if None.
        overwrite: If True, replace existing entries for this person.
        
    Returns:
        Dict with import statistics.
        
    Raises:
        ConfigurationError: If database doesn't exist or CV file not found.
        ValidationError: If CV JSON is invalid.
    """
    db_path = get_db_path(db_path)
    
    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}. Run 'cvgen db init' first.")
    
    # Load CV data
    cv_data = load_cv_json(cv_path)
    
    # Parse filename to get person slug
    slug, lang = parse_cv_filename(cv_path.name)
    
    # Include language in slug if not English
    if lang != "en":
        slug = f"{slug}_{lang}"
    
    # Get display name from basics
    display_name = None
    if "basics" in cv_data and isinstance(cv_data["basics"], list) and cv_data["basics"]:
        basics = cv_data["basics"][0]
        fname = basics.get("fname", "")
        lname = basics.get("lname", "")
        if fname or lname:
            display_name = f"{fname} {lname}".strip()
    
    stats = {
        "person": slug,
        "entries_imported": 0,
        "tags_created": 0,
        "sections": {}
    }
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        
        # Get or create person
        person_id = _get_or_create_person(cursor, slug, display_name)
        
        # If overwrite, delete existing entries for this person
        if overwrite:
            cursor.execute("DELETE FROM entry WHERE person_id = ?", (person_id,))
            logger.info(f"Deleted existing entries for person: {slug}")
        
        # Import all sections from CV data
        # Detect section type dynamically: list or dict
        for section, section_data in cv_data.items():
            if isinstance(section_data, list):
                # List section (e.g., basics, education, projects)
                if len(section_data) == 0:
                    # Store empty list marker
                    now = _utcnow()
                    cursor.execute(
                        """INSERT INTO entry (person_id, section, order_idx, data_json, identity_key, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (person_id, section, -1, "[]", f"{section}:empty_list", now)
                    )
                    stats["entries_imported"] += 1
                    stats["sections"][section] = 0
                    continue
                
                section_count = 0
                for idx, item in enumerate(section_data):
                    if not isinstance(item, dict):
                        continue
                    
                    # Compute identity key
                    identity_key = _compute_identity_key(section, item)
                    
                    # Store data as JSON
                    data_json = json.dumps(item, ensure_ascii=False, sort_keys=True)
                    
                    now = _utcnow()
                    cursor.execute(
                        """INSERT INTO entry (person_id, section, order_idx, data_json, identity_key, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (person_id, section, idx, data_json, identity_key, now)
                    )
                    entry_id = cursor.lastrowid
                    
                    # Extract and link type_key tags
                    type_keys = _extract_type_keys(item)
                    for tag_name in type_keys:
                        tag_id = _get_or_create_tag(cursor, tag_name)
                        cursor.execute(
                            "INSERT OR IGNORE INTO entry_tag (entry_id, tag_id) VALUES (?, ?)",
                            (entry_id, tag_id)
                        )
                    
                    section_count += 1
                    stats["entries_imported"] += 1
                
                stats["sections"][section] = section_count
            
            elif isinstance(section_data, dict):
                # Dict section (e.g., skills)
                # Store entire section as one entry
                data_json = json.dumps(section_data, ensure_ascii=False, sort_keys=True)
                identity_key = f"{section}:full"
                
                now = _utcnow()
                cursor.execute(
                    """INSERT INTO entry (person_id, section, order_idx, data_json, identity_key, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (person_id, section, 0, data_json, identity_key, now)
                )
                
                stats["entries_imported"] += 1
                stats["sections"][section] = 1
            
            else:
                # Skip non-list, non-dict sections (e.g., scalar values)
                logger.debug(f"Skipping section '{section}' with type {type(section_data).__name__}")
        
        # Count tags created
        cursor.execute("SELECT COUNT(*) FROM tag")
        stats["tags_created"] = cursor.fetchone()[0]
        
        conn.commit()
        logger.info(f"Imported CV for '{slug}': {stats['entries_imported']} entries")
        
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()
    
    return stats


def import_all_cvs(
    input_dir: Optional[Path] = None,
    db_path: Optional[Path] = None,
    name_filter: Optional[str] = None,
    overwrite: bool = False,
    backup: bool = True
) -> Dict[str, Any]:
    """
    Import all CV JSON files from a directory into the database.
    
    Args:
        input_dir: Path to directory containing CV JSON files. Uses default if None.
        db_path: Path to the database file. Uses default if None.
        name_filter: If provided, only import CVs matching this base name.
        overwrite: If True, replace existing entries for each person.
        backup: If True, backup the database before overwriting.
        
    Returns:
        Dict with import statistics.
    """
    if input_dir is None:
        input_dir = get_default_cvs_path()
    
    input_dir = Path(input_dir)
    db_path = get_db_path(db_path)
    
    if not input_dir.exists():
        raise ConfigurationError(f"Input directory not found: {input_dir}")
    
    # Backup database before overwrite
    if backup and overwrite and db_path.exists():
        backup_path = db_path.with_suffix(f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backed up to: {backup_path}")
    
    # Find CV files
    cv_files = sorted(input_dir.glob("*.json"))
    
    if name_filter:
        cv_files = [
            f for f in cv_files
            if parse_cv_filename(f.name)[0] == name_filter
        ]
    
    if not cv_files:
        logger.warning(f"No CV files found in {input_dir}")
        return {"files_processed": 0, "total_entries": 0}
    
    results = {
        "files_processed": 0,
        "total_entries": 0,
        "files": []
    }
    
    for cv_path in cv_files:
        try:
            stats = import_cv(cv_path, db_path, overwrite=overwrite)
            results["files"].append({
                "file": cv_path.name,
                "success": True,
                **stats
            })
            results["files_processed"] += 1
            results["total_entries"] += stats["entries_imported"]
        except Exception as e:
            logger.error(f"Error importing {cv_path.name}: {e}")
            results["files"].append({
                "file": cv_path.name,
                "success": False,
                "error": str(e)
            })
    
    return results


def _rebuild_type_keys(cursor: sqlite3.Cursor, entry_id: int) -> List[str]:
    """
    Rebuild type_key list from entry_tag relationships.
    
    Args:
        cursor: Database cursor.
        entry_id: Entry ID.
        
    Returns:
        List of tag names.
    """
    cursor.execute(
        """SELECT t.name FROM tag t
           JOIN entry_tag et ON t.id = et.tag_id
           WHERE et.entry_id = ?
           ORDER BY t.name""",
        (entry_id,)
    )
    return [row[0] for row in cursor.fetchall()]


def export_cv(
    person_slug: str,
    db_path: Optional[Path] = None,
    pretty: bool = True,
    apply_tags: bool = False,
    apply_tags_to_all: bool = False
) -> Dict[str, Any]:
    """
    Export a person's CV from the database to a dict.
    
    Args:
        person_slug: The person's slug.
        db_path: Path to the database file. Uses default if None.
        pretty: If True, format JSON with indentation.
        apply_tags: If True, rebuild type_key from entry_tag for entries that originally had it.
        apply_tags_to_all: If True, add type_key to ALL entries (even those that didn't have it).
        
    Returns:
        CV data dictionary.
        
    Raises:
        ConfigurationError: If database doesn't exist or person not found.
    """
    db_path = get_db_path(db_path)
    
    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        
        # Get person
        cursor.execute("SELECT id FROM person WHERE slug = ?", (person_slug,))
        row = cursor.fetchone()
        if not row:
            raise ConfigurationError(f"Person not found: {person_slug}")
        
        person_id = row[0]
        
        # Get all entries for this person
        cursor.execute(
            """SELECT id, section, order_idx, data_json
               FROM entry
               WHERE person_id = ?
               ORDER BY section, order_idx""",
            (person_id,)
        )
        
        cv_data: Dict[str, Any] = {}
        
        for entry_id, section, order_idx, data_json in cursor.fetchall():
            # Check for empty list marker
            if order_idx == -1 and data_json == "[]":
                cv_data[section] = []
                continue
            
            item = json.loads(data_json)
            
            # Handle type_key based on apply_tags flags
            if apply_tags or apply_tags_to_all:
                # Get tags from entry_tag table
                db_tags = _rebuild_type_keys(cursor, entry_id)
                
                if apply_tags_to_all:
                    # Always add type_key, even if empty
                    if db_tags:
                        item["type_key"] = db_tags
                    elif "type_key" in item:
                        del item["type_key"]
                elif apply_tags:
                    # Only add type_key if the entry originally had it
                    original_had_type_key = "type_key" in item
                    if original_had_type_key and db_tags:
                        item["type_key"] = db_tags
                    elif original_had_type_key and not db_tags:
                        del item["type_key"]
            
            # Check if this is a dict section (stored as single entry with identity_key ending in :full)
            # We detect this by checking if the item is a dict with nested dicts (typical for skills)
            # or by the fact that order_idx is 0 and it's the only entry
            
            if section in cv_data and isinstance(cv_data[section], dict):
                # Already established as dict section, merge (shouldn't happen normally)
                cv_data[section].update(item)
            elif section not in cv_data:
                # First entry for this section, add it
                # We'll determine list vs dict by the structure:
                # If item itself is the complete section (has nested dicts), it's a dict section
                # This is detected by checking if it's a dict of dicts
                is_dict_section = (
                    isinstance(item, dict) and 
                    all(isinstance(v, dict) for v in item.values()) and
                    len(item) > 0
                )
                
                if is_dict_section and order_idx == 0:
                    cv_data[section] = item
                else:
                    cv_data[section] = [item]
            else:
                # Existing list section, append
                cv_data[section].append(item)
        
        return cv_data
        
    finally:
        conn.close()


def export_cv_to_file(
    person_slug: str,
    output_path: Path,
    db_path: Optional[Path] = None,
    pretty: bool = True,
    apply_tags: bool = False,
    apply_tags_to_all: bool = False,
    force: bool = False
) -> Path:
    """
    Export a person's CV from the database to a JSON file.
    
    Args:
        person_slug: The person's slug.
        output_path: Path to output JSON file.
        db_path: Path to the database file. Uses default if None.
        pretty: If True, format JSON with indentation.
        apply_tags: If True, rebuild type_key from entry_tag for entries that originally had it.
        apply_tags_to_all: If True, add type_key to ALL entries.
        force: If True, overwrite existing files.
        
    Returns:
        Path to the created file.
        
    Raises:
        ConfigurationError: If file exists and force is False.
    """
    # Check if file exists and force is not set
    if output_path.exists() and not force:
        raise ConfigurationError(
            f"Output file already exists: {output_path}. Use --force to overwrite."
        )
    
    cv_data = export_cv(person_slug, db_path, pretty, apply_tags, apply_tags_to_all)
    
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(cv_data, f, ensure_ascii=False, indent=2)
        else:
            json.dump(cv_data, f, ensure_ascii=False, separators=(",", ":"))
    
    logger.info(f"Exported CV to: {output_path}")
    return output_path


def export_all_cvs(
    output_dir: Optional[Path] = None,
    db_path: Optional[Path] = None,
    name_filter: Optional[str] = None,
    pretty: bool = True,
    apply_tags: bool = False,
    apply_tags_to_all: bool = False,
    force: bool = False
) -> Dict[str, Any]:
    """
    Export all CVs from the database to JSON files.
    
    Args:
        output_dir: Directory to write JSON files. Uses default if None.
        db_path: Path to the database file. Uses default if None.
        name_filter: If provided, only export CVs matching this slug.
        pretty: If True, format JSON with indentation.
        apply_tags: If True, rebuild type_key from entry_tag for entries that originally had it.
        apply_tags_to_all: If True, add type_key to ALL entries.
        force: If True, overwrite existing files.
        
    Returns:
        Dict with export statistics.
    """
    if output_dir is None:
        output_dir = get_default_cvs_path()
    
    output_dir = Path(output_dir)
    db_path = get_db_path(db_path)
    
    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        
        # Get all persons
        if name_filter:
            cursor.execute(
                "SELECT slug FROM person WHERE slug = ? OR slug LIKE ?",
                (name_filter, f"{name_filter}_%")
            )
        else:
            cursor.execute("SELECT slug FROM person ORDER BY slug")
        
        persons = [row[0] for row in cursor.fetchall()]
        
    finally:
        conn.close()
    
    if not persons:
        logger.warning("No persons found in database")
        return {"files_exported": 0}
    
    results: Dict[str, Any] = {
        "files_exported": 0,
        "files": []
    }
    
    for slug in persons:
        try:
            output_path = output_dir / f"{slug}.json"
            export_cv_to_file(
                slug, output_path, db_path, pretty,
                apply_tags, apply_tags_to_all, force
            )
            results["files"].append({
                "slug": slug,
                "file": output_path.name,
                "success": True
            })
            results["files_exported"] += 1
        except Exception as e:
            logger.error(f"Error exporting {slug}: {e}")
            results["files"].append({
                "slug": slug,
                "success": False,
                "error": str(e)
            })
    
    return results


def _normalize_for_comparison(data: Any) -> Any:
    """
    Normalize data for comparison (sort keys, etc.).
    
    Args:
        data: Data to normalize.
        
    Returns:
        Normalized data.
    """
    if isinstance(data, dict):
        return {k: _normalize_for_comparison(v) for k, v in sorted(data.items())}
    elif isinstance(data, list):
        return [_normalize_for_comparison(item) for item in data]
    else:
        return data


def _find_differences(
    path: str,
    original: Any,
    exported: Any,
    differences: List[Dict[str, Any]]
) -> None:
    """
    Recursively find differences between two structures.
    
    Args:
        path: Current path in the data structure.
        original: Original data.
        exported: Exported data.
        differences: List to append differences to.
    """
    if type(original) != type(exported):
        differences.append({
            "path": path,
            "type": "type_mismatch",
            "original_type": type(original).__name__,
            "exported_type": type(exported).__name__
        })
        return
    
    if isinstance(original, dict):
        all_keys = set(original.keys()) | set(exported.keys())
        for key in sorted(all_keys):
            new_path = f"{path}.{key}" if path else key
            if key not in original:
                differences.append({
                    "path": new_path,
                    "type": "added",
                    "value": exported[key]
                })
            elif key not in exported:
                differences.append({
                    "path": new_path,
                    "type": "removed",
                    "value": original[key]
                })
            else:
                _find_differences(new_path, original[key], exported[key], differences)
    
    elif isinstance(original, list):
        if len(original) != len(exported):
            differences.append({
                "path": path,
                "type": "length_mismatch",
                "original_length": len(original),
                "exported_length": len(exported)
            })
        
        for i in range(min(len(original), len(exported))):
            _find_differences(f"{path}[{i}]", original[i], exported[i], differences)
    
    else:
        if original != exported:
            differences.append({
                "path": path,
                "type": "value_changed",
                "original": original,
                "exported": exported
            })


def diff_cv(
    cv_path: Path,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Compare a CV JSON file with its database export.
    
    Args:
        cv_path: Path to the CV JSON file.
        db_path: Path to the database file. Uses default if None.
        
    Returns:
        Dict with comparison results.
    """
    db_path = get_db_path(db_path)
    
    # Load original JSON
    original_data = load_cv_json(cv_path)
    
    # Get person slug
    slug, lang = parse_cv_filename(cv_path.name)
    if lang != "en":
        slug = f"{slug}_{lang}"
    
    # Export from database
    try:
        exported_data = export_cv(slug, db_path)
    except ConfigurationError as e:
        return {
            "file": cv_path.name,
            "slug": slug,
            "match": False,
            "error": str(e),
            "differences": []
        }
    
    # Normalize and compare
    original_normalized = _normalize_for_comparison(original_data)
    exported_normalized = _normalize_for_comparison(exported_data)
    
    differences = []
    _find_differences("", original_normalized, exported_normalized, differences)
    
    return {
        "file": cv_path.name,
        "slug": slug,
        "match": len(differences) == 0,
        "differences": differences,
        "difference_count": len(differences)
    }


def diff_all_cvs(
    input_dir: Optional[Path] = None,
    db_path: Optional[Path] = None,
    name_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compare all CV JSON files with their database exports.
    
    Args:
        input_dir: Path to directory containing CV JSON files. Uses default if None.
        db_path: Path to the database file. Uses default if None.
        name_filter: If provided, only diff CVs matching this base name.
        
    Returns:
        Dict with comparison results.
    """
    if input_dir is None:
        input_dir = get_default_cvs_path()
    
    input_dir = Path(input_dir)
    
    if not input_dir.exists():
        raise ConfigurationError(f"Input directory not found: {input_dir}")
    
    # Find CV files
    cv_files = sorted(input_dir.glob("*.json"))
    
    if name_filter:
        cv_files = [
            f for f in cv_files
            if parse_cv_filename(f.name)[0] == name_filter
        ]
    
    results = {
        "files_compared": 0,
        "matches": 0,
        "mismatches": 0,
        "files": []
    }
    
    for cv_path in cv_files:
        diff_result = diff_cv(cv_path, db_path)
        results["files"].append(diff_result)
        results["files_compared"] += 1
        
        if diff_result.get("match"):
            results["matches"] += 1
        else:
            results["mismatches"] += 1
    
    return results


def list_persons(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    List all persons in the database.
    
    Args:
        db_path: Path to the database file. Uses default if None.
        
    Returns:
        List of person records.
    """
    db_path = get_db_path(db_path)
    
    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT p.slug, p.display_name, p.created_at,
                      COUNT(e.id) as entry_count
               FROM person p
               LEFT JOIN entry e ON p.id = e.person_id
               GROUP BY p.id
               ORDER BY p.slug"""
        )
        
        return [
            {
                "slug": row[0],
                "display_name": row[1],
                "created_at": row[2],
                "entry_count": row[3]
            }
            for row in cursor.fetchall()
        ]
    finally:
        conn.close()


def get_person_sections(person_slug: str, db_path: Optional[Path] = None) -> List[str]:
    """
    Get list of sections for a person.
    
    Args:
        person_slug: The person's slug.
        db_path: Path to the database file. Uses default if None.
        
    Returns:
        List of section names.
    """
    db_path = get_db_path(db_path)
    
    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM person WHERE slug = ?", (person_slug,))
        row = cursor.fetchone()
        if not row:
            raise ConfigurationError(f"Person not found: {person_slug}")
        
        person_id = row[0]
        
        cursor.execute(
            """SELECT DISTINCT section FROM entry WHERE person_id = ? ORDER BY section""",
            (person_id,)
        )
        
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()


def get_section_entries(
    person_slug: str,
    section: str,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Get all entries for a person's section.
    
    Args:
        person_slug: The person's slug.
        section: The section name.
        db_path: Path to the database file. Uses default if None.
        
    Returns:
        List of entry records with id, order_idx, data, and tags.
    """
    db_path = get_db_path(db_path)
    
    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM person WHERE slug = ?", (person_slug,))
        row = cursor.fetchone()
        if not row:
            raise ConfigurationError(f"Person not found: {person_slug}")
        
        person_id = row[0]
        
        cursor.execute(
            """SELECT e.id, e.order_idx, e.data_json, e.identity_key
               FROM entry e
               WHERE e.person_id = ? AND e.section = ?
               ORDER BY e.order_idx""",
            (person_id, section)
        )
        
        entries = []
        for row in cursor.fetchall():
            entry_id, order_idx, data_json, identity_key = row
            
            # Skip empty list markers
            if order_idx == -1 and data_json == "[]":
                continue
            
            data = json.loads(data_json)
            
            # Get tags for this entry
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
                "tags": tags
            })
        
        return entries
    finally:
        conn.close()


def get_entry(entry_id: int, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Get a single entry by ID.
    
    Args:
        entry_id: The entry ID.
        db_path: Path to the database file. Uses default if None.
        
    Returns:
        Entry record with full data and tags, or None if not found.
    """
    db_path = get_db_path(db_path)
    
    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT e.id, e.person_id, e.section, e.order_idx, e.data_json, e.identity_key, p.slug
               FROM entry e
               JOIN person p ON e.person_id = p.id
               WHERE e.id = ?""",
            (entry_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        entry_id, person_id, section, order_idx, data_json, identity_key, person_slug = row
        data = json.loads(data_json)
        
        # Get tags for this entry
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
            "tags": tags
        }
    finally:
        conn.close()


def create_tag(
    name: str,
    description: Optional[str] = None,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Create a new tag.
    
    Args:
        name: Tag name.
        description: Optional description.
        db_path: Path to the database file. Uses default if None.
        
    Returns:
        Created tag record.
        
    Raises:
        ValidationError: If tag name already exists.
    """
    db_path = get_db_path(db_path)
    
    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")
    
    name = name.strip()
    if not name:
        raise ValidationError("Tag name cannot be empty")
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        
        # Check if tag already exists
        cursor.execute("SELECT id FROM tag WHERE name = ?", (name,))
        if cursor.fetchone():
            raise ValidationError(f"Tag '{name}' already exists")
        
        now = _utcnow()
        cursor.execute(
            "INSERT INTO tag (name, description, created_at) VALUES (?, ?, ?)",
            (name, description, now)
        )
        tag_id = cursor.lastrowid
        conn.commit()
        
        return {
            "id": tag_id,
            "name": name,
            "description": description,
            "created_at": now,
            "usage_count": 0
        }
    finally:
        conn.close()


def update_tag(
    name: str,
    new_name: Optional[str] = None,
    description: Optional[str] = None,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Update a tag.
    
    Args:
        name: Current tag name.
        new_name: New tag name (if renaming).
        description: New description.
        db_path: Path to the database file. Uses default if None.
        
    Returns:
        Updated tag record.
        
    Raises:
        ConfigurationError: If tag not found.
        ValidationError: If new name already exists.
    """
    db_path = get_db_path(db_path)
    
    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        
        # Find existing tag
        cursor.execute("SELECT id, description FROM tag WHERE name = ?", (name,))
        row = cursor.fetchone()
        if not row:
            raise ConfigurationError(f"Tag not found: {name}")
        
        tag_id = row[0]
        current_desc = row[1]
        
        # Check if new name conflicts
        final_name = new_name.strip() if new_name else name
        if final_name != name:
            cursor.execute("SELECT id FROM tag WHERE name = ?", (final_name,))
            if cursor.fetchone():
                raise ValidationError(f"Tag '{final_name}' already exists")
        
        final_desc = description if description is not None else current_desc
        
        cursor.execute(
            "UPDATE tag SET name = ?, description = ? WHERE id = ?",
            (final_name, final_desc, tag_id)
        )
        conn.commit()
        
        # Get usage count
        cursor.execute(
            "SELECT COUNT(*) FROM entry_tag WHERE tag_id = ?",
            (tag_id,)
        )
        usage_count = cursor.fetchone()[0]
        
        return {
            "id": tag_id,
            "name": final_name,
            "description": final_desc,
            "usage_count": usage_count
        }
    finally:
        conn.close()


def delete_tag(name: str, db_path: Optional[Path] = None) -> bool:
    """
    Delete a tag and remove it from all entries.
    
    Args:
        name: Tag name.
        db_path: Path to the database file. Uses default if None.
        
    Returns:
        True if deleted, False if not found.
    """
    db_path = get_db_path(db_path)
    
    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM tag WHERE name = ?", (name,))
        row = cursor.fetchone()
        if not row:
            return False
        
        tag_id = row[0]
        
        # Delete from entry_tag (cascade should handle this but be explicit)
        cursor.execute("DELETE FROM entry_tag WHERE tag_id = ?", (tag_id,))
        cursor.execute("DELETE FROM tag WHERE id = ?", (tag_id,))
        conn.commit()
        
        return True
    finally:
        conn.close()


def update_entry_tags(
    entry_id: int,
    tags: List[str],
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Update tags for an entry and update its data_json type_key field.
    
    This function:
    1. Updates the entry_tag relationships
    2. Updates the type_key field in data_json
    
    Args:
        entry_id: The entry ID.
        tags: List of tag names to assign.
        db_path: Path to the database file. Uses default if None.
        
    Returns:
        Updated entry record.
        
    Raises:
        ConfigurationError: If entry not found.
    """
    db_path = get_db_path(db_path)
    
    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        
        # Verify entry exists and get current data
        cursor.execute(
            "SELECT data_json, section FROM entry WHERE id = ?",
            (entry_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ConfigurationError(f"Entry not found: {entry_id}")
        
        data_json, section = row
        data = json.loads(data_json)
        
        # Clear existing tags for this entry
        cursor.execute("DELETE FROM entry_tag WHERE entry_id = ?", (entry_id,))
        
        # Add new tags
        for tag_name in tags:
            tag_id = _get_or_create_tag(cursor, tag_name)
            cursor.execute(
                "INSERT OR IGNORE INTO entry_tag (entry_id, tag_id) VALUES (?, ?)",
                (entry_id, tag_id)
            )
        
        # Update type_key in data_json
        if tags:
            data["type_key"] = tags
        elif "type_key" in data:
            del data["type_key"]
        
        new_data_json = json.dumps(data, ensure_ascii=False, sort_keys=True)
        cursor.execute(
            "UPDATE entry SET data_json = ? WHERE id = ?",
            (new_data_json, entry_id)
        )
        
        conn.commit()
        
        return {
            "id": entry_id,
            "section": section,
            "data": data,
            "tags": tags
        }
    finally:
        conn.close()


def get_tag_by_name(name: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Get a tag by name.
    
    Args:
        name: Tag name.
        db_path: Path to the database file. Uses default if None.
        
    Returns:
        Tag record or None if not found.
    """
    db_path = get_db_path(db_path)
    
    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT t.id, t.name, t.description, t.created_at,
                      COUNT(et.entry_id) as usage_count
               FROM tag t
               LEFT JOIN entry_tag et ON t.id = et.tag_id
               WHERE t.name = ?
               GROUP BY t.id""",
            (name,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "created_at": row[3],
            "usage_count": row[4]
        }
    finally:
        conn.close()


def list_tags(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    List all tags in the database.
    
    Args:
        db_path: Path to the database file. Uses default if None.
        
    Returns:
        List of tag records.
    """
    db_path = get_db_path(db_path)
    
    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT t.name, t.description, t.created_at,
                      COUNT(et.entry_id) as usage_count
               FROM tag t
               LEFT JOIN entry_tag et ON t.id = et.tag_id
               GROUP BY t.id
               ORDER BY t.name"""
        )
        
        return [
            {
                "name": row[0],
                "description": row[1],
                "created_at": row[2],
                "usage_count": row[3]
            }
            for row in cursor.fetchall()
        ]
    finally:
        conn.close()


def doctor(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Check database health and report any issues.
    
    Performs the following checks:
    - Schema version compatibility
    - Orphaned entries (entries without valid person)
    - Orphaned tags (tags not assigned to any entry)
    - Duplicate tags
    - Missing identity keys
    - Invalid JSON in data_json fields
    
    Args:
        db_path: Path to the database file. Uses default if None.
        
    Returns:
        Dict with health check results.
        
    Raises:
        ConfigurationError: If database doesn't exist.
    """
    db_path = get_db_path(db_path)
    
    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")
    
    logger.info(f"Running health check on: {db_path}")
    
    results: Dict[str, Any] = {
        "database": str(db_path),
        "healthy": True,
        "issues": [],
        "stats": {},
        "checks": {}
    }
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        
        # Check 1: Schema version
        logger.debug("Checking schema version...")
        cursor.execute("SELECT value FROM meta WHERE key = 'schema_version'")
        row = cursor.fetchone()
        if row:
            db_version = int(row[0])
            results["checks"]["schema_version"] = {
                "current": db_version,
                "expected": SCHEMA_VERSION,
                "ok": db_version == SCHEMA_VERSION
            }
            if db_version != SCHEMA_VERSION:
                results["healthy"] = False
                results["issues"].append(
                    f"Schema version mismatch: DB has v{db_version}, expected v{SCHEMA_VERSION}"
                )
        else:
            results["checks"]["schema_version"] = {"ok": False, "error": "No version found"}
            results["healthy"] = False
            results["issues"].append("Schema version not found in meta table")
        
        # Check 2: Basic stats
        logger.debug("Gathering statistics...")
        cursor.execute("SELECT COUNT(*) FROM person")
        results["stats"]["persons"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM entry")
        results["stats"]["entries"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tag")
        results["stats"]["tags"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM entry_tag")
        results["stats"]["tag_assignments"] = cursor.fetchone()[0]
        
        # Check 3: Orphaned entries (entries without valid person)
        logger.debug("Checking for orphaned entries...")
        cursor.execute(
            """SELECT COUNT(*) FROM entry e
               LEFT JOIN person p ON e.person_id = p.id
               WHERE p.id IS NULL"""
        )
        orphaned_entries = cursor.fetchone()[0]
        results["checks"]["orphaned_entries"] = {
            "count": orphaned_entries,
            "ok": orphaned_entries == 0
        }
        if orphaned_entries > 0:
            results["healthy"] = False
            results["issues"].append(f"Found {orphaned_entries} orphaned entries (no valid person)")
        
        # Check 4: Orphaned tags (tags not used by any entry)
        logger.debug("Checking for orphaned tags...")
        cursor.execute(
            """SELECT t.name FROM tag t
               LEFT JOIN entry_tag et ON t.id = et.tag_id
               WHERE et.tag_id IS NULL"""
        )
        orphaned_tags = [row[0] for row in cursor.fetchall()]
        results["checks"]["orphaned_tags"] = {
            "count": len(orphaned_tags),
            "names": orphaned_tags[:MAX_DOCTOR_ERRORS * 2],  # Limit to first few
            "ok": True  # Orphaned tags are not critical
        }
        if orphaned_tags:
            results["issues"].append(
                f"Found {len(orphaned_tags)} unused tags: {', '.join(orphaned_tags[:MAX_DOCTOR_ERRORS])}"
                + ("..." if len(orphaned_tags) > MAX_DOCTOR_ERRORS else "")
            )
        
        # Check 5: Duplicate tags (case-insensitive)
        logger.debug("Checking for duplicate tags...")
        cursor.execute(
            """SELECT LOWER(name), COUNT(*) as cnt
               FROM tag
               GROUP BY LOWER(name)
               HAVING cnt > 1"""
        )
        duplicates = cursor.fetchall()
        results["checks"]["duplicate_tags"] = {
            "count": len(duplicates),
            "duplicates": [{"name": d[0], "count": d[1]} for d in duplicates],
            "ok": len(duplicates) == 0
        }
        if duplicates:
            results["healthy"] = False
            results["issues"].append(
                f"Found {len(duplicates)} duplicate tag names (case-insensitive)"
            )
        
        # Check 6: Missing identity keys
        logger.debug("Checking for missing identity keys...")
        cursor.execute(
            """SELECT COUNT(*) FROM entry
               WHERE identity_key IS NULL OR identity_key = ''"""
        )
        missing_identity = cursor.fetchone()[0]
        results["checks"]["missing_identity_keys"] = {
            "count": missing_identity,
            "ok": True  # Missing identity keys are not critical
        }
        if missing_identity > 0:
            results["issues"].append(
                f"Found {missing_identity} entries without identity keys"
            )
        
        # Check 7: Invalid JSON in data_json
        logger.debug("Checking for invalid JSON...")
        cursor.execute("SELECT id, data_json FROM entry")
        invalid_json_count = 0
        for entry_id, data_json in cursor.fetchall():
            try:
                json.loads(data_json)
            except (json.JSONDecodeError, TypeError):
                invalid_json_count += 1
                if invalid_json_count <= MAX_DOCTOR_ERRORS:
                    results["issues"].append(f"Entry {entry_id} has invalid JSON")
        
        results["checks"]["invalid_json"] = {
            "count": invalid_json_count,
            "ok": invalid_json_count == 0
        }
        if invalid_json_count > 0:
            results["healthy"] = False
        
        # Check 8: Sections per person
        logger.debug("Checking sections distribution...")
        cursor.execute(
            """SELECT p.slug, COUNT(DISTINCT e.section) as sections
               FROM person p
               LEFT JOIN entry e ON p.id = e.person_id
               GROUP BY p.id"""
        )
        results["checks"]["sections_per_person"] = [
            {"slug": row[0], "sections": row[1]}
            for row in cursor.fetchall()
        ]
        
        logger.info(f"Health check complete. Healthy: {results['healthy']}")
        
    finally:
        conn.close()
    
    return results
