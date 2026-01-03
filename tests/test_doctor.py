"""
Tests for cv_generator.doctor module.

Tests the system health check functionality:
- Python version check
- Dependency import checks
- LaTeX engine check
- Template parsing check
- Output directory writability check
- Database health check
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cv_generator.doctor import (
    CheckResult,
    CheckStatus,
    DoctorReport,
    check_database,
    check_dependencies,
    check_latex_engine,
    check_output_writability,
    check_python_version,
    check_templates,
    run_checks,
)


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_ok_status_icon(self):
        """Test OK status displays correct icon."""
        result = CheckResult(
            name="Test",
            status=CheckStatus.OK,
            detail="All good",
        )
        assert result.icon == "✅"

    def test_warning_status_icon(self):
        """Test warning status displays correct icon."""
        result = CheckResult(
            name="Test",
            status=CheckStatus.WARNING,
            detail="Something to note",
        )
        assert result.icon == "⚠️"

    def test_error_status_icon(self):
        """Test error status displays correct icon."""
        result = CheckResult(
            name="Test",
            status=CheckStatus.ERROR,
            detail="Something wrong",
        )
        assert result.icon == "❌"

    def test_to_dict_basic(self):
        """Test basic to_dict conversion."""
        result = CheckResult(
            name="Test Check",
            status=CheckStatus.OK,
            detail="Everything is fine",
        )
        d = result.to_dict()
        assert d["name"] == "Test Check"
        assert d["status"] == "ok"
        assert d["detail"] == "Everything is fine"
        assert "fix_hint" not in d

    def test_to_dict_with_fix_hint(self):
        """Test to_dict includes fix_hint when present."""
        result = CheckResult(
            name="Test Check",
            status=CheckStatus.ERROR,
            detail="Something wrong",
            fix_hint="Try fixing it",
        )
        d = result.to_dict()
        assert d["fix_hint"] == "Try fixing it"


class TestDoctorReport:
    """Tests for DoctorReport dataclass."""

    def test_empty_report_is_healthy(self):
        """Test that an empty report is healthy."""
        report = DoctorReport()
        assert report.is_healthy
        assert report.ok_count == 0
        assert report.warning_count == 0
        assert report.error_count == 0

    def test_all_ok_is_healthy(self):
        """Test that a report with all OK checks is healthy."""
        report = DoctorReport(
            checks=[
                CheckResult("A", CheckStatus.OK, "Good"),
                CheckResult("B", CheckStatus.OK, "Good"),
            ]
        )
        assert report.is_healthy
        assert report.ok_count == 2
        assert report.error_count == 0

    def test_warning_is_still_healthy(self):
        """Test that warnings don't make report unhealthy."""
        report = DoctorReport(
            checks=[
                CheckResult("A", CheckStatus.OK, "Good"),
                CheckResult("B", CheckStatus.WARNING, "Note"),
            ]
        )
        assert report.is_healthy
        assert report.warning_count == 1

    def test_error_makes_unhealthy(self):
        """Test that errors make report unhealthy."""
        report = DoctorReport(
            checks=[
                CheckResult("A", CheckStatus.OK, "Good"),
                CheckResult("B", CheckStatus.ERROR, "Bad"),
            ]
        )
        assert not report.is_healthy
        assert report.error_count == 1

    def test_to_dict(self):
        """Test to_dict conversion."""
        report = DoctorReport(
            checks=[
                CheckResult("A", CheckStatus.OK, "Good"),
                CheckResult("B", CheckStatus.WARNING, "Note"),
            ]
        )
        d = report.to_dict()
        assert d["healthy"] is True
        assert d["summary"]["ok"] == 1
        assert d["summary"]["warnings"] == 1
        assert d["summary"]["errors"] == 0
        assert len(d["checks"]) == 2

    def test_format_text_contains_summary(self):
        """Test format_text includes summary line."""
        report = DoctorReport(
            checks=[
                CheckResult("Python", CheckStatus.OK, "3.12"),
            ]
        )
        text = report.format_text()
        assert "Health Check" in text
        assert "Python" in text
        assert "OK: 1" in text


class TestCheckPythonVersion:
    """Tests for check_python_version function."""

    def test_current_version_ok(self):
        """Test that current Python version passes."""
        result = check_python_version()
        # Current Python should be >= 3.9
        assert result.status == CheckStatus.OK
        assert "Python" in result.detail

    def test_old_version_fails(self, monkeypatch):
        """Test that old Python version fails."""
        # Create a mock version_info object with attributes
        class MockVersionInfo:
            major = 3
            minor = 8

        monkeypatch.setattr(sys, "version_info", MockVersionInfo())
        result = check_python_version()
        assert result.status == CheckStatus.ERROR
        assert result.fix_hint is not None


class TestCheckDependencies:
    """Tests for check_dependencies function."""

    def test_all_dependencies_installed(self):
        """Test that all required dependencies are found."""
        results = check_dependencies()
        assert len(results) == 3  # jinja2, flask, jsonschema
        for result in results:
            assert result.status == CheckStatus.OK

    def test_missing_dependency_detected(self, monkeypatch):
        """Test that missing dependency is detected."""
        import builtins

        # Mock jinja2 import to fail
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "jinja2":
                raise ImportError("No module named 'jinja2'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        results = check_dependencies()
        jinja_result = next(r for r in results if "jinja2" in r.name)
        assert jinja_result.status == CheckStatus.ERROR
        assert "pip install" in jinja_result.fix_hint


class TestCheckLatexEngine:
    """Tests for check_latex_engine function."""

    def test_xelatex_not_found(self, monkeypatch):
        """Test behavior when xelatex is not found."""
        monkeypatch.setattr("shutil.which", lambda x: None)
        result = check_latex_engine()
        assert result.status == CheckStatus.WARNING
        assert "not found" in result.detail
        assert result.fix_hint is not None

    def test_xelatex_found_success(self, monkeypatch):
        """Test behavior when xelatex is found and works."""
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/xelatex")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "XeTeX 3.141592653-2.6-0.999993 (TeX Live 2021)"

        with patch("subprocess.run", return_value=mock_result):
            result = check_latex_engine()
            assert result.status == CheckStatus.OK
            assert "XeTeX" in result.detail or "xelatex" in result.detail.lower()

    def test_xelatex_found_but_fails(self, monkeypatch):
        """Test behavior when xelatex is found but version check fails."""
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/xelatex")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = check_latex_engine()
            assert result.status == CheckStatus.WARNING

    def test_xelatex_timeout(self, monkeypatch):
        """Test behavior when xelatex times out."""
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/xelatex")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("xelatex", 10)):
            result = check_latex_engine()
            assert result.status == CheckStatus.WARNING
            assert "timed out" in result.detail


class TestCheckTemplates:
    """Tests for check_templates function."""

    def test_templates_exist_and_parse(self, tmp_path):
        """Test with valid templates."""
        # Create a simple valid template
        template_file = tmp_path / "test.tex"
        template_file.write_text(r"""
\documentclass{article}
\begin{document}
Hello <VAR> name </VAR>
\end{document}
""")

        results = check_templates(tmp_path)
        assert len(results) == 1
        assert results[0].status == CheckStatus.OK

    def test_templates_directory_not_found(self, tmp_path):
        """Test with non-existent directory."""
        results = check_templates(tmp_path / "nonexistent")
        assert len(results) == 1
        assert results[0].status == CheckStatus.ERROR
        assert "not found" in results[0].detail

    def test_no_templates_found(self, tmp_path):
        """Test with empty templates directory."""
        results = check_templates(tmp_path)
        assert len(results) == 1
        assert results[0].status == CheckStatus.WARNING
        assert "No .tex" in results[0].detail

    def test_template_parse_error(self, tmp_path):
        """Test with invalid template syntax."""
        template_file = tmp_path / "bad.tex"
        # Invalid Jinja2 syntax
        template_file.write_text("<BLOCK> if unclosed")

        results = check_templates(tmp_path)
        assert len(results) == 1
        assert results[0].status == CheckStatus.ERROR
        assert "bad.tex" in results[0].detail or "bad.tex" in results[0].fix_hint


class TestCheckOutputWritability:
    """Tests for check_output_writability function."""

    def test_writable_directory(self, tmp_path):
        """Test with writable directory."""
        result = check_output_writability(tmp_path)
        assert result.status == CheckStatus.OK
        assert "Writable" in result.detail

    def test_creates_directory_if_needed(self, tmp_path):
        """Test that directory is created if it doesn't exist."""
        new_dir = tmp_path / "new_output"
        result = check_output_writability(new_dir)
        assert result.status == CheckStatus.OK
        assert new_dir.exists()


class TestCheckDatabase:
    """Tests for check_database function."""

    def test_no_database(self, monkeypatch):
        """Test when no database exists."""
        # Mock the db path to point to nonexistent location
        monkeypatch.setattr(
            "cv_generator.doctor.get_repo_root",
            lambda: Path("/nonexistent"),
        )

        result = check_database()
        assert result.status == CheckStatus.OK
        assert "No database found" in result.detail


class TestRunChecks:
    """Tests for run_checks function."""

    def test_run_checks_returns_report(self, tmp_path):
        """Test that run_checks returns a valid report."""
        # Create a simple template
        template_file = tmp_path / "templates" / "test.tex"
        template_file.parent.mkdir(parents=True, exist_ok=True)
        template_file.write_text(r"\documentclass{article}")

        output_dir = tmp_path / "output"

        report = run_checks(
            template_dir=tmp_path / "templates",
            output_dir=output_dir,
            check_db=False,
        )

        assert isinstance(report, DoctorReport)
        assert len(report.checks) > 0

    def test_run_checks_includes_all_categories(self):
        """Test that run_checks includes checks from all categories."""
        report = run_checks(check_db=True)

        # Check that we have checks from different categories
        check_names = [c.name for c in report.checks]

        assert any("Python" in name for name in check_names)
        assert any("Dependency" in name for name in check_names)
        assert any("LaTeX" in name for name in check_names)
        assert any("Template" in name for name in check_names)
        assert any("Output" in name for name in check_names)
        assert any("Database" in name for name in check_names)


class TestCLIIntegration:
    """Tests for CLI integration of doctor command."""

    def test_doctor_help(self, capsys):
        """Test that doctor --help works."""
        from cv_generator.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["doctor", "--help"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--format" in captured.out
        assert "--templates-dir" in captured.out

    def test_doctor_runs(self):
        """Test that doctor command runs without error."""
        from cv_generator.cli import main

        # Should run without raising
        result = main(["doctor"])
        # Result should be 0 (healthy) or 2 (unhealthy) - not an error
        assert result in (0, 2)

    def test_doctor_json_output(self, capsys):
        """Test that doctor --format json produces valid JSON."""
        import json

        from cv_generator.cli import main

        main(["doctor", "--format", "json"])
        captured = capsys.readouterr()

        # Should be valid JSON
        data = json.loads(captured.out)
        assert "healthy" in data
        assert "checks" in data
        assert "summary" in data
