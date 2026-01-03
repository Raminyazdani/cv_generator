"""
Schema validation for CV JSON files.

Provides JSON Schema validation with clear error reporting.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from jsonschema import Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    Draft7Validator = None  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""

    path: str
    message: str
    severity: str = "error"  # "error" or "warning"

    def __str__(self) -> str:
        severity_icon = "❌" if self.severity == "error" else "⚠️"
        return f"{severity_icon} {self.path}: {self.message}"


@dataclass
class ValidationReport:
    """Result of validating a CV JSON file."""

    file_path: Optional[Path] = None
    is_valid: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add an issue to the report."""
        self.issues.append(issue)
        if issue.severity == "error":
            self.error_count += 1
            self.is_valid = False
        else:
            self.warning_count += 1

    def format_text(self) -> str:
        """Format the report as human-readable text."""
        lines = []
        if self.file_path:
            lines.append(f"Validation report for: {self.file_path}")
        lines.append("")

        if self.is_valid and not self.issues:
            lines.append("✅ No issues found")
        else:
            status = "❌ INVALID" if not self.is_valid else "⚠️ WARNINGS"
            lines.append(f"Status: {status}")
            lines.append(f"Errors: {self.error_count}, Warnings: {self.warning_count}")
            lines.append("")
            for issue in self.issues:
                lines.append(f"  {issue}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "file": str(self.file_path) if self.file_path else None,
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [
                {"path": i.path, "message": i.message, "severity": i.severity}
                for i in self.issues
            ],
        }


def get_schema_path() -> Path:
    """Get the path to the CV JSON schema file."""
    return Path(__file__).parent / "schemas" / "cv.schema.json"


def load_schema() -> Dict[str, Any]:
    """
    Load the CV JSON schema.

    Returns:
        The schema as a dictionary.

    Raises:
        FileNotFoundError: If the schema file is not found.
        json.JSONDecodeError: If the schema is invalid JSON.
    """
    schema_path = get_schema_path()
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


def _format_json_path(path: List[Any]) -> str:
    """
    Format a JSON path for human-readable display.

    Args:
        path: List of path components (strings and integers).

    Returns:
        JSONPath-like string (e.g., "$.basics[0].fname").
    """
    if not path:
        return "$"

    parts = ["$"]
    for component in path:
        if isinstance(component, int):
            parts.append(f"[{component}]")
        else:
            parts.append(f".{component}")
    return "".join(parts)


def validate_cv_json(
    data: Dict[str, Any],
    strict: bool = False,
    file_path: Optional[Path] = None,
) -> ValidationReport:
    """
    Validate CV JSON data against the schema.

    Args:
        data: The CV data dictionary to validate.
        strict: If True, treat all issues as errors. If False, some issues
                are treated as warnings.
        file_path: Optional path to the source file (for reporting).

    Returns:
        ValidationReport containing all issues found.
    """
    if not JSONSCHEMA_AVAILABLE:
        report = ValidationReport(file_path=file_path)
        report.add_issue(ValidationIssue(
            path="$",
            message="jsonschema package not installed. Run: pip install jsonschema",
            severity="error"
        ))
        return report

    report = ValidationReport(file_path=file_path)

    try:
        schema = load_schema()
    except FileNotFoundError as e:
        report.add_issue(ValidationIssue(
            path="$",
            message=f"Schema loading error: {e}",
            severity="error"
        ))
        return report
    except json.JSONDecodeError as e:
        report.add_issue(ValidationIssue(
            path="$",
            message=f"Invalid schema JSON: {e}",
            severity="error"
        ))
        return report

    validator = Draft7Validator(schema)

    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = _format_json_path(list(error.absolute_path))
        message = error.message

        # Determine severity based on error type and strict mode
        if strict:
            severity = "error"
        else:
            # In non-strict mode, only required and type errors are critical
            # Other issues (e.g., format, additional properties) are warnings
            if error.validator in ("required", "type"):
                severity = "error"
            else:
                severity = "warning"

        report.add_issue(ValidationIssue(
            path=path,
            message=message,
            severity=severity
        ))

    return report


def validate_cv_file(
    file_path: Path,
    strict: bool = False,
) -> ValidationReport:
    """
    Validate a CV JSON file against the schema.

    Args:
        file_path: Path to the CV JSON file.
        strict: If True, treat all issues as errors.

    Returns:
        ValidationReport containing all issues found.
    """
    report = ValidationReport(file_path=file_path)

    if not file_path.exists():
        report.add_issue(ValidationIssue(
            path="$",
            message=f"File not found: {file_path}",
            severity="error"
        ))
        return report

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        report.add_issue(ValidationIssue(
            path="$",
            message=f"Invalid JSON: {e}",
            severity="error"
        ))
        return report
    except Exception as e:
        report.add_issue(ValidationIssue(
            path="$",
            message=f"Error reading file: {e}",
            severity="error"
        ))
        return report

    return validate_cv_json(data, strict=strict, file_path=file_path)
