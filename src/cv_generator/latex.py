"""
LaTeX compilation utilities for CV Generator.

Provides functions for:
- Running xelatex to compile .tex files to PDF
- Handling compilation output and errors
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .errors import LatexError

logger = logging.getLogger(__name__)


def compile_latex(
    tex_file: Path,
    output_dir: Path,
    *,
    timeout: int = 120
) -> Optional[Path]:
    """
    Compile a LaTeX file to PDF using xelatex.
    
    Args:
        tex_file: Path to the .tex file to compile.
        output_dir: Directory for output files.
        timeout: Maximum time in seconds to wait for compilation.
        
    Returns:
        Path to the generated PDF, or None if compilation fails.
        
    Raises:
        LatexError: If xelatex is not found.
    """
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
            logger.debug(f"xelatex stderr: {result.stderr}")
            # Still check if PDF was generated - xelatex often returns non-zero
            # even when a (partial) PDF is created
        
        # Look for the generated PDF
        pdf_name = tex_file.stem + ".pdf"
        pdf_path = output_dir / pdf_name
        
        if pdf_path.exists():
            logger.info(f"PDF generated: {pdf_path}")
            return pdf_path
        else:
            logger.error(f"PDF not generated: {pdf_path}")
            return None
            
    except FileNotFoundError:
        logger.error("xelatex not found. Please install a LaTeX distribution.")
        raise LatexError(
            "xelatex not found. Please install MiKTeX (Windows) or TeX Live (Linux/Mac)."
        )
    except subprocess.TimeoutExpired:
        logger.error(f"xelatex timed out after {timeout} seconds")
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
