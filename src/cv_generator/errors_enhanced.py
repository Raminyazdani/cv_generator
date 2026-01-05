"""
Enhanced exception system with rich context for diagnostics.

All cv_generator exceptions should provide:
1. Clear error message (what went wrong)
2. Context (where it happened, relevant values)
3. Suggestions (how to fix it)
4. Error code (for documentation lookup)

This module extends the base errors.py module with enhanced context
for better diagnostics and user experience.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CVGeneratorError(Exception):
    """
    Base exception for cv_generator with enhanced context.

    All cv_generator exceptions should inherit from this.
    """

    exit_code = 1
    error_code = "CVGEN_ERROR"

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize enhanced exception.

        Args:
            message: Primary error message
            context: Additional context (file paths, values, etc.)
            suggestions: List of actionable suggestions for user
            cause: Original exception if this is a wrapper
        """
        self.message = message
        self.context = context or {}
        self.suggestions = suggestions or []
        self.cause = cause

        # Build full error message
        full_message = self._build_full_message()
        super().__init__(full_message)

        # Log the error (full_message already includes error code)
        logger.error(full_message)

    def _build_full_message(self) -> str:
        """Build comprehensive error message with all context."""
        parts = [f"[{self.error_code}] {self.message}"]

        # Add context
        if self.context:
            parts.append("\nContext:")
            for key, value in self.context.items():
                parts.append(f"  {key}: {value}")

        # Add suggestions
        if self.suggestions:
            parts.append("\nSuggestions:")
            for i, suggestion in enumerate(self.suggestions, 1):
                parts.append(f"  {i}. {suggestion}")

        # Add cause if present
        if self.cause:
            parts.append(f"\nCaused by: {type(self.cause).__name__}: {self.cause}")

        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/reporting."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "suggestions": self.suggestions,
            "cause": str(self.cause) if self.cause else None,
            "exit_code": self.exit_code,
        }


class ConfigurationError(CVGeneratorError):
    """Configuration or path-related errors with context."""

    exit_code = 2
    error_code = "CVGEN_CONFIG"

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        file_path: Optional[str] = None,
        expected: Optional[Any] = None,
        actual: Optional[Any] = None,
        **kwargs,
    ):
        """
        Initialize configuration error with specific context.

        Args:
            message: Error message
            config_key: Configuration key that failed
            file_path: Config file path
            expected: Expected value/type
            actual: Actual value/type
            **kwargs: Additional context, suggestions, cause
        """
        context = kwargs.pop("context", {})
        if config_key:
            context["config_key"] = config_key
        if file_path:
            context["file_path"] = file_path
        if expected is not None:
            context["expected"] = expected
        if actual is not None:
            context["actual"] = actual

        super().__init__(message, context=context, **kwargs)


class TemplateError(CVGeneratorError):
    """Template rendering errors with diagnostic information."""

    exit_code = 3
    error_code = "CVGEN_TEMPLATE"

    def __init__(
        self,
        message: str,
        template_name: Optional[str] = None,
        template_line: Optional[int] = None,
        cv_file: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize template error.

        Args:
            message: Error message
            template_name: Name of the template that failed
            template_line: Line number in the template
            cv_file: CV file being processed
            **kwargs: Additional context, suggestions, cause
        """
        context = kwargs.pop("context", {})
        if template_name:
            context["template_name"] = template_name
        if template_line:
            context["template_line"] = template_line
        if cv_file:
            context["cv_file"] = cv_file

        suggestions = kwargs.pop("suggestions", [])
        if not suggestions:
            suggestions.extend(
                [
                    "Check that all required fields exist in your CV JSON",
                    "Verify template syntax is correct",
                    "Run with --debug for detailed template errors",
                ]
            )

        super().__init__(message, context=context, suggestions=suggestions, **kwargs)


class LaTeXCompilationError(CVGeneratorError):
    """LaTeX compilation failed with diagnostic information."""

    exit_code = 4
    error_code = "CVGEN_LATEX"

    def __init__(
        self,
        message: str,
        tex_file: Optional[str] = None,
        log_file: Optional[str] = None,
        latex_errors: Optional[List[str]] = None,
        **kwargs,
    ):
        """
        Initialize LaTeX compilation error.

        Args:
            message: Error message
            tex_file: Path to .tex file that failed
            log_file: Path to .log file with details
            latex_errors: Parsed LaTeX error messages
            **kwargs: Additional context, suggestions, cause
        """
        context = kwargs.pop("context", {})
        if tex_file:
            context["tex_file"] = tex_file
        if log_file:
            context["log_file"] = log_file
        if latex_errors:
            context["latex_errors"] = latex_errors

        suggestions = kwargs.pop("suggestions", [])
        if log_file:
            suggestions.append(f"Check LaTeX log file: {log_file}")
        if not suggestions:
            suggestions.extend(
                [
                    "Check for special characters in your CV data (escape #, %, _, &, $)",
                    "Verify all LaTeX packages are installed",
                    "Run with --debug to see full LaTeX output",
                ]
            )

        super().__init__(message, context=context, suggestions=suggestions, **kwargs)


class PluginError(CVGeneratorError):
    """Plugin execution failed."""

    exit_code = 5
    error_code = "CVGEN_PLUGIN"

    def __init__(
        self,
        message: str,
        plugin_name: Optional[str] = None,
        hook_name: Optional[str] = None,
        abort_on_error: bool = False,
        **kwargs,
    ):
        """
        Initialize plugin error.

        Args:
            message: Error message
            plugin_name: Name of plugin that failed
            hook_name: Hook that was being executed
            abort_on_error: Whether this should abort the build
            **kwargs: Additional context, suggestions, cause
        """
        self.abort_on_error = abort_on_error

        context = kwargs.pop("context", {})
        if plugin_name:
            context["plugin_name"] = plugin_name
        if hook_name:
            context["hook_name"] = hook_name
        context["abort_on_error"] = abort_on_error

        suggestions = kwargs.pop("suggestions", [])
        if not suggestions:
            if plugin_name:
                suggestions.append(f"Check plugin '{plugin_name}' implementation")
            suggestions.extend(
                [
                    "Try disabling the plugin to isolate the issue",
                    "Check plugin logs with --debug",
                ]
            )

        super().__init__(message, context=context, suggestions=suggestions, **kwargs)


class ValidationError(CVGeneratorError):
    """CV data validation failed."""

    exit_code = 6
    error_code = "CVGEN_VALIDATION"

    def __init__(
        self,
        message: str,
        cv_file: Optional[str] = None,
        field_path: Optional[str] = None,
        validation_errors: Optional[List[str]] = None,
        **kwargs,
    ):
        """
        Initialize validation error.

        Args:
            message: Error message
            cv_file: CV JSON file that failed validation
            field_path: JSONPath to failing field
            validation_errors: List of validation error messages
            **kwargs: Additional context, suggestions, cause
        """
        context = kwargs.pop("context", {})
        if cv_file:
            context["cv_file"] = cv_file
        if field_path:
            context["field_path"] = field_path
        if validation_errors:
            context["validation_errors"] = validation_errors

        suggestions = kwargs.pop("suggestions", [])
        if not suggestions:
            suggestions.extend(
                [
                    "Check JSON schema: docs/json-schema.md",
                    "Run: cvgen lint --file <your-cv.json>",
                    "Verify all required fields are present",
                ]
            )

        super().__init__(message, context=context, suggestions=suggestions, **kwargs)


def get_latex_error_suggestion(error_msg: str) -> Optional[str]:
    """
    Get a suggestion for a LaTeX error message.

    This function is imported from latex.py for consistency.
    Use this for standalone error message suggestions.

    Args:
        error_msg: The LaTeX error message

    Returns:
        Suggestion string or None
    """
    # Import here to avoid circular imports
    import re

    from .latex import LATEX_ERROR_PATTERNS

    for pattern, error_type, suggestion in LATEX_ERROR_PATTERNS:
        if re.search(pattern, error_msg, re.IGNORECASE):
            return suggestion

    return None
