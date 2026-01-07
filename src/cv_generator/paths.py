"""
Path resolution helpers for CV Generator.

Provides consistent path resolution relative to the repository root,
regardless of the current working directory.

This module provides:
- Repository root detection
- OS-agnostic path handling
- Default path helpers for data and output directories
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Cache for the repository root
_repo_root: Optional[Path] = None


def get_repo_root(raise_on_not_found: bool = False) -> Optional[Path]:
    """
    Get the repository root directory.

    Attempts to find the repo root by looking for key files like pyproject.toml.

    Args:
        raise_on_not_found: If True, raise error if repo root not found

    Returns:
        Path to the repository root if found, None otherwise

    Raises:
        FileNotFoundError: If raise_on_not_found=True and repo root not found
    """
    global _repo_root

    # Return cached value if already found
    if _repo_root is not None:
        return _repo_root

    # Marker files that indicate repo root
    markers = ["pyproject.toml", "setup.py", "setup.cfg"]

    # Start from this file's location and search upward
    current = Path(__file__).resolve().parent

    # Walk up directory tree
    for parent in [current] + list(current.parents):
        for marker in markers:
            if (parent / marker).exists():
                _repo_root = parent
                logger.debug(f"Found repo root: {_repo_root} (marker: {marker})")
                return _repo_root

    # Not found
    if raise_on_not_found:
        raise FileNotFoundError(
            "Could not find repository root. Searched for markers: " + ", ".join(markers) + "\n"
            "Please specify paths explicitly or ensure you're running from "
            "within the cv_generator repository."
        )

    logger.warning("Repository root not found, returning None")
    return None


def reset_repo_root_cache():
    """Reset cached repo root (useful for testing)."""
    global _repo_root
    _repo_root = None


def resolve_path(path: str | os.PathLike, base: Optional[Path] = None) -> Path:
    """
    Resolve a path, optionally relative to a base directory.

    Args:
        path: The path to resolve.
        base: Base directory for relative paths. Defaults to repo root.

    Returns:
        Resolved absolute path.
    """
    p = Path(path)
    if p.is_absolute():
        return p.resolve()

    if base is None:
        base = get_repo_root()
        if base is None:
            # Fallback to current directory if repo root not found
            base = Path.cwd()

    return (base / p).resolve()


def get_default_cvs_path() -> Path:
    """Get the default path to CV JSON files."""
    return get_repo_root() / "data" / "cvs"


def get_default_output_path() -> Path:
    """Get the default path for output files."""
    return get_repo_root() / "output"


def get_db_path() -> Path:
    """Get the default path for the SQLite database."""
    return get_repo_root() / "data" / "db" / "cv.db"
