"""
File watching utilities for CV Generator.

Provides:
- Polling-based file watcher (stdlib only, zero external deps)
- Debounced change detection
- Clear rebuild reason reporting
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Default poll interval in seconds
DEFAULT_POLL_INTERVAL = 1.0

# Debounce delay in seconds (wait for rapid changes to settle)
DEFAULT_DEBOUNCE_DELAY = 0.5


@dataclass
class FileState:
    """State of a watched file."""

    path: Path
    mtime: float = 0.0
    size: int = 0

    @classmethod
    def from_path(cls, path: Path) -> Optional["FileState"]:
        """Create FileState from a path, returns None if file doesn't exist."""
        try:
            stat = path.stat()
            return cls(path=path, mtime=stat.st_mtime, size=stat.st_size)
        except OSError:
            return None

    def has_changed(self, other: Optional["FileState"]) -> bool:
        """Check if this file state differs from another."""
        if other is None:
            return True
        return self.mtime != other.mtime or self.size != other.size


@dataclass
class WatchEvent:
    """Represents a file change event."""

    path: Path
    event_type: str  # "modified", "created", "deleted"
    timestamp: float = field(default_factory=time.time)

    def __str__(self) -> str:
        return f"{self.event_type}: {self.path}"


class FileWatcher:
    """
    Polling-based file watcher for CV Generator.

    Uses stdlib only - no external dependencies required.
    Watches directories for .json and .tex file changes.
    """

    def __init__(
        self,
        paths: List[Path],
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        debounce_delay: float = DEFAULT_DEBOUNCE_DELAY,
        patterns: Optional[List[str]] = None,
    ):
        """
        Initialize the file watcher.

        Args:
            paths: List of files or directories to watch.
            poll_interval: How often to check for changes (seconds).
            debounce_delay: How long to wait for rapid changes to settle.
            patterns: File patterns to watch (e.g., ["*.json", "*.tex"]).
        """
        self.paths = [Path(p) for p in paths]
        self.poll_interval = poll_interval
        self.debounce_delay = debounce_delay
        self.patterns = patterns or ["*.json", "*.tex"]
        self._running = False
        self._file_states: Dict[Path, FileState] = {}
        self._initialize_states()

    def _get_watched_files(self) -> Set[Path]:
        """Get all files matching watch patterns."""
        files: Set[Path] = set()
        for path in self.paths:
            if path.is_file():
                files.add(path)
            elif path.is_dir():
                for pattern in self.patterns:
                    files.update(path.glob(pattern))
                    # Also check subdirectories
                    files.update(path.glob(f"**/{pattern}"))
        return files

    def _initialize_states(self) -> None:
        """Initialize file states for all watched files."""
        self._file_states.clear()
        for filepath in self._get_watched_files():
            state = FileState.from_path(filepath)
            if state:
                self._file_states[filepath] = state
        logger.debug(f"Watching {len(self._file_states)} files")

    def _check_changes(self) -> List[WatchEvent]:
        """Check for file changes since last poll."""
        events: List[WatchEvent] = []
        current_files = self._get_watched_files()

        # Check for modified or deleted files
        for filepath, old_state in list(self._file_states.items()):
            if filepath not in current_files:
                # File was deleted
                events.append(WatchEvent(path=filepath, event_type="deleted"))
                del self._file_states[filepath]
            else:
                new_state = FileState.from_path(filepath)
                if new_state is None:
                    # File became inaccessible
                    events.append(WatchEvent(path=filepath, event_type="deleted"))
                    del self._file_states[filepath]
                elif new_state.has_changed(old_state):
                    # File was modified
                    events.append(WatchEvent(path=filepath, event_type="modified"))
                    self._file_states[filepath] = new_state

        # Check for new files
        for filepath in current_files:
            if filepath not in self._file_states:
                state = FileState.from_path(filepath)
                if state:
                    events.append(WatchEvent(path=filepath, event_type="created"))
                    self._file_states[filepath] = state

        return events

    def watch(
        self,
        callback: Callable[[List[WatchEvent]], None],
        on_start: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Start watching for file changes.

        Args:
            callback: Function to call when changes are detected.
            on_start: Optional function to call when watching starts.
        """
        self._running = True
        if on_start:
            on_start()

        logger.info(f"Watching {len(self._file_states)} files for changes...")
        logger.info("Press Ctrl+C to stop watching")

        pending_events: List[WatchEvent] = []
        last_event_time = 0.0

        try:
            while self._running:
                events = self._check_changes()

                if events:
                    pending_events.extend(events)
                    last_event_time = time.time()

                # If we have pending events and debounce delay has passed
                if pending_events and (time.time() - last_event_time >= self.debounce_delay):
                    callback(pending_events)
                    pending_events = []

                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            logger.info("Watch mode stopped by user")
        finally:
            self._running = False

    def stop(self) -> None:
        """Stop the file watcher."""
        self._running = False


def format_change_reason(events: List[WatchEvent]) -> str:
    """
    Format a human-readable reason for rebuilding.

    Args:
        events: List of file change events.

    Returns:
        Formatted string describing what changed.
    """
    if not events:
        return "no changes"

    if len(events) == 1:
        event = events[0]
        return f"{event.path.name} {event.event_type}"

    # Group by event type
    modified = [e for e in events if e.event_type == "modified"]
    created = [e for e in events if e.event_type == "created"]
    deleted = [e for e in events if e.event_type == "deleted"]

    parts = []
    if modified:
        names = ", ".join(e.path.name for e in modified[:3])
        if len(modified) > 3:
            names += f" and {len(modified) - 3} more"
        parts.append(f"modified: {names}")
    if created:
        names = ", ".join(e.path.name for e in created[:3])
        parts.append(f"created: {names}")
    if deleted:
        names = ", ".join(e.path.name for e in deleted[:3])
        parts.append(f"deleted: {names}")

    return "; ".join(parts)
