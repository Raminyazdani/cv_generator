"""
Cleanup utilities for CV Generator.

Provides functions for:
- Reliably removing result directories (Windows-friendly)
- Handling file locks and permission issues
"""

import logging
import os
import shutil
import stat
import subprocess
import time
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def _clear_readonly_windows(root: Path) -> None:
    """
    Best-effort: remove "Read-only" attribute recursively (Windows).
    
    Args:
        root: Root directory to clear read-only attributes from.
    """
    if os.name == "nt":
        try:
            subprocess.run(
                ["attrib", "-R", str(root / "*"), "/S", "/D"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=True,
            )
        except Exception:
            pass


def _make_writable(path: str) -> None:
    """
    Make a file writable by changing its permissions.
    
    Args:
        path: Path to the file to make writable.
    """
    try:
        os.chmod(path, stat.S_IWRITE)
    except Exception:
        pass


def rmtree_reliable(path: str | os.PathLike, *, attempts: int = 25) -> None:
    """
    Reliably remove a directory tree, handling Windows-specific issues.
    
    This function handles:
    - Read-only file attributes (Windows)
    - File locks from OneDrive, antivirus, etc.
    - Permission errors with exponential backoff retry
    
    Args:
        path: Path to the directory to remove.
        attempts: Maximum number of attempts before giving up.
    """
    p = Path(path)

    if not p.exists():
        return

    p = p.resolve()
    
    logger.debug(f"Removing directory: {p}")

    # Rename first to avoid conflicts
    try:
        renamed = p.with_name(f"{p.name}.__deleting__{uuid.uuid4().hex}")
        p.rename(renamed)
        p = renamed
    except Exception:
        pass

    def onerror(func, failed_path, exc_info):
        _make_writable(failed_path)
        try:
            func(failed_path)
        except Exception:
            raise

    for i in range(attempts):
        try:
            _clear_readonly_windows(p)
            shutil.rmtree(p, onerror=onerror)
            logger.debug(f"Successfully removed directory: {p}")
            return
        except FileNotFoundError:
            return
        except PermissionError:
            time.sleep(min(2.0, 0.05 * (2 ** i)))
        except OSError:
            time.sleep(min(2.0, 0.05 * (2 ** i)))

    # Final attempt
    _clear_readonly_windows(p)
    shutil.rmtree(p, onerror=onerror)


def cleanup_result_dir(result_dir: Path) -> None:
    """
    Clean up the result directory after CV generation.
    
    Args:
        result_dir: Path to the result directory.
    """
    if result_dir.exists():
        logger.info(f"Cleaning up result directory: {result_dir}")
        rmtree_reliable(result_dir)
