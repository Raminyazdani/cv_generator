"""
Tests for cv_generator.errors_enhanced module.

Tests the enhanced exception system with context, suggestions, and error codes.
"""

import pytest

from cv_generator.errors_enhanced import (
    ConfigurationError,
    CVGeneratorError,
    LaTeXCompilationError,
    PluginError,
    TemplateError,
    ValidationError,
    get_latex_error_suggestion,
)
from cv_generator.latex import parse_latex_log


class TestCVGeneratorError:
    """Tests for CVGeneratorError base class."""

    def test_basic_error(self):
        """Test basic error with just a message."""
        error = CVGeneratorError("Something went wrong")
        assert "Something went wrong" in str(error)
        assert error.message == "Something went wrong"
        assert error.error_code == "CVGEN_ERROR"
        assert error.exit_code == 1

    def test_error_with_context(self):
        """Test error with context information."""
        error = CVGeneratorError(
            "File not found",
            context={"file": "/path/to/file.json", "operation": "load"},
        )
        assert "file: /path/to/file.json" in str(error)
        assert "operation: load" in str(error)
        assert error.context["file"] == "/path/to/file.json"

    def test_error_with_suggestions(self):
        """Test error with actionable suggestions."""
        error = CVGeneratorError(
            "Database error",
            suggestions=["Run cvgen db init", "Check permissions"],
        )
        assert "1. Run cvgen db init" in str(error)
        assert "2. Check permissions" in str(error)
        assert len(error.suggestions) == 2

    def test_error_with_cause(self):
        """Test error that wraps another exception."""
        original = ValueError("Invalid value")
        error = CVGeneratorError("Validation failed", cause=original)
        assert "Caused by: ValueError: Invalid value" in str(error)
        assert error.cause is original

    def test_to_dict(self):
        """Test conversion to dictionary."""
        error = CVGeneratorError(
            "Test error",
            context={"key": "value"},
            suggestions=["Fix it"],
            cause=RuntimeError("Original"),
        )
        d = error.to_dict()
        assert d["error_code"] == "CVGEN_ERROR"
        assert d["message"] == "Test error"
        assert d["context"] == {"key": "value"}
        assert d["suggestions"] == ["Fix it"]
        assert "Original" in d["cause"]
        assert d["exit_code"] == 1


class TestConfigurationError:
    """Tests for ConfigurationError class."""

    def test_basic_config_error(self):
        """Test basic configuration error."""
        error = ConfigurationError("Config file not found")
        assert error.error_code == "CVGEN_CONFIG"
        assert error.exit_code == 2

    def test_config_error_with_key(self):
        """Test configuration error with config key."""
        error = ConfigurationError(
            "Invalid value",
            config_key="build.latex_engine",
        )
        assert "config_key: build.latex_engine" in str(error)

    def test_config_error_with_file_path(self):
        """Test configuration error with file path."""
        error = ConfigurationError(
            "Cannot read config",
            file_path="/path/to/cv_generator.toml",
        )
        assert "file_path: /path/to/cv_generator.toml" in str(error)

    def test_config_error_with_expected_actual(self):
        """Test configuration error with expected and actual values."""
        error = ConfigurationError(
            "Type mismatch",
            config_key="build.timeout",
            expected="int",
            actual="string",
        )
        assert "expected: int" in str(error)
        assert "actual: string" in str(error)


class TestLaTeXCompilationError:
    """Tests for LaTeXCompilationError class."""

    def test_basic_latex_error(self):
        """Test basic LaTeX compilation error."""
        error = LaTeXCompilationError("Compilation failed")
        assert error.error_code == "CVGEN_LATEX"
        assert error.exit_code == 4

    def test_latex_error_with_files(self):
        """Test LaTeX error with file paths."""
        error = LaTeXCompilationError(
            "PDF not generated",
            tex_file="/path/to/main.tex",
            log_file="/path/to/main.log",
        )
        assert "tex_file: /path/to/main.tex" in str(error)
        assert "log_file: /path/to/main.log" in str(error)

    def test_latex_error_with_parsed_errors(self):
        """Test LaTeX error with parsed error messages."""
        error = LaTeXCompilationError(
            "LaTeX errors found",
            latex_errors=["! Undefined control sequence", "l.42 \\badcommand"],
        )
        assert "latex_errors" in str(error)

    def test_latex_error_default_suggestions(self):
        """Test that LaTeX errors have default suggestions."""
        error = LaTeXCompilationError("Failed")
        assert len(error.suggestions) > 0
        assert any("special characters" in s for s in error.suggestions)


class TestPluginError:
    """Tests for PluginError class."""

    def test_basic_plugin_error(self):
        """Test basic plugin error."""
        error = PluginError("Plugin failed")
        assert error.error_code == "CVGEN_PLUGIN"
        assert error.exit_code == 5

    def test_plugin_error_with_details(self):
        """Test plugin error with plugin and hook names."""
        error = PluginError(
            "Hook execution failed",
            plugin_name="my_plugin",
            hook_name="pre_validate",
        )
        assert "plugin_name: my_plugin" in str(error)
        assert "hook_name: pre_validate" in str(error)

    def test_plugin_error_abort_on_error(self):
        """Test plugin error with abort_on_error flag."""
        error = PluginError(
            "Critical failure",
            plugin_name="critical_plugin",
            abort_on_error=True,
        )
        assert error.abort_on_error is True
        assert "abort_on_error: True" in str(error)


class TestValidationError:
    """Tests for ValidationError class."""

    def test_basic_validation_error(self):
        """Test basic validation error."""
        error = ValidationError("Invalid CV data")
        assert error.error_code == "CVGEN_VALIDATION"
        assert error.exit_code == 6

    def test_validation_error_with_details(self):
        """Test validation error with file and field path."""
        error = ValidationError(
            "Missing required field",
            cv_file="/path/to/cv.json",
            field_path="basics.name",
        )
        assert "cv_file: /path/to/cv.json" in str(error)
        assert "field_path: basics.name" in str(error)

    def test_validation_error_with_multiple_errors(self):
        """Test validation error with multiple validation errors."""
        error = ValidationError(
            "Multiple validation errors",
            validation_errors=["Missing 'name'", "Invalid 'email' format"],
        )
        assert "validation_errors" in str(error)


class TestTemplateError:
    """Tests for TemplateError class."""

    def test_basic_template_error(self):
        """Test basic template error."""
        error = TemplateError("Template rendering failed")
        assert error.error_code == "CVGEN_TEMPLATE"
        assert error.exit_code == 3

    def test_template_error_with_details(self):
        """Test template error with template name and line."""
        error = TemplateError(
            "Syntax error",
            template_name="education.tex",
            template_line=42,
            cv_file="/path/to/cv.json",
        )
        assert "template_name: education.tex" in str(error)
        assert "template_line: 42" in str(error)
        assert "cv_file: /path/to/cv.json" in str(error)


class TestLaTeXErrorParsing:
    """Tests for LaTeX error parsing functions."""

    def test_parse_latex_log_basic(self):
        """Test parsing LaTeX log for errors."""
        log_content = """
This is XeTeX, Version 3.14159265
(./main.tex
! Undefined control sequence.
l.42 \\badcommand
The control sequence at the end of the top line
"""
        errors, suggestions = parse_latex_log(log_content)
        assert len(errors) >= 1
        assert any("Undefined control sequence" in e for e in errors)

    def test_parse_latex_log_empty(self):
        """Test parsing empty log."""
        errors, suggestions = parse_latex_log("")
        assert errors == []
        assert suggestions == []

    def test_parse_latex_log_limits_results(self):
        """Test that error parsing limits to 10 errors."""
        # Create log with many errors
        log_content = "\n".join([f"! Error {i}" for i in range(20)])
        errors, suggestions = parse_latex_log(log_content)
        assert len(errors) <= 10

    def test_get_latex_error_suggestion_undefined_command(self):
        """Test suggestion for undefined control sequence."""
        suggestion = get_latex_error_suggestion("! Undefined control sequence")
        assert suggestion is not None
        assert "template" in suggestion.lower() or "command" in suggestion.lower()

    def test_get_latex_error_suggestion_missing_dollar(self):
        """Test suggestion for missing $ error."""
        suggestion = get_latex_error_suggestion("! Missing $ inserted")
        assert suggestion is not None
        assert "$" in suggestion

    def test_get_latex_error_suggestion_unknown_error(self):
        """Test that unknown errors return None."""
        suggestion = get_latex_error_suggestion("! Some unknown error type xyz")
        assert suggestion is None
