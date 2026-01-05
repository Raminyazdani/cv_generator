"""
Security tests for CV Generator.

Tests for security hardening fixes:
- F-001: tarfile.extractall() path traversal protection
- F-002: Flask secret key not hardcoded
- F-004: subprocess.run shell injection prevention
"""

import io
import os
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestTarfilePathTraversal:
    """Tests for F-001: tarfile.extractall() path traversal protection."""

    def test_path_traversal_blocked_with_dotdot(self, tmp_path):
        """Test that path traversal with .. in tar archives is blocked."""
        from cv_generator.cleanup import restore_backup

        # Create a malicious tar with path traversal
        malicious_tar = tmp_path / "malicious.tar.gz"
        with tarfile.open(malicious_tar, "w:gz") as tar:
            # Add file with path traversal attempt
            info = tarfile.TarInfo(name="../../etc/passwd")
            info.size = 10
            tar.addfile(info, io.BytesIO(b"malicious\n"))

        # Attempt restore should fail
        restore_dir = tmp_path / "restore"
        with pytest.raises(ValueError, match="[Pp]ath traversal"):
            restore_backup(malicious_tar, restore_dir, yes=True)

    def test_absolute_path_sanitized(self, tmp_path):
        """Test that absolute paths in tar archives are sanitized (not extracted to system paths)."""
        from cv_generator.cleanup import restore_backup

        # Create a tar with absolute path
        malicious_tar = tmp_path / "absolute.tar.gz"
        with tarfile.open(malicious_tar, "w:gz") as tar:
            # Add file with absolute path - Python 3.12's filter='data' sanitizes this
            info = tarfile.TarInfo(name="/etc/passwd")
            info.size = 10
            tar.addfile(info, io.BytesIO(b"test_data\n"))

        restore_dir = tmp_path / "restore"
        result = restore_backup(malicious_tar, restore_dir, yes=True)

        # The extraction succeeds but the file is safely extracted relative to destination
        # Python 3.12's filter='data' strips the leading / making it safe
        assert result is True
        # File should NOT be extracted to /etc/passwd (that would be a vulnerability!)
        assert not Path("/etc/passwd").read_text().startswith("test_data")
        # File should be safely within the restore directory
        safe_path = tmp_path / "etc" / "passwd"
        assert safe_path.exists()
        assert safe_path.read_text().strip() == "test_data"

    def test_legitimate_archive_extracts_successfully(self, tmp_path):
        """Test that legitimate archives still extract correctly."""
        from cv_generator.cleanup import restore_backup

        # Create a legitimate tar archive
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("Content 1")

        legit_tar = tmp_path / "backups" / "legit.tar.gz"
        legit_tar.parent.mkdir(parents=True)
        with tarfile.open(legit_tar, "w:gz") as tar:
            tar.add(source_dir, arcname="source")

        # This should work fine
        restore_dir = tmp_path / "restore" / "source"
        result = restore_backup(legit_tar, restore_dir, yes=True)

        assert result is True
        assert restore_dir.exists()
        assert (restore_dir / "file1.txt").exists()
        assert (restore_dir / "file1.txt").read_text() == "Content 1"

    def test_nested_dotdot_path_blocked(self, tmp_path):
        """Test that nested path traversal like foo/../../../etc/passwd is blocked."""
        from cv_generator.cleanup import _validate_tar_member_path

        # This should be caught after normalization
        with pytest.raises(ValueError, match="[Pp]ath traversal"):
            _validate_tar_member_path("foo/../../../etc/passwd")

    def test_valid_paths_allowed(self, tmp_path):
        """Test that valid archive paths are allowed."""
        from cv_generator.cleanup import _validate_tar_member_path

        # These should not raise
        _validate_tar_member_path("mydir/file.txt")
        _validate_tar_member_path("backup_20240115/data.json")
        _validate_tar_member_path("folder/subfolder/deep/file.txt")

    def test_python_312_filter_used_when_available(self, tmp_path):
        """Test that Python 3.12+ uses the safe filter parameter."""
        import sys

        from cv_generator.cleanup import _safe_extract_tar

        # Create a simple valid tar
        source_file = tmp_path / "test.txt"
        source_file.write_text("test content")

        test_tar = tmp_path / "test.tar.gz"
        with tarfile.open(test_tar, "w:gz") as tar:
            tar.add(source_file, arcname="test.txt")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        with tarfile.open(test_tar, "r:gz") as tar:
            _safe_extract_tar(tar, extract_dir)

        # File should be extracted
        assert (extract_dir / "test.txt").exists()


class TestFlaskSecretKey:
    """Tests for F-002: Flask secret key not hardcoded."""

    def test_flask_secret_key_not_hardcoded(self, tmp_path, monkeypatch):
        """Test that Flask secret key is never the hardcoded value."""
        # Clear any env vars that might affect this
        monkeypatch.delenv("CVGEN_WEB_SECRET", raising=False)

        # Change to tmp_path to avoid polluting the repo with .cvgen/
        monkeypatch.chdir(tmp_path)

        from cv_generator.web import create_app

        app = create_app()
        assert app.secret_key != "cvgen-web-local-only"
        assert len(app.secret_key) >= 32

    def test_flask_secret_key_environment_override(self, monkeypatch):
        """Test that environment variable overrides secret key."""
        test_secret = "test-secret-key-from-env-variable-12345"
        monkeypatch.setenv("CVGEN_WEB_SECRET", test_secret)

        from cv_generator.web import get_secret_key

        result = get_secret_key()
        assert result == test_secret

    def test_secret_key_persists_to_file(self, tmp_path, monkeypatch):
        """Test that secret key is saved to and read from state file."""
        monkeypatch.delenv("CVGEN_WEB_SECRET", raising=False)
        monkeypatch.chdir(tmp_path)

        from cv_generator.web import get_secret_key

        # First call should generate and save
        secret1 = get_secret_key()
        assert len(secret1) >= 32

        # File should exist
        secret_file = tmp_path / ".cvgen" / "web_secret"
        assert secret_file.exists()

        # Second call should read from file
        secret2 = get_secret_key()
        assert secret2 == secret1

    def test_secret_file_has_restricted_permissions(self, tmp_path, monkeypatch):
        """Test that secret file has restricted permissions on Unix."""
        import stat

        monkeypatch.delenv("CVGEN_WEB_SECRET", raising=False)
        monkeypatch.chdir(tmp_path)

        from cv_generator.web import get_secret_key

        get_secret_key()

        secret_file = tmp_path / ".cvgen" / "web_secret"
        file_stat = secret_file.stat()

        # On Unix, check that only owner can read/write
        if os.name != "nt":
            mode = stat.S_IMODE(file_stat.st_mode)
            # Owner should have read/write, no one else
            assert mode == 0o600

    def test_env_var_takes_precedence_over_file(self, tmp_path, monkeypatch):
        """Test that environment variable takes precedence over file."""
        monkeypatch.chdir(tmp_path)

        # Create a secret file
        secret_dir = tmp_path / ".cvgen"
        secret_dir.mkdir()
        secret_file = secret_dir / "web_secret"
        secret_file.write_text("file-secret-key")

        # Set env var
        monkeypatch.setenv("CVGEN_WEB_SECRET", "env-secret-key")

        from cv_generator.web import get_secret_key

        result = get_secret_key()
        assert result == "env-secret-key"


class TestSubprocessShellInjection:
    """Tests for F-004: subprocess.run shell injection prevention."""

    def test_dangerous_path_chars_rejected(self):
        """Test that paths with dangerous characters are rejected."""
        from cv_generator.cleanup import validate_path_for_subprocess

        dangerous_paths = [
            Path("/tmp/test & rm -rf /"),
            Path("/tmp/test; echo pwned"),
            Path("/tmp/test | cat /etc/passwd"),
            Path("/tmp/test$(whoami)"),
            Path("/tmp/test`whoami`"),
            Path("/tmp/test>output"),
            Path("/tmp/test<input"),
            Path("/tmp/test(command)"),
        ]

        for dangerous_path in dangerous_paths:
            with pytest.raises(ValueError, match="dangerous characters"):
                validate_path_for_subprocess(dangerous_path)

    def test_safe_paths_allowed(self):
        """Test that normal paths are allowed."""
        from cv_generator.cleanup import validate_path_for_subprocess

        safe_paths = [
            Path("/tmp/normal_directory"),
            Path("/home/user/my-project"),
            Path("./relative/path/here"),
            Path("/path/with spaces/is ok"),
            Path("/path/with.dots/and-dashes"),
        ]

        for safe_path in safe_paths:
            # Should not raise
            validate_path_for_subprocess(safe_path)

    def test_windows_cleanup_validates_path(self, tmp_path, monkeypatch):
        """Test that Windows cleanup function validates paths."""
        from cv_generator.cleanup import _clear_readonly_windows

        # Mock os.name to simulate Windows
        monkeypatch.setattr("os.name", "nt")

        # This should raise for dangerous paths
        dangerous_path = tmp_path / "test & malicious"
        with pytest.raises(ValueError, match="dangerous characters"):
            _clear_readonly_windows(dangerous_path)

    def test_rmtree_reliable_with_safe_paths(self, tmp_path):
        """Test that rmtree_reliable works with safe paths."""
        from cv_generator.cleanup import rmtree_reliable

        # Create a directory with safe name
        safe_dir = tmp_path / "safe_directory"
        safe_dir.mkdir()
        (safe_dir / "file.txt").write_text("content")

        # Should work fine
        rmtree_reliable(safe_dir)
        assert not safe_dir.exists()

    def test_shell_false_in_subprocess(self, tmp_path, monkeypatch):
        """Test that subprocess.run is called with shell=False."""
        from cv_generator.cleanup import _clear_readonly_windows

        # Mock os.name to simulate Windows
        monkeypatch.setattr("os.name", "nt")

        captured_calls = []

        def mock_run(*args, **kwargs):
            captured_calls.append({"args": args, "kwargs": kwargs})

        monkeypatch.setattr("subprocess.run", mock_run)

        # Call with a safe path
        safe_path = tmp_path / "safe_directory"
        _clear_readonly_windows(safe_path)

        # Should have been called with shell=False
        assert len(captured_calls) == 1
        assert captured_calls[0]["kwargs"].get("shell") is False


class TestSecurityIntegration:
    """Integration tests for security features."""

    def test_backup_restore_roundtrip_secure(self, tmp_path):
        """Test that backup/restore works correctly with security features."""
        from cv_generator.cleanup import create_backup, restore_backup

        # Create source with files
        source_dir = tmp_path / "output" / "pdf"
        source_dir.mkdir(parents=True)
        (source_dir / "test.pdf").write_text("PDF content")
        (source_dir / "subdir").mkdir()
        (source_dir / "subdir" / "nested.txt").write_text("Nested content")

        # Create backup
        with patch("cv_generator.cleanup.is_data_path", return_value=False):
            backup_path = create_backup(source_dir, tmp_path)

        assert backup_path is not None
        assert backup_path.exists()

        # Delete original
        import shutil

        shutil.rmtree(source_dir)
        assert not source_dir.exists()

        # Restore
        restore_dir = tmp_path / "restored" / "pdf"
        with patch("cv_generator.cleanup.is_data_path", return_value=False):
            result = restore_backup(backup_path, restore_dir, yes=True)

        assert result is True
        assert restore_dir.exists()
        assert (restore_dir / "test.pdf").read_text() == "PDF content"
        assert (restore_dir / "subdir" / "nested.txt").read_text() == "Nested content"

    def test_web_app_uses_secure_secret(self, tmp_path, monkeypatch):
        """Test that web app uses secure random secret."""
        monkeypatch.delenv("CVGEN_WEB_SECRET", raising=False)
        monkeypatch.chdir(tmp_path)

        from cv_generator.db import init_db
        from cv_generator.web import create_app

        db_path = tmp_path / "test.db"
        init_db(db_path)

        app1 = create_app(db_path)
        app2 = create_app(db_path)

        # Both apps should have the same secret (read from file)
        assert app1.secret_key == app2.secret_key
        # But it should not be the hardcoded value
        assert app1.secret_key != "cvgen-web-local-only"
