"""
Jinja2 environment configuration for CV Generator.

Provides functions for:
- Creating the Jinja2 environment with LaTeX-compatible settings
- Custom filters for LaTeX escaping, translation, etc.
"""

import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from jinja2.bccache import FileSystemBytecodeCache

from .paths import get_default_templates_path, get_repo_root

logger = logging.getLogger(__name__)

# Toggle whether template-inserted comments are emitted
SHOW_COMMENTS = True

# RTL languages
RTL_LANGUAGES = {"fa", "ar", "he"}


def latex_escape(s: Any) -> str:
    """
    Escape LaTeX special characters in plain text.

    Args:
        s: The string to escape.

    Returns:
        LaTeX-escaped string.
    """
    if s is None:
        return ""
    s = str(s)
    # Order matters: backslash first.
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&",  r"\&"),
        ("%",  r"\%"),
        ("$",  r"\$"),
        ("#",  r"\#"),
        ("_",  r"\_"),
        ("{",  r"\{"),
        ("}",  r"\}"),
        ("~",  r"\textasciitilde{}"),
        ("^",  r"\textasciicircum{}"),
    ]
    for k, v in replacements:
        s = s.replace(k, v)
    return s


def file_exists(value: Any) -> bool:
    """Check if a file exists at the given path."""
    if value is None:
        return False
    return os.path.exists(value)


def debug_filter(value: Any) -> str:
    """Debug filter that logs value and type for debugging templates."""
    logger.debug(f"Template debug - value: {value}")
    logger.debug(f"Template debug - type: {type(value)}")
    return ""  # emit nothing in TeX


def types_filter(value: Any) -> str:
    """Types filter that logs the type for debugging templates."""
    logger.debug(f"Template types - type: {type(value)}")
    return ""  # emit nothing in TeX


def cmt(s: Any) -> str:
    """Emit a single LaTeX comment line, gated by SHOW_COMMENTS."""
    if not SHOW_COMMENTS or s is None:
        return ""
    return "% " + str(s).replace("\n", " ").strip() + "\n"


def cblock(s: Any) -> str:
    """Emit multi-line LaTeX comment block, gated by SHOW_COMMENTS."""
    if not SHOW_COMMENTS or s is None:
        return ""
    lines = str(s).splitlines() or [str(s)]
    return "".join("% " + line + "\n" for line in lines)


def find_pic(opt_name: str) -> bool:
    """Check if a profile picture exists for the given name."""
    pic_path = get_repo_root() / "data" / "pics" / f"{opt_name}.jpg"
    return pic_path.exists()


def get_pic(opt_name: str) -> str:
    """Get the path to the profile picture for the given name."""
    pic_path = get_repo_root() / "data" / "pics" / f"{opt_name}.jpg"
    return str(pic_path)


def make_translate_func(lang_map: Dict[str, Dict[str, str]], lang: str) -> Callable:
    """
    Create a translation function for a specific language.

    Returns a function t(key, default=None, escape=True) that:
    - Looks up lang_map[key][lang]
    - Falls back to default, then lang_map[key]["en"], then the raw key
    - LaTeX-escapes by default

    Args:
        lang_map: The translation mapping dictionary.
        lang: The target language code.

    Returns:
        Translation function.
    """
    def t(key: str, default: Optional[str] = None, escape: bool = True) -> str:
        result = None

        # Try to get translation for current language
        if key in lang_map:
            translations = lang_map[key]
            if lang in translations and translations[lang]:
                result = translations[lang]
            elif default is not None:
                result = default
            elif "en" in translations and translations["en"]:
                result = translations["en"]

        # Fallback to default or raw key
        if result is None:
            result = default if default is not None else key

        # LaTeX escape by default
        if escape:
            return latex_escape(result)
        return result

    return t


def make_tr_filter(lang_map: Dict[str, Dict[str, str]], lang: str) -> Callable:
    """Create a |tr filter (LaTeX-escaped translation)."""
    t = make_translate_func(lang_map, lang)
    def tr_filter(key: str) -> str:
        return t(key, escape=True)
    return tr_filter


def make_tr_raw_filter(lang_map: Dict[str, Dict[str, str]], lang: str) -> Callable:
    """Create a |tr_raw filter (unescaped translation)."""
    t = make_translate_func(lang_map, lang)
    def tr_raw_filter(key: str) -> str:
        return t(key, escape=False)
    return tr_raw_filter


def create_jinja_env(
    template_dir: Optional[Path] = None,
    lang_map: Optional[Dict[str, Dict[str, str]]] = None,
    lang: str = "en",
    cache_dir: Optional[Path] = None,
) -> Environment:
    """
    Create a Jinja2 environment configured for LaTeX template rendering.

    Args:
        template_dir: Path to the templates directory.
        lang_map: Language translation mapping (optional).
        lang: Target language code (default: "en").
        cache_dir: Directory for template bytecode cache (optional).
                   If provided, enables template caching for faster reloads.

    Returns:
        Configured Jinja2 Environment.
    """
    if template_dir is None:
        template_dir = get_default_templates_path()

    # Set up bytecode cache if cache_dir is provided
    bytecode_cache = None
    if cache_dir is not None:
        cache_path = Path(cache_dir) / "jinja2"
        cache_path.mkdir(parents=True, exist_ok=True)
        bytecode_cache = FileSystemBytecodeCache(str(cache_path))
        logger.debug(f"Enabled Jinja2 bytecode cache at {cache_path}")

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        block_start_string="<BLOCK>",
        block_end_string="</BLOCK>",
        variable_start_string="<VAR>",
        variable_end_string="</VAR>",
        comment_start_string="/*/*/*",
        comment_end_string="*/*/*/",
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
        bytecode_cache=bytecode_cache,
        auto_reload=True,  # Ensure templates are reloaded when changed
    )

    # Register common filters
    env.filters["latex_escape"] = latex_escape
    env.filters["debug"] = debug_filter
    env.filters["types"] = types_filter
    env.filters["cmt"] = cmt
    env.filters["cblock"] = cblock
    env.filters["file_exists"] = file_exists
    env.filters["get_pic"] = get_pic
    env.filters["find_pic"] = find_pic

    # Add translation filters if lang_map provided
    if lang_map is not None:
        env.filters["tr"] = make_tr_filter(lang_map, lang)
        env.filters["tr_raw"] = make_tr_raw_filter(lang_map, lang)
        env.globals["LANG_MAP"] = lang_map
        env.globals["t"] = make_translate_func(lang_map, lang)

    # Add common globals
    env.globals["SHOW_COMMENTS"] = SHOW_COMMENTS
    env.globals["LANG"] = lang
    env.globals["IS_RTL"] = lang in RTL_LANGUAGES

    logger.debug(f"Created Jinja2 environment for templates in {template_dir}")
    return env
