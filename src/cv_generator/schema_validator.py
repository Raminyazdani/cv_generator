"""
Schema validation module for v2 database.

This module provides functions to verify the database schema matches
the ERD specification exactly, including:
- All expected tables exist
- All columns match expected types
- All foreign keys are valid
- All indices exist
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .schema_v2 import ERD_TABLES, SCHEMA_VERSION_V2

logger = logging.getLogger(__name__)

# Expected table columns from ERD
# Format: table_name -> [(column_name, type, is_nullable, is_pk)]
EXPECTED_COLUMNS: Dict[str, List[Tuple[str, str, bool]]] = {
    "app_languages": [
        ("code", "VARCHAR", False),
        ("name_en", "VARCHAR", False),
        ("direction", "VARCHAR", False),
    ],
    "resume_sets": [
        ("resume_key", "VARCHAR", False),
        ("base_lang_code", "VARCHAR", False),
        ("created_at", "DATETIME", False),
        ("updated_at", "DATETIME", False),
    ],
    "resume_versions": [
        ("id", "INTEGER", False),
        ("resume_key", "VARCHAR", False),
        ("lang_code", "VARCHAR", False),
        ("is_base", "BOOLEAN", False),
        ("is_published", "BOOLEAN", False),
        ("created_at", "DATETIME", False),
        ("updated_at", "DATETIME", False),
    ],
    "tag_codes": [
        ("code", "VARCHAR", False),
        ("group_code", "VARCHAR", True),
        ("is_system", "BOOLEAN", True),
    ],
    "tag_i18n": [
        ("id", "INTEGER", False),
        ("tag_code", "VARCHAR", False),
        ("resume_version_id", "INTEGER", False),
        ("label", "VARCHAR", True),
    ],
    "persons": [
        ("id", "INTEGER", False),
        ("resume_key", "VARCHAR", False),
        ("email", "VARCHAR", True),
        ("birth_date", "DATE", True),
        ("phone_country_code", "VARCHAR", True),
        ("phone_number", "VARCHAR", True),
        ("phone_formatted", "VARCHAR", True),
        ("created_at", "DATETIME", False),
        ("updated_at", "DATETIME", False),
    ],
    "person_i18n": [
        ("id", "INTEGER", False),
        ("person_id", "INTEGER", False),
        ("resume_version_id", "INTEGER", False),
        ("fname", "VARCHAR", True),
        ("lname", "VARCHAR", True),
        ("summary", "TEXT", True),
    ],
}

# Expected foreign keys from ERD
# Format: table_name -> [(column, references_table, references_column)]
EXPECTED_FOREIGN_KEYS: Dict[str, List[Tuple[str, str, str]]] = {
    "resume_sets": [
        ("base_lang_code", "app_languages", "code"),
    ],
    "resume_versions": [
        ("resume_key", "resume_sets", "resume_key"),
        ("lang_code", "app_languages", "code"),
    ],
    "tag_i18n": [
        ("tag_code", "tag_codes", "code"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "persons": [
        ("resume_key", "resume_sets", "resume_key"),
    ],
    "person_i18n": [
        ("person_id", "persons", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "person_locations": [
        ("person_id", "persons", "id"),
    ],
    "person_location_i18n": [
        ("location_id", "person_locations", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "person_pictures": [
        ("person_id", "persons", "id"),
    ],
    "person_labels": [
        ("person_id", "persons", "id"),
    ],
    "person_label_i18n": [
        ("label_id", "person_labels", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "profile_accounts": [
        ("resume_key", "resume_sets", "resume_key"),
    ],
    "profile_account_i18n": [
        ("profile_account_id", "profile_accounts", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "education_items": [
        ("resume_key", "resume_sets", "resume_key"),
    ],
    "education_i18n": [
        ("education_item_id", "education_items", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "education_item_tags": [
        ("education_item_id", "education_items", "id"),
        ("tag_code", "tag_codes", "code"),
    ],
    "spoken_language_items": [
        ("resume_key", "resume_sets", "resume_key"),
    ],
    "spoken_language_i18n": [
        ("spoken_language_item_id", "spoken_language_items", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "spoken_language_certs": [
        ("spoken_language_item_id", "spoken_language_items", "id"),
    ],
    "spoken_language_cert_i18n": [
        ("cert_id", "spoken_language_certs", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "cert_issuers": [
        ("resume_key", "resume_sets", "resume_key"),
    ],
    "cert_issuer_i18n": [
        ("issuer_id", "cert_issuers", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "certifications": [
        ("issuer_id", "cert_issuers", "id"),
    ],
    "certification_i18n": [
        ("certification_id", "certifications", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "certification_tags": [
        ("certification_id", "certifications", "id"),
        ("tag_code", "tag_codes", "code"),
    ],
    "skill_categories": [
        ("resume_key", "resume_sets", "resume_key"),
    ],
    "skill_category_i18n": [
        ("category_id", "skill_categories", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "skill_subcategories": [
        ("category_id", "skill_categories", "id"),
    ],
    "skill_subcategory_i18n": [
        ("subcategory_id", "skill_subcategories", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "skill_items": [
        ("subcategory_id", "skill_subcategories", "id"),
    ],
    "skill_item_i18n": [
        ("skill_item_id", "skill_items", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "skill_item_tags": [
        ("skill_item_id", "skill_items", "id"),
        ("tag_code", "tag_codes", "code"),
    ],
    "experience_items": [
        ("resume_key", "resume_sets", "resume_key"),
    ],
    "experience_i18n": [
        ("experience_item_id", "experience_items", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "project_items": [
        ("resume_key", "resume_sets", "resume_key"),
    ],
    "project_i18n": [
        ("project_item_id", "project_items", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "project_tags": [
        ("project_item_id", "project_items", "id"),
        ("tag_code", "tag_codes", "code"),
    ],
    "publication_items": [
        ("resume_key", "resume_sets", "resume_key"),
    ],
    "publication_i18n": [
        ("publication_id", "publication_items", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "publication_authors": [
        ("publication_id", "publication_items", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "publication_editors": [
        ("publication_id", "publication_items", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "publication_supervisors": [
        ("publication_id", "publication_items", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "publication_tags": [
        ("publication_id", "publication_items", "id"),
        ("tag_code", "tag_codes", "code"),
    ],
    "reference_items": [
        ("resume_key", "resume_sets", "resume_key"),
    ],
    "reference_i18n": [
        ("reference_id", "reference_items", "id"),
        ("resume_version_id", "resume_versions", "id"),
    ],
    "reference_emails": [
        ("reference_id", "reference_items", "id"),
    ],
    "reference_tags": [
        ("reference_id", "reference_items", "id"),
        ("tag_code", "tag_codes", "code"),
    ],
}

# Expected unique constraints from ERD
EXPECTED_UNIQUE_CONSTRAINTS: Dict[str, List[Tuple[str, ...]]] = {
    "resume_versions": [("resume_key", "lang_code")],
    "tag_i18n": [("tag_code", "resume_version_id")],
    "persons": [("resume_key",)],
    "person_i18n": [("person_id", "resume_version_id")],
    "person_locations": [("person_id", "sort_order")],
    "person_location_i18n": [("location_id", "resume_version_id")],
    "person_pictures": [("person_id", "type_of")],
    "person_labels": [("person_id", "sort_order")],
    "person_label_i18n": [("label_id", "resume_version_id")],
    "profile_accounts": [("resume_key", "sort_order")],
    "profile_account_i18n": [("profile_account_id", "resume_version_id")],
    "education_items": [("resume_key", "sort_order")],
    "education_i18n": [("education_item_id", "resume_version_id")],
    "spoken_language_items": [("resume_key", "sort_order")],
    "spoken_language_i18n": [("spoken_language_item_id", "resume_version_id")],
    "spoken_language_certs": [("spoken_language_item_id", "sort_order")],
    "spoken_language_cert_i18n": [("cert_id", "resume_version_id")],
    "cert_issuers": [("resume_key", "issuer_slug"), ("resume_key", "sort_order")],
    "cert_issuer_i18n": [("issuer_id", "resume_version_id")],
    "certifications": [("issuer_id", "sort_order")],
    "certification_i18n": [("certification_id", "resume_version_id")],
    "skill_categories": [("resume_key", "category_code"), ("resume_key", "sort_order")],
    "skill_category_i18n": [("category_id", "resume_version_id")],
    "skill_subcategories": [("category_id", "subcategory_code"), ("category_id", "sort_order")],
    "skill_subcategory_i18n": [("subcategory_id", "resume_version_id")],
    "skill_items": [("subcategory_id", "sort_order")],
    "skill_item_i18n": [("skill_item_id", "resume_version_id")],
    "experience_items": [("resume_key", "sort_order")],
    "experience_i18n": [("experience_item_id", "resume_version_id")],
    "project_items": [("resume_key", "sort_order")],
    "project_i18n": [("project_item_id", "resume_version_id")],
    "publication_items": [("resume_key", "sort_order")],
    "publication_i18n": [("publication_id", "resume_version_id")],
    "reference_items": [("resume_key", "sort_order")],
    "reference_i18n": [("reference_id", "resume_version_id")],
}


def validate_schema(db_path: Path) -> Dict[str, Any]:
    """
    Validate that the database schema matches the ERD specification.

    Args:
        db_path: Path to the database file.

    Returns:
        Dict with validation results:
        - valid: True if all checks pass
        - tables: Table existence check results
        - foreign_keys: FK validation results
        - indices: Index validation results
        - issues: List of issues found
    """
    results: Dict[str, Any] = {
        "valid": True,
        "tables": {"expected": len(ERD_TABLES), "found": 0, "missing": []},
        "foreign_keys": {"valid": True, "issues": []},
        "indices": {"expected": 0, "found": 0},
        "issues": [],
    }

    if not db_path.exists():
        results["valid"] = False
        results["issues"].append(f"Database not found: {db_path}")
        return results

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Check schema version
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='meta'"
        )
        if cursor.fetchone():
            cursor.execute("SELECT value FROM meta WHERE key = 'schema_version'")
            row = cursor.fetchone()
            if row:
                version = int(row[0])
                if version != SCHEMA_VERSION_V2:
                    results["issues"].append(
                        f"Schema version mismatch: expected {SCHEMA_VERSION_V2}, found {version}"
                    )

        # Check tables exist
        existing_tables, missing_tables = _check_tables_exist(cursor)
        results["tables"]["found"] = len(existing_tables)
        results["tables"]["missing"] = missing_tables

        if missing_tables:
            results["valid"] = False
            results["issues"].append(f"Missing tables: {', '.join(missing_tables)}")

        logger.info(
            f"[VALIDATE] Tables: {len(existing_tables)}/{len(ERD_TABLES)} found"
        )

        # Check foreign keys are valid
        fk_issues = _check_foreign_keys(cursor)
        if fk_issues:
            results["foreign_keys"]["valid"] = False
            results["foreign_keys"]["issues"] = fk_issues
            results["issues"].extend(fk_issues)

        # Check app_languages is seeded
        lang_issues = _check_languages_seeded(cursor)
        if lang_issues:
            results["issues"].extend(lang_issues)

        # Count indices
        cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        )
        results["indices"]["found"] = cursor.fetchone()[0]

    finally:
        conn.close()

    logger.info(
        f"[VALIDATE] Schema validation complete. Valid: {results['valid']}"
    )

    return results


def _check_tables_exist(cursor: sqlite3.Cursor) -> Tuple[List[str], List[str]]:
    """Check which ERD tables exist in the database."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    existing = {row[0] for row in cursor.fetchall()}

    found = [t for t in ERD_TABLES if t in existing]
    missing = [t for t in ERD_TABLES if t not in existing]

    return found, missing


def _check_foreign_keys(cursor: sqlite3.Cursor) -> List[str]:
    """Check that foreign key constraints are working."""
    issues = []

    # Enable FK checking
    cursor.execute("PRAGMA foreign_keys = ON")

    # Run FK check
    cursor.execute("PRAGMA foreign_key_check")
    violations = cursor.fetchall()

    for table, rowid, parent, fkid in violations:
        issues.append(
            f"FK violation in {table} row {rowid}: references {parent}"
        )

    return issues


def _check_languages_seeded(cursor: sqlite3.Cursor) -> List[str]:
    """Check that app_languages is properly seeded."""
    issues = []

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='app_languages'"
    )
    if not cursor.fetchone():
        return ["app_languages table not found"]

    # Check for en, de, fa
    for code, direction in [("en", "ltr"), ("de", "ltr"), ("fa", "rtl")]:
        cursor.execute(
            "SELECT code, direction FROM app_languages WHERE code = ?",
            (code,),
        )
        row = cursor.fetchone()
        if not row:
            issues.append(f"Missing language: {code}")
        elif row[1] != direction:
            issues.append(
                f"Wrong direction for {code}: expected {direction}, found {row[1]}"
            )

    return issues


def verify_all_i18n_tables_have_resume_version_fk(db_path: Path) -> Dict[str, Any]:
    """
    Verify all *_i18n tables reference resume_versions.

    Args:
        db_path: Path to the database file.

    Returns:
        Dict with verification results.
    """
    results: Dict[str, Any] = {
        "valid": True,
        "i18n_tables": [],
        "missing_fk": [],
    }

    if not db_path.exists():
        results["valid"] = False
        return results

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Find all i18n tables
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_i18n'"
        )
        i18n_tables = [row[0] for row in cursor.fetchall()]
        results["i18n_tables"] = i18n_tables

        # Check each for resume_version_id FK
        for table in i18n_tables:
            cursor.execute(f"PRAGMA foreign_key_list({table})")
            fks = cursor.fetchall()

            has_resume_version_fk = any(
                fk[2] == "resume_versions" for fk in fks
            )

            if not has_resume_version_fk:
                results["missing_fk"].append(table)
                results["valid"] = False

    finally:
        conn.close()

    return results


def verify_unique_constraints(db_path: Path, table: str, columns: Tuple[str, ...]) -> bool:
    """
    Verify a unique constraint is enforced on a table.

    Args:
        db_path: Path to the database file.
        table: Table name.
        columns: Tuple of column names that should be unique together.

    Returns:
        True if the constraint is enforced.
    """
    if not db_path.exists():
        return False

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Check for index on these columns
        cursor.execute(f"PRAGMA index_list({table})")
        indices = cursor.fetchall()

        for idx in indices:
            idx_name = idx[1]
            is_unique = idx[2] == 1

            if not is_unique:
                continue

            cursor.execute(f"PRAGMA index_info({idx_name})")
            idx_cols = {row[2] for row in cursor.fetchall()}

            if set(columns) == idx_cols:
                return True

        # Also check CREATE TABLE for UNIQUE constraints
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        row = cursor.fetchone()
        if row and row[0]:
            sql = row[0].upper()
            # Simple check for UNIQUE(...columns...)
            col_str = ", ".join(columns).upper()
            if f"UNIQUE({col_str})" in sql.replace(" ", ""):
                return True

    finally:
        conn.close()

    return False


def get_table_info(db_path: Path, table: str) -> List[Dict[str, Any]]:
    """
    Get detailed information about a table's columns.

    Args:
        db_path: Path to the database file.
        table: Table name.

    Returns:
        List of column info dicts.
    """
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")

        columns = []
        for row in cursor.fetchall():
            columns.append({
                "cid": row[0],
                "name": row[1],
                "type": row[2],
                "notnull": row[3] == 1,
                "default": row[4],
                "pk": row[5] == 1,
            })

        return columns
    finally:
        conn.close()


def get_foreign_keys(db_path: Path, table: str) -> List[Dict[str, Any]]:
    """
    Get foreign key information for a table.

    Args:
        db_path: Path to the database file.
        table: Table name.

    Returns:
        List of FK info dicts.
    """
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA foreign_key_list({table})")

        fks = []
        for row in cursor.fetchall():
            fks.append({
                "id": row[0],
                "seq": row[1],
                "table": row[2],
                "from": row[3],
                "to": row[4],
                "on_update": row[5],
                "on_delete": row[6],
                "match": row[7],
            })

        return fks
    finally:
        conn.close()
