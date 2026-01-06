"""
Tests for the TeX diff module.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from cv_generator.tex_diff import (
    BuildState,
    DiffReport,
    DiffResult,
    capture_tex_state,
    compare_builds,
    compute_diff,
    diff_command_handler,
    get_state_dir,
    hash_content,
    load_build_state,
    save_build_state,
)


class TestDiffResult:
    """Tests for DiffResult dataclass."""

    def test_to_dict_no_changes(self):
        """Test conversion when no changes."""
        result = DiffResult(
            file_name="main.tex",
            has_changes=False,
        )
        d = result.to_dict()

        assert d["file_name"] == "main.tex"
        assert d["has_changes"] is False
        assert d["added_lines"] == 0
        assert d["removed_lines"] == 0

    def test_to_dict_with_changes(self):
        """Test conversion when there are changes."""
        result = DiffResult(
            file_name="main.tex",
            has_changes=True,
            added_lines=5,
            removed_lines=3,
            unified_diff="--- a/main.tex\n+++ b/main.tex\n",
        )
        d = result.to_dict()

        assert d["has_changes"] is True
        assert d["added_lines"] == 5
        assert d["removed_lines"] == 3

    def test_to_dict_with_error(self):
        """Test conversion with error."""
        result = DiffResult(
            file_name="main.tex",
            has_changes=False,
            error="File not found",
        )
        d = result.to_dict()

        assert d["error"] == "File not found"


class TestBuildState:
    """Tests for BuildState dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        state = BuildState(
            profile="ramin",
            lang="en",
            timestamp="2024-01-15T10:30:00",
            tex_files={"main.tex": "abc123"},
            tex_contents={"main.tex": "\\documentclass{article}"},
            pdf_path="/output/ramin_en.pdf",
        )
        d = state.to_dict()

        assert d["profile"] == "ramin"
        assert d["lang"] == "en"
        assert d["timestamp"] == "2024-01-15T10:30:00"
        assert "main.tex" in d["tex_files"]
        assert "main.tex" in d["tex_contents"]

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "profile": "ramin",
            "lang": "en",
            "timestamp": "2024-01-15T10:30:00",
            "tex_files": {"main.tex": "abc123"},
            "tex_contents": {"main.tex": "content"},
            "pdf_path": "/output/ramin_en.pdf",
        }
        state = BuildState.from_dict(data)

        assert state.profile == "ramin"
        assert state.lang == "en"
        assert state.tex_files["main.tex"] == "abc123"

    def test_roundtrip(self):
        """Test to_dict and from_dict roundtrip."""
        original = BuildState(
            profile="test",
            lang="de",
            timestamp="2024-01-15T10:30:00",
            tex_files={"a.tex": "hash1"},
            tex_contents={"a.tex": "content1"},
        )
        restored = BuildState.from_dict(original.to_dict())

        assert restored.profile == original.profile
        assert restored.lang == original.lang
        assert restored.tex_files == original.tex_files
        assert restored.tex_contents == original.tex_contents


class TestDiffReport:
    """Tests for DiffReport dataclass."""

    def test_to_json(self):
        """Test JSON serialization."""
        report = DiffReport(
            profile="ramin",
            lang="en",
            files_compared=3,
            files_changed=1,
            has_previous_build=True,
        )
        json_str = report.to_json()
        data = json.loads(json_str)

        assert data["profile"] == "ramin"
        assert data["summary"]["files_compared"] == 3
        assert data["summary"]["files_changed"] == 1

    def test_format_unified_diff(self):
        """Test formatting of unified diffs."""
        report = DiffReport(profile="ramin", lang="en")
        report.diffs = [
            DiffResult(
                file_name="main.tex",
                has_changes=True,
                unified_diff="--- a/main.tex\n+++ b/main.tex\n-old\n+new\n",
            ),
            DiffResult(
                file_name="other.tex",
                has_changes=False,
            ),
        ]

        output = report.format_unified_diff()
        assert "main.tex" in output
        assert "+new" in output
        assert "other.tex" not in output


class TestHashContent:
    """Tests for hash_content function."""

    def test_consistent_hash(self):
        """Test that same content produces same hash."""
        content = "Hello, World!"
        h1 = hash_content(content)
        h2 = hash_content(content)

        assert h1 == h2
        assert len(h1) == 16

    def test_different_content_different_hash(self):
        """Test that different content produces different hash."""
        h1 = hash_content("Hello")
        h2 = hash_content("World")

        assert h1 != h2


class TestComputeDiff:
    """Tests for compute_diff function."""

    def test_no_changes(self):
        """Test when files are identical."""
        content = "Line 1\nLine 2\n"
        result = compute_diff("test.tex", content, content)

        assert result.has_changes is False
        assert result.added_lines == 0
        assert result.removed_lines == 0

    def test_new_file(self):
        """Test when file is new."""
        result = compute_diff("test.tex", None, "New content")

        assert result.has_changes is True
        assert result.added_lines >= 1
        assert result.removed_lines == 0
        assert "new file" in result.unified_diff

    def test_deleted_file(self):
        """Test when file is deleted."""
        result = compute_diff("test.tex", "Old content", None)

        assert result.has_changes is True
        assert result.added_lines == 0
        assert result.removed_lines >= 1
        assert "deleted file" in result.unified_diff

    def test_modified_file(self):
        """Test when file is modified."""
        old_content = "Line 1\nLine 2\n"
        new_content = "Line 1\nLine 2 modified\nLine 3\n"
        result = compute_diff("test.tex", old_content, new_content)

        assert result.has_changes is True
        assert result.added_lines > 0

    def test_both_none(self):
        """Test when both contents are None."""
        result = compute_diff("test.tex", None, None)
        assert result.has_changes is False


class TestStateManagement:
    """Tests for state save/load functions."""

    def test_get_state_dir(self, tmp_path):
        """Test state directory path."""
        result = get_state_dir(tmp_path)
        assert result == tmp_path / ".state"

    def test_save_and_load_state(self, tmp_path):
        """Test saving and loading state."""
        state = BuildState(
            profile="ramin",
            lang="en",
            timestamp="2024-01-15T10:30:00",
            tex_files={"main.tex": "abc123"},
            tex_contents={"main.tex": "\\documentclass{article}"},
        )

        save_build_state(state, tmp_path)
        loaded = load_build_state("ramin", "en", tmp_path)

        assert loaded is not None
        assert loaded.profile == "ramin"
        assert loaded.lang == "en"
        assert loaded.tex_files == state.tex_files
        assert loaded.tex_contents == state.tex_contents

    def test_load_nonexistent_state(self, tmp_path):
        """Test loading state that doesn't exist."""
        result = load_build_state("nonexistent", "xx", tmp_path)
        assert result is None


class TestCaptureTexState:
    """Tests for capture_tex_state function."""

    def test_capture_tex_files(self, tmp_path):
        """Test capturing TeX file state."""
        latex_dir = tmp_path / "latex"
        latex_dir.mkdir()

        # Create some TeX files
        (latex_dir / "main.tex").write_text("\\documentclass{article}")
        sections_dir = latex_dir / "sections"
        sections_dir.mkdir()
        (sections_dir / "header.tex").write_text("\\section{Header}")

        state = capture_tex_state("ramin", "en", latex_dir)

        assert state.profile == "ramin"
        assert state.lang == "en"
        assert "main.tex" in state.tex_files
        assert "sections/header.tex" in state.tex_files
        assert state.timestamp is not None

    def test_capture_empty_directory(self, tmp_path):
        """Test capturing state from non-existent directory."""
        state = capture_tex_state("ramin", "en", tmp_path / "nonexistent")

        assert state.tex_files == {}
        assert state.tex_contents == {}


class TestCompareBuilds:
    """Tests for compare_builds function."""

    def test_no_previous_build(self, tmp_path):
        """Test comparison when there's no previous build."""
        report = compare_builds("ramin", "en", tmp_path / "latex", tmp_path)

        assert report.has_previous_build is False
        assert report.files_compared == 0

    def test_with_changes(self, tmp_path):
        """Test comparison with changes."""
        # Create and save previous state
        prev_state = BuildState(
            profile="ramin",
            lang="en",
            timestamp="2024-01-15T10:00:00",
            tex_files={"main.tex": "oldhash"},
            tex_contents={"main.tex": "Old content"},
        )
        save_build_state(prev_state, tmp_path)

        # Create current files
        latex_dir = tmp_path / "latex" / "ramin" / "en"
        latex_dir.mkdir(parents=True)
        (latex_dir / "main.tex").write_text("New content")

        report = compare_builds("ramin", "en", latex_dir, tmp_path)

        assert report.has_previous_build is True
        assert report.files_compared == 1
        assert report.files_changed == 1


class TestDiffCommandHandler:
    """Tests for diff_command_handler function."""

    def test_no_previous_build_message(self, tmp_path):
        """Test message when no previous build exists."""
        report, output = diff_command_handler("ramin", "en", tmp_path, "text")

        assert report.has_previous_build is False
        assert "No previous build found" in output

    def test_json_output(self, tmp_path):
        """Test JSON output format."""
        report, output = diff_command_handler("ramin", "en", tmp_path, "json")

        data = json.loads(output)
        assert data["profile"] == "ramin"
        assert data["lang"] == "en"
