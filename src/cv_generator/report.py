"""
Build report generation for CV Generator.

Provides functionality to create detailed build reports including:
- Profile/language information
- Output file paths
- Build timings
- Warnings from LaTeX compilation
- Environment summary
"""

import json
import platform
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import __version__


@dataclass
class BuildArtifact:
    """
    Represents a generated artifact from a CV build.

    Each artifact corresponds to one CV (profile + language combination)
    and tracks the outcome of its generation.

    Field Relationships:
        - success=True, skipped=False: Build completed successfully.
        - success=True, skipped=True: Build skipped (e.g., no changes in incremental mode).
        - success=False: Build failed, error field contains the reason.

    Attributes:
        profile: Profile name (e.g., 'ramin').
        lang: Language code (e.g., 'en', 'de', 'fa').
        pdf_path: Absolute path to the generated PDF (None if build failed or dry run).
        tex_path: Absolute path to the generated LaTeX main.tex (None if not kept).
        success: True if the artifact was generated successfully or intentionally skipped.
        error: Error message if generation failed (None on success).
        skipped: True if generation was skipped (e.g., incremental build with no changes).
    """

    profile: str
    lang: str
    pdf_path: Optional[str] = None
    tex_path: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
    skipped: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "profile": self.profile,
            "lang": self.lang,
            "pdf_path": self.pdf_path,
            "tex_path": self.tex_path,
            "success": self.success,
            "error": self.error,
            "skipped": self.skipped,
        }


@dataclass
class BuildReport:
    """
    Build report containing information about a CV generation run.

    This dataclass captures comprehensive information about a build,
    including timing, generated artifacts, warnings, errors, and
    environment details. Reports can be serialized to JSON and Markdown.

    Datetime Format:
        All datetime fields use ISO 8601 format (e.g., '2024-01-15T10:30:00.123456').

    Build Options:
        - dry_run: When True, LaTeX was rendered but not compiled to PDF.
        - incremental: When True, unchanged CVs were skipped.
        - variant: Optional variant filter applied (e.g., 'academic', 'industry').

    Attributes:
        run_id: Unique 8-character hex identifier for this build run.
        tool_version: Version of cv_generator that performed the build.
        datetime_started: ISO 8601 timestamp when build started.
        datetime_finished: ISO 8601 timestamp when build finished.
        duration_seconds: Total build duration in seconds.
        platform_info: System information (system, release, python_version, platform).
        artifacts: List of BuildArtifact objects for each CV processed.
        warnings: List of warning messages from the build (e.g., font substitutions).
        errors: List of error messages from the build (e.g., compilation failures).
        dry_run: Whether this was a dry run (LaTeX only, no PDF).
        incremental: Whether incremental build mode was enabled.
        variant: Variant filter applied to the build (None if not filtered).
    """

    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    tool_version: str = __version__
    datetime_started: Optional[str] = None
    datetime_finished: Optional[str] = None
    duration_seconds: Optional[float] = None
    platform_info: Dict[str, str] = field(default_factory=dict)
    artifacts: List[BuildArtifact] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    dry_run: bool = False
    incremental: bool = False
    variant: Optional[str] = None

    def __post_init__(self):
        """Initialize platform info if not provided."""
        if not self.platform_info:
            self.platform_info = {
                "system": platform.system(),
                "release": platform.release(),
                "python_version": sys.version.split()[0],
                "platform": platform.platform(),
            }

    @property
    def total_count(self) -> int:
        """Total number of artifacts."""
        return len(self.artifacts)

    @property
    def success_count(self) -> int:
        """Number of successful builds."""
        return sum(1 for a in self.artifacts if a.success)

    @property
    def failure_count(self) -> int:
        """Number of failed builds."""
        return sum(1 for a in self.artifacts if not a.success)

    @property
    def skipped_count(self) -> int:
        """Number of skipped builds."""
        return sum(1 for a in self.artifacts if a.skipped)

    def add_artifact(self, artifact: BuildArtifact) -> None:
        """Add an artifact to the report."""
        self.artifacts.append(artifact)

    def add_warning(self, warning: str) -> None:
        """Add a warning message to the report."""
        self.warnings.append(warning)

    def add_error(self, error: str) -> None:
        """Add an error message to the report."""
        self.errors.append(error)

    def start(self) -> None:
        """Mark the build start time."""
        self.datetime_started = datetime.now().isoformat()

    def finish(self) -> None:
        """Mark the build end time and calculate duration."""
        self.datetime_finished = datetime.now().isoformat()
        if self.datetime_started:
            started = datetime.fromisoformat(self.datetime_started)
            finished = datetime.fromisoformat(self.datetime_finished)
            self.duration_seconds = (finished - started).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary representation."""
        return {
            "run_id": self.run_id,
            "tool_version": self.tool_version,
            "datetime_started": self.datetime_started,
            "datetime_finished": self.datetime_finished,
            "duration_seconds": self.duration_seconds,
            "platform": self.platform_info,
            "summary": {
                "total": self.total_count,
                "success": self.success_count,
                "failed": self.failure_count,
                "skipped": self.skipped_count,
            },
            "options": {
                "dry_run": self.dry_run,
                "incremental": self.incremental,
                "variant": self.variant,
            },
            "artifacts": [a.to_dict() for a in self.artifacts],
            "warnings": self.warnings,
            "errors": self.errors,
        }

    def to_json(self, pretty: bool = True) -> str:
        """Convert report to JSON string."""
        indent = 2 if pretty else None
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Convert report to Markdown format."""
        lines = [
            "# Build Report",
            "",
            f"**Run ID:** `{self.run_id}`  ",
            f"**Tool Version:** {self.tool_version}  ",
            f"**Started:** {self.datetime_started}  ",
            f"**Finished:** {self.datetime_finished}  ",
        ]

        if self.duration_seconds is not None:
            lines.append(f"**Duration:** {self.duration_seconds:.2f}s  ")

        lines.extend([
            "",
            "## Summary",
            "",
            "| Metric | Count |",
            "|--------|-------|",
            f"| Total | {self.total_count} |",
            f"| Success | {self.success_count} |",
            f"| Failed | {self.failure_count} |",
            f"| Skipped | {self.skipped_count} |",
            "",
        ])

        if self.artifacts:
            lines.extend([
                "## Artifacts",
                "",
            ])
            for artifact in self.artifacts:
                status = "✅" if artifact.success else "❌"
                if artifact.skipped:
                    status = "⏭️"
                lines.append(f"- {status} **{artifact.profile}_{artifact.lang}**")
                if artifact.pdf_path:
                    lines.append(f"  - PDF: `{artifact.pdf_path}`")
                if artifact.tex_path:
                    lines.append(f"  - TeX: `{artifact.tex_path}`")
                if artifact.error:
                    lines.append(f"  - Error: {artifact.error}")
            lines.append("")

        if self.warnings:
            lines.extend([
                "## Warnings",
                "",
            ])
            for warning in self.warnings:
                lines.append(f"- ⚠️ {warning}")
            lines.append("")

        if self.errors:
            lines.extend([
                "## Errors",
                "",
            ])
            for error in self.errors:
                lines.append(f"- ❌ {error}")
            lines.append("")

        lines.extend([
            "## Environment",
            "",
            f"- **System:** {self.platform_info.get('system', 'Unknown')}",
            f"- **Release:** {self.platform_info.get('release', 'Unknown')}",
            f"- **Python:** {self.platform_info.get('python_version', 'Unknown')}",
            "",
        ])

        return "\n".join(lines)


def get_reports_dir(output_root: Optional[Path] = None) -> Path:
    """
    Get the directory for storing build reports.

    Args:
        output_root: Root output directory. Defaults to repo_root/output.

    Returns:
        Path to the reports directory.
    """
    if output_root is None:
        from .paths import get_default_output_path
        output_root = get_default_output_path()

    return output_root / "reports"


def write_build_report(
    report: BuildReport,
    output_root: Optional[Path] = None,
    timestamp: Optional[datetime] = None,
) -> Dict[str, Path]:
    """
    Write a build report to files.

    Args:
        report: The build report to write.
        output_root: Root output directory. Defaults to repo_root/output.
        timestamp: Optional timestamp for file naming. Defaults to current time.

    Returns:
        Dictionary with paths to written files ('json' and 'md' keys).
    """
    reports_dir = get_reports_dir(output_root)
    reports_dir.mkdir(parents=True, exist_ok=True)

    if timestamp is None:
        timestamp = datetime.now()

    date_str = timestamp.strftime("%Y%m%d_%H%M%S")

    json_path = reports_dir / f"build_{date_str}.json"
    md_path = reports_dir / f"build_{date_str}.md"

    # Write JSON report
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(report.to_json())
        f.write("\n")

    # Write Markdown report
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report.to_markdown())

    return {"json": json_path, "md": md_path}
