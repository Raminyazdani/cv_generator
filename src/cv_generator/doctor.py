"""
System health check module for CV Generator.

Provides the `cvgen doctor` command that validates the environment
and repo configuration before users attempt builds.

Checks include:
- Python version compatibility
- Dependencies importable (jinja2, flask, jsonschema)
- LaTeX engine availability
- Template sanity (Jinja2 parse check)
- Output directory writability
- Optional: DB health check
"""

import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .paths import get_default_output_path, get_default_templates_path, get_repo_root

logger = logging.getLogger(__name__)


class CheckStatus(Enum):
    """Status of a health check."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class CheckResult:
    """
    Result of a single health check.

    Attributes:
        name: Name of the check (e.g., "Python Version").
        status: Status of the check (ok, warning, error).
        detail: Detailed description of the check result.
        fix_hint: Suggested fix for failing checks.
    """

    name: str
    status: CheckStatus
    detail: str
    fix_hint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "name": self.name,
            "status": self.status.value,
            "detail": self.detail,
        }
        if self.fix_hint:
            result["fix_hint"] = self.fix_hint
        return result

    @property
    def icon(self) -> str:
        """Get status icon for display."""
        if self.status == CheckStatus.OK:
            return "✅"
        elif self.status == CheckStatus.WARNING:
            return "⚠️"
        else:
            return "❌"


@dataclass
class DoctorReport:
    """
    Complete health check report.

    Attributes:
        checks: List of check results.
        summary: Summary counts.
    """

    checks: List[CheckResult] = field(default_factory=list)

    @property
    def ok_count(self) -> int:
        """Count of OK checks."""
        return sum(1 for c in self.checks if c.status == CheckStatus.OK)

    @property
    def warning_count(self) -> int:
        """Count of warning checks."""
        return sum(1 for c in self.checks if c.status == CheckStatus.WARNING)

    @property
    def error_count(self) -> int:
        """Count of error checks."""
        return sum(1 for c in self.checks if c.status == CheckStatus.ERROR)

    @property
    def is_healthy(self) -> bool:
        """True if no errors."""
        return self.error_count == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "healthy": self.is_healthy,
            "summary": {
                "ok": self.ok_count,
                "warnings": self.warning_count,
                "errors": self.error_count,
            },
            "checks": [c.to_dict() for c in self.checks],
        }

    def format_text(self, verbose: bool = False) -> str:
        """Format as human-readable text."""
        lines = []

        # Summary
        status_emoji = "✅" if self.is_healthy else "❌"
        lines.append(f"\n{status_emoji} CV Generator Health Check")
        lines.append("=" * 40)

        # Summary counts
        lines.append(
            f"   OK: {self.ok_count} | Warnings: {self.warning_count} | Errors: {self.error_count}"
        )
        lines.append("")

        # Individual checks
        for check in self.checks:
            lines.append(f"{check.icon} {check.name}")
            lines.append(f"   {check.detail}")
            if check.fix_hint and (check.status != CheckStatus.OK or verbose):
                lines.append(f"   💡 {check.fix_hint}")
            lines.append("")

        return "\n".join(lines)


def _get_required_python_version() -> str:
    """
    Get the minimum required Python version from pyproject.toml.

    Returns:
        Minimum Python version string (e.g., "3.9").
    """
    pyproject_path = get_repo_root() / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text(encoding="utf-8")
        # Look for requires-python = ">=3.9"
        import re

        match = re.search(r'requires-python\s*=\s*["\']>=(\d+\.\d+)', content)
        if match:
            return match.group(1)
    return "3.9"  # Default fallback


def check_python_version() -> CheckResult:
    """
    Check if current Python version meets requirements.

    Returns:
        CheckResult with Python version status.
    """
    current = f"{sys.version_info.major}.{sys.version_info.minor}"
    required = _get_required_python_version()

    current_tuple = tuple(map(int, current.split(".")))
    required_tuple = tuple(map(int, required.split(".")))

    if current_tuple >= required_tuple:
        return CheckResult(
            name="Python Version",
            status=CheckStatus.OK,
            detail=f"Python {current} (requires >={required})",
        )
    else:
        return CheckResult(
            name="Python Version",
            status=CheckStatus.ERROR,
            detail=f"Python {current} is below required {required}",
            fix_hint=f"Upgrade to Python {required} or later",
        )


def check_dependencies() -> List[CheckResult]:
    """
    Check if required dependencies are importable.

    Returns:
        List of CheckResults for each dependency.
    """
    results = []

    # Core dependencies from pyproject.toml
    dependencies = [
        ("jinja2", "Jinja2 templating engine"),
        ("flask", "Flask web framework"),
        ("jsonschema", "JSON Schema validation"),
    ]

    for module_name, description in dependencies:
        try:
            __import__(module_name)
            # Use importlib.metadata to get version (more reliable)
            try:
                from importlib.metadata import PackageNotFoundError
                from importlib.metadata import version as get_version

                version = get_version(module_name)
            except PackageNotFoundError:
                version = "unknown"
            results.append(
                CheckResult(
                    name=f"Dependency: {module_name}",
                    status=CheckStatus.OK,
                    detail=f"{description} v{version}",
                )
            )
        except ImportError:
            results.append(
                CheckResult(
                    name=f"Dependency: {module_name}",
                    status=CheckStatus.ERROR,
                    detail=f"{description} is not installed",
                    fix_hint=f"pip install {module_name}",
                )
            )

    return results


def check_latex_engine(engine: str = "xelatex") -> CheckResult:
    """
    Check if a LaTeX engine is available.

    Args:
        engine: Name of the LaTeX engine to check (default: xelatex).

    Returns:
        CheckResult with LaTeX engine status.
    """
    # Use shutil.which for cross-platform compatibility
    engine_path = shutil.which(engine)

    if engine_path is None:
        return CheckResult(
            name=f"LaTeX Engine ({engine})",
            status=CheckStatus.WARNING,
            detail=f"{engine} not found in PATH",
            fix_hint="Install TeX Live or MiKTeX and ensure xelatex is in PATH",
        )

    # Try to get version
    try:
        result = subprocess.run(
            [engine, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            # Extract first line of version output
            version_line = result.stdout.strip().split("\n")[0]
            return CheckResult(
                name=f"LaTeX Engine ({engine})",
                status=CheckStatus.OK,
                detail=version_line,
            )
        else:
            return CheckResult(
                name=f"LaTeX Engine ({engine})",
                status=CheckStatus.WARNING,
                detail=f"{engine} found but version check failed",
                fix_hint="Verify LaTeX installation is complete",
            )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name=f"LaTeX Engine ({engine})",
            status=CheckStatus.WARNING,
            detail=f"{engine} found but timed out getting version",
            fix_hint="LaTeX installation may be misconfigured",
        )
    except Exception as e:
        return CheckResult(
            name=f"LaTeX Engine ({engine})",
            status=CheckStatus.WARNING,
            detail=f"Error checking {engine}: {e}",
            fix_hint="Verify LaTeX installation",
        )


def check_templates(template_dir: Optional[Path] = None) -> List[CheckResult]:
    """
    Check if templates can be parsed by Jinja2.

    Args:
        template_dir: Path to templates directory.

    Returns:
        List of CheckResults for template parsing.
    """
    results = []

    if template_dir is None:
        template_dir = get_default_templates_path()

    if not template_dir.exists():
        results.append(
            CheckResult(
                name="Template Directory",
                status=CheckStatus.ERROR,
                detail=f"Templates directory not found: {template_dir}",
                fix_hint="Create templates directory or specify correct path",
            )
        )
        return results

    # List template files
    template_files = list(template_dir.glob("*.tex"))

    if not template_files:
        results.append(
            CheckResult(
                name="Template Directory",
                status=CheckStatus.WARNING,
                detail=f"No .tex template files found in {template_dir}",
                fix_hint="Add LaTeX template files to templates directory",
            )
        )
        return results

    # Try to parse each template with Jinja2
    # Use the existing jinja_env module to get proper filter registration
    from jinja2 import TemplateSyntaxError

    from .jinja_env import create_jinja_env

    env = create_jinja_env(template_dir=template_dir)

    errors = []
    for template_file in template_files:
        try:
            env.get_template(template_file.name)
        except TemplateSyntaxError as e:
            errors.append(f"{template_file.name}: {e.message} (line {e.lineno})")
        except Exception as e:
            errors.append(f"{template_file.name}: {e}")

    if errors:
        results.append(
            CheckResult(
                name="Template Parsing",
                status=CheckStatus.ERROR,
                detail=f"{len(errors)} template(s) failed to parse: {', '.join(e.split(':')[0] for e in errors)}",
                fix_hint="Check template syntax: " + errors[0],
            )
        )
    else:
        results.append(
            CheckResult(
                name="Template Parsing",
                status=CheckStatus.OK,
                detail=f"All {len(template_files)} templates parsed successfully",
            )
        )

    return results


def check_output_writability(output_dir: Optional[Path] = None) -> CheckResult:
    """
    Check if the output directory is writable.

    Args:
        output_dir: Path to output directory.

    Returns:
        CheckResult with output directory status.
    """
    if output_dir is None:
        output_dir = get_default_output_path()

    # Check if we can write to the output directory
    try:
        # Try to create a temporary file in the output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create temp file to test writability
        test_file = output_dir / ".doctor_test"
        test_file.write_text("test")
        test_file.unlink()

        return CheckResult(
            name="Output Directory",
            status=CheckStatus.OK,
            detail=f"Writable: {output_dir}",
        )
    except PermissionError:
        return CheckResult(
            name="Output Directory",
            status=CheckStatus.ERROR,
            detail=f"Cannot write to {output_dir}",
            fix_hint="Check directory permissions or specify different output path",
        )
    except Exception as e:
        return CheckResult(
            name="Output Directory",
            status=CheckStatus.WARNING,
            detail=f"Error checking output directory: {e}",
            fix_hint="Verify output directory path and permissions",
        )


def check_database() -> CheckResult:
    """
    Check database health if DB feature is used.

    Returns:
        CheckResult with database status.
    """
    from .paths import get_repo_root

    db_path = get_repo_root() / "data" / "db" / "cv.db"

    if not db_path.exists():
        return CheckResult(
            name="Database",
            status=CheckStatus.OK,
            detail="No database found (not required)",
            fix_hint="Run 'cvgen db init' to create database if needed",
        )

    # Check if database is accessible
    try:
        from .db import doctor as db_doctor

        results = db_doctor(db_path)
        if results["healthy"]:
            return CheckResult(
                name="Database",
                status=CheckStatus.OK,
                detail=f"Healthy - {results['stats'].get('entries', 0)} entries",
            )
        else:
            issues = results.get("issues", [])
            return CheckResult(
                name="Database",
                status=CheckStatus.WARNING,
                detail=f"{len(issues)} issue(s) found",
                fix_hint="Run 'cvgen db doctor' for details",
            )
    except Exception as e:
        return CheckResult(
            name="Database",
            status=CheckStatus.WARNING,
            detail=f"Error checking database: {e}",
            fix_hint="Run 'cvgen db doctor' for details",
        )


def check_assets(cvs_dir: Optional[Path] = None) -> CheckResult:
    """
    Check if assets referenced in CV files are accessible.

    This is a read-only check that validates asset references exist.

    Args:
        cvs_dir: Directory containing CV JSON files.

    Returns:
        CheckResult with asset validation status.
    """
    from .assets import check_assets as validate_cv_assets
    from .assets import discover_asset_references
    from .io import discover_cv_files, load_cv_json
    from .paths import get_default_cvs_path

    if cvs_dir is None:
        cvs_dir = get_default_cvs_path()

    if not cvs_dir.exists():
        return CheckResult(
            name="Assets",
            status=CheckStatus.OK,
            detail="CVs directory not found (not required)",
        )

    # Find CV files
    try:
        cv_files = discover_cv_files(cvs_path=cvs_dir)
    except Exception as e:
        return CheckResult(
            name="Assets",
            status=CheckStatus.WARNING,
            detail=f"Error discovering CV files: {e}",
        )

    if not cv_files:
        return CheckResult(
            name="Assets",
            status=CheckStatus.OK,
            detail="No CV files found (not required)",
        )

    # Check assets in each CV
    total_assets = 0
    missing_assets = 0
    asset_errors = []

    for cv_file in cv_files:
        try:
            cv_data = load_cv_json(cv_file)
        except Exception:
            continue

        assets = discover_asset_references(cv_data)
        total_assets += len(assets)

        report = validate_cv_assets(cv_data)
        missing_count = report.missing_count
        missing_assets += missing_count

        if missing_count > 0:
            for result in report.results:
                if not result.is_valid and result.asset.is_local:
                    asset_errors.append(f"{cv_file.name}: {result.asset.path}")

    if missing_assets > 0:
        error_preview = ", ".join(asset_errors[:3])
        if len(asset_errors) > 3:
            error_preview += f" (+{len(asset_errors) - 3} more)"
        return CheckResult(
            name="Assets",
            status=CheckStatus.WARNING,
            detail=f"{missing_assets} missing local asset(s) of {total_assets} total",
            fix_hint=f"Missing: {error_preview}. Run 'cvgen assets check' for details.",
        )

    if total_assets == 0:
        return CheckResult(
            name="Assets",
            status=CheckStatus.OK,
            detail="No asset references found in CV files",
        )

    return CheckResult(
        name="Assets",
        status=CheckStatus.OK,
        detail=f"All {total_assets} asset(s) validated",
    )


def run_checks(
    template_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    latex_engine: str = "xelatex",
    check_db: bool = True,
    check_assets_flag: bool = True,
) -> DoctorReport:
    """
    Run all health checks.

    Args:
        template_dir: Path to templates directory.
        output_dir: Path to output directory.
        latex_engine: Name of the LaTeX engine to check.
        check_db: Whether to check database health.
        check_assets_flag: Whether to check asset references.

    Returns:
        DoctorReport with all check results.
    """
    report = DoctorReport()

    # Python version
    report.checks.append(check_python_version())

    # Dependencies
    report.checks.extend(check_dependencies())

    # LaTeX engine
    report.checks.append(check_latex_engine(latex_engine))

    # Templates
    report.checks.extend(check_templates(template_dir))

    # Output directory
    report.checks.append(check_output_writability(output_dir))

    # Database (optional)
    if check_db:
        report.checks.append(check_database())

    # Assets (optional)
    if check_assets_flag:
        report.checks.append(check_assets())

    return report
