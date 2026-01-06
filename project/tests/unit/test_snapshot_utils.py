"""
Unit tests for snapshot testing utilities.
"""

import os
from pathlib import Path

import pytest

from tests.snapshot_utils import (
    assert_snapshot,
    format_diff,
    get_snapshots_dir,
    normalize_text,
    should_update_snapshots,
)


class TestNormalizeText:
    """Tests for text normalization."""

    def test_removes_trailing_whitespace(self):
        """Test that trailing whitespace is removed from lines."""
        text = "line1   \nline2  \nline3"
        result = normalize_text(text)
        assert result == "line1\nline2\nline3"

    def test_removes_trailing_empty_lines(self):
        """Test that trailing empty lines are removed."""
        text = "line1\nline2\n\n\n"
        result = normalize_text(text)
        assert result == "line1\nline2"

    def test_preserves_internal_empty_lines(self):
        """Test that internal empty lines are preserved."""
        text = "line1\n\nline2"
        result = normalize_text(text)
        assert result == "line1\n\nline2"

    def test_handles_windows_line_endings(self):
        """Test that Windows line endings are handled correctly."""
        text = "line1\r\nline2\r\n"
        result = normalize_text(text)
        # After splitlines and rejoin with \n
        assert "line1" in result and "line2" in result


class TestShouldUpdateSnapshots:
    """Tests for snapshot update detection."""

    def test_returns_false_when_not_set(self, monkeypatch):
        """Test that function returns False when env var is not set."""
        monkeypatch.delenv("UPDATE_SNAPSHOTS", raising=False)
        assert should_update_snapshots() is False

    def test_returns_true_when_set_to_1(self, monkeypatch):
        """Test that function returns True when env var is '1'."""
        monkeypatch.setenv("UPDATE_SNAPSHOTS", "1")
        assert should_update_snapshots() is True

    def test_returns_true_when_set_to_true(self, monkeypatch):
        """Test that function returns True when env var is 'true'."""
        monkeypatch.setenv("UPDATE_SNAPSHOTS", "true")
        assert should_update_snapshots() is True

    def test_returns_true_case_insensitive(self, monkeypatch):
        """Test that function handles case insensitively."""
        monkeypatch.setenv("UPDATE_SNAPSHOTS", "TRUE")
        assert should_update_snapshots() is True

    def test_returns_false_for_other_values(self, monkeypatch):
        """Test that function returns False for non-truthy values."""
        monkeypatch.setenv("UPDATE_SNAPSHOTS", "0")
        assert should_update_snapshots() is False


class TestFormatDiff:
    """Tests for diff formatting."""

    def test_shows_added_lines(self):
        """Test that added lines are shown in diff."""
        expected = "line1\nline2"
        actual = "line1\nline2\nline3"
        diff = format_diff(expected, actual, "test")

        assert "+line3" in diff

    def test_shows_removed_lines(self):
        """Test that removed lines are shown in diff."""
        expected = "line1\nline2\nline3"
        actual = "line1\nline2"
        diff = format_diff(expected, actual, "test")

        assert "-line3" in diff

    def test_shows_snapshot_name(self):
        """Test that snapshot name is included in diff."""
        expected = "line1"
        actual = "line2"
        diff = format_diff(expected, actual, "my_snapshot")

        assert "my_snapshot" in diff


class TestAssertSnapshot:
    """Tests for the main snapshot assertion function."""

    def test_creates_snapshot_on_first_run(self, tmp_path, monkeypatch):
        """Test that snapshot is created if it doesn't exist."""
        monkeypatch.delenv("UPDATE_SNAPSHOTS", raising=False)

        snapshot_dir = tmp_path / "snapshots"
        actual = "test content"

        # Should create the snapshot
        assert_snapshot(actual, "new_snapshot", snapshot_dir)

        snapshot_path = snapshot_dir / "new_snapshot.snap"
        assert snapshot_path.exists()
        assert snapshot_path.read_text() == "test content"

    def test_passes_when_snapshot_matches(self, tmp_path, monkeypatch):
        """Test that assertion passes when content matches snapshot."""
        monkeypatch.delenv("UPDATE_SNAPSHOTS", raising=False)

        snapshot_dir = tmp_path / "snapshots"
        snapshot_dir.mkdir()

        # Create existing snapshot
        snapshot_path = snapshot_dir / "existing.snap"
        snapshot_path.write_text("expected content")

        # Should pass without error
        assert_snapshot("expected content", "existing", snapshot_dir)

    def test_fails_when_snapshot_differs(self, tmp_path, monkeypatch):
        """Test that assertion fails when content differs from snapshot."""
        monkeypatch.delenv("UPDATE_SNAPSHOTS", raising=False)

        snapshot_dir = tmp_path / "snapshots"
        snapshot_dir.mkdir()

        # Create existing snapshot
        snapshot_path = snapshot_dir / "existing.snap"
        snapshot_path.write_text("expected content")

        # Should raise AssertionError
        with pytest.raises(AssertionError) as exc_info:
            assert_snapshot("different content", "existing", snapshot_dir)

        assert "Snapshot mismatch" in str(exc_info.value)
        assert "UPDATE_SNAPSHOTS=1" in str(exc_info.value)

    def test_updates_snapshot_when_env_set(self, tmp_path, monkeypatch):
        """Test that snapshot is updated when UPDATE_SNAPSHOTS is set."""
        monkeypatch.setenv("UPDATE_SNAPSHOTS", "1")

        snapshot_dir = tmp_path / "snapshots"
        snapshot_dir.mkdir()

        # Create existing snapshot with old content
        snapshot_path = snapshot_dir / "update_me.snap"
        snapshot_path.write_text("old content")

        # Should update the snapshot
        assert_snapshot("new content", "update_me", snapshot_dir)

        # Verify snapshot was updated
        assert snapshot_path.read_text() == "new content"

    def test_normalizes_content_before_comparison(self, tmp_path, monkeypatch):
        """Test that trailing whitespace is normalized."""
        monkeypatch.delenv("UPDATE_SNAPSHOTS", raising=False)

        snapshot_dir = tmp_path / "snapshots"
        snapshot_dir.mkdir()

        # Create existing snapshot
        snapshot_path = snapshot_dir / "whitespace.snap"
        snapshot_path.write_text("line1\nline2")

        # Should pass despite different trailing whitespace
        assert_snapshot("line1   \nline2  \n\n", "whitespace", snapshot_dir)


class TestGetSnapshotsDir:
    """Tests for snapshots directory path."""

    def test_returns_path_object(self):
        """Test that function returns a Path object."""
        result = get_snapshots_dir()
        assert isinstance(result, Path)

    def test_points_to_snapshots_dir(self):
        """Test that function returns path ending in 'snapshots'."""
        result = get_snapshots_dir()
        assert result.name == "snapshots"
