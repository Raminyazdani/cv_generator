"""
Path resolution helpers for CV Generator.

Provides consistent path resolution relative to the repository root,
regardless of the current working directory.
"""

import os
from pathlib import Path
from typing import Optional

# Cache for the repository root
_repo_root: Optional[Path] = None


def get_repo_root() -> Path:
    """
    Get the repository root directory.
    
    Attempts to find the repo root by looking for key files:
    - pyproject.toml
    - generate_cv.py
    - awesome-cv.cls
    
    Returns:
        Path to the repository root.
        
    Raises:
        RuntimeError: If the repository root cannot be determined.
    """
    global _repo_root
    
    if _repo_root is not None:
        return _repo_root
    
    # Start from this file's location and search upward
    current = Path(__file__).resolve()
    
    # Marker files that indicate repo root
    markers = ["pyproject.toml", "generate_cv.py", "awesome-cv.cls"]
    
    # Walk up the directory tree
    for parent in [current] + list(current.parents):
        for marker in markers:
            if (parent / marker).exists():
                _repo_root = parent
                return _repo_root
    
    # Fallback: use CWD
    _repo_root = Path.cwd().resolve()
    return _repo_root


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
    
    return (base / p).resolve()


def get_default_cvs_path() -> Path:
    """Get the default path to CV JSON files."""
    return get_repo_root() / "data" / "cvs"


def get_default_templates_path() -> Path:
    """Get the default path to template files."""
    return get_repo_root() / "templates"


def get_default_output_path() -> Path:
    """Get the default path for output files."""
    return get_repo_root() / "output"


def get_default_result_path() -> Path:
    """Get the default path for intermediate result files."""
    return get_repo_root() / "result"


def get_lang_engine_path() -> Path:
    """Get the path to the language engine directory."""
    return Path(__file__).resolve().parent / "lang_engine"
