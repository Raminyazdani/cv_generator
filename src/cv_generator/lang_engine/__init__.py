"""
Lang Engine - Language translation utilities for CV Generator.

This module provides tools for:
- Generating language mapping files (lang.json) from CV JSON keys
- Translating CV JSON keys to different languages
"""

# Lazy imports to avoid circular import warnings when running as __main__
def __getattr__(name: str):
    """Lazy import of submodule attributes."""
    if name in ("collect_keys", "merge_lang_data", "update_lang_json"):
        from .create_lang import collect_keys, merge_lang_data, update_lang_json
        return {"collect_keys": collect_keys, "merge_lang_data": merge_lang_data,
                "update_lang_json": update_lang_json}[name]
    elif name in ("detect_language_from_filename", "translate_key", "translate_cv",
                  "load_lang_map", "process_cv_file"):
        from .translate_cv_keys import (
            detect_language_from_filename,
            load_lang_map,
            process_cv_file,
            translate_cv,
            translate_key,
        )
        return {"detect_language_from_filename": detect_language_from_filename,
                "translate_key": translate_key, "translate_cv": translate_cv,
                "load_lang_map": load_lang_map, "process_cv_file": process_cv_file}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "collect_keys",
    "merge_lang_data",
    "update_lang_json",
    "detect_language_from_filename",
    "translate_key",
    "translate_cv",
    "load_lang_map",
    "process_cv_file",
]
