"""
Tests for the cleanup module with backup functionality.
"""

import tarfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from cv_generator.cleanup import (
    confirm_action,
    create_backup,
    get_backups_dir,
    is_data_path,
    list_backups,
    safe_cleanup,
)


class TestGetBackupsDir:
    """Tests for get_backups_dir function."""

    def test_with_custom_root(self, tmp_path):
        """Test with custom output root."""
        result = get_backups_dir(tmp_path)
        assert result == tmp_path / "backups"

    def test_returns_backups_subdir(self):
        """Test that backups directory is a subdirectory."""
        result = get_backups_dir(Path("/some/output"))
        assert result.name == "backups"
        assert result.parent == Path("/some/output")


class TestIsDataPath:
    """Tests for is_data_path function."""

    def test_data_path(self, tmp_path):
        """Test that data/ paths are detected."""
        with patch("cv_generator.cleanup.get_repo_root") as mock:
            mock.return_value = tmp_path
            data_dir = tmp_path / "data"
            data_dir.mkdir()

            assert is_data_path(data_dir) is True
            assert is_data_path(data_dir / "cvs") is True
            assert is_data_path(data_dir / "cvs" / "test.json") is True

    def test_non_data_path(self, tmp_path):
        """Test that non-data paths are not detected."""
        with patch("cv_generator.cleanup.get_repo_root") as mock:
            mock.return_value = tmp_path
            (tmp_path / "data").mkdir()
            output_dir = tmp_path / "output"
            output_dir.mkdir()

            assert is_data_path(output_dir) is False
            assert is_data_path(output_dir / "pdf") is False

    def test_fallback_on_exception(self, tmp_path):
        """Test fallback behavior when exception occurs."""
        with patch("cv_generator.cleanup.get_repo_root") as mock:
            mock.side_effect = Exception("Cannot determine root")

            # Should fall back to string check
            assert is_data_path(Path("/some/data/path")) is True
            assert is_data_path(Path("/some/output/path")) is False


class TestCreateBackup:
    """Tests for create_backup function."""

    def test_create_backup_success(self, tmp_path):
        """Test successful backup creation."""
        # Create source directory with files
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("Content 1")
        (source_dir / "file2.txt").write_text("Content 2")

        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        with patch("cv_generator.cleanup.is_data_path", return_value=False):
            result = create_backup(source_dir, tmp_path, timestamp)

        assert result is not None
        assert result.name == "source_20240115_103000.tar.gz"
        assert result.exists()

        # Verify archive contents
        with tarfile.open(result, "r:gz") as tar:
            names = tar.getnames()
            assert "source" in names
            assert "source/file1.txt" in names
            assert "source/file2.txt" in names

    def test_create_backup_nonexistent_source(self, tmp_path):
        """Test backup of non-existent source."""
        with patch("cv_generator.cleanup.is_data_path", return_value=False):
            result = create_backup(tmp_path / "nonexistent", tmp_path)
        assert result is None

    def test_create_backup_data_path_blocked(self, tmp_path):
        """Test that backup from data/ is blocked."""
        source_dir = tmp_path / "data" / "cvs"
        source_dir.mkdir(parents=True)

        with patch("cv_generator.cleanup.is_data_path", return_value=True):
            with pytest.raises(ValueError) as exc:
                create_backup(source_dir, tmp_path)
            assert "Cannot backup from data/" in str(exc.value)


class TestSafeCleanup:
    """Tests for safe_cleanup function."""

    def test_cleanup_with_backup(self, tmp_path):
        """Test cleanup creates backup before deletion."""
        # Create target directory
        target_dir = tmp_path / "output" / "pdf"
        target_dir.mkdir(parents=True)
        (target_dir / "test.pdf").write_text("PDF content")

        with patch("cv_generator.cleanup.is_data_path", return_value=False):
            result = safe_cleanup(target_dir, backup=True, yes=True, output_root=tmp_path)

        assert result is True
        assert not target_dir.exists()

        # Verify backup exists
        backups_dir = tmp_path / "backups"
        assert backups_dir.exists()
        backups = list(backups_dir.glob("*.tar.gz"))
        assert len(backups) == 1

    def test_cleanup_without_backup(self, tmp_path):
        """Test cleanup without backup."""
        target_dir = tmp_path / "output" / "pdf"
        target_dir.mkdir(parents=True)
        (target_dir / "test.pdf").write_text("PDF content")

        with patch("cv_generator.cleanup.is_data_path", return_value=False):
            result = safe_cleanup(target_dir, backup=False, yes=True)

        assert result is True
        assert not target_dir.exists()

    def test_cleanup_nonexistent_path(self, tmp_path):
        """Test cleanup of non-existent path."""
        with patch("cv_generator.cleanup.is_data_path", return_value=False):
            result = safe_cleanup(tmp_path / "nonexistent", yes=True)
        assert result is True

    def test_cleanup_data_path_blocked(self, tmp_path):
        """Test that cleanup of data/ is blocked."""
        target_dir = tmp_path / "data" / "cvs"
        target_dir.mkdir(parents=True)

        with patch("cv_generator.cleanup.is_data_path", return_value=True):
            with pytest.raises(ValueError) as exc:
                safe_cleanup(target_dir, yes=True)
            assert "Cannot delete from data/" in str(exc.value)


class TestListBackups:
    """Tests for list_backups function."""

    def test_no_backups(self, tmp_path):
        """Test listing when no backups exist."""
        result = list_backups(tmp_path)
        assert result == []

    def test_list_backups(self, tmp_path):
        """Test listing existing backups."""
        backups_dir = tmp_path / "backups"
        backups_dir.mkdir()

        # Create some backup files
        (backups_dir / "pdf_20240115_100000.tar.gz").write_bytes(b"")
        (backups_dir / "latex_20240115_110000.tar.gz").write_bytes(b"")
        (backups_dir / "pdf_20240116_100000.tar.gz").write_bytes(b"")

        result = list_backups(tmp_path)

        assert len(result) == 3
        # Should be sorted newest first
        assert "20240116" in result[0].name


class TestConfirmAction:
    """Tests for confirm_action function."""

    def test_yes_response(self):
        """Test 'y' response returns True."""
        with patch("builtins.input", return_value="y"):
            assert confirm_action("Delete?") is True

    def test_no_response(self):
        """Test 'n' response returns False."""
        with patch("builtins.input", return_value="n"):
            assert confirm_action("Delete?") is False

    def test_empty_response_default_false(self):
        """Test empty response uses default (False)."""
        with patch("builtins.input", return_value=""):
            assert confirm_action("Delete?", default=False) is False

    def test_empty_response_default_true(self):
        """Test empty response uses default (True)."""
        with patch("builtins.input", return_value=""):
            assert confirm_action("Delete?", default=True) is True

    def test_eof_returns_false(self):
        """Test EOF returns False."""
        with patch("builtins.input", side_effect=EOFError):
            assert confirm_action("Delete?") is False

    def test_keyboard_interrupt_returns_false(self):
        """Test KeyboardInterrupt returns False."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            assert confirm_action("Delete?") is False
