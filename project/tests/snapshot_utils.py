"""
Snapshot testing utilities for CV Generator.

Provides functions to compare generated LaTeX output against stored snapshots,
with readable diffs on failure and support for updating snapshots.
"""

import difflib
import os
from pathlib import Path
from typing import Optional


def get_snapshots_dir() -> Path:
    """Return the path to the snapshots directory."""
    return Path(__file__).parent / "snapshots"


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison by removing trailing whitespace and
    ensuring consistent line endings.

    Args:
        text: The text to normalize.

    Returns:
        Normalized text with consistent formatting.
    """
    # Split into lines, strip trailing whitespace from each, rejoin
    lines = text.splitlines()
    normalized_lines = [line.rstrip() for line in lines]
    # Remove trailing empty lines
    while normalized_lines and not normalized_lines[-1]:
        normalized_lines.pop()
    return "\n".join(normalized_lines)


def should_update_snapshots() -> bool:
    """
    Check if snapshots should be updated.

    Returns True if the UPDATE_SNAPSHOTS environment variable is set to
    '1', 'true', or 'yes' (case-insensitive).
    """
    value = os.environ.get("UPDATE_SNAPSHOTS", "").lower()
    return value in ("1", "true", "yes")


def format_diff(expected: str, actual: str, snapshot_name: str) -> str:
    """
    Create a readable unified diff between expected and actual content.

    Args:
        expected: Expected content from snapshot.
        actual: Actual content from test.
        snapshot_name: Name of the snapshot for context.

    Returns:
        A formatted diff string.
    """
    expected_lines = expected.splitlines(keepends=True)
    actual_lines = actual.splitlines(keepends=True)

    diff = difflib.unified_diff(
        expected_lines,
        actual_lines,
        fromfile=f"snapshot: {snapshot_name}",
        tofile="actual output",
        lineterm=""
    )

    return "".join(diff)


def assert_snapshot(
    actual: str,
    snapshot_name: str,
    snapshot_dir: Optional[Path] = None
) -> None:
    """
    Compare actual output against a stored snapshot.

    If the UPDATE_SNAPSHOTS environment variable is set, updates the snapshot
    instead of comparing.

    Args:
        actual: The actual output to compare.
        snapshot_name: Name of the snapshot file (without extension).
        snapshot_dir: Optional custom snapshot directory. Defaults to tests/snapshots/.

    Raises:
        AssertionError: If the snapshot doesn't match and UPDATE_SNAPSHOTS is not set.
    """
    if snapshot_dir is None:
        snapshot_dir = get_snapshots_dir()

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / f"{snapshot_name}.snap"

    normalized_actual = normalize_text(actual)

    if should_update_snapshots():
        # Update mode: write new snapshot
        snapshot_path.write_text(normalized_actual, encoding="utf-8")
        return

    if not snapshot_path.exists():
        # No existing snapshot - create it on first run
        snapshot_path.write_text(normalized_actual, encoding="utf-8")
        return

    # Compare mode
    expected = snapshot_path.read_text(encoding="utf-8")
    normalized_expected = normalize_text(expected)

    if normalized_actual != normalized_expected:
        diff = format_diff(normalized_expected, normalized_actual, snapshot_name)
        raise AssertionError(
            f"Snapshot mismatch for '{snapshot_name}'.\n"
            f"To update, run with UPDATE_SNAPSHOTS=1.\n\n"
            f"Diff:\n{diff}"
        )


def assert_snapshot_tex(
    actual: str,
    snapshot_name: str,
    snapshot_dir: Optional[Path] = None
) -> None:
    """
    Compare actual LaTeX output against a stored snapshot.

    This is an alias for assert_snapshot with the .tex extension hint in the name.

    Args:
        actual: The actual LaTeX output to compare.
        snapshot_name: Name of the snapshot file (without extension).
        snapshot_dir: Optional custom snapshot directory.

    Raises:
        AssertionError: If the snapshot doesn't match.
    """
    assert_snapshot(actual, snapshot_name, snapshot_dir)
