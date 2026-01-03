"""
Tests for cv_generator.validate_schema module and lint CLI command.

Tests JSON schema validation for CV files.
"""

import json
from pathlib import Path

import pytest

from cv_generator.cli import create_parser, main
from cv_generator.validate_schema import (
    ValidationIssue,
    ValidationReport,
    load_schema,
    validate_cv_file,
    validate_cv_json,
)

# Path to lint test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "lint"


class TestLoadSchema:
    """Tests for schema loading."""

    def test_schema_loads_successfully(self):
        """Test that the schema file loads without errors."""
        schema = load_schema()
        assert schema is not None
        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert "properties" in schema

    def test_schema_has_basics_required(self):
        """Test that schema requires 'basics' field."""
        schema = load_schema()
        assert "required" in schema
        assert "basics" in schema["required"]


class TestValidateCvJson:
    """Tests for JSON validation."""

    def test_valid_cv_passes(self):
        """Test that a valid CV passes validation."""
        data = {
            "basics": [{"fname": "John", "lname": "Doe"}],
            "education": [],
        }
        report = validate_cv_json(data)
        assert report.is_valid
        assert report.error_count == 0

    def test_missing_basics_fails(self):
        """Test that missing 'basics' field fails validation."""
        data = {"education": []}
        report = validate_cv_json(data)
        assert not report.is_valid
        assert report.error_count > 0
        # Check that error message contains 'basics'
        error_messages = [i.message for i in report.issues]
        assert any("basics" in msg for msg in error_messages)

    def test_wrong_basics_type_fails(self):
        """Test that wrong type for 'basics' fails validation."""
        data = {"basics": {"fname": "John"}}  # Should be array
        report = validate_cv_json(data)
        assert not report.is_valid
        assert report.error_count > 0
        # Check that error mentions type
        error_messages = [i.message for i in report.issues]
        assert any("array" in msg for msg in error_messages)

    def test_missing_fname_fails(self):
        """Test that missing 'fname' in basics fails validation."""
        data = {"basics": [{"lname": "Doe"}]}
        report = validate_cv_json(data)
        assert not report.is_valid
        assert report.error_count > 0
        # Check that error mentions fname
        error_messages = [i.message for i in report.issues]
        assert any("fname" in msg for msg in error_messages)

    def test_error_paths_are_correct(self):
        """Test that error paths point to the correct location."""
        data = {"basics": [{"lname": "Doe"}]}  # Missing fname
        report = validate_cv_json(data)
        assert not report.is_valid
        # Check path format
        paths = [i.path for i in report.issues]
        assert any("$.basics[0]" in path for path in paths)


class TestValidateCvFile:
    """Tests for file validation."""

    def test_valid_file_passes(self):
        """Test validating a valid fixture file."""
        file_path = FIXTURES_DIR / "valid_minimal.json"
        report = validate_cv_file(file_path)
        assert report.is_valid
        assert report.error_count == 0
        assert report.file_path == file_path

    def test_missing_basics_file_fails(self):
        """Test validating a file missing basics."""
        file_path = FIXTURES_DIR / "missing_basics.json"
        report = validate_cv_file(file_path)
        assert not report.is_valid
        assert report.error_count > 0

    def test_wrong_type_file_fails(self):
        """Test validating a file with wrong type."""
        file_path = FIXTURES_DIR / "wrong_basics_type.json"
        report = validate_cv_file(file_path)
        assert not report.is_valid
        assert report.error_count > 0

    def test_nonexistent_file_fails(self):
        """Test validating a nonexistent file."""
        file_path = FIXTURES_DIR / "does_not_exist.json"
        report = validate_cv_file(file_path)
        assert not report.is_valid
        assert report.error_count > 0
        assert any("not found" in i.message.lower() for i in report.issues)


class TestValidationReport:
    """Tests for ValidationReport class."""

    def test_add_error_issue(self):
        """Test adding an error issue updates counts."""
        report = ValidationReport()
        issue = ValidationIssue(path="$.test", message="Test error", severity="error")
        report.add_issue(issue)

        assert not report.is_valid
        assert report.error_count == 1
        assert report.warning_count == 0

    def test_add_warning_issue(self):
        """Test adding a warning issue updates counts."""
        report = ValidationReport()
        issue = ValidationIssue(path="$.test", message="Test warning", severity="warning")
        report.add_issue(issue)

        assert report.is_valid  # Warnings don't invalidate
        assert report.error_count == 0
        assert report.warning_count == 1

    def test_format_text_output(self):
        """Test text formatting of report."""
        report = ValidationReport(file_path=Path("test.json"))
        issue = ValidationIssue(path="$.basics", message="Missing field", severity="error")
        report.add_issue(issue)

        text = report.format_text()
        assert "test.json" in text
        assert "$.basics" in text
        assert "Missing field" in text

    def test_to_dict(self):
        """Test dictionary serialization."""
        report = ValidationReport(file_path=Path("test.json"))
        issue = ValidationIssue(path="$.test", message="Error", severity="error")
        report.add_issue(issue)

        result = report.to_dict()
        assert result["file"] == "test.json"
        assert result["is_valid"] is False
        assert result["error_count"] == 1
        assert len(result["issues"]) == 1


class TestLintCLI:
    """Tests for the lint CLI command."""

    def test_lint_help(self, capsys):
        """Test that lint --help works."""
        with pytest.raises(SystemExit) as exc_info:
            main(["lint", "--help"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--strict" in captured.out
        assert "--file" in captured.out

    def test_lint_valid_file(self):
        """Test linting a valid file returns success."""
        file_path = str(FIXTURES_DIR / "valid_minimal.json")
        result = main(["lint", "--file", file_path])
        assert result == 0

    def test_lint_invalid_file(self):
        """Test linting an invalid file returns error code."""
        file_path = str(FIXTURES_DIR / "missing_basics.json")
        result = main(["lint", "--file", file_path])
        assert result == 5  # EXIT_VALIDATION_ERROR

    def test_lint_strict_mode(self):
        """Test strict mode treats all issues as errors."""
        file_path = str(FIXTURES_DIR / "missing_basics.json")
        result = main(["lint", "--file", file_path, "--strict"])
        assert result == 5  # EXIT_VALIDATION_ERROR

    def test_lint_json_format(self, capsys):
        """Test JSON output format."""
        file_path = str(FIXTURES_DIR / "valid_minimal.json")
        result = main(["lint", "--file", file_path, "--format", "json"])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["all_valid"] is True
        assert output["files_validated"] == 1

    def test_lint_nonexistent_file(self):
        """Test linting nonexistent file returns config error."""
        nonexistent_path = str(FIXTURES_DIR / "nonexistent_file.json")
        result = main(["lint", "--file", nonexistent_path])
        assert result == 2  # EXIT_CONFIG_ERROR


class TestLintParser:
    """Tests for lint command argument parsing."""

    def test_parser_lint_command(self):
        """Test parsing lint command arguments."""
        parser = create_parser()
        args = parser.parse_args(["lint", "--file", "test.json", "--strict"])

        assert args.command == "lint"
        assert args.file == "test.json"
        assert args.strict is True

    def test_parser_lint_name_filter(self):
        """Test parsing name filter option."""
        parser = create_parser()
        args = parser.parse_args(["lint", "--name", "ramin"])

        assert args.command == "lint"
        assert args.name == "ramin"

    def test_parser_lint_format_json(self):
        """Test parsing format option."""
        parser = create_parser()
        args = parser.parse_args(["lint", "--format", "json"])

        assert args.format == "json"
