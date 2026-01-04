"""
Tests for the build report module.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from cv_generator.report import (
    BuildArtifact,
    BuildReport,
    get_reports_dir,
    write_build_report,
)


class TestBuildArtifact:
    """Tests for BuildArtifact dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        artifact = BuildArtifact(
            profile="ramin",
            lang="en",
            pdf_path="/output/pdf/ramin/en/ramin_en.pdf",
            tex_path="/output/latex/ramin/en/main.tex",
            success=True,
        )
        result = artifact.to_dict()

        assert result["profile"] == "ramin"
        assert result["lang"] == "en"
        assert result["pdf_path"] == "/output/pdf/ramin/en/ramin_en.pdf"
        assert result["tex_path"] == "/output/latex/ramin/en/main.tex"
        assert result["success"] is True
        assert result["error"] is None
        assert result["skipped"] is False

    def test_failed_artifact(self):
        """Test failed artifact representation."""
        artifact = BuildArtifact(
            profile="ramin",
            lang="de",
            success=False,
            error="LaTeX compilation failed",
        )
        result = artifact.to_dict()

        assert result["success"] is False
        assert result["error"] == "LaTeX compilation failed"


class TestBuildReport:
    """Tests for BuildReport dataclass."""

    def test_default_values(self):
        """Test default report values."""
        report = BuildReport()

        assert report.run_id is not None
        assert len(report.run_id) == 8
        assert report.platform_info is not None
        assert "system" in report.platform_info
        assert report.artifacts == []
        assert report.warnings == []
        assert report.errors == []

    def test_add_artifact(self):
        """Test adding artifacts to report."""
        report = BuildReport()
        artifact = BuildArtifact(profile="ramin", lang="en")
        report.add_artifact(artifact)

        assert len(report.artifacts) == 1
        assert report.total_count == 1

    def test_success_failure_counts(self):
        """Test success and failure counting."""
        report = BuildReport()
        report.add_artifact(BuildArtifact(profile="a", lang="en", success=True))
        report.add_artifact(BuildArtifact(profile="b", lang="en", success=True))
        report.add_artifact(BuildArtifact(profile="c", lang="en", success=False))
        report.add_artifact(BuildArtifact(profile="d", lang="en", success=True, skipped=True))

        assert report.total_count == 4
        assert report.success_count == 3
        assert report.failure_count == 1
        assert report.skipped_count == 1

    def test_timing(self):
        """Test start and finish timing."""
        report = BuildReport()
        report.start()
        assert report.datetime_started is not None

        report.finish()
        assert report.datetime_finished is not None
        assert report.duration_seconds is not None
        assert report.duration_seconds >= 0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        report = BuildReport(dry_run=True, incremental=True, variant="academic")
        report.add_artifact(BuildArtifact(profile="ramin", lang="en"))
        report.add_warning("Font not found")
        report.add_error("Compilation failed")

        result = report.to_dict()

        assert result["tool_version"] is not None
        assert result["options"]["dry_run"] is True
        assert result["options"]["incremental"] is True
        assert result["options"]["variant"] == "academic"
        assert result["summary"]["total"] == 1
        assert len(result["warnings"]) == 1
        assert len(result["errors"]) == 1

    def test_to_json(self):
        """Test JSON serialization."""
        report = BuildReport()
        report.add_artifact(BuildArtifact(profile="ramin", lang="en"))

        json_str = report.to_json()
        parsed = json.loads(json_str)

        assert "run_id" in parsed
        assert "artifacts" in parsed
        assert len(parsed["artifacts"]) == 1

    def test_to_markdown(self):
        """Test Markdown generation."""
        report = BuildReport()
        report.add_artifact(BuildArtifact(
            profile="ramin",
            lang="en",
            pdf_path="/output/ramin_en.pdf",
            success=True,
        ))
        report.add_warning("Font substituted")

        md = report.to_markdown()

        assert "# Build Report" in md
        assert "ramin_en" in md
        assert "✅" in md
        assert "Font substituted" in md


class TestGetReportsDir:
    """Tests for get_reports_dir function."""

    def test_with_custom_root(self, tmp_path):
        """Test with custom output root."""
        result = get_reports_dir(tmp_path)
        assert result == tmp_path / "reports"

    def test_returns_reports_subdir(self):
        """Test that reports directory is a subdirectory."""
        result = get_reports_dir(Path("/some/output"))
        assert result.name == "reports"
        assert result.parent == Path("/some/output")


class TestWriteBuildReport:
    """Tests for write_build_report function."""

    def test_writes_both_formats(self, tmp_path):
        """Test that both JSON and Markdown files are written."""
        report = BuildReport()
        report.add_artifact(BuildArtifact(profile="test", lang="en"))
        report.start()
        report.finish()

        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        result = write_build_report(report, tmp_path, timestamp)

        assert "json" in result
        assert "md" in result

        json_path = result["json"]
        md_path = result["md"]

        assert json_path.exists()
        assert md_path.exists()
        assert json_path.name == "build_20240115_103000.json"
        assert md_path.name == "build_20240115_103000.md"

    def test_json_is_valid(self, tmp_path):
        """Test that written JSON is valid."""
        report = BuildReport()
        report.add_artifact(BuildArtifact(profile="test", lang="en"))

        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        result = write_build_report(report, tmp_path, timestamp)

        with open(result["json"], "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "run_id" in data
        assert "artifacts" in data
        assert len(data["artifacts"]) == 1

    def test_creates_reports_directory(self, tmp_path):
        """Test that reports directory is created if it doesn't exist."""
        report = BuildReport()
        output_root = tmp_path / "nested" / "output"

        result = write_build_report(report, output_root)

        reports_dir = output_root / "reports"
        assert reports_dir.exists()
