"""
LaTeX compilation utilities for CV Generator.

Provides functions for:
- Running xelatex to compile .tex files to PDF
- Handling compilation output and errors
- Parsing LaTeX log files for better error diagnostics
"""

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from .errors import LatexError

logger = logging.getLogger(__name__)

# LaTeX error patterns for diagnostics
LATEX_ERROR_PATTERNS = [
    # (regex_pattern, error_type, suggestion)
    (r"! LaTeX Error: File `(.+)' not found", "missing_file", "Install the missing LaTeX package"),
    (r"! Package inputenc Error: Unicode char", "unicode", "Use XeLaTeX or escape special characters"),
    (r"! Undefined control sequence", "undefined_command", "Check template for undefined LaTeX commands"),
    (r"! Missing \$ inserted", "math_mode", "Escape $ characters with \\$"),
    (r"! Missing \{ inserted", "brace", "Check for mismatched braces in template"),
    (r"! Emergency stop", "fatal", "Critical error - check log file for details"),
    (r"! Font (.+) not found", "font", "Install the required font or use a different one"),
    (r"! Package fontspec Error", "fontspec", "Check font configuration in template"),
    (r"Runaway argument\?", "runaway", "Check for unclosed braces or environments"),
    (r"! Too many \}'s", "extra_brace", "Check for extra closing braces"),
]


def parse_latex_log(log_content: str) -> Tuple[List[str], List[str]]:
    """
    Parse LaTeX log content for error messages and suggestions.

    Args:
        log_content: Content of the LaTeX log file

    Returns:
        Tuple of (error_messages, suggestions)
    """
    errors = []
    suggestions = set()

    lines = log_content.split("\n")
    for i, line in enumerate(lines):
        line = line.strip()

        # Look for lines starting with !
        if line.startswith("!"):
            errors.append(line)

            # Check against known patterns for suggestions
            for pattern, error_type, suggestion in LATEX_ERROR_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    suggestions.add(suggestion)
                    break

        # Also capture file:line: error format
        if re.match(r"^\./.*:\d+:", line) or re.match(r"^l\.\d+", line):
            errors.append(line)

    return errors[:10], list(suggestions)  # Return at most 10 errors


def _read_log_file(log_path: Path) -> str:
    """Read LaTeX log file content."""
    try:
        return log_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


# Default LaTeX compilation timeout (can be overridden via --latex-timeout)
DEFAULT_LATEX_TIMEOUT = 120


def compile_latex(
    tex_file: Path,
    output_dir: Path,
    *,
    timeout: Optional[int] = None
) -> Optional[Path]:
    """
    Compile a LaTeX file to PDF using xelatex.

    Args:
        tex_file: Path to the .tex file to compile.
        output_dir: Directory for output files.
        timeout: Maximum time in seconds to wait for compilation (default: 120).
                 Can be overridden via CLI --latex-timeout option.

    Returns:
        Path to the generated PDF, or None if compilation fails.

    Raises:
        LatexError: If xelatex is not found.
    """
    # Use default if not specified (F-009 enhancement)
    if timeout is None:
        timeout = DEFAULT_LATEX_TIMEOUT

    if not tex_file.exists():
        raise LatexError(f"LaTeX source file not found: {tex_file}")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build the xelatex command
    cmd = [
        "xelatex",
        "-enable-etex",
        "-interaction=nonstopmode",
        "-file-line-error",
        "-synctex=1",
        f"-output-directory={output_dir}",
        str(tex_file)
    ]

    logger.info(f"Compiling LaTeX: {tex_file.name}")
    logger.debug(f"Command: {' '.join(cmd)}")

    # Path for log file
    log_path = output_dir / (tex_file.stem + ".log")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tex_file.parent
        )

        if result.returncode != 0:
            logger.warning(f"xelatex returned non-zero exit code: {result.returncode}")

            # Parse log file for errors - log at WARNING level for visibility (F-015)
            if log_path.exists():
                log_content = _read_log_file(log_path)
                errors, suggestions = parse_latex_log(log_content)

                if errors:
                    logger.warning("LaTeX errors found:")
                    for error in errors[:5]:  # Show first 5 errors at WARNING level
                        logger.warning(f"  {error}")
                    if len(errors) > 5:
                        logger.warning(f"  ... and {len(errors) - 5} more errors")

                if suggestions:
                    logger.info("Suggestions:")
                    for suggestion in suggestions:
                        logger.info(f"  - {suggestion}")

                logger.info(f"Full log available at: {log_path}")
            else:
                # Fallback to stderr if no log file
                logger.warning(f"xelatex stderr: {result.stderr}")

        # Look for the generated PDF
        pdf_name = tex_file.stem + ".pdf"
        pdf_path = output_dir / pdf_name

        if pdf_path.exists():
            logger.info(f"PDF generated: {pdf_path}")
            return pdf_path
        else:
            logger.error(f"PDF not generated: {pdf_path}")
            # Provide actionable error message
            if log_path.exists():
                logger.error(f"Check LaTeX log for details: {log_path}")
            logger.error("Common fixes:")
            logger.error("  1. Check for special characters in your CV data (#, %, _, &, $)")
            logger.error("  2. Verify all LaTeX packages are installed")
            logger.error("  3. Run with --debug to see full LaTeX output")
            return None

    except FileNotFoundError:
        logger.error("xelatex not found. Please install a LaTeX distribution.")
        raise LatexError(
            "xelatex not found. Please install MiKTeX (Windows) or TeX Live (Linux/Mac)."
        )
    except subprocess.TimeoutExpired:
        # Enhanced timeout error with helpful message (F-009)
        suggestions = (
            f"xelatex timed out after {timeout} seconds\n"
            f"Suggestions:\n"
            f"  1. Try increasing timeout: --latex-timeout {timeout * 2}\n"
            f"  2. Check for infinite loops or very large documents\n"
            f"  3. Complex CVs with many images may need more time\n"
            f"  4. Manual compilation: xelatex {tex_file}"
        )
        logger.error(suggestions)
        return None
    except Exception as e:
        logger.error(f"Error running xelatex: {e}")
        return None


def cleanup_latex_artifacts(output_dir: Path, keep_pdf: bool = True) -> None:
    """
    Clean up LaTeX auxiliary files from the output directory.

    Removes files with extensions: .aux, .log, .out, .synctex.gz, etc.

    Args:
        output_dir: Directory containing LaTeX output files.
        keep_pdf: If True, keep .pdf files. If False, remove everything.
    """
    if not output_dir.exists():
        return

    # Extensions to remove
    aux_extensions = {
        ".aux", ".log", ".out", ".synctex.gz", ".synctex",
        ".toc", ".lof", ".lot", ".bbl", ".blg", ".fdb_latexmk",
        ".fls", ".nav", ".snm", ".vrb"
    }

    for filepath in output_dir.iterdir():
        if filepath.is_file():
            if filepath.suffix in aux_extensions:
                logger.debug(f"Removing LaTeX artifact: {filepath.name}")
                try:
                    filepath.unlink()
                except OSError as e:
                    logger.warning(f"Could not remove {filepath.name}: {e}")
            elif filepath.suffix == ".pdf" and not keep_pdf:
                logger.debug(f"Removing PDF: {filepath.name}")
                try:
                    filepath.unlink()
                except OSError as e:
                    logger.warning(f"Could not remove {filepath.name}: {e}")


def rename_pdf(
    source_pdf: Path,
    target_name: str,
    output_dir: Optional[Path] = None
) -> Path:
    """
    Rename/move a PDF file to the target name.

    Args:
        source_pdf: Path to the source PDF.
        target_name: Target filename (with or without .pdf extension).
        output_dir: Target directory (defaults to source directory).

    Returns:
        Path to the renamed PDF.
    """
    if output_dir is None:
        output_dir = source_pdf.parent

    if not target_name.endswith(".pdf"):
        target_name = target_name + ".pdf"

    target_path = output_dir / target_name

    if source_pdf != target_path:
        logger.debug(f"Renaming PDF: {source_pdf.name} -> {target_name}")
        shutil.move(str(source_pdf), str(target_path))

    return target_path
