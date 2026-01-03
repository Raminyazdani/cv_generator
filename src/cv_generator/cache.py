"""
Build cache management for CV Generator.

Provides:
- Content hashing for inputs (CV JSON, templates, assets)
- Cache state storage in output/.cache/
- Incremental build detection
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Cache format version - bump this if cache structure changes
CACHE_VERSION = 1


def hash_file(filepath: Path) -> str:
    """
    Compute SHA256 hash of a file's contents.

    Args:
        filepath: Path to the file to hash.

    Returns:
        Hex-encoded SHA256 hash string.
    """
    hasher = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, IOError) as e:
        logger.debug(f"Could not hash file {filepath}: {e}")
        return ""


def hash_bytes(data: bytes) -> str:
    """
    Compute SHA256 hash of bytes.

    Args:
        data: Bytes to hash.

    Returns:
        Hex-encoded SHA256 hash string.
    """
    return hashlib.sha256(data).hexdigest()


def hash_dict(data: Dict[str, Any]) -> str:
    """
    Compute SHA256 hash of a dictionary by serializing to JSON.

    Args:
        data: Dictionary to hash.

    Returns:
        Hex-encoded SHA256 hash string.
    """
    # Use sort_keys for deterministic ordering
    json_bytes = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hash_bytes(json_bytes)


@dataclass
class BuildCacheEntry:
    """Cache entry for a single CV build."""

    cv_json_hash: str = ""
    template_hashes: Dict[str, str] = field(default_factory=dict)
    asset_hashes: Dict[str, str] = field(default_factory=dict)
    output_hash: str = ""
    version: int = CACHE_VERSION

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "cv_json_hash": self.cv_json_hash,
            "template_hashes": self.template_hashes,
            "asset_hashes": self.asset_hashes,
            "output_hash": self.output_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BuildCacheEntry":
        """Create from dictionary."""
        return cls(
            cv_json_hash=data.get("cv_json_hash", ""),
            template_hashes=data.get("template_hashes", {}),
            asset_hashes=data.get("asset_hashes", {}),
            output_hash=data.get("output_hash", ""),
            version=data.get("version", 0),
        )


class BuildCache:
    """
    Manages build cache for incremental builds.

    Cache is stored in output/.cache/ directory, outside of data/.
    """

    def __init__(self, cache_dir: Path):
        """
        Initialize the build cache.

        Args:
            cache_dir: Directory to store cache files (e.g., output/.cache/).
        """
        self.cache_dir = cache_dir

    def _get_cache_path(self, profile: str, lang: str) -> Path:
        """Get the cache file path for a specific profile/lang combination."""
        return self.cache_dir / f"{profile}_{lang}.json"

    def get_entry(self, profile: str, lang: str) -> Optional[BuildCacheEntry]:
        """
        Get cached entry for a profile/lang combination.

        Args:
            profile: Profile name (e.g., "ramin").
            lang: Language code (e.g., "en").

        Returns:
            BuildCacheEntry if cache exists and is valid, None otherwise.
        """
        cache_path = self._get_cache_path(profile, lang)
        if not cache_path.exists():
            logger.debug(f"No cache found for {profile}_{lang}")
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            entry = BuildCacheEntry.from_dict(data)

            # Validate cache version
            if entry.version != CACHE_VERSION:
                logger.debug(
                    f"Cache version mismatch for {profile}_{lang}: "
                    f"{entry.version} != {CACHE_VERSION}"
                )
                return None

            return entry
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.debug(f"Error reading cache for {profile}_{lang}: {e}")
            return None

    def save_entry(self, profile: str, lang: str, entry: BuildCacheEntry) -> None:
        """
        Save a cache entry for a profile/lang combination.

        Args:
            profile: Profile name.
            lang: Language code.
            entry: Cache entry to save.
        """
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self._get_cache_path(profile, lang)

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, indent=2)
            logger.debug(f"Saved cache for {profile}_{lang}")
        except OSError as e:
            logger.warning(f"Could not save cache for {profile}_{lang}: {e}")

    def clear(self) -> None:
        """Clear all cache files."""
        if self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                except OSError:
                    pass
            logger.info("Cleared build cache")


def compute_input_hashes(
    cv_file: Path,
    templates_dir: Path,
    assets: Optional[List[Path]] = None,
) -> BuildCacheEntry:
    """
    Compute hashes for all build inputs.

    Args:
        cv_file: Path to the CV JSON file.
        templates_dir: Path to the templates directory.
        assets: Optional list of asset files (e.g., profile picture).

    Returns:
        BuildCacheEntry with computed hashes.
    """
    entry = BuildCacheEntry()

    # Hash CV JSON
    entry.cv_json_hash = hash_file(cv_file)

    # Hash all template files
    if templates_dir.exists():
        for tmpl_path in sorted(templates_dir.glob("*.tex")):
            entry.template_hashes[tmpl_path.name] = hash_file(tmpl_path)

    # Hash assets
    if assets:
        for asset_path in assets:
            if asset_path.exists():
                entry.asset_hashes[str(asset_path)] = hash_file(asset_path)

    return entry


def needs_rebuild(
    cached: Optional[BuildCacheEntry],
    current: BuildCacheEntry,
) -> tuple[bool, str]:
    """
    Determine if a rebuild is needed by comparing cache entries.

    Args:
        cached: Previously cached entry (None if no cache).
        current: Current input hashes.

    Returns:
        Tuple of (needs_rebuild: bool, reason: str).
    """
    if cached is None:
        return True, "no cache"

    if cached.cv_json_hash != current.cv_json_hash:
        return True, "CV JSON changed"

    # Check template changes
    for tmpl_name, tmpl_hash in current.template_hashes.items():
        if cached.template_hashes.get(tmpl_name) != tmpl_hash:
            return True, f"template '{tmpl_name}' changed"

    # Check for removed templates
    for tmpl_name in cached.template_hashes:
        if tmpl_name not in current.template_hashes:
            return True, f"template '{tmpl_name}' removed"

    # Check asset changes
    for asset_path, asset_hash in current.asset_hashes.items():
        if cached.asset_hashes.get(asset_path) != asset_hash:
            return True, f"asset '{asset_path}' changed"

    return False, "up to date"


def get_cache_dir(output_root: Path) -> Path:
    """
    Get the cache directory path.

    Args:
        output_root: Root output directory.

    Returns:
        Path to the cache directory (output/.cache/).
    """
    return output_root / ".cache"
