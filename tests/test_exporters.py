"""
Tests for cv_generator.exporters module.

Tests the HTML and Markdown export functionality.
"""

from pathlib import Path

import pytest

from cv_generator.exporters import (
    HTMLExporter,
    MarkdownExporter,
    get_exporter,
    list_exporters,
)
from cv_generator.exporters.base import ExportResult

# Sample CV data for testing
SAMPLE_CV_DATA = {
    "basics": [
        {
            "fname": "Test",
            "lname": "User",
            "email": "test@example.com",
            "phone": {"formatted": "+1 555-0100"},
            "label": ["Software Engineer", "Developer"],
            "location": [{"city": "San Francisco", "region": "CA", "country": "USA"}],
        }
    ],
    "education": [
        {
            "institution": "Test University",
            "area": "Computer Science",
            "studyType": "Bachelor's",
        }
    ],
    "experiences": [
        {
            "role": "Senior Developer",
            "institution": "Test Corp",
            "duration": "2020-2023",
            "description": "Led development of core features",
        }
    ],
    "skills": {
        "Technical Skills": {
            "Programming": [
                {"short_name": "Python", "long_name": "Python 3.x"},
                {"short_name": "JavaScript"},
            ],
        },
    },
    "projects": [
        {
            "title": "Open Source Project",
            "description": "A sample project",
            "url": "https://github.com/example/project",
        }
    ],
}


class TestExporterRegistry:
    """Tests for the exporter registry functions."""

    def test_list_exporters_returns_available_formats(self):
        """Test that list_exporters returns known formats."""
        formats = list_exporters()
        assert "html" in formats
        assert "md" in formats

    def test_get_exporter_returns_html_exporter(self):
        """Test getting HTML exporter by name."""
        exporter = get_exporter("html")
        assert exporter is not None
        assert isinstance(exporter, HTMLExporter)
        assert exporter.format_name == "html"

    def test_get_exporter_returns_md_exporter(self):
        """Test getting Markdown exporter by name."""
        exporter = get_exporter("md")
        assert exporter is not None
        assert isinstance(exporter, MarkdownExporter)
        assert exporter.format_name == "md"

    def test_get_exporter_returns_none_for_unknown(self):
        """Test that unknown format returns None."""
        exporter = get_exporter("unknown_format")
        assert exporter is None


class TestHTMLExporter:
    """Tests for the HTML exporter."""

    def test_html_export_creates_file(self, tmp_path):
        """Test that HTML export creates a file."""
        exporter = HTMLExporter()
        result = exporter.export(
            cv_data=SAMPLE_CV_DATA,
            output_dir=tmp_path,
            profile_name="testuser",
            lang="en",
        )

        assert result.success is True
        assert result.output_path is not None
        assert result.output_path.exists()
        assert result.output_path.suffix == ".html"

    def test_html_export_contains_name(self, tmp_path):
        """Test that exported HTML contains the user's name."""
        exporter = HTMLExporter()
        result = exporter.export(
            cv_data=SAMPLE_CV_DATA,
            output_dir=tmp_path,
            profile_name="testuser",
            lang="en",
        )

        content = result.output_path.read_text(encoding="utf-8")
        assert "Test User" in content

    def test_html_export_contains_email(self, tmp_path):
        """Test that exported HTML contains contact information."""
        exporter = HTMLExporter()
        result = exporter.export(
            cv_data=SAMPLE_CV_DATA,
            output_dir=tmp_path,
            profile_name="testuser",
            lang="en",
        )

        content = result.output_path.read_text(encoding="utf-8")
        assert "test@example.com" in content

    def test_html_export_contains_experience_section(self, tmp_path):
        """Test that exported HTML contains experience section."""
        exporter = HTMLExporter()
        result = exporter.export(
            cv_data=SAMPLE_CV_DATA,
            output_dir=tmp_path,
            profile_name="testuser",
            lang="en",
        )

        content = result.output_path.read_text(encoding="utf-8")
        assert "Experience" in content
        assert "Senior Developer" in content

    def test_html_export_contains_skills(self, tmp_path):
        """Test that exported HTML contains skills."""
        exporter = HTMLExporter()
        result = exporter.export(
            cv_data=SAMPLE_CV_DATA,
            output_dir=tmp_path,
            profile_name="testuser",
            lang="en",
        )

        content = result.output_path.read_text(encoding="utf-8")
        assert "Skills" in content
        assert "Python" in content

    def test_html_export_output_path_structure(self, tmp_path):
        """Test that output path follows expected structure."""
        exporter = HTMLExporter()
        result = exporter.export(
            cv_data=SAMPLE_CV_DATA,
            output_dir=tmp_path,
            profile_name="testuser",
            lang="en",
        )

        # Expected path: tmp_path/html/testuser/en/cv.html
        expected_path = tmp_path / "html" / "testuser" / "en" / "cv.html"
        assert result.output_path == expected_path

    def test_html_export_rtl_language(self, tmp_path):
        """Test that RTL language (Persian) sets correct direction."""
        exporter = HTMLExporter()
        result = exporter.export(
            cv_data=SAMPLE_CV_DATA,
            output_dir=tmp_path,
            profile_name="testuser",
            lang="fa",
        )

        content = result.output_path.read_text(encoding="utf-8")
        assert 'dir="rtl"' in content


class TestMarkdownExporter:
    """Tests for the Markdown exporter."""

    def test_md_export_creates_file(self, tmp_path):
        """Test that Markdown export creates a file."""
        exporter = MarkdownExporter()
        result = exporter.export(
            cv_data=SAMPLE_CV_DATA,
            output_dir=tmp_path,
            profile_name="testuser",
            lang="en",
        )

        assert result.success is True
        assert result.output_path is not None
        assert result.output_path.exists()
        assert result.output_path.suffix == ".md"

    def test_md_export_contains_h1_name(self, tmp_path):
        """Test that exported Markdown contains H1 with name."""
        exporter = MarkdownExporter()
        result = exporter.export(
            cv_data=SAMPLE_CV_DATA,
            output_dir=tmp_path,
            profile_name="testuser",
            lang="en",
        )

        content = result.output_path.read_text(encoding="utf-8")
        assert "# Test User" in content

    def test_md_export_contains_h2_sections(self, tmp_path):
        """Test that exported Markdown contains H2 section headers."""
        exporter = MarkdownExporter()
        result = exporter.export(
            cv_data=SAMPLE_CV_DATA,
            output_dir=tmp_path,
            profile_name="testuser",
            lang="en",
        )

        content = result.output_path.read_text(encoding="utf-8")
        assert "## Experience" in content
        assert "## Education" in content
        assert "## Skills" in content

    def test_md_export_contains_experience_entries(self, tmp_path):
        """Test that exported Markdown contains experience entries."""
        exporter = MarkdownExporter()
        result = exporter.export(
            cv_data=SAMPLE_CV_DATA,
            output_dir=tmp_path,
            profile_name="testuser",
            lang="en",
        )

        content = result.output_path.read_text(encoding="utf-8")
        assert "Senior Developer" in content
        assert "Test Corp" in content

    def test_md_export_contains_project_links(self, tmp_path):
        """Test that exported Markdown contains project links."""
        exporter = MarkdownExporter()
        result = exporter.export(
            cv_data=SAMPLE_CV_DATA,
            output_dir=tmp_path,
            profile_name="testuser",
            lang="en",
        )

        content = result.output_path.read_text(encoding="utf-8")
        assert "Open Source Project" in content
        assert "https://github.com/example/project" in content

    def test_md_export_output_path_structure(self, tmp_path):
        """Test that output path follows expected structure."""
        exporter = MarkdownExporter()
        result = exporter.export(
            cv_data=SAMPLE_CV_DATA,
            output_dir=tmp_path,
            profile_name="testuser",
            lang="en",
        )

        # Expected path: tmp_path/md/testuser/en/cv.md
        expected_path = tmp_path / "md" / "testuser" / "en" / "cv.md"
        assert result.output_path == expected_path


class TestExportResult:
    """Tests for ExportResult dataclass."""

    def test_export_result_success(self):
        """Test successful export result."""
        result = ExportResult(
            format_name="html",
            success=True,
            output_path=Path("/output/cv.html"),
        )
        assert result.success is True
        assert result.error is None
        assert "✅" in repr(result)

    def test_export_result_failure(self):
        """Test failed export result."""
        result = ExportResult(
            format_name="html",
            success=False,
            error="File write failed",
        )
        assert result.success is False
        assert result.error == "File write failed"
        assert "❌" in repr(result)


class TestExportWithRealData:
    """Tests using the fixtures from tests/fixtures/ramin/."""

    @pytest.fixture
    def ramin_cv_data(self):
        """Load the ramin test CV data."""
        import json

        fixture_path = Path(__file__).parent / "fixtures" / "ramin" / "cv.en.json"
        if fixture_path.exists():
            with open(fixture_path, encoding="utf-8") as f:
                return json.load(f)
        return SAMPLE_CV_DATA

    def test_html_export_with_fixture_data(self, tmp_path, ramin_cv_data):
        """Test HTML export with fixture data."""
        exporter = HTMLExporter()
        result = exporter.export(
            cv_data=ramin_cv_data,
            output_dir=tmp_path,
            profile_name="ramin",
            lang="en",
        )

        assert result.success is True
        content = result.output_path.read_text(encoding="utf-8")
        assert "Ramin" in content

    def test_md_export_with_fixture_data(self, tmp_path, ramin_cv_data):
        """Test Markdown export with fixture data."""
        exporter = MarkdownExporter()
        result = exporter.export(
            cv_data=ramin_cv_data,
            output_dir=tmp_path,
            profile_name="ramin",
            lang="en",
        )

        assert result.success is True
        content = result.output_path.read_text(encoding="utf-8")
        assert "# Ramin" in content
