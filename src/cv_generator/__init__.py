"""
CV Generator - Web UI for managing CV data.

This package provides a lightweight web interface for:
- Browsing and editing CV data stored in a SQLite database
- Managing tags and filtering CV entries
- Importing and exporting CV JSON files
- Multi-language support (English, German, Persian)
"""

__version__ = "2.0.0"
__author__ = "CV Generator Contributors"

# Database operations
from .db import (
    create_tag,
    delete_tag,
    export_cv,
    get_entry,
    get_person_sections,
    get_section_entries,
    import_cv,
    init_db,
    list_persons,
    list_tags,
    update_entry_tags,
    update_tag,
)

# IO utilities
from .io import discover_cv_files, load_cv_json

# Path utilities
from .paths import get_repo_root

__all__ = [
    # Database operations
    "init_db",
    "import_cv",
    "export_cv",
    "list_persons",
    "list_tags",
    "create_tag",
    "update_tag",
    "delete_tag",
    "update_entry_tags",
    "get_entry",
    "get_section_entries",
    "get_person_sections",
    # IO utilities
    "discover_cv_files",
    "load_cv_json",
    # Path utilities
    "get_repo_root",
    # Version
    "__version__",
]
