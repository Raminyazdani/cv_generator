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

    This function handles all LaTeX special characters that could cause
    compilation failures or unintended behavior when rendering user-provided
    content in LaTeX documents.

    Escaping rules (order matters - backslash must be first):
    1. Backslash (\\) -> \\textbackslash{} - Must be first to avoid double-escaping
    2. Braces ({}) -> \\{ \\} - After backslash to preserve \\textbackslash{}
    3. Ampersand (&) -> \\&
    4. Percent (%) -> \\%
    5. Dollar ($) -> \\$
    6. Hash (#) -> \\#
    7. Underscore (_) -> \\_
    8. Tilde (~) -> \\textasciitilde{}
    9. Caret (^) -> \\textasciicircum{}
    10. Newlines (\\n) -> \\newline{} - LaTeX line break
    11. Tabs (\\t) -> \\hspace{1em} - Visual tab spacing

    Args:
        s: The string to escape. Can be any type; None returns empty string.

    Returns:
        LaTeX-escaped string safe for use in LaTeX documents.

    Examples:
        >>> latex_escape("100%")
        '100\\%'
        >>> latex_escape("C# code")
        'C\\# code'
        >>> latex_escape("Line1\\nLine2")
        'Line1\\newline{}Line2'
        >>> latex_escape(None)
        ''
    """
    if s is None:
        return ""
    s = str(s)

    # Order matters: backslash first, then braces, then other characters.
    # This prevents double-escaping issues.
    replacements = [
        # Step 1: Backslash must be escaped first
        ("\\", r"\textbackslash{}"),
        # Step 2: Braces - after backslash to preserve \textbackslash{}
        ("{",  r"\{"),
        ("}",  r"\}"),
        # Step 3: Other special characters
        ("&",  r"\&"),
        ("%",  r"\%"),
        ("$",  r"\$"),
        ("#",  r"\#"),
        ("_",  r"\_"),
        ("~",  r"\textasciitilde{}"),
        ("^",  r"\textasciicircum{}"),
        # Step 4: Whitespace characters
        ("\n", r"\newline{}"),
        ("\t", r"\hspace{1em}"),
    ]
    for k, v in replacements:
        s = s.replace(k, v)
    return s


def latex_raw(s: Any) -> str:
    """
    Pass through a value as raw LaTeX without escaping.

    USE WITH CAUTION: This filter allows raw LaTeX commands to be rendered
    without escaping. Only use this for content that you control and trust,
    such as template-defined LaTeX markup. Never use with untrusted user input.

    Safe use cases:
    - Template-defined formatting commands
    - LaTeX commands from your own code
    - Trusted configuration values

    Unsafe use cases (DO NOT USE):
    - User-provided text fields from JSON
    - Content from external sources
    - Arbitrary user input

    Args:
        s: The string to pass through. None returns empty string.

    Returns:
        The original string unchanged, or empty string if None.

    Examples:
        >>> latex_raw("\\textbf{bold}")
        '\\textbf{bold}'
        >>> latex_raw(None)
        ''
    """
    if s is None:
        return ""
    return str(s)


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


def find_pic(opt_name: str, pics_dir: Optional[Path] = None) -> bool:
    """
    Check if a profile picture exists for the given name.
    
    Args:
        opt_name: Picture filename without extension
        pics_dir: Directory containing pictures (defaults to data/pics for backward compatibility)
    
    Returns:
        True if picture exists, False otherwise
    """
    if pics_dir is None:
        # Backward compatibility: use legacy data/pics
        repo_root = get_repo_root()
        if repo_root:
            pics_dir = repo_root / "data" / "pics"
        else:
            # Fallback to home directory
            pics_dir = Path.home() / ".cvgen" / "pics"
    
    pic_path = pics_dir / f"{opt_name}.jpg"
    return pic_path.exists()


def get_pic(opt_name: str, pics_dir: Optional[Path] = None) -> str:
    """
    Get the path to the profile picture for the given name.
    
    Args:
        opt_name: Picture filename without extension
        pics_dir: Directory containing pictures (defaults to data/pics for backward compatibility)
    
    Returns:
        String path to the picture
    """
    if pics_dir is None:
        # Backward compatibility: use legacy data/pics
        repo_root = get_repo_root()
        if repo_root:
            pics_dir = repo_root / "data" / "pics"
        else:
            # Fallback to home directory
            pics_dir = Path.home() / ".cvgen" / "pics"
    
    pic_path = pics_dir / f"{opt_name}.jpg"
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
    pics_dir: Optional[Path] = None,
) -> Environment:
    """
    Create a Jinja2 environment configured for LaTeX template rendering.

    Args:
        template_dir: Path to the templates directory.
        lang_map: Language translation mapping (optional).
        lang: Target language code (default: "en").
        cache_dir: Directory for template bytecode cache (optional).
                   If provided, enables template caching for faster reloads.
        pics_dir: Directory containing profile pictures (optional).

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

    # Create partial functions with pics_dir bound
    def find_pic_bound(opt_name: str) -> bool:
        return find_pic(opt_name, pics_dir)

    def get_pic_bound(opt_name: str) -> str:
        return get_pic(opt_name, pics_dir)

    # Register common filters
    env.filters["latex_escape"] = latex_escape
    env.filters["latex_raw"] = latex_raw
    env.filters["debug"] = debug_filter
    env.filters["types"] = types_filter
    env.filters["cmt"] = cmt
    env.filters["cblock"] = cblock
    env.filters["file_exists"] = file_exists
    env.filters["get_pic"] = get_pic_bound
    env.filters["find_pic"] = find_pic_bound

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
