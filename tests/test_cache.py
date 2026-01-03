"""
Tests for cv_generator.cache module.

Tests the build caching system for incremental builds.
"""

import json
from pathlib import Path

import pytest

from cv_generator.cache import (
    CACHE_VERSION,
    BuildCache,
    BuildCacheEntry,
    compute_input_hashes,
    get_cache_dir,
    hash_bytes,
    hash_dict,
    hash_file,
    needs_rebuild,
)


class TestHashFunctions:
    """Tests for hash utility functions."""

    def test_hash_bytes(self):
        """Test hashing bytes."""
        data = b"hello world"
        h = hash_bytes(data)
        assert len(h) == 64  # SHA256 hex is 64 chars
        assert h == hash_bytes(data)  # Same input = same hash

    def test_hash_bytes_different_input(self):
        """Test that different inputs produce different hashes."""
        h1 = hash_bytes(b"hello")
        h2 = hash_bytes(b"world")
        assert h1 != h2

    def test_hash_dict(self):
        """Test hashing dictionaries."""
        d = {"name": "test", "value": 123}
        h = hash_dict(d)
        assert len(h) == 64

    def test_hash_dict_order_independent(self):
        """Test that dict order doesn't affect hash."""
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 2, "a": 1}
        assert hash_dict(d1) == hash_dict(d2)

    def test_hash_file(self, tmp_path):
        """Test hashing a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        h = hash_file(test_file)
        assert len(h) == 64
        assert h == hash_file(test_file)

    def test_hash_file_nonexistent(self, tmp_path):
        """Test hashing a nonexistent file returns empty string."""
        nonexistent = tmp_path / "nonexistent.txt"
        h = hash_file(nonexistent)
        assert h == ""


class TestBuildCacheEntry:
    """Tests for BuildCacheEntry dataclass."""

    def test_to_dict(self):
        """Test converting to dictionary."""
        entry = BuildCacheEntry(
            cv_json_hash="abc123",
            template_hashes={"layout.tex": "def456"},
            asset_hashes={"/path/to/pic.jpg": "ghi789"},
            output_hash="jkl012",
        )

        d = entry.to_dict()
        assert d["cv_json_hash"] == "abc123"
        assert d["template_hashes"]["layout.tex"] == "def456"
        assert d["version"] == CACHE_VERSION

    def test_from_dict(self):
        """Test creating from dictionary."""
        d = {
            "version": CACHE_VERSION,
            "cv_json_hash": "abc123",
            "template_hashes": {"layout.tex": "def456"},
            "asset_hashes": {},
            "output_hash": "",
        }

        entry = BuildCacheEntry.from_dict(d)
        assert entry.cv_json_hash == "abc123"
        assert entry.template_hashes["layout.tex"] == "def456"

    def test_roundtrip(self):
        """Test to_dict/from_dict roundtrip."""
        original = BuildCacheEntry(
            cv_json_hash="abc",
            template_hashes={"a.tex": "123", "b.tex": "456"},
        )

        restored = BuildCacheEntry.from_dict(original.to_dict())
        assert restored.cv_json_hash == original.cv_json_hash
        assert restored.template_hashes == original.template_hashes


class TestBuildCache:
    """Tests for BuildCache class."""

    def test_save_and_get_entry(self, tmp_path):
        """Test saving and retrieving cache entries."""
        cache_dir = tmp_path / ".cache"
        cache = BuildCache(cache_dir)

        entry = BuildCacheEntry(cv_json_hash="abc123")
        cache.save_entry("ramin", "en", entry)

        # Verify cache file was created
        cache_file = cache_dir / "ramin_en.json"
        assert cache_file.exists()

        # Retrieve entry
        retrieved = cache.get_entry("ramin", "en")
        assert retrieved is not None
        assert retrieved.cv_json_hash == "abc123"

    def test_get_entry_nonexistent(self, tmp_path):
        """Test getting a nonexistent entry returns None."""
        cache = BuildCache(tmp_path / ".cache")
        entry = cache.get_entry("nonexistent", "en")
        assert entry is None

    def test_get_entry_invalid_version(self, tmp_path):
        """Test that old cache versions are invalidated."""
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()

        # Write an old version cache
        old_cache = {
            "version": CACHE_VERSION - 1,  # Old version
            "cv_json_hash": "abc",
            "template_hashes": {},
            "asset_hashes": {},
            "output_hash": "",
        }
        cache_file = cache_dir / "test_en.json"
        cache_file.write_text(json.dumps(old_cache))

        cache = BuildCache(cache_dir)
        entry = cache.get_entry("test", "en")
        assert entry is None  # Old version should be rejected

    def test_clear(self, tmp_path):
        """Test clearing the cache."""
        cache_dir = tmp_path / ".cache"
        cache = BuildCache(cache_dir)

        # Save some entries
        cache.save_entry("user1", "en", BuildCacheEntry(cv_json_hash="a"))
        cache.save_entry("user2", "de", BuildCacheEntry(cv_json_hash="b"))

        assert len(list(cache_dir.glob("*.json"))) == 2

        # Clear cache
        cache.clear()

        assert len(list(cache_dir.glob("*.json"))) == 0


class TestComputeInputHashes:
    """Tests for compute_input_hashes function."""

    def test_compute_hashes(self, tmp_path):
        """Test computing input hashes."""
        # Create a CV file
        cv_file = tmp_path / "test.json"
        cv_file.write_text('{"basics": [{"fname": "Test"}]}')

        # Create templates directory
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "layout.tex").write_text("\\documentclass{article}")
        (templates_dir / "header.tex").write_text("% Header")

        entry = compute_input_hashes(cv_file, templates_dir)

        assert entry.cv_json_hash != ""
        assert len(entry.template_hashes) == 2
        assert "layout.tex" in entry.template_hashes
        assert "header.tex" in entry.template_hashes

    def test_compute_hashes_with_assets(self, tmp_path):
        """Test computing hashes with assets."""
        cv_file = tmp_path / "test.json"
        cv_file.write_text("{}")

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "layout.tex").write_text("test")

        asset = tmp_path / "pic.jpg"
        asset.write_bytes(b"\xff\xd8\xff\xe0")  # JPEG magic bytes

        entry = compute_input_hashes(cv_file, templates_dir, assets=[asset])

        assert len(entry.asset_hashes) == 1
        assert str(asset) in entry.asset_hashes


class TestNeedsRebuild:
    """Tests for needs_rebuild function."""

    def test_needs_rebuild_no_cache(self):
        """Test that missing cache triggers rebuild."""
        current = BuildCacheEntry(cv_json_hash="abc")
        needs, reason = needs_rebuild(None, current)
        assert needs is True
        assert "no cache" in reason

    def test_needs_rebuild_json_changed(self):
        """Test that changed JSON triggers rebuild."""
        cached = BuildCacheEntry(cv_json_hash="old")
        current = BuildCacheEntry(cv_json_hash="new")

        needs, reason = needs_rebuild(cached, current)
        assert needs is True
        assert "JSON changed" in reason

    def test_needs_rebuild_template_changed(self):
        """Test that changed template triggers rebuild."""
        cached = BuildCacheEntry(
            cv_json_hash="same",
            template_hashes={"layout.tex": "old"},
        )
        current = BuildCacheEntry(
            cv_json_hash="same",
            template_hashes={"layout.tex": "new"},
        )

        needs, reason = needs_rebuild(cached, current)
        assert needs is True
        assert "layout.tex" in reason

    def test_needs_rebuild_template_removed(self):
        """Test that removed template triggers rebuild."""
        cached = BuildCacheEntry(
            cv_json_hash="same",
            template_hashes={"layout.tex": "abc", "old.tex": "def"},
        )
        current = BuildCacheEntry(
            cv_json_hash="same",
            template_hashes={"layout.tex": "abc"},
        )

        needs, reason = needs_rebuild(cached, current)
        assert needs is True
        assert "old.tex" in reason

    def test_no_rebuild_needed(self):
        """Test that identical inputs don't trigger rebuild."""
        cached = BuildCacheEntry(
            cv_json_hash="abc",
            template_hashes={"layout.tex": "def"},
        )
        current = BuildCacheEntry(
            cv_json_hash="abc",
            template_hashes={"layout.tex": "def"},
        )

        needs, reason = needs_rebuild(cached, current)
        assert needs is False
        assert "up to date" in reason


class TestGetCacheDir:
    """Tests for get_cache_dir function."""

    def test_cache_dir_path(self, tmp_path):
        """Test cache directory path."""
        cache_dir = get_cache_dir(tmp_path)
        assert cache_dir == tmp_path / ".cache"
