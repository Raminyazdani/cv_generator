"""
Path resolution helpers for CV Generator.

Provides consistent path resolution relative to the repository root,
regardless of the current working directory.

This module provides:
- Repository root detection
- Unified artifact path management via ArtifactPaths class
- OS-agnostic path handling

Output Structure:
    output/
      pdf/<profile_name>/<lang>/cv.pdf
      latex/<profile_name>/<lang>/main.tex
      latex/<profile_name>/<lang>/build/  (aux/log files)
      json/<profile_name>/<lang>/cv.json
      logs/run_<datetime>.log
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

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
    """
    Get the default path for intermediate result files.
    
    DEPRECATED: Use ArtifactPaths.latex_dir instead.
    This function is kept for backward compatibility but now returns
    a path inside the unified output directory.
    """
    # Now points to output/latex for backward compatibility
    return get_repo_root() / "output" / "latex"


def get_lang_engine_path() -> Path:
    """Get the path to the language engine directory."""
    return Path(__file__).resolve().parent / "lang_engine"


class ArtifactPaths:
    """
    Centralized artifact path management for CV Generator.
    
    Provides a predictable, unified output structure for all generated artifacts.
    All paths are OS-agnostic and deterministic.
    
    Output Structure:
        output/
          pdf/<profile_name>/<lang>/cv.pdf
          latex/<profile_name>/<lang>/main.tex
          latex/<profile_name>/<lang>/build/  (aux/log files)
          json/<profile_name>/<lang>/cv.json
          logs/run_<datetime>.log
    
    Example:
        paths = ArtifactPaths(profile="ramin", lang="en")
        print(paths.pdf_path)      # output/pdf/ramin/en/cv.pdf
        print(paths.latex_dir)     # output/latex/ramin/en
        print(paths.tex_path)      # output/latex/ramin/en/main.tex
    """
    
    def __init__(
        self,
        profile: str,
        lang: str,
        output_root: Optional[Path] = None,
        variant: Optional[str] = None
    ):
        """
        Initialize artifact paths for a CV generation run.
        
        Args:
            profile: Profile/person name (e.g., "ramin").
            lang: Language code (e.g., "en", "de", "fa").
            output_root: Root output directory. Defaults to repo_root/output.
            variant: Optional CV variant (e.g., "full", "academic", "onepage").
        """
        self.profile = profile
        self.lang = lang
        self.variant = variant
        
        if output_root is None:
            output_root = get_default_output_path()
        self.output_root = Path(output_root)
        
        # Build the base path with optional variant
        if variant:
            self._base_path = f"{profile}/{variant}/{lang}"
        else:
            self._base_path = f"{profile}/{lang}"
    
    @property
    def pdf_dir(self) -> Path:
        """Directory for PDF output."""
        return self.output_root / "pdf" / self._base_path
    
    @property
    def pdf_path(self) -> Path:
        """Path to the generated PDF file."""
        return self.pdf_dir / "cv.pdf"
    
    @property
    def pdf_named_path(self) -> Path:
        """Path to PDF with profile_lang naming (for backward compatibility)."""
        return self.pdf_dir / f"{self.profile}_{self.lang}.pdf"
    
    @property
    def latex_dir(self) -> Path:
        """Directory for LaTeX source files."""
        return self.output_root / "latex" / self._base_path
    
    @property
    def tex_path(self) -> Path:
        """Path to the main rendered LaTeX file."""
        return self.latex_dir / "main.tex"
    
    @property
    def sections_dir(self) -> Path:
        """Directory for individual section .tex files."""
        return self.latex_dir / "sections"
    
    @property
    def build_dir(self) -> Path:
        """Directory for LaTeX build artifacts (aux, log, etc.)."""
        return self.latex_dir / "build"
    
    @property
    def json_dir(self) -> Path:
        """Directory for exported JSON files."""
        return self.output_root / "json" / self._base_path
    
    @property
    def json_path(self) -> Path:
        """Path to the exported CV JSON file."""
        return self.json_dir / "cv.json"
    
    @property
    def logs_dir(self) -> Path:
        """Directory for log files."""
        return self.output_root / "logs"
    
    def ensure_dirs(self) -> None:
        """Create all necessary directories."""
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.latex_dir.mkdir(parents=True, exist_ok=True)
        self.sections_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created artifact directories for {self.profile}/{self.lang}")
    
    def log_paths(self) -> None:
        """Log the artifact paths for visibility."""
        logger.info(f"📁 Output root: {self.output_root}")
        logger.info(f"   PDF output: {self.pdf_dir}")
        logger.info(f"   LaTeX source: {self.latex_dir}")
    
    def __repr__(self) -> str:
        return f"ArtifactPaths(profile={self.profile!r}, lang={self.lang!r}, output_root={self.output_root})"


def get_run_log_path(output_root: Optional[Path] = None) -> Path:
    """
    Get the path for a timestamped run log file.
    
    Args:
        output_root: Root output directory. Defaults to repo_root/output.
        
    Returns:
        Path to the log file (e.g., output/logs/run_20260102_234110.log)
    """
    if output_root is None:
        output_root = get_default_output_path()
    
    logs_dir = output_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return logs_dir / f"run_{timestamp}.log"


def get_legacy_pdf_path(profile: str, lang: str, output_root: Optional[Path] = None) -> Path:
    """
    Get the legacy PDF path for backward compatibility.
    
    This returns the path where PDFs were stored in the old structure
    (output/<profile>_<lang>.pdf) for migration purposes.
    
    Args:
        profile: Profile/person name.
        lang: Language code.
        output_root: Root output directory.
        
    Returns:
        Legacy PDF path.
    """
    if output_root is None:
        output_root = get_default_output_path()
    
    return output_root / f"{profile}_{lang}.pdf"
