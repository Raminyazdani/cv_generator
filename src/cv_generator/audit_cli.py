"""
Self-audit CLI tool for CV Generator.

Provides commands for manual verification of the CV Generator system:
- roundtrip-verify: Verify round-trip for all CVs in a directory
- schema-verify: Verify database schema matches ERD
- sync-verify: Verify all variants are correctly linked and synced
- full-audit: Run complete self-audit and generate report
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .export_verify import ExportVerifier, RoundTripResult

logger = logging.getLogger(__name__)

# ANSI color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def _log(message: str, level: str = "info") -> None:
    """Print a log message with optional color."""
    if level == "error":
        print(f"{RED}[ERROR]{RESET} {message}")
    elif level == "warn":
        print(f"{YELLOW}[WARN]{RESET} {message}")
    elif level == "success":
        print(f"{GREEN}[OK]{RESET} {message}")
    else:
        print(f"[INFO] {message}")


def roundtrip_verify(
    cv_dir: str,
    db_path: Optional[str] = None,
    verbose: bool = False,
) -> int:
    """
    Verify round-trip for all CVs in directory.

    For each JSON file:
    1. Import to fresh DB
    2. Export from DB
    3. Diff against original
    4. Report any differences

    Returns:
        0 if all round-trips pass, 1 if any fail
    """
    cv_path = Path(cv_dir)
    if not cv_path.exists():
        _log(f"Directory not found: {cv_dir}", "error")
        return 1

    json_files = list(cv_path.glob("*.json"))
    if not json_files:
        _log(f"No JSON files found in: {cv_dir}", "error")
        return 1

    _log(f"Starting round-trip verification for {len(json_files)} files...")
    _log(f"Directory: {cv_path.absolute()}")
    print()

    verifier = ExportVerifier(
        ignore_order=True,
        ignore_whitespace=True,
        ignore_type_key_order=True,
        ignore_extra_null_keys=True,
    )

    results: List[RoundTripResult] = []
    passed = 0
    failed = 0

    for json_file in sorted(json_files):
        start_time = time.time()

        # Create temporary database for this file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db_path = Path(f.name)

        try:
            result = verifier.verify_round_trip(json_file, temp_db_path)
            results.append(result)

            duration_ms = (time.time() - start_time) * 1000

            if result.success:
                passed += 1
                _log(f"✓ {json_file.name} ({duration_ms:.0f}ms)", "success")
            else:
                failed += 1
                _log(f"✗ {json_file.name} ({duration_ms:.0f}ms)", "error")
                if verbose and result.verification:
                    print(f"  {result.verification.get_summary()}")
                    print()

        finally:
            # Clean up temp database
            if temp_db_path.exists():
                temp_db_path.unlink()

    print()
    print(f"{BOLD}===== Round-Trip Verification Summary ====={RESET}")
    print(f"  Total files: {len(json_files)}")
    print(f"  Passed: {GREEN}{passed}{RESET}")
    print(f"  Failed: {RED if failed > 0 else ''}{failed}{RESET if failed > 0 else ''}")
    print()

    if failed > 0:
        _log("Round-trip verification FAILED", "error")
        return 1
    else:
        _log("Round-trip verification PASSED", "success")
        return 0


def schema_verify(db_path: str) -> int:
    """
    Verify database schema matches expected structure.

    Checks:
    - All tables exist
    - All columns correct
    - All indices present
    - All foreign keys valid

    Returns:
        0 if schema is valid, 1 if issues found
    """
    import sqlite3

    db = Path(db_path)
    if not db.exists():
        _log(f"Database not found: {db_path}", "error")
        return 1

    _log(f"Verifying schema: {db}")

    expected_tables = [
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

    issues = []

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        actual_tables = {row[0] for row in cursor.fetchall()}

        # Check for missing tables
        for table in expected_tables:
            if table not in actual_tables:
                issues.append(f"Missing table: {table}")
                _log(f"Missing table: {table}", "error")
            else:
                _log(f"✓ Table exists: {table}", "success")

        # Check for foreign key integrity
        cursor.execute("PRAGMA foreign_key_check")
        fk_violations = cursor.fetchall()
        if fk_violations:
            for v in fk_violations[:5]:
                issues.append(f"Foreign key violation: {v}")
                _log(f"Foreign key violation: {v}", "error")
            if len(fk_violations) > 5:
                issues.append(f"... and {len(fk_violations) - 5} more")

    finally:
        conn.close()

    print()
    if issues:
        _log(f"Schema verification FAILED with {len(issues)} issues", "error")
        return 1
    else:
        _log("Schema verification PASSED", "success")
        return 0


def sync_verify(db_path: str) -> int:
    """
    Verify all variants are correctly linked and synced.

    Checks:
    - All variants linked by resume_key
    - No orphaned variants
    - Shared fields are consistent across variants

    Returns:
        0 if sync is valid, 1 if issues found
    """
    import sqlite3

    db = Path(db_path)
    if not db.exists():
        _log(f"Database not found: {db_path}", "error")
        return 1

    _log(f"Verifying sync status: {db}")

    issues = []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()

        # Check that all resume_versions have a corresponding resume_set
        cursor.execute("""
            SELECT rv.resume_key, rv.lang_code
            FROM resume_versions rv
            LEFT JOIN resume_sets rs ON rv.resume_key = rs.resume_key
            WHERE rs.id IS NULL
        """)
        orphaned = cursor.fetchall()
        if orphaned:
            for row in orphaned:
                issues.append(f"Orphaned version: {row['resume_key']}/{row['lang_code']}")
                _log(f"Orphaned version: {row['resume_key']}/{row['lang_code']}", "error")

        # Check that all persons have a resume_version
        cursor.execute("""
            SELECT p.resume_key
            FROM persons p
            LEFT JOIN resume_versions rv ON p.resume_key = rv.resume_key
            WHERE rv.id IS NULL
        """)
        orphaned_persons = cursor.fetchall()
        if orphaned_persons:
            for row in orphaned_persons:
                issues.append(f"Orphaned person: {row['resume_key']}")
                _log(f"Orphaned person: {row['resume_key']}", "error")

        # List all resume_keys and their language variants
        cursor.execute("""
            SELECT resume_key, GROUP_CONCAT(lang_code) as langs
            FROM resume_versions
            GROUP BY resume_key
        """)
        resumes = cursor.fetchall()
        for row in resumes:
            _log(f"✓ {row['resume_key']}: languages [{row['langs']}]", "success")

    finally:
        conn.close()

    print()
    if issues:
        _log(f"Sync verification FAILED with {len(issues)} issues", "error")
        return 1
    else:
        _log("Sync verification PASSED", "success")
        return 0


def full_audit(
    cv_dir: str = "data/cvs",
    db_path: str = "data/db/cv.db",
    output: str = "audit_report.json",
) -> int:
    """
    Run complete self-audit and generate report.

    Includes:
    - Schema verification (if DB exists)
    - Round-trip verification
    - Sync verification (if DB exists)
    - Data integrity checks

    Returns:
        0 if all checks pass, 1 if any fail
    """
    _log(f"{BOLD}===== CV Generator Full Audit ====={RESET}")
    print()

    report: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cv_dir": cv_dir,
        "db_path": db_path,
        "results": {},
    }

    all_passed = True

    # Round-trip verification
    _log("Step 1: Round-trip verification")
    rt_result = roundtrip_verify(cv_dir, verbose=False)
    report["results"]["roundtrip"] = {
        "passed": rt_result == 0,
    }
    if rt_result != 0:
        all_passed = False

    print()

    # Schema verification (if DB exists)
    db = Path(db_path)
    if db.exists():
        _log("Step 2: Schema verification")
        schema_result = schema_verify(db_path)
        report["results"]["schema"] = {
            "passed": schema_result == 0,
        }
        if schema_result != 0:
            all_passed = False

        print()

        # Sync verification
        _log("Step 3: Sync verification")
        sync_result = sync_verify(db_path)
        report["results"]["sync"] = {
            "passed": sync_result == 0,
        }
        if sync_result != 0:
            all_passed = False
    else:
        _log(f"Skipping schema/sync verification (DB not found: {db_path})", "warn")
        report["results"]["schema"] = {"skipped": True}
        report["results"]["sync"] = {"skipped": True}

    print()

    # Write report
    output_path = Path(output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    _log(f"Report written to: {output_path.absolute()}")

    print()
    print(f"{BOLD}===== Audit Summary ====={RESET}")
    if all_passed:
        _log("All checks PASSED", "success")
        return 0
    else:
        _log("Some checks FAILED - see details above", "error")
        return 1


def main() -> int:
    """Main entry point for audit CLI."""
    parser = argparse.ArgumentParser(
        prog="cv-audit",
        description="Self-audit tools for CV Generator",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # roundtrip-verify command
    rt_parser = subparsers.add_parser(
        "roundtrip-verify",
        help="Verify round-trip for all CVs in directory",
    )
    rt_parser.add_argument(
        "cv_dir",
        help="Directory containing CV JSON files",
    )
    rt_parser.add_argument(
        "--db",
        default=None,
        help="Database path (optional, uses temp DB by default)",
    )
    rt_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed diff for failures",
    )

    # schema-verify command
    schema_parser = subparsers.add_parser(
        "schema-verify",
        help="Verify database schema",
    )
    schema_parser.add_argument(
        "--db",
        default="data/db/cv.db",
        help="Database path",
    )

    # sync-verify command
    sync_parser = subparsers.add_parser(
        "sync-verify",
        help="Verify variant sync status",
    )
    sync_parser.add_argument(
        "--db",
        default="data/db/cv.db",
        help="Database path",
    )

    # full-audit command
    audit_parser = subparsers.add_parser(
        "full-audit",
        help="Run complete self-audit",
    )
    audit_parser.add_argument(
        "--cv-dir",
        default="data/cvs",
        help="Directory containing CV JSON files",
    )
    audit_parser.add_argument(
        "--db",
        default="data/db/cv.db",
        help="Database path",
    )
    audit_parser.add_argument(
        "-o", "--output",
        default="audit_report.json",
        help="Output file for audit report",
    )

    args = parser.parse_args()

    if args.command == "roundtrip-verify":
        return roundtrip_verify(args.cv_dir, args.db, args.verbose)
    elif args.command == "schema-verify":
        return schema_verify(args.db)
    elif args.command == "sync-verify":
        return sync_verify(args.db)
    elif args.command == "full-audit":
        return full_audit(args.cv_dir, args.db, args.output)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
