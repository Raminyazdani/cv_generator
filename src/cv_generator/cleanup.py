"""
Cleanup utilities for CV Generator.

Provides functions for:
- Reliably removing result directories (Windows-friendly)
- Handling file locks and permission issues
- Safe cleanup with backup functionality
- Confirmation prompts for destructive operations
"""

import logging
import os
import shutil
import stat
import subprocess
import tarfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .paths import get_repo_root

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


def get_backups_dir(output_root: Optional[Path] = None) -> Path:
    """
    Get the directory for storing backups.
    
    Args:
        output_root: Root output directory. Defaults to repo_root/output.
        
    Returns:
        Path to the backups directory.
    """
    if output_root is None:
        from .paths import get_default_output_path
        output_root = get_default_output_path()
    
    return output_root / "backups"


def is_data_path(path: Path) -> bool:
    """
    Check if a path is under the data/ directory.
    
    This is a safety check to prevent accidental deletion of source data.
    
    Args:
        path: Path to check.
        
    Returns:
        True if path is under data/, False otherwise.
    """
    try:
        repo_root = get_repo_root()
        data_dir = repo_root / "data"
        resolved_path = path.resolve()
        resolved_data = data_dir.resolve()
        return resolved_data in resolved_path.parents or resolved_path == resolved_data
    except Exception:
        # If we can't determine, be conservative
        return "data" in str(path)


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Prompt user for confirmation.
    
    Args:
        message: Message to display.
        default: Default response if user presses Enter.
        
    Returns:
        True if user confirms, False otherwise.
    """
    suffix = " [y/N] " if not default else " [Y/n] "
    try:
        response = input(message + suffix).strip().lower()
        if not response:
            return default
        return response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def create_backup(
    source_path: Path,
    output_root: Optional[Path] = None,
    timestamp: Optional[datetime] = None,
) -> Optional[Path]:
    """
    Create a timestamped backup archive of a directory.
    
    Args:
        source_path: Path to the directory to backup.
        output_root: Root output directory for storing backup.
        timestamp: Optional timestamp for naming. Defaults to current time.
        
    Returns:
        Path to the created archive, or None if backup failed.
        
    Raises:
        ValueError: If source path is under data/ directory.
    """
    if is_data_path(source_path):
        raise ValueError(
            f"Cannot backup from data/ directory: {source_path}. "
            "Backups should only be created from output/ directories."
        )
    
    if not source_path.exists():
        return None
    
    backups_dir = get_backups_dir(output_root)
    backups_dir.mkdir(parents=True, exist_ok=True)
    
    if timestamp is None:
        timestamp = datetime.now()
    
    date_str = timestamp.strftime("%Y%m%d_%H%M%S")
    source_name = source_path.name
    archive_name = f"{source_name}_{date_str}.tar.gz"
    archive_path = backups_dir / archive_name
    
    try:
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(source_path, arcname=source_name)
        logger.info(f"Created backup: {archive_path}")
        return archive_path
    except Exception as e:
        logger.error(f"Backup creation failed: {e}")
        # Cleanup partial archive if creation failed
        if archive_path.exists():
            archive_path.unlink()
        return None


def safe_cleanup(
    path: Path,
    backup: bool = True,
    yes: bool = False,
    output_root: Optional[Path] = None,
    verbose: bool = False,
) -> bool:
    """
    Safely clean up (remove) a directory with optional backup.
    
    Args:
        path: Path to the directory to clean up.
        backup: Whether to create a backup before deletion.
        yes: If True, skip confirmation prompt.
        output_root: Root output directory for storing backup.
        verbose: If True, print status messages.
        
    Returns:
        True if cleanup was successful, False if cancelled or failed.
        
    Raises:
        ValueError: If attempting to delete from data/ directory.
    """
    if is_data_path(path):
        raise ValueError(
            f"Cannot delete from data/ directory: {path}. "
            "This operation is blocked for safety."
        )
    
    if not path.exists():
        if verbose:
            print(f"Path does not exist: {path}")
        return True
    
    # Calculate size for user info
    total_size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    file_count = sum(1 for f in path.rglob("*") if f.is_file())
    size_mb = total_size / (1024 * 1024)
    
    if not yes:
        msg = f"Delete {path} ({file_count} files, {size_mb:.2f} MB)?"
        if backup:
            msg += " (backup will be created)"
        if not confirm_action(msg):
            if verbose:
                print("Cleanup cancelled.")
            return False
    
    # Create backup if requested
    backup_path = None
    if backup:
        backup_path = create_backup(path, output_root)
        if backup_path and verbose:
            print(f"📦 Backup created: {backup_path}")
        elif not backup_path and verbose:
            print("⚠️ Warning: Backup creation failed, proceeding anyway...")
    
    # Perform deletion
    try:
        rmtree_reliable(path)
        if verbose:
            print(f"🗑️ Deleted: {path}")
        return True
    except Exception as e:
        if verbose:
            print(f"❌ Error deleting {path}: {e}")
        return False


def clean_output_directory(
    output_types: Optional[List[str]] = None,
    output_root: Optional[Path] = None,
    backup: bool = True,
    yes: bool = False,
    verbose: bool = False,
) -> dict:
    """
    Clean up output directories.
    
    Args:
        output_types: List of output types to clean ('pdf', 'latex', 'html', 'md').
                     If None, cleans all.
        output_root: Root output directory.
        backup: Whether to create backups before deletion.
        yes: If True, skip confirmation prompts.
        verbose: If True, print status messages.
        
    Returns:
        Dictionary with cleanup results.
    """
    if output_root is None:
        from .paths import get_default_output_path
        output_root = get_default_output_path()
    
    if output_types is None:
        output_types = ["pdf", "latex", "html", "md"]
    
    results = {
        "cleaned": [],
        "failed": [],
        "skipped": [],
        "backups": [],
    }
    
    for output_type in output_types:
        type_dir = output_root / output_type
        if not type_dir.exists():
            results["skipped"].append(str(type_dir))
            continue
        
        try:
            backup_path = None
            if backup:
                backup_path = create_backup(type_dir, output_root)
                if backup_path:
                    results["backups"].append(str(backup_path))
            
            if safe_cleanup(type_dir, backup=False, yes=yes, verbose=verbose):
                results["cleaned"].append(str(type_dir))
            else:
                results["skipped"].append(str(type_dir))
        except Exception as e:
            results["failed"].append({"path": str(type_dir), "error": str(e)})
    
    return results


def list_backups(output_root: Optional[Path] = None) -> List[Path]:
    """
    List all backup archives.
    
    Args:
        output_root: Root output directory.
        
    Returns:
        List of paths to backup archives, sorted by date (newest first).
    """
    backups_dir = get_backups_dir(output_root)
    if not backups_dir.exists():
        return []
    
    backups = list(backups_dir.glob("*.tar.gz"))
    return sorted(backups, reverse=True)


def restore_backup(
    archive_path: Path,
    destination: Path,
    overwrite: bool = False,
    yes: bool = False,
    verbose: bool = False,
) -> bool:
    """
    Restore a backup archive to a destination.
    
    Args:
        archive_path: Path to the backup archive.
        destination: Destination directory.
        overwrite: Whether to overwrite existing destination.
        yes: If True, skip confirmation prompt.
        verbose: If True, print status messages.
        
    Returns:
        True if restoration was successful, False otherwise.
        
    Raises:
        ValueError: If destination is under data/ directory.
    """
    if is_data_path(destination):
        raise ValueError(
            f"Cannot restore to data/ directory: {destination}. "
            "This operation is blocked for safety."
        )
    
    if not archive_path.exists():
        if verbose:
            print(f"❌ Archive not found: {archive_path}")
        return False
    
    if destination.exists() and not overwrite:
        if not yes:
            if not confirm_action(f"Overwrite {destination}?"):
                if verbose:
                    print("Restore cancelled.")
                return False
        
        rmtree_reliable(destination)
    
    try:
        destination.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(destination.parent)
        if verbose:
            print(f"✅ Restored: {archive_path} -> {destination}")
        return True
    except Exception as e:
        if verbose:
            print(f"❌ Error restoring backup: {e}")
        return False
