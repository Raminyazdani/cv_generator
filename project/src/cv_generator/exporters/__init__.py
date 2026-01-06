"""
CV Generator exporters package.

Provides export functionality for generating CV output in various formats:
- HTML: Web-ready preview
- Markdown: Plain text with formatting
- DOCX: Optional Word document export (requires Pandoc)
"""

from .base import Exporter, ExportResult, get_exporter, list_exporters
from .html import HTMLExporter
from .markdown import MarkdownExporter

__all__ = [
    "Exporter",
    "ExportResult",
    "get_exporter",
    "list_exporters",
    "HTMLExporter",
    "MarkdownExporter",
]
