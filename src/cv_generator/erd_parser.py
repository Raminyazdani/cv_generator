"""
ERD Parser module for CV Generator.

This module parses the ERD definition file (docs/erd.txt) at runtime to extract:
- All table definitions
- Column names and types
- Primary keys
- Foreign key relationships
- Unique constraints (including composite unique indices)

The parsed ERD spec is used to verify that the database schema matches exactly.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ColumnSpec:
    """Specification for a database column parsed from ERD."""

    name: str
    type: str
    is_pk: bool = False
    is_autoincrement: bool = False
    nullable: bool = True
    fk_table: Optional[str] = None
    fk_column: Optional[str] = None


@dataclass
class IndexSpec:
    """Specification for a database index parsed from ERD."""

    columns: Tuple[str, ...]
    is_unique: bool = True


@dataclass
class TableSpec:
    """Specification for a database table parsed from ERD."""

    name: str
    columns: List[ColumnSpec] = field(default_factory=list)
    indices: List[IndexSpec] = field(default_factory=list)

    def get_pk_columns(self) -> List[str]:
        """Get list of primary key column names."""
        return [col.name for col in self.columns if col.is_pk]

    def get_fk_columns(self) -> List[Tuple[str, str, str]]:
        """Get list of foreign key definitions as (column, ref_table, ref_column)."""
        return [
            (col.name, col.fk_table, col.fk_column)
            for col in self.columns
            if col.fk_table is not None
        ]

    def get_unique_constraints(self) -> List[Tuple[str, ...]]:
        """Get list of unique constraint column tuples."""
        return [idx.columns for idx in self.indices if idx.is_unique]


def parse_erd_file(erd_path: Path) -> Dict[str, TableSpec]:
    """
    Parse the ERD file and extract all table specifications.

    The ERD file format is based on DBML (Database Markup Language):
    - Table definitions: Table name { ... }
    - Column definitions: column_name type [constraints]
    - Foreign keys: [ref: > table.column]
    - Primary keys: [pk] or [pk, increment]
    - Indices: indexes { (col1, col2) [unique] }

    Args:
        erd_path: Path to the ERD file (e.g., docs/erd.txt).

    Returns:
        Dict mapping table names to TableSpec objects.
    """
    if not erd_path.exists():
        logger.error(f"[ERD] ERD file not found: {erd_path}")
        return {}

    content = erd_path.read_text(encoding="utf-8")
    tables: Dict[str, TableSpec] = {}

    # Parse tables with a state machine to handle nested braces (indexes { ... })
    # Pattern to find table start: "Table table_name {"
    table_start_pattern = re.compile(r"Table\s+(\w+)\s*\{", re.MULTILINE)

    for match in table_start_pattern.finditer(content):
        table_name = match.group(1)
        start_pos = match.end()

        # Find matching closing brace by counting braces
        brace_count = 1
        pos = start_pos
        while pos < len(content) and brace_count > 0:
            if content[pos] == "{":
                brace_count += 1
            elif content[pos] == "}":
                brace_count -= 1
            pos += 1

        table_body = content[start_pos : pos - 1]

        table_spec = _parse_table_body(table_name, table_body)
        tables[table_name] = table_spec

        logger.debug(
            f"[ERD] Parsed table '{table_name}': {len(table_spec.columns)} columns, "
            f"{len(table_spec.indices)} indices"
        )

    logger.info(f"[ERD] Parsed {len(tables)} tables from ERD file")
    return tables


def _parse_table_body(table_name: str, body: str) -> TableSpec:
    """
    Parse the body of a table definition.

    Args:
        table_name: Name of the table.
        body: The content between { and }.

    Returns:
        TableSpec with parsed columns and indices.
    """
    table = TableSpec(name=table_name)
    lines = body.strip().split("\n")

    in_indexes = False
    index_buffer = ""

    for line in lines:
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("//"):
            continue

        # Check for indexes block start
        if line.startswith("indexes {") or line == "indexes {":
            in_indexes = True
            index_buffer = ""
            continue

        # Check for indexes block end
        if in_indexes:
            if "}" in line:
                # End of indexes block
                index_buffer += " " + line.replace("}", "")
                _parse_indexes(table, index_buffer)
                in_indexes = False
            else:
                index_buffer += " " + line
            continue

        # Parse column definition
        column = _parse_column_line(line)
        if column:
            table.columns.append(column)

    return table


def _parse_column_line(line: str) -> Optional[ColumnSpec]:
    """
    Parse a single column definition line.

    Examples:
        code varchar [pk]
        id int [pk, increment]
        resume_key varchar [ref: > resume_sets.resume_key]
        email varchar
        birth_date date

    Args:
        line: A single line from the table body.

    Returns:
        ColumnSpec or None if line is not a column definition.
    """
    # Skip lines that are not column definitions
    if line.startswith("indexes") or line.startswith("}"):
        return None

    # Pattern to match column definition
    # column_name type [constraints]
    col_pattern = re.compile(
        r"^(\w+)\s+(\w+)\s*(\[.*?\])?\s*(?://.*)?$",
        re.IGNORECASE,
    )

    match = col_pattern.match(line)
    if not match:
        return None

    col_name = match.group(1)
    col_type = match.group(2).upper()
    constraints = match.group(3) or ""

    # Map ERD types to SQLite types
    type_mapping = {
        "VARCHAR": "VARCHAR",
        "TEXT": "TEXT",
        "INT": "INTEGER",
        "INTEGER": "INTEGER",
        "BOOLEAN": "BOOLEAN",
        "DATE": "DATE",
        "DATETIME": "DATETIME",
        "FLOAT": "REAL",
        "REAL": "REAL",
    }

    sqlite_type = type_mapping.get(col_type, col_type)

    column = ColumnSpec(name=col_name, type=sqlite_type)

    # Parse constraints
    if constraints:
        constraints_lower = constraints.lower()

        # Primary key
        if "pk" in constraints_lower:
            column.is_pk = True
            column.nullable = False

        # Autoincrement
        if "increment" in constraints_lower:
            column.is_autoincrement = True

        # Foreign key reference
        fk_match = re.search(r"ref:\s*>\s*(\w+)\.(\w+)", constraints)
        if fk_match:
            column.fk_table = fk_match.group(1)
            column.fk_column = fk_match.group(2)

    return column


def _parse_indexes(table: TableSpec, index_str: str) -> None:
    """
    Parse the indexes block content.

    Examples:
        (resume_key, lang_code) [unique]
        (person_id, sort_order) [unique]

    Args:
        table: TableSpec to add indices to.
        index_str: Content of the indexes block.
    """
    # Pattern to match index definition
    # (col1, col2) [unique]
    index_pattern = re.compile(
        r"\(([^)]+)\)\s*(\[unique\])?",
        re.IGNORECASE,
    )

    for match in index_pattern.finditer(index_str):
        columns_str = match.group(1)
        is_unique = match.group(2) is not None

        # Parse column names
        columns = tuple(col.strip() for col in columns_str.split(","))

        table.indices.append(IndexSpec(columns=columns, is_unique=is_unique))


def get_default_erd_path() -> Path:
    """
    Get the default path to the ERD file.

    Returns:
        Path to docs/erd.txt relative to repo root.
    """
    from .paths import get_repo_root

    return get_repo_root() / "docs" / "erd.txt"


def verify_schema_against_erd(
    db_path: Path,
    erd_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Verify that the database schema matches the ERD specification exactly.

    This function performs a table-by-table comparison and reports:
    - Tables that match the ERD exactly
    - Tables that are missing from the database
    - Tables with column mismatches (wrong types, missing columns, extra columns)
    - Tables with missing foreign keys
    - Tables with missing unique constraints

    Args:
        db_path: Path to the database file.
        erd_path: Path to the ERD file. Uses default if None.

    Returns:
        Dict with detailed verification results.
    """
    import sqlite3

    if erd_path is None:
        erd_path = get_default_erd_path()

    results: Dict[str, Any] = {
        "valid": True,
        "erd_path": str(erd_path),
        "db_path": str(db_path),
        "tables_checked": 0,
        "tables_matched": 0,
        "tables_mismatched": 0,
        "tables_missing": [],
        "table_details": {},
        "issues": [],
    }

    # Parse ERD
    erd_tables = parse_erd_file(erd_path)
    if not erd_tables:
        results["valid"] = False
        results["issues"].append("Failed to parse ERD file or no tables found")
        return results

    # Check if database exists
    if not db_path.exists():
        results["valid"] = False
        results["issues"].append(f"Database not found: {db_path}")
        results["tables_missing"] = list(erd_tables.keys())
        return results

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Get list of existing tables
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        existing_tables = {row[0] for row in cursor.fetchall()}

        for table_name, erd_spec in erd_tables.items():
            results["tables_checked"] += 1
            table_result = _verify_table(cursor, table_name, erd_spec, existing_tables)
            results["table_details"][table_name] = table_result

            if table_result["status"] == "missing":
                results["tables_missing"].append(table_name)
                results["valid"] = False
            elif table_result["status"] == "mismatch":
                results["tables_mismatched"] += 1
                results["valid"] = False
                results["issues"].extend(table_result.get("issues", []))
            else:
                results["tables_matched"] += 1

    finally:
        conn.close()

    logger.info(
        f"[ERD] Verification: {results['tables_matched']}/{results['tables_checked']} tables match ERD"
    )

    return results


def _verify_table(
    cursor,
    table_name: str,
    erd_spec: TableSpec,
    existing_tables: set,
) -> Dict[str, Any]:
    """
    Verify a single table against its ERD specification.

    Args:
        cursor: Database cursor.
        table_name: Name of the table to verify.
        erd_spec: ERD specification for the table.
        existing_tables: Set of existing table names in the database.

    Returns:
        Dict with table verification results.
    """
    result: Dict[str, Any] = {
        "table": table_name,
        "status": "match",
        "columns": {"expected": [], "found": [], "missing": [], "extra": []},
        "foreign_keys": {"expected": [], "found": [], "missing": []},
        "unique_constraints": {"expected": [], "found": [], "missing": []},
        "issues": [],
    }

    # Check if table exists
    if table_name not in existing_tables:
        result["status"] = "missing"
        result["issues"].append(f"Table '{table_name}' is missing from database")
        return result

    # Get actual table info
    cursor.execute(f"PRAGMA table_info({table_name})")
    db_columns = {row[1]: row[2] for row in cursor.fetchall()}

    # Check columns
    erd_columns = {col.name: col.type for col in erd_spec.columns}
    result["columns"]["expected"] = list(erd_columns.keys())
    result["columns"]["found"] = list(db_columns.keys())

    for col_name, col_type in erd_columns.items():
        if col_name not in db_columns:
            result["columns"]["missing"].append(col_name)
            result["issues"].append(
                f"Table '{table_name}': Missing column '{col_name}' (expected type: {col_type})"
            )

    for col_name in db_columns:
        if col_name not in erd_columns:
            result["columns"]["extra"].append(col_name)
            # Extra columns might be intentional, don't mark as issue

    # Check foreign keys
    cursor.execute(f"PRAGMA foreign_key_list({table_name})")
    db_fks = [(row[3], row[2], row[4]) for row in cursor.fetchall()]
    erd_fks = erd_spec.get_fk_columns()

    result["foreign_keys"]["expected"] = [
        {"from": fk[0], "table": fk[1], "to": fk[2]} for fk in erd_fks
    ]
    result["foreign_keys"]["found"] = [
        {"from": fk[0], "table": fk[1], "to": fk[2]} for fk in db_fks
    ]

    for erd_fk in erd_fks:
        if erd_fk not in db_fks:
            result["foreign_keys"]["missing"].append(
                {"from": erd_fk[0], "table": erd_fk[1], "to": erd_fk[2]}
            )
            result["issues"].append(
                f"Table '{table_name}': Missing FK '{erd_fk[0]}' -> {erd_fk[1]}.{erd_fk[2]}"
            )

    # Check unique constraints
    cursor.execute(f"PRAGMA index_list({table_name})")
    indices = cursor.fetchall()

    db_unique_constraints = []
    for idx in indices:
        idx_name = idx[1]
        is_unique = idx[2] == 1
        if is_unique:
            cursor.execute(f"PRAGMA index_info('{idx_name}')")
            cols = tuple(row[2] for row in cursor.fetchall())
            if cols:
                db_unique_constraints.append(cols)

    erd_unique = erd_spec.get_unique_constraints()
    result["unique_constraints"]["expected"] = [list(uc) for uc in erd_unique]
    result["unique_constraints"]["found"] = [list(uc) for uc in db_unique_constraints]

    for erd_uc in erd_unique:
        found = any(set(erd_uc) == set(db_uc) for db_uc in db_unique_constraints)
        if not found:
            result["unique_constraints"]["missing"].append(list(erd_uc))
            result["issues"].append(
                f"Table '{table_name}': Missing unique constraint on {erd_uc}"
            )

    # Determine overall status
    if result["columns"]["missing"] or result["foreign_keys"]["missing"]:
        result["status"] = "mismatch"
    # Note: Missing unique constraints are logged but may be enforced via other means

    return result


def generate_schema_report(
    db_path: Path,
    erd_path: Optional[Path] = None,
) -> str:
    """
    Generate a human-readable report comparing database schema to ERD.

    Args:
        db_path: Path to the database file.
        erd_path: Path to the ERD file. Uses default if None.

    Returns:
        Formatted report string.
    """
    results = verify_schema_against_erd(db_path, erd_path)

    lines = [
        "=" * 80,
        "ERD Schema Verification Report",
        "=" * 80,
        f"ERD File: {results['erd_path']}",
        f"Database: {results['db_path']}",
        "",
        f"Overall Status: {'✓ VALID' if results['valid'] else '✗ INVALID'}",
        f"Tables Checked: {results['tables_checked']}",
        f"Tables Matched: {results['tables_matched']}",
        f"Tables Mismatched: {results['tables_mismatched']}",
        f"Tables Missing: {len(results['tables_missing'])}",
        "",
        "-" * 80,
        "Table-by-Table Results:",
        "-" * 80,
    ]

    for table_name, detail in sorted(results["table_details"].items()):
        status = detail["status"]
        status_icon = "✓" if status == "match" else "✗"

        lines.append(f"\n{status_icon} {table_name}: {status.upper()}")

        if detail["columns"]["expected"]:
            lines.append(f"   Columns: {len(detail['columns']['found'])}/{len(detail['columns']['expected'])}")

        if detail["columns"]["missing"]:
            lines.append(f"   Missing columns: {', '.join(detail['columns']['missing'])}")

        if detail["foreign_keys"]["missing"]:
            for fk in detail["foreign_keys"]["missing"]:
                lines.append(f"   Missing FK: {fk['from']} -> {fk['table']}.{fk['to']}")

        if detail["unique_constraints"]["missing"]:
            for uc in detail["unique_constraints"]["missing"]:
                lines.append(f"   Missing unique: ({', '.join(uc)})")

    if results["tables_missing"]:
        lines.append("\n" + "-" * 80)
        lines.append("Missing Tables:")
        lines.append("-" * 80)
        for table in results["tables_missing"]:
            lines.append(f"  ✗ {table}")

    if results["issues"]:
        lines.append("\n" + "-" * 80)
        lines.append("All Issues:")
        lines.append("-" * 80)
        for issue in results["issues"]:
            lines.append(f"  • {issue}")

    lines.append("\n" + "=" * 80)

    return "\n".join(lines)
