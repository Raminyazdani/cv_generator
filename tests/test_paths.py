"""
Tests for cv_generator.paths module.

Tests the path resolution helpers.
"""

from pathlib import Path

import pytest

from cv_generator.paths import (
    get_default_output_path,
    get_default_cvs_path,
    get_repo_root,
    resolve_path,
    reset_repo_root_cache,
)


class TestPathHelpers:
    """Tests for path helper functions."""

    def test_get_repo_root_returns_path(self):
        """Test that get_repo_root returns a Path or None."""
        root = get_repo_root()
        assert root is None or isinstance(root, Path)

    def test_get_default_output_path(self):
        """Test get_default_output_path returns a valid path."""
        output_path = get_default_output_path()
        assert isinstance(output_path, Path)
        assert output_path.name == "output"

    def test_get_default_cvs_path(self):
        """Test get_default_cvs_path returns a valid path."""
        cvs_path = get_default_cvs_path()
        assert isinstance(cvs_path, Path)
        assert cvs_path.name == "cvs"

    def test_resolve_path_absolute(self, tmp_path):
        """Test resolving an absolute path."""
        abs_path = tmp_path / "test"
        resolved = resolve_path(abs_path)
        assert resolved == abs_path.resolve()

    def test_resolve_path_relative(self, tmp_path):
        """Test resolving a relative path."""
        resolved = resolve_path("some/relative/path", base=tmp_path)
        assert resolved == (tmp_path / "some/relative/path").resolve()

    def test_reset_repo_root_cache(self):
        """Test that cache can be reset."""
        # This shouldn't raise an error
        reset_repo_root_cache()
        # And get_repo_root should still work
        root = get_repo_root()
        assert root is None or isinstance(root, Path)
