"""
Base exporter interface for CV Generator.

Defines the protocol that all exporters must implement and provides
shared utilities for export path management.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    """Result of an export operation."""

    format_name: str
    success: bool
    output_path: Optional[Path] = None
    error: Optional[str] = None

    def __repr__(self) -> str:
        status = "✅" if self.success else "❌"
        return f"ExportResult({status} {self.format_name}: {self.output_path or self.error})"


class Exporter(ABC):
    """
    Base class for CV exporters.

    All exporters must implement:
    - format_name: The name of the export format (e.g., 'html', 'md', 'docx')
    - export(): Export CV data to the target format
    """

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Return the name of the export format."""
        ...

    @property
    def file_extension(self) -> str:
        """Return the file extension for this format (default: format_name)."""
        return self.format_name

    @abstractmethod
    def export(
        self,
        cv_data: Dict[str, Any],
        output_dir: Path,
        profile_name: str,
        lang: str,
        **_opts: Any
    ) -> ExportResult:
        """
        Export CV data to the target format.

        Args:
            cv_data: Dictionary containing CV data.
            output_dir: Directory to write output files.
            profile_name: Name of the CV profile (e.g., 'ramin').
            lang: Language code (e.g., 'en', 'de', 'fa').
            **opts: Additional exporter-specific options.

        Returns:
            ExportResult with success status and output path.
        """
        ...

    def get_output_path(
        self,
        output_dir: Path,
        profile_name: str,
        lang: str
    ) -> Path:
        """
        Get the standard output path for this exporter.

        Args:
            output_dir: Base output directory.
            profile_name: Name of the CV profile.
            lang: Language code.

        Returns:
            Full path to the output file.
        """
        # Structure: output/<format>/<profile>/<lang>/cv.<ext>
        format_dir = output_dir / self.format_name / profile_name / lang
        format_dir.mkdir(parents=True, exist_ok=True)
        return format_dir / f"cv.{self.file_extension}"


# Registry of available exporters
_EXPORTERS: Dict[str, Type[Exporter]] = {}


def register_exporter(exporter_class: Type[Exporter]) -> Type[Exporter]:
    """
    Register an exporter class.

    Args:
        exporter_class: The exporter class to register.

    Returns:
        The exporter class (for use as a decorator).

    Note:
        The exporter class must have format_name as a property.
        We create a temporary instance to get the format_name for registration.
        This happens once at import time, not on each use.
    """
    # Create a single instance at registration time (module load)
    # This is a one-time cost, not per-export
    instance = exporter_class()
    format_key = instance.format_name
    _EXPORTERS[format_key] = exporter_class
    logger.debug(f"Registered exporter: {format_key}")
    return exporter_class


def get_exporter(format_name: str) -> Optional[Exporter]:
    """
    Get an exporter instance by format name.

    Args:
        format_name: The format to export to (e.g., 'html', 'md').

    Returns:
        Exporter instance or None if not found.
    """
    exporter_class = _EXPORTERS.get(format_name)
    if exporter_class:
        return exporter_class()
    return None


def list_exporters() -> List[str]:
    """
    List all registered exporter format names.

    Returns:
        List of format names.
    """
    return list(_EXPORTERS.keys())
