"""
Tests for cv_generator.paths module.

Tests the path resolution and ArtifactPaths class.
"""

from pathlib import Path

import pytest

from cv_generator.paths import (
    ArtifactPaths,
    get_default_output_path,
    get_default_result_path,
    get_legacy_pdf_path,
    get_run_log_path,
)


class TestArtifactPaths:
    """Tests for the ArtifactPaths class."""

    def test_basic_creation(self, tmp_path):
        """Test creating ArtifactPaths with basic parameters."""
        paths = ArtifactPaths(profile="ramin", lang="en", output_root=tmp_path)

        assert paths.profile == "ramin"
        assert paths.lang == "en"
        assert paths.output_root == tmp_path
        assert paths.variant is None

    def test_pdf_paths(self, tmp_path):
        """Test PDF path generation."""
        paths = ArtifactPaths(profile="ramin", lang="en", output_root=tmp_path)

        assert paths.pdf_dir == tmp_path / "pdf" / "ramin" / "en"
        assert paths.pdf_path == tmp_path / "pdf" / "ramin" / "en" / "cv.pdf"
        assert paths.pdf_named_path == tmp_path / "pdf" / "ramin" / "en" / "ramin_en.pdf"

    def test_latex_paths(self, tmp_path):
        """Test LaTeX path generation."""
        paths = ArtifactPaths(profile="ramin", lang="de", output_root=tmp_path)

        assert paths.latex_dir == tmp_path / "latex" / "ramin" / "de"
        assert paths.tex_path == tmp_path / "latex" / "ramin" / "de" / "main.tex"
        assert paths.sections_dir == tmp_path / "latex" / "ramin" / "de" / "sections"
        assert paths.build_dir == tmp_path / "latex" / "ramin" / "de" / "build"

    def test_json_paths(self, tmp_path):
        """Test JSON path generation."""
        paths = ArtifactPaths(profile="ramin", lang="fa", output_root=tmp_path)

        assert paths.json_dir == tmp_path / "json" / "ramin" / "fa"
        assert paths.json_path == tmp_path / "json" / "ramin" / "fa" / "cv.json"

    def test_logs_dir(self, tmp_path):
        """Test logs directory path."""
        paths = ArtifactPaths(profile="ramin", lang="en", output_root=tmp_path)

        assert paths.logs_dir == tmp_path / "logs"

    def test_with_variant(self, tmp_path):
        """Test paths with variant specified."""
        paths = ArtifactPaths(
            profile="ramin",
            lang="en",
            variant="academic",
            output_root=tmp_path
        )

        assert paths.pdf_dir == tmp_path / "pdf" / "ramin" / "academic" / "en"
        assert paths.latex_dir == tmp_path / "latex" / "ramin" / "academic" / "en"
        assert paths.json_dir == tmp_path / "json" / "ramin" / "academic" / "en"

    def test_ensure_dirs(self, tmp_path):
        """Test that ensure_dirs creates the necessary directories."""
        paths = ArtifactPaths(profile="test", lang="en", output_root=tmp_path)

        # Directories should not exist yet
        assert not paths.pdf_dir.exists()
        assert not paths.latex_dir.exists()

        # Create directories
        paths.ensure_dirs()

        # Now they should exist
        assert paths.pdf_dir.exists()
        assert paths.latex_dir.exists()
        assert paths.sections_dir.exists()

    def test_repr(self, tmp_path):
        """Test string representation."""
        paths = ArtifactPaths(profile="ramin", lang="en", output_root=tmp_path)

        repr_str = repr(paths)
        assert "ArtifactPaths" in repr_str
        assert "ramin" in repr_str
        assert "en" in repr_str

    def test_os_agnostic_paths(self, tmp_path):
        """Test that paths are OS-agnostic (use Path objects)."""
        paths = ArtifactPaths(profile="user", lang="de", output_root=tmp_path)

        # All path properties should return Path objects
        assert isinstance(paths.pdf_dir, Path)
        assert isinstance(paths.pdf_path, Path)
        assert isinstance(paths.latex_dir, Path)
        assert isinstance(paths.tex_path, Path)
        assert isinstance(paths.json_dir, Path)
        assert isinstance(paths.json_path, Path)
        assert isinstance(paths.logs_dir, Path)


class TestPathHelpers:
    """Tests for path helper functions."""

    def test_get_default_result_path_returns_latex_subdir(self):
        """Test that deprecated get_default_result_path now returns output/latex."""
        result_path = get_default_result_path()

        # Should be under output/latex now (for backward compatibility)
        assert result_path.name == "latex"
        assert result_path.parent.name == "output"

    def test_get_run_log_path(self, tmp_path):
        """Test run log path generation."""
        log_path = get_run_log_path(output_root=tmp_path)

        # Should be in logs directory
        assert log_path.parent.name == "logs"
        assert log_path.parent.parent == tmp_path

        # Should have correct naming pattern
        assert log_path.name.startswith("run_")
        assert log_path.suffix == ".log"

        # Directory should be created
        assert log_path.parent.exists()

    def test_get_legacy_pdf_path(self, tmp_path):
        """Test legacy PDF path generation."""
        legacy_path = get_legacy_pdf_path("ramin", "en", output_root=tmp_path)

        assert legacy_path == tmp_path / "ramin_en.pdf"

    def test_get_legacy_pdf_path_default_output(self):
        """Test legacy PDF path with default output."""
        legacy_path = get_legacy_pdf_path("ramin", "de")

        assert legacy_path.name == "ramin_de.pdf"
        assert legacy_path.parent == get_default_output_path()
