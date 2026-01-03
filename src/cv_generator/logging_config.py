"""
Logging configuration for CV Generator.

Provides centralized logging setup with support for:
- CLI verbosity flags (--quiet, --verbose, --debug)
- Console and optional file logging
- Human-friendly log formatting
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Default log format for different verbosity levels
DEFAULT_FORMAT = "%(message)s"
VERBOSE_FORMAT = "%(message)s"
DEBUG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def configure_logging(
    level: int = logging.WARNING,
    log_file: Optional[Path] = None,
    format_str: Optional[str] = None,
) -> None:
    """
    Configure logging for the CV Generator application.

    This function should be called once early in the CLI entrypoint.
    Subsequent calls will reconfigure the root logger.

    Args:
        level: The logging level (e.g., logging.DEBUG, logging.INFO).
        log_file: Optional path to a log file. Directory will be created if missing.
        format_str: Optional custom format string. If None, uses level-appropriate default.
    """
    # Determine format string based on level if not provided
    if format_str is None:
        if level <= logging.DEBUG:
            format_str = DEBUG_FORMAT
        else:
            format_str = DEFAULT_FORMAT

    # Configure root logger
    root_logger = logging.getLogger()

    # Clear existing handlers to allow reconfiguration
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(format_str))
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file is not None:
        try:
            # Create parent directories if they don't exist
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(DEBUG_FORMAT))
            root_logger.addHandler(file_handler)
        except (OSError, IOError) as e:
            # Log a warning when file logging fails (visible in debug mode)
            # This helps with troubleshooting while not breaking builds on read-only filesystems
            logging.getLogger(__name__).debug(
                f"Could not set up file logging to {log_file}: {e}"
            )

    # Configure the cv_generator package logger
    cv_logger = logging.getLogger("cv_generator")
    cv_logger.setLevel(level)


def get_log_level_from_flags(
    quiet: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """
    Determine the appropriate log level from CLI flags.

    Flag precedence (highest to lowest):
    1. --debug: DEBUG level (most verbose)
    2. --quiet: ERROR level only (least verbose, overrides --verbose)
    3. --verbose: INFO level
    4. default: WARNING level

    Args:
        quiet: If True, only show errors.
        verbose: If True, show info messages.
        debug: If True, show debug messages (overrides all).

    Returns:
        The appropriate logging level constant.
    """
    if debug:
        return logging.DEBUG
    if quiet:
        return logging.ERROR
    if verbose:
        return logging.INFO
    return logging.WARNING


def setup_logging(
    verbose: bool = False,
    debug: bool = False,
    quiet: bool = False,
    log_file: Optional[Path] = None,
) -> None:
    """
    Configure logging based on CLI verbosity flags.

    This is the primary entry point for CLI logging configuration.
    It wraps configure_logging with flag-to-level conversion.

    Args:
        verbose: Enable INFO level logging.
        debug: Enable DEBUG level logging (overrides verbose and quiet).
        quiet: Enable ERROR level only (overrides verbose, overridden by debug).
        log_file: Optional path to a log file.
    """
    level = get_log_level_from_flags(quiet=quiet, verbose=verbose, debug=debug)
    configure_logging(level=level, log_file=log_file)
