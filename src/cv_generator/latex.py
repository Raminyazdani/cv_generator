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
LATEX_ERROR_PATTERNS = [("! LaTeX Error: File `(.+)' not found", 'missing_file', 'Install the missing LaTeX package'), ('! Package inputenc Error: Unicode char', 'unicode', 'Use XeLaTeX or escape special characters'), ('! Undefined control sequence', 'undefined_command', 'Check template for undefined LaTeX commands'), ('! Missing \\$ inserted', 'math_mode', 'Escape $ characters with \\$'), ('! Missing \\{ inserted', 'brace', 'Check for mismatched braces in template'), ('! Emergency stop', 'fatal', 'Critical error - check log file for details'), ('! Font (.+) not found', 'font', 'Install the required font or use a different one'), ('! Package fontspec Error', 'fontspec', 'Check font configuration in template'), ('Runaway argument\\?', 'runaway', 'Check for unclosed braces or environments'), ("! Too many \\}'s", 'extra_brace', 'Check for extra closing braces')]

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
    lines = log_content.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('!'):
            errors.append(line)
            for pattern, error_type, suggestion in LATEX_ERROR_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    suggestions.add(suggestion)
                    break
        if re.match('^\\./.*:\\d+:', line) or re.match('^l\\.\\d+', line):
            errors.append(line)
    return (errors[:10], list(suggestions))

def _read_log_file(log_path: Path) -> str:
    """Read LaTeX log file content."""
    try:
        return log_path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return ''
DEFAULT_LATEX_TIMEOUT = 120

def compile_latex(tex_file: Path, output_dir: Path, *, timeout: Optional[int]=None) -> Optional[Path]:
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
    if timeout is None:
        timeout = DEFAULT_LATEX_TIMEOUT
    if not tex_file.exists():
        raise LatexError(f'LaTeX source file not found: {tex_file}')
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = ['xelatex', '-enable-etex', '-interaction=nonstopmode', '-file-line-error', '-synctex=1', f'-output-directory={output_dir}', str(tex_file)]
    logger.info(f'Compiling LaTeX: {tex_file.name}')
    logger.debug(f"Command: {' '.join(cmd)}")
    log_path = output_dir / (tex_file.stem + '.log')
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=tex_file.parent)
        if result.returncode != 0:
            logger.warning(f'xelatex returned non-zero exit code: {result.returncode}')
            if log_path.exists():
                log_content = _read_log_file(log_path)
                errors, suggestions = parse_latex_log(log_content)
                if errors:
                    logger.warning('LaTeX errors found:')
                    for error in errors[:5]:
                        logger.warning(f'  {error}')
                    if len(errors) > 5:
                        logger.warning(f'  ... and {len(errors) - 5} more errors')
                if suggestions:
                    logger.info('Suggestions:')
                    for suggestion in suggestions:
                        logger.info(f'  - {suggestion}')
                logger.info(f'Full log available at: {log_path}')
            else:
                logger.warning(f'xelatex stderr: {result.stderr}')
        pdf_name = tex_file.stem + '.pdf'
        pdf_path = output_dir / pdf_name
        if pdf_path.exists():
            logger.info(f'PDF generated: {pdf_path}')
            return pdf_path
        else:
            logger.error(f'PDF not generated: {pdf_path}')
            if log_path.exists():
                logger.error(f'Check LaTeX log for details: {log_path}')
            logger.error('Common fixes:')
            logger.error('  1. Check for special characters in your CV data (#, %, _, &, $)')
            logger.error('  2. Verify all LaTeX packages are installed')
            logger.error('  3. Run with --debug to see full LaTeX output')
            return None
    except FileNotFoundError:
        logger.error('xelatex not found. Please install a LaTeX distribution.')
        raise LatexError('xelatex not found. Please install MiKTeX (Windows) or TeX Live (Linux/Mac).')
    except subprocess.TimeoutExpired:
        suggestions = f'xelatex timed out after {timeout} seconds\nSuggestions:\n  1. Try increasing timeout: --latex-timeout {timeout * 2}\n  2. Check for infinite loops or very large documents\n  3. Complex CVs with many images may need more time\n  4. Manual compilation: xelatex {tex_file}'
        logger.error(suggestions)
        return None
    except Exception as e:
        logger.error(f'Error running xelatex: {e}')
        return None

def cleanup_latex_artifacts(output_dir: Path, keep_pdf: bool=True) -> None:
    """
    Clean up LaTeX auxiliary files from the output directory.

    Removes files with extensions: .aux, .log, .out, .synctex.gz, etc.

    Args:
        output_dir: Directory containing LaTeX output files.
        keep_pdf: If True, keep .pdf files. If False, remove everything.
    """
    if not output_dir.exists():
        return
    aux_extensions = {'.aux', '.log', '.out', '.synctex.gz', '.synctex', '.toc', '.lof', '.lot', '.bbl', '.blg', '.fdb_latexmk', '.fls', '.nav', '.snm', '.vrb'}
    for filepath in output_dir.iterdir():
        if filepath.is_file():
            if filepath.suffix in aux_extensions:
                logger.debug(f'Removing LaTeX artifact: {filepath.name}')
                try:
                    filepath.unlink()
                except OSError as e:
                    logger.warning(f'Could not remove {filepath.name}: {e}')
            elif filepath.suffix == '.pdf' and (not keep_pdf):
                logger.debug(f'Removing PDF: {filepath.name}')
                try:
                    filepath.unlink()
                except OSError as e:
                    logger.warning(f'Could not remove {filepath.name}: {e}')

def rename_pdf(source_pdf: Path, target_name: str, output_dir: Optional[Path]=None) -> Path:
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
    if not target_name.endswith('.pdf'):
        target_name = target_name + '.pdf'
    target_path = output_dir / target_name
    if source_pdf != target_path:
        logger.debug(f'Renaming PDF: {source_pdf.name} -> {target_name}')
        shutil.move(str(source_pdf), str(target_path))
    return target_path
