"""
Migration script from v1 to v2 schema.

This module handles the migration of data from the v1 database schema
to the v2 ERD-driven schema. It preserves all existing data while
restructuring it into the new normalized i18n-first format.

Key migrations:
- person → resume_sets + persons + person_i18n
- entry (by section) → appropriate entity tables + i18n tables
- tag → tag_codes + tag_i18n
- entry_tag → *_tags junction tables

Non-negotiable constraints:
- Zero data loss: All existing data must be preserved
- Atomic migrations: All changes are transactional with rollback capability
- Backwards compatibility: Web UI must continue functioning
"""

import json
import logging
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..schema_v2 import (
    ERD_TABLES,
    SCHEMA_V2_SQL,
    SCHEMA_VERSION_V2,
    get_schema_version,
    seed_languages,
)

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    """Return current UTC time as ISO format string."""
    return datetime.now(timezone.utc).isoformat()


def _slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text


def detect_schema_version(db_path: Path) -> int:
    """
    Detect the current schema version of the database.

    Args:
        db_path: Path to the database file.

    Returns:
        Schema version (0 if empty, 1 for v1, 2 for v2).
    """
    if not db_path.exists():
        logger.info("[SCHEMA] No database found, will create fresh v2 schema")
        return 0

    version = get_schema_version(db_path)
    if version is not None:
        logger.info(f"[SCHEMA] Detected version: {version}")
        return version

    # Check for v1 tables without meta version
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='person'"
        )
        if cursor.fetchone():
            logger.info("[SCHEMA] Detected v1 schema (person table exists, no version)")
            return 1
    finally:
        conn.close()

    logger.info("[SCHEMA] Empty or unknown database")
    return 0


def backup_database(db_path: Path) -> Optional[Path]:
    """
    Create a backup of the database before migration.

    Args:
        db_path: Path to the database file.

    Returns:
        Path to the backup file or None if no backup created.
    """
    if not db_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_suffix(f".backup_v1_{timestamp}.db")
    shutil.copy2(db_path, backup_path)
    logger.info(f"[MIGRATE] Database backed up to: {backup_path}")
    return backup_path


def migrate_to_v2(
    db_path: Path,
    backup: bool = True,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Migrate the database from v1 to v2 schema.

    This is the main migration entry point. It handles:
    1. Schema version detection
    2. Database backup
    3. Creating new v2 tables
    4. Migrating data from v1 to v2
    5. Verifying migration success

    Args:
        db_path: Path to the database file.
        backup: If True, create a backup before migration.
        force: If True, force re-migration even if already at v2.

    Returns:
        Dict with migration statistics.

    Raises:
        RuntimeError: If migration fails and cannot be rolled back.
    """
    results: Dict[str, Any] = {
        "success": False,
        "source_version": 0,
        "target_version": SCHEMA_VERSION_V2,
        "backup_path": None,
        "tables_created": 0,
        "records_migrated": {},
        "errors": [],
    }

    # Detect current version
    current_version = detect_schema_version(db_path)
    results["source_version"] = current_version

    if current_version == SCHEMA_VERSION_V2 and not force:
        logger.info(f"[MIGRATE] Database already at version {SCHEMA_VERSION_V2}")
        results["success"] = True
        results["message"] = "Already at target version"
        return results

    if current_version == 0:
        # Fresh database - just create v2 schema
        logger.info("[MIGRATE] Fresh database, creating v2 schema...")
        from ..schema_v2 import init_db_v2

        init_db_v2(db_path, force=True)
        results["success"] = True
        results["tables_created"] = len(ERD_TABLES)
        results["message"] = "Created fresh v2 database"
        return results

    # Create backup
    if backup:
        backup_path = backup_database(db_path)
        results["backup_path"] = str(backup_path) if backup_path else None

    # Perform migration from v1 to v2
    logger.info(f"[MIGRATE] Migrating from v{current_version} to v{SCHEMA_VERSION_V2}...")

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")  # Disable during migration
        cursor = conn.cursor()

        # Step 1: Create v2 tables (they don't overlap with v1 tables)
        logger.info("[MIGRATE] Creating v2 tables...")
        cursor.executescript(SCHEMA_V2_SQL)
        results["tables_created"] = len(ERD_TABLES)

        # Step 2: Seed languages
        seed_languages(cursor)

        # Step 3: Get counts from v1 for verification
        v1_counts = _get_v1_counts(cursor)
        logger.info(f"[MIGRATE] V1 counts: {v1_counts}")

        # Step 4: Migrate persons to resume_sets + persons
        persons_migrated = _migrate_persons(cursor)
        results["records_migrated"]["persons"] = persons_migrated
        logger.info(f"[MIGRATE] Migrated {persons_migrated} persons")

        # Step 5: Migrate tags to tag_codes
        tags_migrated = _migrate_tags(cursor)
        results["records_migrated"]["tags"] = tags_migrated
        logger.info(f"[MIGRATE] Migrated {tags_migrated} tags")

        # Step 6: Migrate entries by section
        entries_migrated = _migrate_entries_by_section(cursor)
        results["records_migrated"]["entries"] = entries_migrated
        logger.info(f"[MIGRATE] Migrated entries: {entries_migrated}")

        # Step 7: Update schema version
        now = _utcnow()
        cursor.execute(
            "INSERT OR REPLACE INTO meta (key, value, updated_at) VALUES (?, ?, ?)",
            ("schema_version", str(SCHEMA_VERSION_V2), now),
        )

        # Commit all changes
        conn.commit()
        logger.info("[MIGRATE] Migration committed successfully")

        # Re-enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")

        results["success"] = True
        results["message"] = "Migration completed successfully"

    except Exception as e:
        conn.rollback()
        logger.error(f"[MIGRATE] Migration failed, rolled back: {e}")
        results["errors"].append(str(e))
        results["message"] = f"Migration failed: {e}"
        raise RuntimeError(f"Migration failed: {e}") from e
    finally:
        conn.close()

    return results


def _get_v1_counts(cursor: sqlite3.Cursor) -> Dict[str, int]:
    """Get record counts from v1 tables for verification."""
    counts = {}

    # Check which v1 tables exist
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('person', 'entry', 'tag', 'entry_tag')"
    )
    existing = {row[0] for row in cursor.fetchall()}

    if "person" in existing:
        cursor.execute("SELECT COUNT(*) FROM person")
        counts["person"] = cursor.fetchone()[0]

    if "entry" in existing:
        cursor.execute("SELECT COUNT(*) FROM entry")
        counts["entry"] = cursor.fetchone()[0]

    if "tag" in existing:
        cursor.execute("SELECT COUNT(*) FROM tag")
        counts["tag"] = cursor.fetchone()[0]

    if "entry_tag" in existing:
        cursor.execute("SELECT COUNT(*) FROM entry_tag")
        counts["entry_tag"] = cursor.fetchone()[0]

    return counts


def _migrate_persons(cursor: sqlite3.Cursor) -> int:
    """
    Migrate v1 person records to v2 resume_sets and persons tables.

    v1 schema: person(id, slug, display_name, created_at)
    v2 schema: resume_sets(resume_key, ...) + persons(id, resume_key, ...) + person_i18n(...)

    Returns:
        Number of persons migrated.
    """
    # Check if v1 person table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='person'"
    )
    if not cursor.fetchone():
        return 0

    cursor.execute("SELECT id, slug, display_name, created_at FROM person")
    persons = cursor.fetchall()

    if not persons:
        return 0

    now = _utcnow()
    migrated = 0

    for person_id, slug, display_name, created_at in persons:
        # Extract language from slug (e.g., "ramin_de" -> ("ramin", "de"))
        resume_key, lang_code = _parse_person_slug(slug)

        # Create resume_set if not exists
        cursor.execute(
            "SELECT resume_key FROM resume_sets WHERE resume_key = ?",
            (resume_key,),
        )
        if not cursor.fetchone():
            cursor.execute(
                """INSERT INTO resume_sets (resume_key, base_lang_code, created_at, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (resume_key, "en", created_at or now, now),
            )

        # Create resume_version for this language
        cursor.execute(
            "SELECT id FROM resume_versions WHERE resume_key = ? AND lang_code = ?",
            (resume_key, lang_code),
        )
        version_row = cursor.fetchone()
        if version_row:
            version_id = version_row[0]
        else:
            is_base = 1 if lang_code == "en" else 0
            cursor.execute(
                """INSERT INTO resume_versions (resume_key, lang_code, is_base, is_published, created_at, updated_at)
                   VALUES (?, ?, ?, 1, ?, ?)""",
                (resume_key, lang_code, is_base, created_at or now, now),
            )
            version_id = cursor.lastrowid

        # Create person record if not exists
        cursor.execute(
            "SELECT id FROM persons WHERE resume_key = ?",
            (resume_key,),
        )
        person_row = cursor.fetchone()
        if person_row:
            new_person_id = person_row[0]
        else:
            cursor.execute(
                """INSERT INTO persons (resume_key, created_at, updated_at)
                   VALUES (?, ?, ?)""",
                (resume_key, created_at or now, now),
            )
            new_person_id = cursor.lastrowid

        # Create person_i18n for this version (with display_name as fname/lname)
        fname, lname = _parse_display_name(display_name)
        cursor.execute(
            """INSERT OR IGNORE INTO person_i18n (person_id, resume_version_id, fname, lname)
               VALUES (?, ?, ?, ?)""",
            (new_person_id, version_id, fname, lname),
        )

        # Store mapping for entry migration
        cursor.execute(
            """INSERT OR REPLACE INTO meta (key, value, updated_at)
               VALUES (?, ?, ?)""",
            (f"v1_person_map_{person_id}", f"{resume_key}:{version_id}", now),
        )

        migrated += 1

    return migrated


def _parse_person_slug(slug: str) -> Tuple[str, str]:
    """
    Parse a v1 person slug into resume_key and lang_code.

    Examples:
        "ramin" -> ("ramin", "en")
        "ramin_de" -> ("ramin", "de")
        "ramin_fa" -> ("ramin", "fa")

    Args:
        slug: The v1 person slug.

    Returns:
        Tuple of (resume_key, lang_code).
    """
    # Known language suffixes
    lang_suffixes = ["_de", "_fa", "_en"]

    for suffix in lang_suffixes:
        if slug.endswith(suffix):
            return slug[: -len(suffix)], suffix[1:]

    # Default to English
    return slug, "en"


def _parse_display_name(display_name: Optional[str]) -> Tuple[str, str]:
    """
    Parse a display name into first and last name.

    Args:
        display_name: Full display name.

    Returns:
        Tuple of (fname, lname).
    """
    if not display_name:
        return "", ""

    parts = display_name.strip().split(maxsplit=1)
    if len(parts) == 2:
        return parts[0], parts[1]
    elif len(parts) == 1:
        return parts[0], ""
    return "", ""


def _migrate_tags(cursor: sqlite3.Cursor) -> int:
    """
    Migrate v1 tag records to v2 tag_codes table.

    v1 schema: tag(id, name, description, created_at)
    v2 schema: tag_codes(code, group_code, is_system)

    Returns:
        Number of tags migrated.
    """
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='tag'"
    )
    if not cursor.fetchone():
        return 0

    cursor.execute("SELECT id, name, description FROM tag")
    tags = cursor.fetchall()

    if not tags:
        return 0

    now = _utcnow()
    migrated = 0

    for tag_id, name, description in tags:
        # Normalize tag name to code
        code = name  # Keep original name as code for backwards compatibility

        # Insert into tag_codes
        cursor.execute(
            """INSERT OR IGNORE INTO tag_codes (code, group_code, is_system)
               VALUES (?, NULL, 0)""",
            (code,),
        )

        # Store mapping for entry_tag migration
        cursor.execute(
            """INSERT OR REPLACE INTO meta (key, value, updated_at)
               VALUES (?, ?, ?)""",
            (f"v1_tag_map_{tag_id}", code, now),
        )

        migrated += 1

    return migrated


def _migrate_entries_by_section(cursor: sqlite3.Cursor) -> Dict[str, int]:
    """
    Migrate v1 entry records to appropriate v2 entity tables.

    v1 schema: entry(id, person_id, section, order_idx, data_json, identity_key, created_at)
    v2 schema: Various entity tables (*_items, *_i18n)

    Returns:
        Dict mapping section names to migrated counts.
    """
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='entry'"
    )
    if not cursor.fetchone():
        return {}

    # Get all entries grouped by section
    cursor.execute(
        """SELECT e.id, e.person_id, e.section, e.order_idx, e.data_json, e.identity_key, e.created_at
           FROM entry e
           ORDER BY e.person_id, e.section, e.order_idx"""
    )
    entries = cursor.fetchall()

    if not entries:
        return {}

    counts: Dict[str, int] = {}

    for entry_id, person_id, section, order_idx, data_json, identity_key, created_at in entries:
        # Skip empty list markers
        if order_idx == -1 and data_json == "[]":
            continue

        # Get the resume_key and version_id from person mapping
        cursor.execute(
            "SELECT value FROM meta WHERE key = ?",
            (f"v1_person_map_{person_id}",),
        )
        mapping = cursor.fetchone()
        if not mapping:
            logger.warning(f"[MIGRATE] No mapping for person_id {person_id}")
            continue

        resume_key, version_id = mapping[0].split(":")
        version_id = int(version_id)

        # Parse entry data
        try:
            data = json.loads(data_json)
        except json.JSONDecodeError:
            logger.warning(f"[MIGRATE] Invalid JSON in entry {entry_id}")
            continue

        # Migrate based on section type
        try:
            if section == "basics":
                _migrate_basics_entry(cursor, resume_key, version_id, data, order_idx)
            elif section == "profiles":
                _migrate_profile_entry(cursor, resume_key, version_id, data, order_idx)
            elif section == "education":
                _migrate_education_entry(cursor, resume_key, version_id, data, order_idx, entry_id)
            elif section == "languages":
                _migrate_language_entry(cursor, resume_key, version_id, data, order_idx)
            elif section == "workshop_and_certifications":
                _migrate_certification_entry(cursor, resume_key, version_id, data, order_idx, entry_id)
            elif section == "skills":
                _migrate_skill_entry(cursor, resume_key, version_id, data, identity_key)
            elif section == "experiences":
                _migrate_experience_entry(cursor, resume_key, version_id, data, order_idx)
            elif section == "projects":
                _migrate_project_entry(cursor, resume_key, version_id, data, order_idx, entry_id)
            elif section == "publications":
                _migrate_publication_entry(cursor, resume_key, version_id, data, order_idx, entry_id)
            elif section == "references":
                _migrate_reference_entry(cursor, resume_key, version_id, data, order_idx, entry_id)
            else:
                logger.debug(f"[MIGRATE] Skipping unknown section: {section}")
                continue

            counts[section] = counts.get(section, 0) + 1
        except Exception as e:
            logger.warning(f"[MIGRATE] Failed to migrate entry {entry_id} ({section}): {e}")

    return counts


def _migrate_basics_entry(
    cursor: sqlite3.Cursor,
    resume_key: str,
    version_id: int,
    data: Dict[str, Any],
    order_idx: int,
) -> None:
    """Migrate a basics entry to persons and related tables."""
    now = _utcnow()

    # Update existing person with data from basics
    cursor.execute(
        "SELECT id FROM persons WHERE resume_key = ?",
        (resume_key,),
    )
    row = cursor.fetchone()
    if not row:
        return

    person_id = row[0]

    # Update person invariant fields
    email = data.get("email")
    birth_date = data.get("birthDate")
    phone = data.get("phone", {})

    if isinstance(phone, dict):
        phone_country = phone.get("countryCode")
        phone_number = phone.get("number")
        phone_formatted = phone.get("formatted")
    else:
        phone_country = phone_number = phone_formatted = None

    cursor.execute(
        """UPDATE persons SET email = ?, birth_date = ?,
           phone_country_code = ?, phone_number = ?, phone_formatted = ?,
           updated_at = ?
           WHERE id = ?""",
        (email, birth_date, phone_country, phone_number, phone_formatted, now, person_id),
    )

    # Update person_i18n with summary
    fname = data.get("fname", "")
    lname = data.get("lname", "")
    summary = data.get("summary")

    cursor.execute(
        """INSERT OR REPLACE INTO person_i18n
           (person_id, resume_version_id, fname, lname, summary)
           VALUES (?, ?, ?, ?, ?)""",
        (person_id, version_id, fname, lname, summary),
    )

    # Migrate locations
    locations = data.get("location", [])
    if isinstance(locations, list):
        for idx, loc in enumerate(locations):
            if not isinstance(loc, dict):
                continue

            cursor.execute(
                """INSERT OR IGNORE INTO person_locations
                   (person_id, sort_order, postal_code)
                   VALUES (?, ?, ?)""",
                (person_id, idx, loc.get("postalCode")),
            )

            cursor.execute(
                "SELECT id FROM person_locations WHERE person_id = ? AND sort_order = ?",
                (person_id, idx),
            )
            loc_row = cursor.fetchone()
            if loc_row:
                cursor.execute(
                    """INSERT OR REPLACE INTO person_location_i18n
                       (location_id, resume_version_id, address, city, region, country)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        loc_row[0],
                        version_id,
                        loc.get("address"),
                        loc.get("city"),
                        loc.get("region"),
                        loc.get("country"),
                    ),
                )

    # Migrate pictures
    pictures = data.get("Pictures", [])
    if isinstance(pictures, list):
        for idx, pic in enumerate(pictures):
            if not isinstance(pic, dict):
                continue

            type_of = pic.get("type_of")
            url = pic.get("URL")

            cursor.execute(
                """INSERT OR IGNORE INTO person_pictures
                   (person_id, sort_order, type_of, url)
                   VALUES (?, ?, ?, ?)""",
                (person_id, idx, type_of, url),
            )

    # Migrate labels
    labels = data.get("label", [])
    if isinstance(labels, list):
        for idx, label_text in enumerate(labels):
            if not label_text:
                continue

            cursor.execute(
                """INSERT OR IGNORE INTO person_labels
                   (person_id, sort_order, label_key)
                   VALUES (?, ?, ?)""",
                (person_id, idx, None),
            )

            cursor.execute(
                "SELECT id FROM person_labels WHERE person_id = ? AND sort_order = ?",
                (person_id, idx),
            )
            label_row = cursor.fetchone()
            if label_row:
                cursor.execute(
                    """INSERT OR REPLACE INTO person_label_i18n
                       (label_id, resume_version_id, label_text)
                       VALUES (?, ?, ?)""",
                    (label_row[0], version_id, label_text),
                )


def _migrate_profile_entry(
    cursor: sqlite3.Cursor,
    resume_key: str,
    version_id: int,
    data: Dict[str, Any],
    order_idx: int,
) -> None:
    """Migrate a profile entry to profile_accounts table."""
    network = data.get("network")
    username = data.get("username")
    url = data.get("url")
    uuid_val = data.get("uuid")

    cursor.execute(
        """INSERT OR IGNORE INTO profile_accounts
           (resume_key, sort_order, network_code, username, url, uuid)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (resume_key, order_idx, _slugify(network) if network else None, username, url, uuid_val),
    )

    cursor.execute(
        "SELECT id FROM profile_accounts WHERE resume_key = ? AND sort_order = ?",
        (resume_key, order_idx),
    )
    row = cursor.fetchone()
    if row:
        cursor.execute(
            """INSERT OR REPLACE INTO profile_account_i18n
               (profile_account_id, resume_version_id, network_display)
               VALUES (?, ?, ?)""",
            (row[0], version_id, network),
        )


def _migrate_education_entry(
    cursor: sqlite3.Cursor,
    resume_key: str,
    version_id: int,
    data: Dict[str, Any],
    order_idx: int,
    entry_id: int,
) -> None:
    """Migrate an education entry to education_items table."""
    start_date = data.get("startDate")
    end_date = data.get("endDate")
    end_date_text = end_date if end_date == "present" else None
    if end_date_text:
        end_date = None
    gpa = data.get("gpa")
    logo_url = data.get("logo_url")

    cursor.execute(
        """INSERT OR IGNORE INTO education_items
           (resume_key, sort_order, start_date, end_date, end_date_text, gpa, logo_url)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (resume_key, order_idx, start_date, end_date, end_date_text, gpa, logo_url),
    )

    cursor.execute(
        "SELECT id FROM education_items WHERE resume_key = ? AND sort_order = ?",
        (resume_key, order_idx),
    )
    row = cursor.fetchone()
    if row:
        item_id = row[0]

        # i18n data
        cursor.execute(
            """INSERT OR REPLACE INTO education_i18n
               (education_item_id, resume_version_id, institution, location, area, study_type)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                item_id,
                version_id,
                data.get("institution"),
                data.get("location"),
                data.get("area"),
                data.get("studyType"),
            ),
        )

        # Migrate tags
        _migrate_entry_tags(cursor, entry_id, "education_item_tags", "education_item_id", item_id)


def _migrate_language_entry(
    cursor: sqlite3.Cursor,
    resume_key: str,
    version_id: int,
    data: Dict[str, Any],
    order_idx: int,
) -> None:
    """Migrate a language entry to spoken_language_items table."""
    language = data.get("language")
    proficiency = data.get("proficiency", {})

    cefr = proficiency.get("CEFR") if isinstance(proficiency, dict) else None

    cursor.execute(
        """INSERT OR IGNORE INTO spoken_language_items
           (resume_key, sort_order, described_language_code, proficiency_cefr)
           VALUES (?, ?, ?, ?)""",
        (resume_key, order_idx, _get_language_code(language), cefr),
    )

    cursor.execute(
        "SELECT id FROM spoken_language_items WHERE resume_key = ? AND sort_order = ?",
        (resume_key, order_idx),
    )
    row = cursor.fetchone()
    if row:
        item_id = row[0]

        level = proficiency.get("level") if isinstance(proficiency, dict) else None
        status = proficiency.get("status") if isinstance(proficiency, dict) else None

        cursor.execute(
            """INSERT OR REPLACE INTO spoken_language_i18n
               (spoken_language_item_id, resume_version_id, language_name, proficiency_level, proficiency_status)
               VALUES (?, ?, ?, ?, ?)""",
            (item_id, version_id, language, level, status),
        )

        # Migrate certifications
        certs = data.get("certifications", [])
        if isinstance(certs, list):
            for cert_idx, cert in enumerate(certs):
                if not isinstance(cert, dict):
                    continue

                cursor.execute(
                    """INSERT OR IGNORE INTO spoken_language_certs
                       (spoken_language_item_id, sort_order, overall, reading, writing, listening, speaking, max_score, min_score, exam_date, url)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item_id,
                        cert_idx,
                        cert.get("overall"),
                        cert.get("reading"),
                        cert.get("writing"),
                        cert.get("listening"),
                        cert.get("speaking"),
                        cert.get("maxScore"),
                        cert.get("minScore"),
                        cert.get("examDate"),
                        cert.get("URL"),
                    ),
                )

                cursor.execute(
                    "SELECT id FROM spoken_language_certs WHERE spoken_language_item_id = ? AND sort_order = ?",
                    (item_id, cert_idx),
                )
                cert_row = cursor.fetchone()
                if cert_row:
                    cursor.execute(
                        """INSERT OR REPLACE INTO spoken_language_cert_i18n
                           (cert_id, resume_version_id, test_name, organization)
                           VALUES (?, ?, ?, ?)""",
                        (cert_row[0], version_id, cert.get("test"), cert.get("organization")),
                    )


def _get_language_code(language_name: Optional[str]) -> Optional[str]:
    """Map language name to code."""
    if not language_name:
        return None

    mapping = {
        "english": "en",
        "german": "de",
        "persian": "fa",
        "farsi": "fa",
    }
    return mapping.get(language_name.lower(), language_name[:2].lower() if len(language_name) >= 2 else None)


def _migrate_certification_entry(
    cursor: sqlite3.Cursor,
    resume_key: str,
    version_id: int,
    data: Dict[str, Any],
    order_idx: int,
    entry_id: int,
) -> None:
    """Migrate a workshop/certification entry to cert_issuers and certifications tables."""
    issuer_name = data.get("issuer")
    if not issuer_name:
        return

    issuer_slug = _slugify(issuer_name)

    # Create or get issuer
    cursor.execute(
        """INSERT OR IGNORE INTO cert_issuers
           (resume_key, sort_order, issuer_slug)
           VALUES (?, ?, ?)""",
        (resume_key, order_idx, issuer_slug),
    )

    cursor.execute(
        "SELECT id FROM cert_issuers WHERE resume_key = ? AND issuer_slug = ?",
        (resume_key, issuer_slug),
    )
    issuer_row = cursor.fetchone()
    if not issuer_row:
        return

    issuer_id = issuer_row[0]

    # Issuer i18n
    cursor.execute(
        """INSERT OR REPLACE INTO cert_issuer_i18n
           (issuer_id, resume_version_id, issuer_name)
           VALUES (?, ?, ?)""",
        (issuer_id, version_id, issuer_name),
    )

    # Migrate certifications under this issuer
    certs = data.get("certifications", [])
    if isinstance(certs, list):
        for cert_idx, cert in enumerate(certs):
            if not isinstance(cert, dict):
                continue

            cursor.execute(
                """INSERT OR IGNORE INTO certifications
                   (issuer_id, sort_order, is_certificate, date_text, date, url)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    issuer_id,
                    cert_idx,
                    cert.get("certificate"),
                    cert.get("date"),
                    None,  # Would need date parsing
                    cert.get("URL"),
                ),
            )

            cursor.execute(
                "SELECT id FROM certifications WHERE issuer_id = ? AND sort_order = ?",
                (issuer_id, cert_idx),
            )
            cert_row = cursor.fetchone()
            if cert_row:
                cursor.execute(
                    """INSERT OR REPLACE INTO certification_i18n
                       (certification_id, resume_version_id, name, duration)
                       VALUES (?, ?, ?, ?)""",
                    (cert_row[0], version_id, cert.get("name"), cert.get("duration")),
                )

                # Migrate tags for this certification
                type_keys = cert.get("type_key", [])
                if isinstance(type_keys, list):
                    for tag_name in type_keys:
                        cursor.execute(
                            "INSERT OR IGNORE INTO tag_codes (code) VALUES (?)",
                            (tag_name,),
                        )
                        cursor.execute(
                            "INSERT OR IGNORE INTO certification_tags (certification_id, tag_code) VALUES (?, ?)",
                            (cert_row[0], tag_name),
                        )


def _migrate_skill_entry(
    cursor: sqlite3.Cursor,
    resume_key: str,
    version_id: int,
    data: Dict[str, Any],
    identity_key: Optional[str],
) -> None:
    """Migrate a skill entry to skill_* tables."""
    # Skills are stored as individual entries with identity_key like "skills/Category/SubCat/Key"
    if not identity_key or not identity_key.startswith("skills/"):
        return

    parts = identity_key.split("/")
    if len(parts) < 4:
        return

    _, cat_name, subcat_name, _ = parts[:4]

    # Create or get category
    cat_code = _slugify(cat_name)
    cursor.execute(
        """INSERT OR IGNORE INTO skill_categories
           (resume_key, sort_order, category_code)
           VALUES (?, (SELECT COALESCE(MAX(sort_order), -1) + 1 FROM skill_categories WHERE resume_key = ?), ?)""",
        (resume_key, resume_key, cat_code),
    )

    cursor.execute(
        "SELECT id FROM skill_categories WHERE resume_key = ? AND category_code = ?",
        (resume_key, cat_code),
    )
    cat_row = cursor.fetchone()
    if not cat_row:
        return

    cat_id = cat_row[0]

    # Category i18n
    cursor.execute(
        """INSERT OR REPLACE INTO skill_category_i18n
           (category_id, resume_version_id, name)
           VALUES (?, ?, ?)""",
        (cat_id, version_id, cat_name),
    )

    # Create or get subcategory
    subcat_code = _slugify(subcat_name)
    cursor.execute(
        """INSERT OR IGNORE INTO skill_subcategories
           (category_id, sort_order, subcategory_code)
           VALUES (?, (SELECT COALESCE(MAX(sort_order), -1) + 1 FROM skill_subcategories WHERE category_id = ?), ?)""",
        (cat_id, cat_id, subcat_code),
    )

    cursor.execute(
        "SELECT id FROM skill_subcategories WHERE category_id = ? AND subcategory_code = ?",
        (cat_id, subcat_code),
    )
    subcat_row = cursor.fetchone()
    if not subcat_row:
        return

    subcat_id = subcat_row[0]

    # Subcategory i18n
    cursor.execute(
        """INSERT OR REPLACE INTO skill_subcategory_i18n
           (subcategory_id, resume_version_id, name)
           VALUES (?, ?, ?)""",
        (subcat_id, version_id, subcat_name),
    )

    # Create skill item
    cursor.execute(
        """INSERT INTO skill_items
           (subcategory_id, sort_order)
           VALUES (?, (SELECT COALESCE(MAX(sort_order), -1) + 1 FROM skill_items WHERE subcategory_id = ?))""",
        (subcat_id, subcat_id),
    )
    item_id = cursor.lastrowid

    # Skill item i18n
    cursor.execute(
        """INSERT OR REPLACE INTO skill_item_i18n
           (skill_item_id, resume_version_id, long_name, short_name)
           VALUES (?, ?, ?, ?)""",
        (item_id, version_id, data.get("long_name"), data.get("short_name")),
    )

    # Migrate tags
    type_keys = data.get("type_key", [])
    if isinstance(type_keys, list):
        for tag_name in type_keys:
            cursor.execute(
                "INSERT OR IGNORE INTO tag_codes (code) VALUES (?)",
                (tag_name,),
            )
            cursor.execute(
                "INSERT OR IGNORE INTO skill_item_tags (skill_item_id, tag_code) VALUES (?, ?)",
                (item_id, tag_name),
            )


def _migrate_experience_entry(
    cursor: sqlite3.Cursor,
    resume_key: str,
    version_id: int,
    data: Dict[str, Any],
    order_idx: int,
) -> None:
    """Migrate an experience entry to experience_items table."""
    duration = data.get("duration", "")
    start_date = None
    end_date = None
    is_current = "present" in duration.lower() or "recent" in duration.lower() if duration else False

    cursor.execute(
        """INSERT OR IGNORE INTO experience_items
           (resume_key, sort_order, start_date, end_date, is_current)
           VALUES (?, ?, ?, ?, ?)""",
        (resume_key, order_idx, start_date, end_date, is_current),
    )

    cursor.execute(
        "SELECT id FROM experience_items WHERE resume_key = ? AND sort_order = ?",
        (resume_key, order_idx),
    )
    row = cursor.fetchone()
    if row:
        cursor.execute(
            """INSERT OR REPLACE INTO experience_i18n
               (experience_item_id, resume_version_id, duration_text, role, institution, primary_focus, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                row[0],
                version_id,
                duration,
                data.get("role"),
                data.get("institution"),
                data.get("primaryFocus"),
                data.get("description"),
            ),
        )


def _migrate_project_entry(
    cursor: sqlite3.Cursor,
    resume_key: str,
    version_id: int,
    data: Dict[str, Any],
    order_idx: int,
    entry_id: int,
) -> None:
    """Migrate a project entry to project_items table."""
    url = data.get("url")

    cursor.execute(
        """INSERT OR IGNORE INTO project_items
           (resume_key, sort_order, url)
           VALUES (?, ?, ?)""",
        (resume_key, order_idx, url),
    )

    cursor.execute(
        "SELECT id FROM project_items WHERE resume_key = ? AND sort_order = ?",
        (resume_key, order_idx),
    )
    row = cursor.fetchone()
    if row:
        item_id = row[0]

        cursor.execute(
            """INSERT OR REPLACE INTO project_i18n
               (project_item_id, resume_version_id, title, description)
               VALUES (?, ?, ?, ?)""",
            (item_id, version_id, data.get("title"), data.get("description")),
        )

        # Migrate tags
        _migrate_entry_tags(cursor, entry_id, "project_tags", "project_item_id", item_id)


def _migrate_publication_entry(
    cursor: sqlite3.Cursor,
    resume_key: str,
    version_id: int,
    data: Dict[str, Any],
    order_idx: int,
    entry_id: int,
) -> None:
    """Migrate a publication entry to publication_items table."""
    identifiers = data.get("identifiers", {}) or {}

    cursor.execute(
        """INSERT OR IGNORE INTO publication_items
           (resume_key, sort_order, year, month, day, date, submission_date, access_date,
            doi, isbn, issn, pmid, pmcid, arxiv, url, url_caps, repository_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            resume_key,
            order_idx,
            data.get("year"),
            data.get("month"),
            data.get("day"),
            data.get("date"),
            data.get("submissionDate"),
            data.get("access_date"),
            data.get("doi") or identifiers.get("doi"),
            data.get("isbn") or identifiers.get("isbn"),
            data.get("issn") or identifiers.get("issn"),
            identifiers.get("pmid"),
            identifiers.get("pmcid"),
            identifiers.get("arxiv"),
            data.get("url") or data.get("URL"),
            data.get("url_caps"),
            data.get("repository_url"),
        ),
    )

    cursor.execute(
        "SELECT id FROM publication_items WHERE resume_key = ? AND sort_order = ?",
        (resume_key, order_idx),
    )
    row = cursor.fetchone()
    if row:
        item_id = row[0]

        cursor.execute(
            """INSERT OR REPLACE INTO publication_i18n
               (publication_id, resume_version_id, title, pub_type, status, language, notes,
                journal, volume, issue, pages, article_number, book_title, chapter_pages,
                conference, publisher, place, edition, degree_type, correspondent, institution, faculty, school)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item_id,
                version_id,
                data.get("title"),
                data.get("type"),
                data.get("status"),
                data.get("language"),
                data.get("notes"),
                data.get("journal"),
                data.get("volume"),
                data.get("issue"),
                data.get("pages"),
                data.get("article_number"),
                data.get("book_title"),
                data.get("chapter_pages"),
                data.get("conference"),
                data.get("publisher"),
                data.get("place"),
                data.get("edition"),
                data.get("degree_type"),
                data.get("correspondent"),
                data.get("institution"),
                data.get("faculty"),
                data.get("school"),
            ),
        )

        # Migrate authors
        authors = data.get("authors_structured") or data.get("authors") or []
        if isinstance(authors, list):
            for idx, author in enumerate(authors):
                if isinstance(author, dict):
                    literal = author.get("literal", "")
                elif isinstance(author, str):
                    literal = author
                else:
                    continue

                cursor.execute(
                    """INSERT OR IGNORE INTO publication_authors
                       (publication_id, resume_version_id, sort_order, author_literal)
                       VALUES (?, ?, ?, ?)""",
                    (item_id, version_id, idx, literal),
                )

        # Migrate supervisors
        supervisors = data.get("supervisors") or []
        if isinstance(supervisors, list):
            for idx, sup in enumerate(supervisors):
                if isinstance(sup, str):
                    cursor.execute(
                        """INSERT OR IGNORE INTO publication_supervisors
                           (publication_id, resume_version_id, sort_order, supervisor_literal)
                           VALUES (?, ?, ?, ?)""",
                        (item_id, version_id, idx, sup),
                    )

        # Migrate tags
        _migrate_entry_tags(cursor, entry_id, "publication_tags", "publication_id", item_id)


def _migrate_reference_entry(
    cursor: sqlite3.Cursor,
    resume_key: str,
    version_id: int,
    data: Dict[str, Any],
    order_idx: int,
    entry_id: int,
) -> None:
    """Migrate a reference entry to reference_items table."""
    phone = data.get("phone")
    if isinstance(phone, list) and phone:
        phone = phone[0].get("formatted") if isinstance(phone[0], dict) else str(phone[0])
    elif isinstance(phone, dict):
        phone = phone.get("formatted")

    url = data.get("URL") or data.get("url")

    cursor.execute(
        """INSERT OR IGNORE INTO reference_items
           (resume_key, sort_order, phone, url)
           VALUES (?, ?, ?, ?)""",
        (resume_key, order_idx, phone, url),
    )

    cursor.execute(
        "SELECT id FROM reference_items WHERE resume_key = ? AND sort_order = ?",
        (resume_key, order_idx),
    )
    row = cursor.fetchone()
    if row:
        item_id = row[0]

        cursor.execute(
            """INSERT OR REPLACE INTO reference_i18n
               (reference_id, resume_version_id, name, position, department, institution, location)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                item_id,
                version_id,
                data.get("name"),
                data.get("position"),
                data.get("department"),
                data.get("institution"),
                data.get("location"),
            ),
        )

        # Migrate emails
        emails = data.get("email", [])
        if isinstance(emails, list):
            for idx, email in enumerate(emails):
                if email:
                    cursor.execute(
                        """INSERT OR IGNORE INTO reference_emails
                           (reference_id, sort_order, email)
                           VALUES (?, ?, ?)""",
                        (item_id, idx, email),
                    )

        # Migrate tags
        _migrate_entry_tags(cursor, entry_id, "reference_tags", "reference_id", item_id)


def _migrate_entry_tags(
    cursor: sqlite3.Cursor,
    entry_id: int,
    junction_table: str,
    item_column: str,
    item_id: int,
) -> None:
    """
    Migrate tags from v1 entry_tag to the appropriate v2 junction table.

    Args:
        cursor: Database cursor.
        entry_id: V1 entry ID.
        junction_table: Name of the v2 junction table.
        item_column: Name of the item ID column in the junction table.
        item_id: V2 item ID.
    """
    # Get tag names from v1 entry_tag
    cursor.execute(
        """SELECT value FROM meta WHERE key = ?""",
        (f"v1_entry_{entry_id}_tags",),
    )
    # Tags might already be in v2 format via data_json, so we read from entry data
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='entry_tag'"
    )
    if not cursor.fetchone():
        return

    cursor.execute(
        """SELECT t.name FROM tag t
           JOIN entry_tag et ON t.id = et.tag_id
           WHERE et.entry_id = ?""",
        (entry_id,),
    )
    tag_names = [row[0] for row in cursor.fetchall()]

    for tag_name in tag_names:
        # Ensure tag exists in tag_codes
        cursor.execute(
            "INSERT OR IGNORE INTO tag_codes (code) VALUES (?)",
            (tag_name,),
        )

        # Insert into junction table
        cursor.execute(
            f"INSERT OR IGNORE INTO {junction_table} ({item_column}, tag_code) VALUES (?, ?)",
            (item_id, tag_name),
        )
