"""
CV Generator - Generate beautiful PDF CVs from JSON data.

This package provides tools to convert JSON CV files into professional
PDF resumes using Jinja2 templates and the Awesome-CV LaTeX class.
"""

__version__ = "1.0.0"
__author__ = "CV Generator Contributors"

from .generator import generate_cv, generate_all_cvs
from .io import discover_cv_files, load_cv_json, load_lang_map
from .jinja_env import create_jinja_env
from .paths import get_repo_root
from .ensure import run_ensure, EnsureReport, EnsureIssue
from .db import (
    init_db,
    import_cv,
    import_all_cvs,
    export_cv,
    export_all_cvs,
    diff_cv,
    diff_all_cvs,
    list_persons,
    list_tags,
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
    "init_db",
    "import_cv",
    "import_all_cvs",
    "export_cv",
    "export_all_cvs",
    "diff_cv",
    "diff_all_cvs",
    "list_persons",
    "list_tags",
    "__version__",
]
