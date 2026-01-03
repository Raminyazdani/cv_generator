"""
Tests for cv_generator.watch module.

Tests the file watching utilities for watch mode.
"""

import time
from pathlib import Path

import pytest

from cv_generator.watch import (
    DEFAULT_DEBOUNCE_DELAY,
    DEFAULT_POLL_INTERVAL,
    FileState,
    FileWatcher,
    WatchEvent,
    format_change_reason,
)


class TestFileState:
    """Tests for FileState dataclass."""

    def test_from_path(self, tmp_path):
        """Test creating FileState from a path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        state = FileState.from_path(test_file)
        assert state is not None
        assert state.path == test_file
        assert state.mtime > 0
        assert state.size == 5

    def test_from_path_nonexistent(self, tmp_path):
        """Test that nonexistent file returns None."""
        nonexistent = tmp_path / "nonexistent.txt"
        state = FileState.from_path(nonexistent)
        assert state is None

    def test_has_changed_different_mtime(self, tmp_path):
        """Test detecting changed mtime."""
        state1 = FileState(path=tmp_path / "test.txt", mtime=100.0, size=10)
        state2 = FileState(path=tmp_path / "test.txt", mtime=200.0, size=10)

        assert state1.has_changed(state2)
        assert state2.has_changed(state1)

    def test_has_changed_different_size(self, tmp_path):
        """Test detecting changed size."""
        state1 = FileState(path=tmp_path / "test.txt", mtime=100.0, size=10)
        state2 = FileState(path=tmp_path / "test.txt", mtime=100.0, size=20)

        assert state1.has_changed(state2)

    def test_has_changed_none(self, tmp_path):
        """Test that comparing to None returns True."""
        state = FileState(path=tmp_path / "test.txt", mtime=100.0, size=10)
        assert state.has_changed(None)

    def test_has_changed_same(self, tmp_path):
        """Test that identical states return False."""
        state1 = FileState(path=tmp_path / "test.txt", mtime=100.0, size=10)
        state2 = FileState(path=tmp_path / "test.txt", mtime=100.0, size=10)

        assert not state1.has_changed(state2)


class TestWatchEvent:
    """Tests for WatchEvent dataclass."""

    def test_str_modified(self, tmp_path):
        """Test string representation for modified event."""
        event = WatchEvent(path=tmp_path / "test.json", event_type="modified")
        s = str(event)
        assert "modified" in s
        assert "test.json" in s

    def test_str_created(self, tmp_path):
        """Test string representation for created event."""
        event = WatchEvent(path=tmp_path / "new.tex", event_type="created")
        s = str(event)
        assert "created" in s
        assert "new.tex" in s


class TestFileWatcher:
    """Tests for FileWatcher class."""

    def test_init(self, tmp_path):
        """Test initializing a file watcher."""
        watcher = FileWatcher([tmp_path])
        assert watcher.poll_interval == DEFAULT_POLL_INTERVAL
        assert watcher.debounce_delay == DEFAULT_DEBOUNCE_DELAY
        assert "*.json" in watcher.patterns
        assert "*.tex" in watcher.patterns

    def test_init_with_files(self, tmp_path):
        """Test initializing with files to watch."""
        (tmp_path / "test.json").write_text("{}")
        (tmp_path / "layout.tex").write_text("test")

        watcher = FileWatcher([tmp_path])
        files = watcher._get_watched_files()

        assert len(files) >= 2
        assert any(f.name == "test.json" for f in files)
        assert any(f.name == "layout.tex" for f in files)

    def test_check_changes_modified(self, tmp_path):
        """Test detecting modified files."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        watcher = FileWatcher([tmp_path])

        # Initially no changes
        events = watcher._check_changes()
        assert len(events) == 0

        # Modify the file
        time.sleep(0.1)  # Ensure mtime is different
        test_file.write_text('{"modified": true}')

        events = watcher._check_changes()
        assert len(events) == 1
        assert events[0].event_type == "modified"
        assert events[0].path.name == "test.json"

    def test_check_changes_created(self, tmp_path):
        """Test detecting created files."""
        watcher = FileWatcher([tmp_path])

        # Create a new file
        new_file = tmp_path / "new.json"
        new_file.write_text("{}")

        events = watcher._check_changes()
        assert len(events) == 1
        assert events[0].event_type == "created"
        assert events[0].path.name == "new.json"

    def test_check_changes_deleted(self, tmp_path):
        """Test detecting deleted files."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        watcher = FileWatcher([tmp_path])

        # Delete the file
        test_file.unlink()

        events = watcher._check_changes()
        assert len(events) == 1
        assert events[0].event_type == "deleted"
        assert events[0].path.name == "test.json"

    def test_stop(self, tmp_path):
        """Test stopping the watcher."""
        watcher = FileWatcher([tmp_path])
        assert watcher._running is False

        watcher._running = True
        watcher.stop()
        assert watcher._running is False


class TestFormatChangeReason:
    """Tests for format_change_reason function."""

    def test_no_changes(self):
        """Test formatting no changes."""
        result = format_change_reason([])
        assert "no changes" in result

    def test_single_change(self, tmp_path):
        """Test formatting a single change."""
        events = [WatchEvent(path=tmp_path / "test.json", event_type="modified")]
        result = format_change_reason(events)
        assert "test.json" in result
        assert "modified" in result

    def test_multiple_modified(self, tmp_path):
        """Test formatting multiple modified files."""
        events = [
            WatchEvent(path=tmp_path / "a.json", event_type="modified"),
            WatchEvent(path=tmp_path / "b.json", event_type="modified"),
        ]
        result = format_change_reason(events)
        assert "a.json" in result
        assert "b.json" in result

    def test_mixed_events(self, tmp_path):
        """Test formatting mixed event types."""
        events = [
            WatchEvent(path=tmp_path / "a.json", event_type="modified"),
            WatchEvent(path=tmp_path / "b.tex", event_type="created"),
        ]
        result = format_change_reason(events)
        assert "modified" in result
        assert "created" in result

    def test_many_files_truncated(self, tmp_path):
        """Test that many files are truncated."""
        events = [
            WatchEvent(path=tmp_path / f"file{i}.json", event_type="modified")
            for i in range(10)
        ]
        result = format_change_reason(events)
        # Should show first 3 and "and X more"
        assert "more" in result
