"""
Tests for the cleanup module with backup functionality.

Includes enhanced Windows cleanup tests for:
- Locked file detection
- Lock suggestions
- Retry logic with exponential backoff
- CleanupError exception handling
"""

import shutil
import tarfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from cv_generator.cleanup import (
    CleanupError,
    _find_locked_files,
    _get_lock_suggestions,
    confirm_action,
    create_backup,
    get_backups_dir,
    is_data_path,
    is_windows,
    list_backups,
    remove_directory,
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


class TestIsWindows:
    """Tests for is_windows function."""

    def test_is_windows_returns_bool(self):
        """Test that is_windows returns a boolean."""
        result = is_windows()
        assert isinstance(result, bool)


class TestCleanupError:
    """Tests for CleanupError exception class."""

    def test_cleanup_error_with_message(self):
        """Test CleanupError with basic message."""
        error = CleanupError("Test error", Path("/test"))
        assert str(error) == "Test error"
        assert error.path == Path("/test")
        assert error.locked_files == []

    def test_cleanup_error_with_locked_files(self):
        """Test CleanupError with locked files list."""
        locked = ["/path/file1.txt", "/path/file2.txt"]
        error = CleanupError("Test error", Path("/test"), locked)
        assert error.locked_files == locked


class TestFindLockedFiles:
    """Tests for _find_locked_files function."""

    def test_find_locked_files_nonexistent_path(self, tmp_path):
        """Test with non-existent path."""
        result = _find_locked_files(tmp_path / "nonexistent")
        assert result == []

    def test_find_locked_files_empty_dir(self, tmp_path):
        """Test with empty directory."""
        result = _find_locked_files(tmp_path)
        assert result == []

    def test_find_locked_files_unlocked_files(self, tmp_path):
        """Test with unlocked files."""
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")

        # Should return empty list on non-Windows (files not locked)
        result = _find_locked_files(tmp_path)
        assert result == []


class TestGetLockSuggestions:
    """Tests for _get_lock_suggestions function."""

    def test_onedrive_detection(self, tmp_path):
        """Test OneDrive suggestion generation."""
        onedrive_path = tmp_path / "OneDrive" / "Documents"
        locked_files = [str(onedrive_path / "file.txt")]

        suggestions = _get_lock_suggestions(onedrive_path, locked_files)

        # Should suggest pausing OneDrive
        assert any('OneDrive' in s for s in suggestions)
        assert any('Pause' in s or 'pause' in s for s in suggestions)

    def test_dropbox_detection(self, tmp_path):
        """Test Dropbox suggestion generation."""
        dropbox_path = tmp_path / "Dropbox" / "Documents"
        locked_files = [str(dropbox_path / "file.txt")]

        suggestions = _get_lock_suggestions(dropbox_path, locked_files)

        # Should suggest pausing Dropbox
        assert any('Dropbox' in s for s in suggestions)

    def test_pdf_file_suggestion(self, tmp_path):
        """Test PDF file lock suggestions."""
        locked_files = [
            str(tmp_path / "document.pdf"),
            str(tmp_path / "cv.pdf"),
        ]

        suggestions = _get_lock_suggestions(tmp_path, locked_files)

        # Should suggest closing PDF readers
        assert any('PDF' in s or 'pdf' in s for s in suggestions)

    def test_latex_file_suggestion(self, tmp_path):
        """Test LaTeX file lock suggestions."""
        locked_files = [
            str(tmp_path / "main.tex"),
            str(tmp_path / "main.log"),
        ]

        suggestions = _get_lock_suggestions(tmp_path, locked_files)

        # Should suggest closing LaTeX editors
        assert any('LaTeX' in s for s in suggestions)

    def test_always_includes_generic_suggestions(self, tmp_path):
        """Test that generic suggestions are always included."""
        suggestions = _get_lock_suggestions(tmp_path, [])

        # Should include generic suggestions
        assert any('Explorer' in s or 'explorer' in s for s in suggestions)
        assert any('retry' in s.lower() for s in suggestions)


class TestRemoveDirectory:
    """Tests for remove_directory function."""

    def test_remove_nonexistent_directory(self, tmp_path):
        """Test removing non-existent directory (should succeed)."""
        test_dir = tmp_path / "nonexistent"

        result = remove_directory(test_dir)

        assert result is True

    def test_remove_empty_directory(self, tmp_path):
        """Test removing empty directory."""
        test_dir = tmp_path / "empty"
        test_dir.mkdir()

        result = remove_directory(test_dir)

        assert result is True
        assert not test_dir.exists()

    def test_remove_directory_with_files(self, tmp_path):
        """Test removing directory with files."""
        test_dir = tmp_path / "with_files"
        test_dir.mkdir()

        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.txt").write_text("content2")

        result = remove_directory(test_dir)

        assert result is True
        assert not test_dir.exists()

    def test_remove_directory_with_subdirectories(self, tmp_path):
        """Test removing nested directory structure."""
        test_dir = tmp_path / "nested"
        (test_dir / "sub1" / "sub2").mkdir(parents=True)
        (test_dir / "sub1" / "file1.txt").write_text("content")
        (test_dir / "sub1" / "sub2" / "file2.txt").write_text("content")

        result = remove_directory(test_dir)

        assert result is True
        assert not test_dir.exists()

    def test_remove_directory_raises_cleanup_error_on_persistent_failure(
        self, tmp_path, monkeypatch
    ):
        """Test that CleanupError is raised after all retries fail."""
        test_dir = tmp_path / "persistent_failure"
        test_dir.mkdir()

        def mock_rmtree(path, onerror=None):
            raise PermissionError("Mocked persistent lock")

        monkeypatch.setattr('shutil.rmtree', mock_rmtree)

        with pytest.raises(CleanupError) as exc_info:
            remove_directory(test_dir, max_attempts=3, initial_delay=0.01)

        error = exc_info.value
        assert error.path == test_dir
        assert "Cannot remove directory" in str(error)

    def test_retry_with_exponential_backoff(self, tmp_path, monkeypatch):
        """Test exponential backoff timing."""
        test_dir = tmp_path / "retry_test"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        attempts = []
        real_rmtree = shutil.rmtree

        def mock_rmtree(path, onerror=None):
            attempts.append(time.time())
            if len(attempts) < 3:
                raise PermissionError("Mocked lock")
            # Third attempt succeeds - use real rmtree
            real_rmtree(path, onerror=onerror)

        monkeypatch.setattr('cv_generator.cleanup.shutil.rmtree', mock_rmtree)

        result = remove_directory(
            test_dir,
            max_attempts=5,
            initial_delay=0.05,
            max_delay=1.0
        )

        assert result is True
        assert len(attempts) == 3

        # Check delays are increasing
        if len(attempts) >= 3:
            delay1 = attempts[1] - attempts[0]
            delay2 = attempts[2] - attempts[1]
            # Second delay should be greater than first due to exponential backoff
            # Use small tolerance for timing variations
            assert delay2 > delay1 * 0.8


class TestRemoveDirectoryInteractive:
    """Tests for remove_directory_interactive function (non-interactive scenarios)."""

    def test_successful_removal(self, tmp_path):
        """Test successful removal in non-interactive mode."""
        from cv_generator.cleanup import remove_directory_interactive

        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        result = remove_directory_interactive(test_dir)

        assert result is True
        assert not test_dir.exists()


class TestCleanupCrossplatform:
    """Cross-platform cleanup tests that run on all platforms."""

    def test_remove_nonexistent_directory(self, tmp_path):
        """Test removing non-existent directory."""
        test_dir = tmp_path / "nonexistent"

        result = remove_directory(test_dir)

        assert result is True

    def test_safe_cleanup_handles_cleanup_error(self, tmp_path, monkeypatch):
        """Test that safe_cleanup handles CleanupError gracefully."""
        test_dir = tmp_path / "error_test"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        def mock_rmtree_reliable(*args, **kwargs):
            raise CleanupError("Mocked error", test_dir, [])

        monkeypatch.setattr('cv_generator.cleanup.rmtree_reliable', mock_rmtree_reliable)

        with patch("cv_generator.cleanup.is_data_path", return_value=False):
            result = safe_cleanup(test_dir, backup=False, yes=True, verbose=True)

        # Should return False but not crash
        assert result is False
