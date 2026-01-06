"""
Custom error types and exit codes for CV Generator.
"""

import logging
import sys
from typing import NoReturn

logger = logging.getLogger(__name__)


class CVGeneratorError(Exception):
    """Base exception for CV Generator errors."""

    exit_code = 1

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ConfigurationError(CVGeneratorError):
    """Configuration or path-related errors."""

    exit_code = 2


class TemplateError(CVGeneratorError):
    """Template rendering errors."""

    exit_code = 3


class LatexError(CVGeneratorError):
    """LaTeX compilation errors."""

    exit_code = 4


class ValidationError(CVGeneratorError):
    """CV validation errors."""

    exit_code = 5


# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_CONFIG_ERROR = 2
EXIT_TEMPLATE_ERROR = 3
EXIT_LATEX_ERROR = 4
EXIT_VALIDATION_ERROR = 5


def fatal_error(message: str, exit_code: int = EXIT_ERROR) -> NoReturn:
    """Log an error message and exit with the given code."""
    logger.error(message)
    sys.exit(exit_code)
