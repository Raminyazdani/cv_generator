"""
Database audit module.

Checks database schema, integrity, and operations.
"""

import json
import sqlite3
import sys
from pathlib import Path
from typing import Callable


class DatabaseAuditor:
    """Auditor for database schema and integrity."""

    # Tables expected per ERD/schema
    EXPECTED_TABLES = [
        "meta",
        "person",
        "entry",
        "tag",
        "entry_tag",
    ]

    # Extended schema tables (from audit_cli.py)
    EXTENDED_TABLES = [
        "resume_sets",
        "resume_versions",
        "persons",
        "person_i18n",
        "person_locations",
        "person_location_i18n",
        "person_pictures",
        "person_labels",
        "person_label_i18n",
        "profile_accounts",
        "profile_account_i18n",
        "education_items",
        "education_i18n",
        "education_item_tags",
        "spoken_language_items",
        "spoken_language_i18n",
        "spoken_language_certs",
        "spoken_language_cert_i18n",
        "cert_issuers",
        "cert_issuer_i18n",
        "certifications",
        "certification_i18n",
        "certification_tags",
        "skill_categories",
        "skill_category_i18n",
        "skill_subcategories",
        "skill_subcategory_i18n",
        "skill_items",
        "skill_item_i18n",
        "skill_item_tags",
        "experience_items",
        "experience_i18n",
        "project_items",
        "project_i18n",
        "project_tags",
        "publication_items",
        "publication_i18n",
        "publication_authors",
        "publication_editors",
        "publication_supervisors",
        "publication_tags",
        "reference_items",
        "reference_i18n",
        "reference_emails",
        "reference_tags",
        "tag_codes",
        "tag_i18n",
    ]

    def __init__(self, project_root: Path, add_problem: Callable):
        self.project_root = project_root
        self.add_problem = add_problem
        self.db_path = project_root / "data" / "db" / "cv.db"

    def run_all_checks(self):
        """Run all database checks."""
        # Check if database module exists
        self._check_db_module_exists()

        # Check schema SQL
        self._check_schema_definition()

        # If DB exists, check its structure
        if self.db_path.exists():
            self._check_database_integrity()
            self._check_orphaned_records()
            self._check_json_validity()

    def _check_db_module_exists(self):
        """Check that the database module exists."""
        db_module = self.project_root / "src" / "cv_generator" / "db.py"
        if not db_module.exists():
            self.add_problem(
                severity=self._severity("CRITICAL"),
                category="Database",
                subcategory="Missing Module",
                title="Database module not found",
                description="The db.py module is missing from cv_generator",
                reproduction_steps=["1. Check for src/cv_generator/db.py"],
                expected="db.py exists",
                actual="File not found",
                affected_files=[str(db_module)],
            )

    def _check_schema_definition(self):
        """Check that schema SQL is properly defined."""
        db_module = self.project_root / "src" / "cv_generator" / "db.py"
        if not db_module.exists():
            return

        try:
            with open(db_module, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for SCHEMA_SQL definition
            if "SCHEMA_SQL" not in content:
                self.add_problem(
                    severity=self._severity("HIGH"),
                    category="Database",
                    subcategory="Schema",
                    title="SCHEMA_SQL not defined",
                    description="The SCHEMA_SQL constant is not defined in db.py",
                    reproduction_steps=["1. Search for SCHEMA_SQL in db.py"],
                    expected="SCHEMA_SQL constant is defined",
                    actual="SCHEMA_SQL not found",
                    affected_files=[str(db_module)],
                )

            # Check for required table definitions in schema
            required_tables = ["person", "entry", "tag", "entry_tag", "meta"]
            for table in required_tables:
                if f"CREATE TABLE IF NOT EXISTS {table}" not in content:
                    self.add_problem(
                        severity=self._severity("HIGH"),
                        category="Database",
                        subcategory="Schema",
                        title=f"Missing table definition: {table}",
                        description=f"Table '{table}' not found in SCHEMA_SQL",
                        reproduction_steps=[f"1. Search for 'CREATE TABLE IF NOT EXISTS {table}'"],
                        expected=f"Table '{table}' is defined in schema",
                        actual="Table definition not found",
                        affected_files=[str(db_module)],
                    )

        except Exception as e:
            self.add_problem(
                severity=self._severity("MEDIUM"),
                category="Database",
                subcategory="Parse Error",
                title="Cannot parse db.py",
                description=str(e),
                reproduction_steps=["1. Try to read db.py"],
                expected="File is readable",
                actual=f"Exception: {type(e).__name__}",
                affected_files=[str(db_module)],
                error_message=str(e),
            )

    def _check_database_integrity(self):
        """Check database integrity if it exists."""
        if not self.db_path.exists():
            return

        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            if result[0] != "ok":
                self.add_problem(
                    severity=self._severity("CRITICAL"),
                    category="Database",
                    subcategory="Integrity",
                    title="Database integrity check failed",
                    description="SQLite integrity check returned errors",
                    reproduction_steps=[
                        "1. Open database",
                        "2. Run: PRAGMA integrity_check",
                    ],
                    expected="Result: 'ok'",
                    actual=f"Result: {result[0]}",
                    affected_files=[str(self.db_path)],
                )

            # Check foreign key violations
            cursor.execute("PRAGMA foreign_key_check")
            violations = cursor.fetchall()
            if violations:
                self.add_problem(
                    severity=self._severity("HIGH"),
                    category="Database",
                    subcategory="Integrity",
                    title=f"{len(violations)} foreign key violations found",
                    description="Database has foreign key constraint violations",
                    reproduction_steps=[
                        "1. Open database",
                        "2. Run: PRAGMA foreign_key_check",
                    ],
                    expected="No violations",
                    actual=f"Found {len(violations)} violations",
                    affected_files=[str(self.db_path)],
                )

            # Check for expected tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            actual_tables = {row[0] for row in cursor.fetchall()}

            for table in self.EXPECTED_TABLES:
                if table not in actual_tables:
                    self.add_problem(
                        severity=self._severity("HIGH"),
                        category="Database",
                        subcategory="Schema",
                        title=f"Missing table: {table}",
                        description=f"Expected table '{table}' not found in database",
                        reproduction_steps=[
                            "1. Open database",
                            f"2. Check for table '{table}'",
                        ],
                        expected=f"Table '{table}' exists",
                        actual="Table not found",
                        affected_files=[str(self.db_path)],
                    )

            conn.close()

        except sqlite3.Error as e:
            self.add_problem(
                severity=self._severity("CRITICAL"),
                category="Database",
                subcategory="Connection Error",
                title="Cannot connect to database",
                description=str(e),
                reproduction_steps=["1. Try to open database"],
                expected="Database opens successfully",
                actual=f"SQLite error: {e}",
                affected_files=[str(self.db_path)],
                error_message=str(e),
            )

    def _check_orphaned_records(self):
        """Check for orphaned records in the database."""
        if not self.db_path.exists():
            return

        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Check for entries without valid person
            cursor.execute("""
                SELECT COUNT(*) FROM entry e
                LEFT JOIN person p ON e.person_id = p.id
                WHERE p.id IS NULL
            """)
            orphaned_entries = cursor.fetchone()[0]
            if orphaned_entries > 0:
                self.add_problem(
                    severity=self._severity("HIGH"),
                    category="Database",
                    subcategory="Data Integrity",
                    title=f"{orphaned_entries} orphaned entries found",
                    description="Entries exist without a valid person reference",
                    reproduction_steps=[
                        "1. Query entries with NULL person_id",
                    ],
                    expected="All entries have valid person_id",
                    actual=f"{orphaned_entries} entries orphaned",
                    affected_files=[str(self.db_path)],
                )

            # Check for unused tags
            cursor.execute("""
                SELECT COUNT(*) FROM tag t
                LEFT JOIN entry_tag et ON t.id = et.tag_id
                WHERE et.tag_id IS NULL
            """)
            unused_tags = cursor.fetchone()[0]
            if unused_tags > 0:
                # This is informational, not a problem
                pass

            conn.close()

        except sqlite3.Error:
            pass

    def _check_json_validity(self):
        """Check that all data_json fields contain valid JSON."""
        if not self.db_path.exists():
            return

        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("SELECT id, data_json FROM entry")
            invalid_count = 0
            for entry_id, data_json in cursor.fetchall():
                try:
                    json.loads(data_json)
                except (json.JSONDecodeError, TypeError):
                    invalid_count += 1

            if invalid_count > 0:
                self.add_problem(
                    severity=self._severity("CRITICAL"),
                    category="Database",
                    subcategory="Data Integrity",
                    title=f"{invalid_count} entries with invalid JSON",
                    description="Some entries have invalid JSON in data_json field",
                    reproduction_steps=[
                        "1. Query all entries",
                        "2. Try to parse each data_json",
                    ],
                    expected="All data_json fields are valid JSON",
                    actual=f"{invalid_count} entries have invalid JSON",
                    affected_files=[str(self.db_path)],
                )

            conn.close()

        except sqlite3.Error:
            pass

    def _severity(self, level: str):
        """Convert severity string to enum."""
        # Import here to avoid circular imports
        sys.path.insert(0, str(self.project_root / "scripts"))
        from final_audit import Severity

        return getattr(Severity, level)
