"""
Person Entity module for CV Generator.

Provides a first-class Person concept that groups CV language variants together.

Key Concepts:
- PersonEntity: A real person with a stable ID and basic identity information
- CV Variant: A language-specific CV for a person (stored in `person` table as slugs like "ramin_de")
- Grouping: Automatically groups CV variants by normalized firstName + lastName from basics

Grouping Logic:
- Uses normalized (trim, casefold, Unicode NFKC) firstName + lastName to identify same person
- Stores persistent Person ID so future grouping doesn't rely only on names
- If two people share same name (collision), requires manual UI resolution

Data Folder LOCKED:
This module does NOT modify files in data/. All changes are stored in the SQLite database.
"""

import json
import logging
import sqlite3
import unicodedata
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .db import _utcnow, get_db_path
from .errors import ConfigurationError, ValidationError

logger = logging.getLogger(__name__)

# Supported languages for CV variants
SUPPORTED_LANGUAGES = ["en", "de", "fa"]
DEFAULT_LANGUAGE = "en"


# =============================================================================
# NAME NORMALIZATION
# =============================================================================

def normalize_name(name: Optional[str]) -> str:
    """
    Normalize a name for comparison and grouping.

    Performs:
    1. Strip leading/trailing whitespace
    2. Unicode NFKC normalization (decompose and compose)
    3. Case folding (lowercase, but Unicode-aware)
    4. Collapse multiple spaces to single space

    Note on non-Latin scripts:
        casefold() is primarily designed for Latin scripts and has limited effect
        on scripts like Arabic, Hebrew, Chinese, etc. This means names in different
        scripts (e.g., "Ramin Yazdani" vs "رامین یزدانی") will produce different
        name keys and won't auto-group together. This is intentional - manual
        linking is required to associate names across different scripts.

    Args:
        name: The name string to normalize. Can be None.

    Returns:
        Normalized name string. Empty string if name is None or empty.

    Examples:
        >>> normalize_name("  Ramin  ")
        'ramin'
        >>> normalize_name("YAZDANI")
        'yazdani'
        >>> normalize_name("رامین")  # Persian name, unchanged after casefold
        'رامین'
        >>> normalize_name(None)
        ''
    """
    if not name:
        return ""

    # Strip whitespace
    result = name.strip()

    # Unicode NFKC normalization
    result = unicodedata.normalize("NFKC", result)

    # Case fold (Unicode-aware lowercase)
    result = result.casefold()

    # Collapse multiple spaces
    result = " ".join(result.split())

    return result


def compute_name_key(first_name: Optional[str], last_name: Optional[str]) -> str:
    """
    Compute a stable key for grouping persons by name.

    The key is formed by normalizing firstName and lastName and joining with a separator.

    Args:
        first_name: First name (can be None)
        last_name: Last name (can be None)

    Returns:
        Normalized key like "ramin|yazdani". Empty string if both are empty.
    """
    norm_first = normalize_name(first_name)
    norm_last = normalize_name(last_name)

    if not norm_first and not norm_last:
        return ""

    return f"{norm_first}|{norm_last}"


# =============================================================================
# PERSON ENTITY SCHEMA
# =============================================================================

PERSON_ENTITY_SCHEMA_SQL = """
-- Person entity table: represents a real person with stable ID
-- This groups multiple CV language variants (ramin, ramin_de, ramin_fa) under one person
CREATE TABLE IF NOT EXISTS person_entity (
    id TEXT PRIMARY KEY,
    name_key TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    display_name TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Index for name-based lookups and collision detection
CREATE INDEX IF NOT EXISTS idx_person_entity_name_key ON person_entity(name_key);

-- Link table: connects person_entity to cv variants (person table records)
CREATE TABLE IF NOT EXISTS person_entity_variant (
    person_entity_id TEXT NOT NULL,
    person_id INTEGER NOT NULL,
    language TEXT NOT NULL,
    is_primary INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    PRIMARY KEY (person_entity_id, person_id),
    FOREIGN KEY (person_entity_id) REFERENCES person_entity(id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES person(id) ON DELETE CASCADE
);

-- Index for reverse lookup (find person_entity from cv variant)
CREATE INDEX IF NOT EXISTS idx_person_entity_variant_person ON person_entity_variant(person_id);
CREATE INDEX IF NOT EXISTS idx_person_entity_variant_lang ON person_entity_variant(language);

-- Collision table: tracks potential name collisions that need manual resolution
CREATE TABLE IF NOT EXISTS person_name_collision (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_key TEXT NOT NULL,
    person_entity_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    resolved_at TEXT,
    resolved_by TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (person_entity_id) REFERENCES person_entity(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_person_name_collision_name_key ON person_name_collision(name_key);
CREATE INDEX IF NOT EXISTS idx_person_name_collision_status ON person_name_collision(status);
"""


def ensure_person_entity_schema(db_path: Optional[Path] = None) -> None:
    """
    Ensure the person entity schema tables exist in the database.

    Args:
        db_path: Path to the database file. Uses default if None.
    """
    db_path = get_db_path(db_path)

    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.executescript(PERSON_ENTITY_SCHEMA_SQL)
        conn.commit()
        logger.debug("Person entity schema ensured")
    finally:
        conn.close()


def generate_person_entity_id() -> str:
    """Generate a new stable person entity ID."""
    return str(uuid.uuid4())


# =============================================================================
# PERSON ENTITY CRUD
# =============================================================================

def create_person_entity(
    first_name: str,
    last_name: str,
    display_name: Optional[str] = None,
    notes: Optional[str] = None,
    db_path: Optional[Path] = None,
    check_collision: bool = True
) -> Dict[str, Any]:
    """
    Create a new person entity.

    Args:
        first_name: Person's first name (required)
        last_name: Person's last name (required)
        display_name: Optional display name override
        notes: Optional notes about this person
        db_path: Path to database
        check_collision: If True, check for existing persons with same name

    Returns:
        Created person entity record

    Raises:
        ValidationError: If first_name or last_name is empty
        ValidationError: If a person with same name already exists and check_collision is True
    """
    db_path = get_db_path(db_path)
    ensure_person_entity_schema(db_path)

    # Validate inputs
    first_name = first_name.strip() if first_name else ""
    last_name = last_name.strip() if last_name else ""

    if not first_name:
        raise ValidationError("First name is required")
    if not last_name:
        raise ValidationError("Last name is required")

    # Compute name key
    name_key = compute_name_key(first_name, last_name)

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Check for collision
        if check_collision:
            cursor.execute(
                "SELECT id, first_name, last_name FROM person_entity WHERE name_key = ?",
                (name_key,)
            )
            existing = cursor.fetchone()
            if existing:
                raise ValidationError(
                    f"A person with name '{first_name} {last_name}' already exists "
                    f"(ID: {existing[0][:8]}...). Use the existing person or provide a different name."
                )

        # Generate ID and create record
        person_id = generate_person_entity_id()
        now = _utcnow()

        # Use provided display_name or generate from first/last
        if not display_name:
            display_name = f"{first_name} {last_name}".strip()

        cursor.execute(
            """INSERT INTO person_entity
               (id, name_key, first_name, last_name, display_name, notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (person_id, name_key, first_name, last_name, display_name, notes, now, now)
        )

        conn.commit()

        logger.info(f"Created person entity: {display_name} (ID: {person_id[:8]}...)")

        return {
            "id": person_id,
            "name_key": name_key,
            "first_name": first_name,
            "last_name": last_name,
            "display_name": display_name,
            "notes": notes,
            "created_at": now,
            "updated_at": now,
            "variants": {}
        }
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error creating person entity: {e}")
        raise ConfigurationError(f"Failed to create person entity: {e}") from e
    finally:
        conn.close()


def get_person_entity(
    person_entity_id: str,
    db_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """
    Get a person entity by ID.

    Args:
        person_entity_id: Person entity ID
        db_path: Path to database

    Returns:
        Person entity record with variants, or None if not found
    """
    db_path = get_db_path(db_path)
    ensure_person_entity_schema(db_path)

    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute(
            """SELECT id, name_key, first_name, last_name, display_name, notes, created_at, updated_at
               FROM person_entity WHERE id = ?""",
            (person_entity_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        person = {
            "id": row[0],
            "name_key": row[1],
            "first_name": row[2],
            "last_name": row[3],
            "display_name": row[4],
            "notes": row[5],
            "created_at": row[6],
            "updated_at": row[7],
            "variants": {}
        }

        # Get linked variants
        cursor.execute(
            """SELECT pev.language, pev.is_primary, p.id, p.slug, p.display_name,
                      (SELECT COUNT(*) FROM entry WHERE person_id = p.id) as entry_count
               FROM person_entity_variant pev
               JOIN person p ON pev.person_id = p.id
               WHERE pev.person_entity_id = ?
               ORDER BY pev.language""",
            (person_entity_id,)
        )

        for vrow in cursor.fetchall():
            lang, is_primary, pid, slug, disp_name, entry_count = vrow
            person["variants"][lang] = {
                "person_id": pid,
                "slug": slug,
                "display_name": disp_name,
                "entry_count": entry_count,
                "is_primary": bool(is_primary)
            }

        return person
    finally:
        conn.close()


def list_person_entities(
    db_path: Optional[Path] = None,
    search: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List all person entities with their variants.

    Args:
        db_path: Path to database
        search: Optional search string to filter by name

    Returns:
        List of person entity records with variants
    """
    db_path = get_db_path(db_path)
    ensure_person_entity_schema(db_path)

    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        if search:
            search_norm = normalize_name(search)
            cursor.execute(
                """SELECT id, name_key, first_name, last_name, display_name, notes, created_at, updated_at
                   FROM person_entity
                   WHERE name_key LIKE ? OR display_name LIKE ?
                   ORDER BY display_name""",
                (f"%{search_norm}%", f"%{search}%")
            )
        else:
            cursor.execute(
                """SELECT id, name_key, first_name, last_name, display_name, notes, created_at, updated_at
                   FROM person_entity
                   ORDER BY display_name"""
            )

        persons = []
        for row in cursor.fetchall():
            person = {
                "id": row[0],
                "name_key": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "display_name": row[4],
                "notes": row[5],
                "created_at": row[6],
                "updated_at": row[7],
                "variants": {}
            }

            # Get linked variants
            cursor.execute(
                """SELECT pev.language, pev.is_primary, p.id, p.slug, p.display_name,
                          (SELECT COUNT(*) FROM entry WHERE person_id = p.id) as entry_count
                   FROM person_entity_variant pev
                   JOIN person p ON pev.person_id = p.id
                   WHERE pev.person_entity_id = ?
                   ORDER BY pev.language""",
                (row[0],)
            )

            for vrow in cursor.fetchall():
                lang, is_primary, pid, slug, disp_name, entry_count = vrow
                person["variants"][lang] = {
                    "person_id": pid,
                    "slug": slug,
                    "display_name": disp_name,
                    "entry_count": entry_count,
                    "is_primary": bool(is_primary)
                }

            persons.append(person)

        return persons
    finally:
        conn.close()


def get_unlinked_variants(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Get CV variants (person records) that are not linked to any person entity.

    These are "orphan" variants that need manual linking.

    Args:
        db_path: Path to database

    Returns:
        List of unlinked person records with their basics info
    """
    db_path = get_db_path(db_path)
    ensure_person_entity_schema(db_path)

    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Find person records not in person_entity_variant
        cursor.execute(
            """SELECT p.id, p.slug, p.display_name, p.created_at,
                      (SELECT COUNT(*) FROM entry WHERE person_id = p.id) as entry_count
               FROM person p
               LEFT JOIN person_entity_variant pev ON p.id = pev.person_id
               WHERE pev.person_id IS NULL
               ORDER BY p.slug"""
        )

        unlinked = []
        for row in cursor.fetchall():
            pid, slug, disp_name, created_at, entry_count = row

            # Try to get basics info for grouping hints
            cursor.execute(
                """SELECT data_json FROM entry
                   WHERE person_id = ? AND section = 'basics' AND order_idx = 0""",
                (pid,)
            )
            basics_row = cursor.fetchone()
            basics_info = {}
            if basics_row:
                try:
                    basics_data = json.loads(basics_row[0])
                    basics_info = {
                        "first_name": basics_data.get("fname", ""),
                        "last_name": basics_data.get("lname", ""),
                    }
                except (json.JSONDecodeError, TypeError):
                    pass

            # Detect language from slug
            lang = DEFAULT_LANGUAGE
            for supported_lang in SUPPORTED_LANGUAGES:
                if supported_lang != DEFAULT_LANGUAGE and slug.endswith(f"_{supported_lang}"):
                    lang = supported_lang
                    break

            unlinked.append({
                "person_id": pid,
                "slug": slug,
                "display_name": disp_name,
                "created_at": created_at,
                "entry_count": entry_count,
                "language": lang,
                **basics_info
            })

        return unlinked
    finally:
        conn.close()


def link_variant_to_person(
    person_entity_id: str,
    person_id: int,
    language: str,
    is_primary: bool = False,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Link a CV variant (person record) to a person entity.

    Args:
        person_entity_id: Person entity ID
        person_id: Person record ID (the CV variant)
        language: Language code for this variant
        is_primary: Whether this is the primary variant
        db_path: Path to database

    Returns:
        Updated person entity record

    Raises:
        ValidationError: If variant is already linked to another person entity
    """
    db_path = get_db_path(db_path)
    ensure_person_entity_schema(db_path)

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Check if variant already linked to another entity
        cursor.execute(
            """SELECT person_entity_id FROM person_entity_variant WHERE person_id = ?""",
            (person_id,)
        )
        existing = cursor.fetchone()
        if existing and existing[0] != person_entity_id:
            raise ValidationError(
                f"This variant is already linked to another person (ID: {existing[0][:8]}...)"
            )

        # Check if person entity exists
        cursor.execute("SELECT id FROM person_entity WHERE id = ?", (person_entity_id,))
        if not cursor.fetchone():
            raise ConfigurationError(f"Person entity not found: {person_entity_id}")

        # Check if person variant exists
        cursor.execute("SELECT id FROM person WHERE id = ?", (person_id,))
        if not cursor.fetchone():
            raise ConfigurationError(f"Person variant not found: {person_id}")

        now = _utcnow()

        # If is_primary, clear other primaries for this entity
        if is_primary:
            cursor.execute(
                "UPDATE person_entity_variant SET is_primary = 0 WHERE person_entity_id = ?",
                (person_entity_id,)
            )

        # Insert or update link
        cursor.execute(
            """INSERT OR REPLACE INTO person_entity_variant
               (person_entity_id, person_id, language, is_primary, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (person_entity_id, person_id, language, 1 if is_primary else 0, now)
        )

        # Update person entity timestamp
        cursor.execute(
            "UPDATE person_entity SET updated_at = ? WHERE id = ?",
            (now, person_entity_id)
        )

        conn.commit()

        logger.info(f"Linked variant {person_id} ({language}) to person entity {person_entity_id[:8]}...")

        return get_person_entity(person_entity_id, db_path)
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error linking variant: {e}")
        raise ConfigurationError(f"Failed to link variant: {e}") from e
    finally:
        conn.close()


def unlink_variant_from_person(
    person_entity_id: str,
    person_id: int,
    db_path: Optional[Path] = None
) -> bool:
    """
    Unlink a CV variant from a person entity.

    Args:
        person_entity_id: Person entity ID
        person_id: Person record ID (the CV variant)
        db_path: Path to database

    Returns:
        True if unlinked, False if link not found
    """
    db_path = get_db_path(db_path)
    ensure_person_entity_schema(db_path)

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute(
            """DELETE FROM person_entity_variant
               WHERE person_entity_id = ? AND person_id = ?""",
            (person_entity_id, person_id)
        )

        deleted = cursor.rowcount > 0

        if deleted:
            # Update person entity timestamp
            now = _utcnow()
            cursor.execute(
                "UPDATE person_entity SET updated_at = ? WHERE id = ?",
                (now, person_entity_id)
            )

        conn.commit()

        if deleted:
            logger.info(f"Unlinked variant {person_id} from person entity {person_entity_id[:8]}...")

        return deleted
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error unlinking variant: {e}")
        raise ConfigurationError(f"Failed to unlink variant: {e}") from e
    finally:
        conn.close()


# =============================================================================
# AUTO-GROUPING MIGRATION
# =============================================================================

def auto_group_variants(
    db_path: Optional[Path] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Automatically group existing CV variants into person entities based on config.ID.

    This migration function:
    1. Finds all unlinked CV variants
    2. Groups them by config.ID from the config section (primary grouping key)
    3. Falls back to normalized firstName + lastName from basics if config.ID is not available
    4. Creates person entities for each unique group
    5. Links variants to their corresponding person entities
    6. Flags potential collisions for manual review

    The config.ID grouping ensures that multilingual CVs with the same config.ID
    are grouped together regardless of the script used in name fields (e.g., "Ramin"
    in English vs "رامین" in Persian are grouped if they share the same config.ID).

    Args:
        db_path: Path to database
        dry_run: If True, don't actually make changes, just report what would be done

    Returns:
        Migration statistics
    """
    db_path = get_db_path(db_path)
    ensure_person_entity_schema(db_path)

    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")

    stats = {
        "variants_found": 0,
        "persons_created": 0,
        "variants_linked": 0,
        "collisions_detected": 0,
        "groups": [],
        "dry_run": dry_run
    }

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Get all unlinked variants with their basics and config info
        # We join with both basics and config sections to get all needed data
        cursor.execute(
            """SELECT p.id, p.slug, p.display_name, 
                      e_basics.data_json as basics_json,
                      e_config.data_json as config_json
               FROM person p
               LEFT JOIN person_entity_variant pev ON p.id = pev.person_id
               LEFT JOIN entry e_basics ON p.id = e_basics.person_id 
                   AND e_basics.section = 'basics' AND e_basics.order_idx = 0
               LEFT JOIN entry e_config ON p.id = e_config.person_id 
                   AND e_config.section = 'config' AND e_config.order_idx = 0
               WHERE pev.person_id IS NULL
               ORDER BY p.slug"""
        )

        # Group by config.ID (primary) or name_key (fallback)
        groups: Dict[str, List[Dict[str, Any]]] = {}

        for row in cursor.fetchall():
            pid, slug, disp_name, basics_json, config_json = row
            stats["variants_found"] += 1

            # Parse config to get config.ID (primary grouping key)
            config_id = None
            config_lang = None
            if config_json:
                try:
                    config = json.loads(config_json)
                    config_id = config.get("ID")
                    config_lang = config.get("lang")
                except (json.JSONDecodeError, TypeError):
                    pass

            # Parse basics to get name
            first_name = ""
            last_name = ""
            if basics_json:
                try:
                    basics = json.loads(basics_json)
                    first_name = basics.get("fname", "")
                    last_name = basics.get("lname", "")
                except (json.JSONDecodeError, TypeError):
                    pass

            # Use config.ID as the primary grouping key, fall back to name_key
            if config_id:
                group_key = f"config_id:{config_id}"
            else:
                name_key = compute_name_key(first_name, last_name)
                group_key = f"name:{name_key}" if name_key else ""

            # Detect language from config.lang first, then from slug
            lang = config_lang or DEFAULT_LANGUAGE
            if not config_lang:
                for supported_lang in SUPPORTED_LANGUAGES:
                    if supported_lang != DEFAULT_LANGUAGE and slug.endswith(f"_{supported_lang}"):
                        lang = supported_lang
                        break

            variant = {
                "person_id": pid,
                "slug": slug,
                "display_name": disp_name,
                "first_name": first_name,
                "last_name": last_name,
                "language": lang,
                "config_id": config_id
            }

            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(variant)

        # Process each group
        for group_key, variants in groups.items():
            if not group_key:
                # No grouping info - skip for now, these are "Unlinked" variants
                logger.warning(f"Skipping {len(variants)} variants with no grouping info")
                continue

            # Determine the best first_name/last_name for display
            # Prefer the English variant's name, or the first available non-empty name
            first_name = ""
            last_name = ""
            for variant in variants:
                if variant["language"] == DEFAULT_LANGUAGE and (variant["first_name"] or variant["last_name"]):
                    first_name = variant["first_name"]
                    last_name = variant["last_name"]
                    break
            # Fallback: use the first variant with any name
            if not first_name and not last_name:
                for variant in variants:
                    if variant["first_name"] or variant["last_name"]:
                        first_name = variant["first_name"]
                        last_name = variant["last_name"]
                        break

            # Extract config_id if available (for logging/debugging)
            config_id = variants[0].get("config_id")

            group_info = {
                "group_key": group_key,
                "config_id": config_id,
                "first_name": first_name,
                "last_name": last_name,
                "variants": variants
            }
            stats["groups"].append(group_info)

            if dry_run:
                continue

            # Check if person entity already exists with this group_key
            cursor.execute(
                "SELECT id FROM person_entity WHERE name_key = ?",
                (group_key,)
            )
            existing = cursor.fetchone()

            if existing:
                person_entity_id = existing[0]
                stats["collisions_detected"] += 1
                logger.warning(
                    f"Person entity already exists for group '{group_key}', "
                    f"linking variants to existing entity"
                )
            else:
                # Create new person entity
                person_entity_id = generate_person_entity_id()
                now = _utcnow()
                # Create display name: prefer actual names, then convert config_id to readable format
                if first_name or last_name:
                    display_name = f"{first_name} {last_name}".strip()
                elif config_id:
                    # Convert snake_case/dash-case to Title Case (e.g., "ramin_yazdani" -> "Ramin Yazdani")
                    display_name = config_id.replace("_", " ").replace("-", " ").title()
                else:
                    display_name = "Unknown"

                cursor.execute(
                    """INSERT INTO person_entity
                       (id, name_key, first_name, last_name, display_name, notes, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (person_entity_id, group_key, first_name, last_name, display_name, None, now, now)
                )
                stats["persons_created"] += 1

            # Link variants to person entity
            # Primary variant logic: prefer DEFAULT_LANGUAGE (en), else first variant
            now = _utcnow()
            has_set_primary = False
            for variant in variants:
                # Set as primary if it's the default language, or if no primary set yet
                should_be_primary = (
                    variant["language"] == DEFAULT_LANGUAGE or
                    (not has_set_primary and variant == variants[0])
                )
                if should_be_primary:
                    has_set_primary = True

                cursor.execute(
                    """INSERT OR REPLACE INTO person_entity_variant
                       (person_entity_id, person_id, language, is_primary, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (person_entity_id, variant["person_id"], variant["language"],
                     1 if should_be_primary else 0, now)
                )
                stats["variants_linked"] += 1

        if not dry_run:
            conn.commit()

        logger.info(
            f"Auto-grouping complete: {stats['persons_created']} persons created, "
            f"{stats['variants_linked']} variants linked"
        )

        return stats
    except Exception:
        if not dry_run:
            conn.rollback()
        raise
    finally:
        conn.close()


def get_person_entity_by_variant(
    person_id: int,
    db_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """
    Get the person entity that a CV variant belongs to.

    Args:
        person_id: Person record ID (the CV variant)
        db_path: Path to database

    Returns:
        Person entity record, or None if variant is not linked
    """
    db_path = get_db_path(db_path)
    ensure_person_entity_schema(db_path)

    if not db_path.exists():
        raise ConfigurationError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT person_entity_id FROM person_entity_variant WHERE person_id = ?",
            (person_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        return get_person_entity(row[0], db_path)
    finally:
        conn.close()


def update_person_entity(
    person_entity_id: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    display_name: Optional[str] = None,
    notes: Optional[str] = None,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Update a person entity.

    Args:
        person_entity_id: Person entity ID
        first_name: New first name (optional)
        last_name: New last name (optional)
        display_name: New display name (optional)
        notes: New notes (optional)
        db_path: Path to database

    Returns:
        Updated person entity record
    """
    db_path = get_db_path(db_path)
    ensure_person_entity_schema(db_path)

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Get current values
        cursor.execute(
            """SELECT first_name, last_name, display_name, notes
               FROM person_entity WHERE id = ?""",
            (person_entity_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ConfigurationError(f"Person entity not found: {person_entity_id}")

        current_first, current_last, current_display, current_notes = row

        # Apply updates
        new_first = first_name.strip() if first_name else current_first
        new_last = last_name.strip() if last_name else current_last
        new_display = display_name.strip() if display_name else current_display
        new_notes = notes if notes is not None else current_notes

        # Recompute name key if names changed
        new_name_key = compute_name_key(new_first, new_last)

        now = _utcnow()
        cursor.execute(
            """UPDATE person_entity
               SET name_key = ?, first_name = ?, last_name = ?, display_name = ?, notes = ?, updated_at = ?
               WHERE id = ?""",
            (new_name_key, new_first, new_last, new_display, new_notes, now, person_entity_id)
        )

        conn.commit()

        return get_person_entity(person_entity_id, db_path)
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error updating person entity: {e}")
        raise ConfigurationError(f"Failed to update person entity: {e}") from e
    finally:
        conn.close()


def delete_person_entity(
    person_entity_id: str,
    db_path: Optional[Path] = None,
    cascade_variants: bool = False
) -> bool:
    """
    Delete a person entity.

    Args:
        person_entity_id: Person entity ID
        db_path: Path to database
        cascade_variants: If True, also delete the CV variant person records

    Returns:
        True if deleted, False if not found
    """
    db_path = get_db_path(db_path)
    ensure_person_entity_schema(db_path)

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        if cascade_variants:
            # Get linked variant IDs
            cursor.execute(
                "SELECT person_id FROM person_entity_variant WHERE person_entity_id = ?",
                (person_entity_id,)
            )
            variant_ids = [r[0] for r in cursor.fetchall()]

            # Delete entries for these variants
            for vid in variant_ids:
                cursor.execute("DELETE FROM entry WHERE person_id = ?", (vid,))
                cursor.execute("DELETE FROM person WHERE id = ?", (vid,))

        # Delete person entity (cascades to person_entity_variant)
        cursor.execute("DELETE FROM person_entity WHERE id = ?", (person_entity_id,))
        deleted = cursor.rowcount > 0

        conn.commit()

        if deleted:
            logger.info(f"Deleted person entity: {person_entity_id[:8]}...")

        return deleted
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error deleting person entity: {e}")
        raise ConfigurationError(f"Failed to delete person entity: {e}") from e
    finally:
        conn.close()


def create_variant_for_entity(
    person_entity_id: str,
    language: str,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Create a new language variant for an existing person entity.

    This creates a new person record (slug) for the specified language and links
    it to the person entity. Also creates an initial 'basics' entry with the
    person's name from the entity.

    Args:
        person_entity_id: Person entity ID
        language: Language code (en, de, fa)
        db_path: Path to database

    Returns:
        Dict with created variant info

    Raises:
        ValidationError: If language is not supported or variant already exists
        ConfigurationError: If person entity not found
    """
    import re

    db_path = get_db_path(db_path)
    ensure_person_entity_schema(db_path)

    if language not in SUPPORTED_LANGUAGES:
        raise ValidationError(f"Unsupported language: {language}")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Get person entity
        cursor.execute(
            """SELECT id, first_name, last_name, display_name, name_key
               FROM person_entity WHERE id = ?""",
            (person_entity_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ConfigurationError(f"Person entity not found: {person_entity_id}")

        _, first_name, last_name, display_name, name_key = row

        # Check if variant already exists for this language
        cursor.execute(
            """SELECT p.id, p.slug FROM person_entity_variant pev
               JOIN person p ON pev.person_id = p.id
               WHERE pev.person_entity_id = ? AND pev.language = ?""",
            (person_entity_id, language)
        )
        existing = cursor.fetchone()
        if existing:
            raise ValidationError(
                f"A {language.upper()} variant already exists for this person (slug: {existing[1]})"
            )

        # Generate slug for the new variant
        # Use the name_key to create a base slug
        base_slug = name_key.replace("|", "_").replace(" ", "_").lower() if name_key else "new_person"
        # Remove special characters
        base_slug = re.sub(r'[^a-z0-9_]', '', base_slug)

        if language == DEFAULT_LANGUAGE:
            slug = base_slug
        else:
            slug = f"{base_slug}_{language}"

        # Check for slug collision and make unique
        cursor.execute("SELECT id FROM person WHERE slug = ?", (slug,))
        if cursor.fetchone():
            # Add a unique suffix
            slug = f"{slug}_{uuid.uuid4().hex[:6]}"

        now = _utcnow()

        # Create person record
        cursor.execute(
            """INSERT INTO person (slug, display_name, created_at)
               VALUES (?, ?, ?)""",
            (slug, display_name, now)
        )
        person_id = cursor.lastrowid

        # Create initial basics entry with name info
        basics_data = {
            "fname": first_name or "",
            "lname": last_name or ""
        }
        basics_json = json.dumps(basics_data, ensure_ascii=False, sort_keys=True)

        # Construct identity_key with proper null handling
        identity_key = f"basics:{first_name or ''}-{last_name or ''}"

        cursor.execute(
            """INSERT INTO entry (person_id, section, order_idx, data_json, identity_key, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (person_id, "basics", 0, basics_json, identity_key, now)
        )

        # Link variant to person entity
        cursor.execute(
            """INSERT INTO person_entity_variant
               (person_entity_id, person_id, language, is_primary, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (person_entity_id, person_id, language, 0, now)
        )

        # Update person entity timestamp
        cursor.execute(
            "UPDATE person_entity SET updated_at = ? WHERE id = ?",
            (now, person_entity_id)
        )

        conn.commit()

        logger.info(
            f"Created {language.upper()} variant for person entity {person_entity_id[:8]}... "
            f"(slug: {slug}, person_id: {person_id})"
        )

        return {
            "person_id": person_id,
            "slug": slug,
            "language": language,
            "display_name": display_name,
            "person_entity_id": person_entity_id
        }
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error creating variant: {e}")
        raise ConfigurationError(f"Failed to create variant: {e}") from e
    finally:
        conn.close()
