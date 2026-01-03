"""
CV Generator - Generate beautiful PDF CVs from JSON data.

This package provides tools to convert JSON CV files into professional
PDF resumes using Jinja2 templates and the Awesome-CV LaTeX class.
"""

__version__ = "1.0.0"
__author__ = "CV Generator Contributors"

from .db import (
    create_tag,
    delete_tag,
    diff_all_cvs,
    diff_cv,
    export_all_cvs,
    export_cv,
    get_entry,
    get_person_sections,
    get_section_entries,
    import_all_cvs,
    import_cv,
    init_db,
    list_persons,
    list_tags,
    update_entry_tags,
    update_tag,
)
from .ensure import EnsureIssue, EnsureReport, run_ensure
from .generator import generate_all_cvs, generate_cv

# Registry and plugin system
from .hooks import HookContext, HookManager, HookType, get_hook_manager, register_hook
from .io import discover_cv_files, load_cv_json, load_lang_map
from .jinja_env import create_jinja_env
from .paths import get_repo_root
from .plugins import PluginInfo, PluginManager, discover_and_load_plugins, get_plugin_manager
from .registry import (
    GenericSectionAdapter,
    SectionAdapter,
    SectionRegistry,
    get_default_registry,
    register_section,
)
from .validate_schema import (
    ValidationIssue,
    ValidationReport,
    validate_cv_file,
    validate_cv_json,
)

__all__ = [
    "generate_cv",
    "generate_all_cvs",
    "discover_cv_files",
    "load_cv_json",
    "load_lang_map",
    "create_jinja_env",
    "get_repo_root",
    "run_ensure",
    "EnsureReport",
    "EnsureIssue",
    "validate_cv_file",
    "validate_cv_json",
    "ValidationReport",
    "ValidationIssue",
    "init_db",
    "import_cv",
    "import_all_cvs",
    "export_cv",
    "export_all_cvs",
    "diff_cv",
    "diff_all_cvs",
    "list_persons",
    "list_tags",
    "create_tag",
    "update_tag",
    "delete_tag",
    "update_entry_tags",
    "get_entry",
    "get_section_entries",
    "get_person_sections",
    "__version__",
    # Registry and plugin system
    "SectionAdapter",
    "GenericSectionAdapter",
    "SectionRegistry",
    "get_default_registry",
    "register_section",
    "HookType",
    "HookContext",
    "HookManager",
    "get_hook_manager",
    "register_hook",
    "PluginInfo",
    "PluginManager",
    "get_plugin_manager",
    "discover_and_load_plugins",
]
