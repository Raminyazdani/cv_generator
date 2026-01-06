"""
Tests for cv_generator.erd_parser module.

Tests the ERD parser and schema verification:
- ERD file parsing
- Table/column/FK extraction
- Schema comparison against database
- Report generation
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from cv_generator.erd_parser import (
    ColumnSpec,
    IndexSpec,
    TableSpec,
    parse_erd_file,
    verify_schema_against_erd,
    generate_schema_report,
    get_default_erd_path,
    _parse_column_line,
    _parse_table_body,
)
from cv_generator.schema_v2 import init_db_v2, ERD_TABLES


class TestColumnParsing:
    """Tests for column line parsing."""

    def test_parse_simple_column(self):
        """Parse simple column without constraints."""
        col = _parse_column_line("email varchar")
        assert col is not None
        assert col.name == "email"
        assert col.type == "VARCHAR"
        assert col.is_pk is False
        assert col.fk_table is None

    def test_parse_pk_column(self):
        """Parse primary key column."""
        col = _parse_column_line("code varchar [pk]")
        assert col is not None
        assert col.name == "code"
        assert col.is_pk is True
        assert col.nullable is False

    def test_parse_pk_increment_column(self):
        """Parse auto-increment primary key column."""
        col = _parse_column_line("id int [pk, increment]")
        assert col is not None
        assert col.name == "id"
        assert col.type == "INTEGER"
        assert col.is_pk is True
        assert col.is_autoincrement is True

    def test_parse_fk_column(self):
        """Parse foreign key column."""
        col = _parse_column_line("resume_key varchar [ref: > resume_sets.resume_key]")
        assert col is not None
        assert col.name == "resume_key"
        assert col.fk_table == "resume_sets"
        assert col.fk_column == "resume_key"

    def test_parse_column_with_comment(self):
        """Parse column with trailing comment."""
        col = _parse_column_line("code varchar [pk] // e.g., 'en', 'de', 'fa', 'it'")
        assert col is not None
        assert col.name == "code"
        assert col.is_pk is True

    def test_parse_date_column(self):
        """Parse date type column."""
        col = _parse_column_line("birth_date date")
        assert col is not None
        assert col.name == "birth_date"
        assert col.type == "DATE"

    def test_parse_float_column(self):
        """Parse float type column."""
        col = _parse_column_line("overall float")
        assert col is not None
        assert col.name == "overall"
        assert col.type == "REAL"


class TestTableParsing:
    """Tests for table body parsing."""

    def test_parse_simple_table(self):
        """Parse table with simple columns."""
        body = """
        code varchar [pk]
        name_en varchar
        direction varchar
        """
        table = _parse_table_body("app_languages", body)

        assert table.name == "app_languages"
        assert len(table.columns) == 3
        assert table.columns[0].name == "code"
        assert table.columns[0].is_pk is True

    def test_parse_table_with_fks(self):
        """Parse table with foreign key references."""
        body = """
        id int [pk, increment]
        person_id int [ref: > persons.id]
        resume_version_id int [ref: > resume_versions.id]
        fname varchar
        """
        table = _parse_table_body("person_i18n", body)

        assert len(table.columns) == 4
        fks = table.get_fk_columns()
        assert len(fks) == 2
        assert ("person_id", "persons", "id") in fks
        assert ("resume_version_id", "resume_versions", "id") in fks

    def test_parse_table_with_indexes(self):
        """Parse table with index definitions."""
        body = """
        id int [pk, increment]
        resume_key varchar [ref: > resume_sets.resume_key]
        lang_code varchar [ref: > app_languages.code]

        indexes {
            (resume_key, lang_code) [unique]
        }
        """
        table = _parse_table_body("resume_versions", body)

        assert len(table.columns) == 3
        assert len(table.indices) == 1
        assert table.indices[0].columns == ("resume_key", "lang_code")
        assert table.indices[0].is_unique is True

    def test_parse_table_with_multiple_indexes(self):
        """Parse table with multiple index definitions."""
        body = """
        id int [pk, increment]
        resume_key varchar
        category_code varchar
        sort_order int

        indexes {
            (resume_key, category_code) [unique]
            (resume_key, sort_order) [unique]
        }
        """
        table = _parse_table_body("skill_categories", body)

        assert len(table.indices) == 2
        unique_constraints = table.get_unique_constraints()
        assert ("resume_key", "category_code") in unique_constraints
        assert ("resume_key", "sort_order") in unique_constraints


class TestErdFileParsing:
    """Tests for full ERD file parsing."""

    def test_parse_real_erd_file(self):
        """Parse the actual docs/erd.txt file."""
        erd_path = get_default_erd_path()
        if not erd_path.exists():
            pytest.skip("ERD file not found")

        tables = parse_erd_file(erd_path)

        # Should have many tables
        assert len(tables) >= 40

        # Check some expected tables exist
        assert "app_languages" in tables
        assert "resume_sets" in tables
        assert "resume_versions" in tables
        assert "persons" in tables
        assert "person_i18n" in tables
        assert "education_items" in tables
        assert "publication_items" in tables

    def test_parse_app_languages_table(self):
        """Verify app_languages table parsing."""
        erd_path = get_default_erd_path()
        if not erd_path.exists():
            pytest.skip("ERD file not found")

        tables = parse_erd_file(erd_path)
        app_lang = tables.get("app_languages")

        assert app_lang is not None
        assert len(app_lang.columns) == 3

        col_names = [c.name for c in app_lang.columns]
        assert "code" in col_names
        assert "name_en" in col_names
        assert "direction" in col_names

        pks = app_lang.get_pk_columns()
        assert "code" in pks

    def test_parse_resume_versions_table(self):
        """Verify resume_versions table parsing with FK and unique constraint."""
        erd_path = get_default_erd_path()
        if not erd_path.exists():
            pytest.skip("ERD file not found")

        tables = parse_erd_file(erd_path)
        rv = tables.get("resume_versions")

        assert rv is not None

        # Check FKs
        fks = rv.get_fk_columns()
        assert len(fks) >= 2
        assert any(fk[1] == "resume_sets" for fk in fks)
        assert any(fk[1] == "app_languages" for fk in fks)

        # Check unique constraint
        unique = rv.get_unique_constraints()
        assert len(unique) >= 1
        assert any("resume_key" in uc and "lang_code" in uc for uc in unique)

    def test_nonexistent_erd_file(self):
        """Parse returns empty dict for missing file."""
        tables = parse_erd_file(Path("/nonexistent/erd.txt"))
        assert tables == {}


class TestSchemaVerification:
    """Tests for schema verification against ERD."""

    @pytest.fixture
    def v2_db(self, tmp_path):
        """Create a v2 database for testing."""
        db_path = tmp_path / "test_v2.db"
        init_db_v2(db_path)
        return db_path

    def test_verify_fresh_v2_database(self, v2_db):
        """Verify fresh v2 database matches ERD."""
        erd_path = get_default_erd_path()
        if not erd_path.exists():
            pytest.skip("ERD file not found")

        results = verify_schema_against_erd(v2_db, erd_path)

        assert results["valid"] is True
        assert results["tables_checked"] >= 40
        assert results["tables_matched"] == results["tables_checked"]
        assert results["tables_mismatched"] == 0
        assert len(results["tables_missing"]) == 0

    def test_verify_all_erd_tables_exist(self, v2_db):
        """Verify all ERD tables exist in database."""
        erd_path = get_default_erd_path()
        if not erd_path.exists():
            pytest.skip("ERD file not found")

        results = verify_schema_against_erd(v2_db, erd_path)

        # Check each table in ERD_TABLES constant
        for table_name in ERD_TABLES:
            if table_name in results["table_details"]:
                detail = results["table_details"][table_name]
                assert detail["status"] in ["match", "mismatch"], (
                    f"Table '{table_name}' has unexpected status: {detail['status']}"
                )

    def test_verify_reports_missing_tables(self, tmp_path):
        """Verify missing tables are reported."""
        # Create empty database
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(db_path)
        conn.close()

        erd_path = get_default_erd_path()
        if not erd_path.exists():
            pytest.skip("ERD file not found")

        results = verify_schema_against_erd(db_path, erd_path)

        assert results["valid"] is False
        assert len(results["tables_missing"]) > 0
        assert "app_languages" in results["tables_missing"]

    def test_verify_nonexistent_database(self, tmp_path):
        """Verify nonexistent database is handled."""
        db_path = tmp_path / "nonexistent.db"
        erd_path = get_default_erd_path()

        results = verify_schema_against_erd(db_path, erd_path)

        assert results["valid"] is False
        assert any("not found" in issue.lower() for issue in results["issues"])


class TestSchemaReport:
    """Tests for schema report generation."""

    @pytest.fixture
    def v2_db(self, tmp_path):
        """Create a v2 database for testing."""
        db_path = tmp_path / "test_v2.db"
        init_db_v2(db_path)
        return db_path

    def test_generate_report_for_valid_db(self, v2_db):
        """Generate report for valid database."""
        erd_path = get_default_erd_path()
        if not erd_path.exists():
            pytest.skip("ERD file not found")

        report = generate_schema_report(v2_db, erd_path)

        assert "ERD Schema Verification Report" in report
        assert "✓ VALID" in report
        assert "app_languages: MATCH" in report
        assert "persons: MATCH" in report

    def test_report_includes_table_counts(self, v2_db):
        """Report includes table match counts."""
        erd_path = get_default_erd_path()
        if not erd_path.exists():
            pytest.skip("ERD file not found")

        report = generate_schema_report(v2_db, erd_path)

        assert "Tables Checked:" in report
        assert "Tables Matched:" in report
        assert "Tables Mismatched: 0" in report

    def test_report_for_empty_db(self, tmp_path):
        """Report shows missing tables for empty database."""
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(db_path)
        conn.close()

        erd_path = get_default_erd_path()
        if not erd_path.exists():
            pytest.skip("ERD file not found")

        report = generate_schema_report(db_path, erd_path)

        assert "✗ INVALID" in report
        assert "Missing Tables:" in report


class TestTableSpec:
    """Tests for TableSpec dataclass methods."""

    def test_get_pk_columns(self):
        """Test getting primary key columns."""
        table = TableSpec(
            name="test",
            columns=[
                ColumnSpec(name="id", type="INTEGER", is_pk=True),
                ColumnSpec(name="code", type="VARCHAR", is_pk=True),
                ColumnSpec(name="value", type="VARCHAR"),
            ],
        )

        pks = table.get_pk_columns()
        assert pks == ["id", "code"]

    def test_get_fk_columns(self):
        """Test getting foreign key columns."""
        table = TableSpec(
            name="test",
            columns=[
                ColumnSpec(name="id", type="INTEGER", is_pk=True),
                ColumnSpec(
                    name="parent_id",
                    type="INTEGER",
                    fk_table="parent",
                    fk_column="id",
                ),
                ColumnSpec(name="value", type="VARCHAR"),
            ],
        )

        fks = table.get_fk_columns()
        assert len(fks) == 1
        assert fks[0] == ("parent_id", "parent", "id")

    def test_get_unique_constraints(self):
        """Test getting unique constraints."""
        table = TableSpec(
            name="test",
            columns=[],
            indices=[
                IndexSpec(columns=("col1", "col2"), is_unique=True),
                IndexSpec(columns=("col3",), is_unique=True),
            ],
        )

        constraints = table.get_unique_constraints()
        assert len(constraints) == 2
        assert ("col1", "col2") in constraints
        assert ("col3",) in constraints
