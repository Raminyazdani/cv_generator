"""
Cleanup utilities for CV Generator.

Enhanced Windows-safe directory cleanup with comprehensive diagnostics.

Provides functions for:
- Reliably removing result directories (Windows-friendly)
- Handling file locks and permission issues
- Safe cleanup with backup functionality
- Confirmation prompts for destructive operations

Handles common Windows file locking issues:
- OneDrive sync locks
- Dropbox sync locks
- Antivirus file scanning
- Explorer.exe file handles
- Running applications with open files
"""

import logging
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from .paths import get_repo_root

logger = logging.getLogger(__name__)


class CleanupError(Exception):
    """
    Exception raised when cleanup fails after all retries.

    Provides detailed diagnostics about which files are locked
    and actionable suggestions for resolving the issue.
    """

    def __init__(self, message: str, path: Path, locked_files: Optional[List[str]] = None):
        """
        Initialize the CleanupError.

        Args:
            message: Human-readable error message with diagnostics.
            path: Path that could not be cleaned up.
            locked_files: List of file paths that appear to be locked.
        """
        self.path = path
        self.locked_files = locked_files or []
        super().__init__(message)


def is_windows() -> bool:
    """
    Check if running on Windows.

    Returns:
        True if running on Windows, False otherwise.
    """
    return sys.platform.startswith('win')

# Characters that could enable shell injection if passed to subprocess with shell=True
DANGEROUS_PATH_CHARS = ['&', '|', ';', '$', '`', '<', '>', '(', ')', '\n', '\r']


def validate_path_for_subprocess(path: Path) -> None:
    """
    Validate that a path doesn't contain dangerous characters for subprocess calls.

    This prevents shell injection attacks when passing paths to subprocess.run().

    Args:
        path: Path to validate.

    Raises:
        ValueError: If path contains potentially dangerous characters.
    """
    path_str = str(path)
    for char in DANGEROUS_PATH_CHARS:
        if char in path_str:
            logger.warning(f"Path contains dangerous character '{char}': {path_str}")
            raise ValueError(
                f"Path contains potentially dangerous characters: {path_str}. "
                "Please rename the directory to remove special characters like & | ; $ ` < >"
            )


def _clear_readonly_windows(root: Path) -> None:
    """
    Best-effort: remove "Read-only" attribute recursively (Windows).

    Args:
        root: Root directory to clear read-only attributes from.

    Raises:
        ValueError: If path contains potentially dangerous characters.
    """
    if os.name == "nt":
        try:
            # Validate path before passing to subprocess to prevent injection
            validate_path_for_subprocess(root)

            logger.debug(f"Clearing Windows read-only attributes for {root}")
            subprocess.run(
                ["attrib", "-R", str(root / "*"), "/S", "/D"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,  # Security: Never use shell=True with user-controlled paths
            )
        except ValueError:
            raise  # Re-raise path validation errors
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


def _find_locked_files(path: Path) -> List[str]:
    """
    Attempt to identify which files are locked (Windows).

    Scans through files in the directory and attempts to open each
    for writing to detect which files have locks held by other processes.

    Args:
        path: Directory to check for locked files.

    Returns:
        List of file paths that appear to be locked.
    """
    if not is_windows():
        return []

    locked = []

    try:
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = Path(root) / file
                try:
                    # Try to open for write (detects locks)
                    with open(file_path, 'a'):
                        pass
                except PermissionError:
                    locked.append(str(file_path))
                except Exception:
                    pass  # Other errors don't indicate locks
    except Exception as e:
        logger.debug(f"Error scanning for locked files: {e}")

    return locked


def _get_lock_suggestions(path: Path, locked_files: List[str]) -> List[str]:
    """
    Generate helpful suggestions based on locked files.

    Analyzes the path and locked file list to provide context-specific
    suggestions for resolving file lock issues on Windows.

    Args:
        path: Base directory path.
        locked_files: List of locked file paths.

    Returns:
        List of actionable suggestions for the user.
    """
    suggestions = []

    # Check for common lock sources
    path_str = str(path).lower()

    # OneDrive detection
    if 'onedrive' in path_str or any('onedrive' in f.lower() for f in locked_files):
        suggestions.append(
            "OneDrive detected: Pause OneDrive sync (right-click OneDrive icon → Pause syncing)"
        )

    # Dropbox detection
    if 'dropbox' in path_str or any('dropbox' in f.lower() for f in locked_files):
        suggestions.append(
            "Dropbox detected: Pause Dropbox sync (Dropbox icon → Preferences → Pause syncing)"
        )

    # Common file extensions that get locked
    locked_extensions = set()
    for f in locked_files:
        ext = Path(f).suffix.lower()
        if ext:
            locked_extensions.add(ext)

    if '.pdf' in locked_extensions:
        suggestions.append(
            "PDF files locked: Close PDF readers (Adobe, Chrome, Edge, etc.)"
        )

    if '.tex' in locked_extensions or '.log' in locked_extensions:
        suggestions.append(
            "LaTeX files locked: Close LaTeX editors (TeXstudio, Overleaf Desktop, etc.)"
        )

    if '.db' in locked_extensions or '.sqlite' in locked_extensions:
        suggestions.append(
            "Database files locked: Close database browsers or stop web UI"
        )

    # Generic suggestions
    suggestions.extend([
        "Close Windows Explorer windows showing this directory",
        "Close any applications with open files from this directory",
        "Wait 30 seconds for file handles to release, then retry",
        "Restart your computer if the issue persists",
    ])

    return suggestions


def _onerror_handler(func: Callable, path: str, exc_info: tuple) -> None:
    """
    Error handler for shutil.rmtree that logs detailed information.

    On Windows, attempts to clear read-only attributes and retry
    the operation once before giving up.

    Args:
        func: Function that raised the error.
        path: Path that caused the error.
        exc_info: Exception information tuple (type, value, traceback).
    """
    exc_type, exc_value, exc_traceback = exc_info

    logger.debug(
        f"Error in {func.__name__} for {path}: "
        f"{exc_type.__name__}: {exc_value}"
    )

    # On Windows, try to clear read-only and retry once
    if is_windows() and isinstance(exc_value, PermissionError):
        try:
            os.chmod(path, 0o777)
            func(path)
            logger.debug(f"Successfully deleted {path} after chmod")
        except Exception as e:
            logger.debug(f"Retry failed for {path}: {e}")


def remove_directory(
    path: Path,
    *,
    max_attempts: int = 30,
    initial_delay: float = 0.1,
    max_delay: float = 5.0,
    show_progress: bool = False,
) -> bool:
    """
    Remove directory with robust Windows file lock handling.

    Uses exponential backoff retry logic to handle transient file locks
    from OneDrive, Dropbox, antivirus software, and other applications.

    Args:
        path: Directory to remove.
        max_attempts: Maximum retry attempts (default: 30, ~2 minutes total).
        initial_delay: Initial retry delay in seconds (default: 0.1).
        max_delay: Maximum retry delay in seconds (default: 5.0).
        show_progress: Show progress messages to user.

    Returns:
        True if successful, False if failed.

    Raises:
        CleanupError: If cleanup fails after all retries (with diagnostics).
    """
    if not path.exists():
        logger.debug(f"Path does not exist, nothing to remove: {path}")
        return True

    logger.info(f"Removing directory: {path}")

    # On Windows, clear read-only attributes first
    if is_windows():
        logger.debug("Clearing read-only attributes (Windows)")
        try:
            _clear_readonly_windows(path)
        except ValueError:
            pass  # Path validation error - continue anyway

    # Retry loop with exponential backoff
    for attempt in range(1, max_attempts + 1):
        try:
            logger.debug(f"Cleanup attempt {attempt}/{max_attempts}")

            shutil.rmtree(path, onerror=_onerror_handler)

            # Verify removal
            if not path.exists():
                logger.info(f"Successfully removed: {path}")
                return True
            else:
                logger.warning(f"Path still exists after rmtree: {path}")
                # Continue to next attempt

        except PermissionError:
            if show_progress and attempt % 5 == 0:
                logger.info(
                    f"Waiting for file locks to release... (attempt {attempt}/{max_attempts})"
                )

            if attempt < max_attempts:
                # Exponential backoff with cap
                delay = min(max_delay, initial_delay * (1.5 ** attempt))
                logger.debug(f"Waiting {delay:.2f}s before retry")
                time.sleep(delay)

        except Exception as e:
            logger.error(f"Unexpected error during cleanup: {e}")
            break

    # All retries failed - provide diagnostics
    logger.error(f"Failed to remove directory after {max_attempts} attempts: {path}")

    # Find locked files
    locked_files = _find_locked_files(path) if is_windows() else []

    if locked_files:
        logger.error(f"Found {len(locked_files)} locked file(s):")
        for i, locked_file in enumerate(locked_files[:10], 1):  # Show max 10
            logger.error(f"  {i}. {locked_file}")
        if len(locked_files) > 10:
            logger.error(f"  ... and {len(locked_files) - 10} more")

    # Generate suggestions
    suggestions = _get_lock_suggestions(path, locked_files)

    logger.error("Suggestions to resolve:")
    for i, suggestion in enumerate(suggestions, 1):
        logger.error(f"  {i}. {suggestion}")

    # Calculate approximate total time
    total_time = sum(min(max_delay, initial_delay * (1.5 ** i)) for i in range(max_attempts))

    # Build detailed error message
    error_message = (
        f"Cannot remove directory (file locks): {path}\n"
        f"Attempted {max_attempts} times over ~{total_time:.0f} seconds.\n"
    )

    if locked_files:
        error_message += f"\nLocked files ({len(locked_files)}):\n"
        for locked_file in locked_files[:5]:
            error_message += f"  • {locked_file}\n"
        if len(locked_files) > 5:
            error_message += f"  ... and {len(locked_files) - 5} more\n"

    error_message += "\nPlease:\n"
    for suggestion in suggestions[:3]:
        error_message += f"  • {suggestion}\n"

    raise CleanupError(error_message, path, locked_files)


def remove_directory_interactive(path: Path, force: bool = False) -> bool:
    """
    Remove directory with user interaction on failure.

    Provides an interactive retry flow for when automatic cleanup fails.
    Allows users to close applications and retry, or skip/abort.

    Args:
        path: Directory to remove.
        force: If True, skip confirmation prompts.

    Returns:
        True if successful, False if user cancelled or failed.

    Raises:
        KeyboardInterrupt: If user chooses to abort the operation.
    """
    try:
        return remove_directory(path, show_progress=True)

    except CleanupError as e:
        logger.error(str(e))

        if force:
            logger.error("Cleanup failed even with --force")
            return False

        # Ask user if they want to retry
        if sys.stdin.isatty():
            print("\n" + "=" * 60)
            print("Cleanup Failed")
            print("=" * 60)
            print(str(e))
            print("\nOptions:")
            print("  1. Retry now (after closing applications)")
            print("  2. Skip cleanup (leave directory)")
            print("  3. Abort operation")

            while True:
                try:
                    choice = input("\nChoose [1/2/3]: ").strip()
                except (EOFError, KeyboardInterrupt):
                    choice = '3'

                if choice == '1':
                    print("\nRetrying cleanup...")
                    try:
                        return remove_directory(path, show_progress=True)
                    except CleanupError:
                        print("Retry failed. Skipping cleanup.")
                        return False

                elif choice == '2':
                    logger.warning(f"Skipping cleanup of {path}")
                    return False

                elif choice == '3':
                    logger.error("Operation aborted by user")
                    raise KeyboardInterrupt("User aborted due to cleanup failure")

                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
        else:
            # Non-interactive mode
            logger.error("Cannot prompt user in non-interactive mode")
            return False


def rmtree_reliable(path: str | os.PathLike, *, attempts: int = 30) -> None:
    """
    Reliably remove a directory tree, handling Windows-specific issues.

    This function handles:
    - Read-only file attributes (Windows)
    - File locks from OneDrive, antivirus, etc.
    - Permission errors with exponential backoff retry

    Args:
        path: Path to the directory to remove.
        attempts: Maximum number of attempts before giving up.

    Raises:
        CleanupError: If cleanup fails after all retries (with diagnostics).
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
            # Exponential backoff with cap
            delay = min(2.0, 0.05 * (2 ** i))
            time.sleep(delay)
        except OSError:
            delay = min(2.0, 0.05 * (2 ** i))
            time.sleep(delay)

    # Final attempt with better error handling
    try:
        _clear_readonly_windows(p)
        shutil.rmtree(p, onerror=onerror)
    except (PermissionError, OSError) as e:
        # Provide diagnostics on final failure
        locked_files = _find_locked_files(p) if is_windows() else []
        suggestions = _get_lock_suggestions(p, locked_files)

        error_message = (
            f"Cannot remove directory after {attempts} attempts: {p}\n"
        )

        if locked_files:
            error_message += f"\nLocked files ({len(locked_files)}):\n"
            for locked_file in locked_files[:5]:
                error_message += f"  • {locked_file}\n"
            if len(locked_files) > 5:
                error_message += f"  ... and {len(locked_files) - 5} more\n"

        error_message += "\nPlease:\n"
        for suggestion in suggestions[:3]:
            error_message += f"  • {suggestion}\n"

        raise CleanupError(error_message, p, locked_files) from e


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
    except CleanupError as e:
        if verbose:
            print(f"❌ Error deleting {path}: {e}")
        # Return False but don't re-raise - allow caller to continue
        return False
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
        ValueError: If destination is under data/ directory or archive contains
                   path traversal attempts.
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
            logger.info(f"Restoring backup from {archive_path}")
            logger.debug(f"Validating {len(tar.getmembers())} archive members")

            # Security: Use safe extraction with path traversal protection
            _safe_extract_tar(tar, destination.parent)

        if verbose:
            print(f"✅ Restored: {archive_path} -> {destination}")
        return True
    except ValueError:
        # Re-raise path traversal errors for proper handling
        raise
    except Exception as e:
        if verbose:
            print(f"❌ Error restoring backup: {e}")
        return False


def _safe_extract_tar(tar: tarfile.TarFile, destination: Path) -> None:
    """
    Safely extract a tar archive with path traversal protection.

    For Python 3.12+, uses the built-in 'data' filter.
    For older versions, performs manual validation of all member paths.

    Args:
        tar: Open TarFile object.
        destination: Destination directory for extraction.

    Raises:
        ValueError: If any member path attempts path traversal.
    """
    # Python 3.12+ has the filter parameter for safe extraction
    if sys.version_info >= (3, 12):
        logger.debug("Using Python 3.12+ tar filter='data' for safe extraction")
        try:
            tar.extractall(destination, filter='data')
        except tarfile.OutsideDestinationError as e:
            # Convert to ValueError for consistent error handling
            logger.warning(f"Path traversal blocked: {e}")
            raise ValueError(f"Path traversal detected: {e}") from e
        except tarfile.FilterError as e:
            # Catch other filter errors (e.g., AbsolutePathError, LinkOutsideDestinationError)
            logger.warning(f"Unsafe archive content blocked: {e}")
            raise ValueError(f"Unsafe path in archive: {e}") from e
    else:
        # Manual validation for Python < 3.12
        logger.debug("Using manual path validation for safe extraction")
        for member in tar.getmembers():
            _validate_tar_member_path(member.name)
            tar.extract(member, destination)


def _validate_tar_member_path(member_name: str) -> None:
    """
    Validate that a tar member path is safe (no path traversal).

    Args:
        member_name: The member name/path from the tar archive.

    Raises:
        ValueError: If the path attempts path traversal.
    """
    # Normalize the path first to handle all cases consistently
    safe_path = os.path.normpath(member_name)

    # Reject absolute paths (cross-platform check)
    if os.path.isabs(safe_path):
        logger.warning(f"Unsafe absolute path in archive: {member_name}")
        raise ValueError(f"Unsafe path in archive: {member_name}")

    # Reject paths that try to escape the destination (after normalization)
    if safe_path.startswith('..'):
        logger.warning(f"Path traversal detected: {member_name}")
        raise ValueError(f"Path traversal detected: {member_name}")
