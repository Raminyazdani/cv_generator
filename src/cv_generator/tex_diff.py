"""
TeX diff module for comparing LaTeX artifacts between builds.

Provides functionality to:
- Compare current vs previous .tex files
- Store last-build metadata in output/.state/
- Generate unified diff output
- Create JSON diff summaries
"""

import difflib
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class DiffResult:
    """Result of comparing two files."""
    
    file_name: str
    has_changes: bool
    added_lines: int = 0
    removed_lines: int = 0
    unified_diff: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "file_name": self.file_name,
            "has_changes": self.has_changes,
            "added_lines": self.added_lines,
            "removed_lines": self.removed_lines,
        }
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class BuildState:
    """State information from a previous build."""
    
    profile: str
    lang: str
    timestamp: str
    tex_files: Dict[str, str] = field(default_factory=dict)  # filename -> content hash
    tex_contents: Dict[str, str] = field(default_factory=dict)  # filename -> content
    pdf_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "profile": self.profile,
            "lang": self.lang,
            "timestamp": self.timestamp,
            "tex_files": self.tex_files,
            "tex_contents": self.tex_contents,
            "pdf_path": self.pdf_path,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BuildState":
        """Create BuildState from dictionary."""
        return cls(
            profile=data["profile"],
            lang=data["lang"],
            timestamp=data["timestamp"],
            tex_files=data.get("tex_files", {}),
            tex_contents=data.get("tex_contents", {}),
            pdf_path=data.get("pdf_path"),
        )


@dataclass
class DiffReport:
    """Report comparing current build against previous build."""
    
    profile: str
    lang: str
    previous_timestamp: Optional[str] = None
    current_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    files_compared: int = 0
    files_changed: int = 0
    files_added: int = 0
    files_removed: int = 0
    diffs: List[DiffResult] = field(default_factory=list)
    has_previous_build: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "profile": self.profile,
            "lang": self.lang,
            "previous_timestamp": self.previous_timestamp,
            "current_timestamp": self.current_timestamp,
            "summary": {
                "files_compared": self.files_compared,
                "files_changed": self.files_changed,
                "files_added": self.files_added,
                "files_removed": self.files_removed,
            },
            "has_previous_build": self.has_previous_build,
            "diffs": [d.to_dict() for d in self.diffs],
        }
    
    def to_json(self, pretty: bool = True) -> str:
        """Convert to JSON string."""
        indent = 2 if pretty else None
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def format_unified_diff(self) -> str:
        """Format all diffs as unified diff output."""
        lines = []
        for diff in self.diffs:
            if diff.has_changes and diff.unified_diff:
                lines.append(f"=== {diff.file_name} ===")
                lines.append(diff.unified_diff)
                lines.append("")
        return "\n".join(lines)


def get_state_dir(output_root: Optional[Path] = None) -> Path:
    """
    Get the directory for storing build state.
    
    Args:
        output_root: Root output directory. Defaults to repo_root/output.
        
    Returns:
        Path to the .state directory.
    """
    if output_root is None:
        from .paths import get_default_output_path
        output_root = get_default_output_path()
    
    return output_root / ".state"


def hash_content(content: str) -> str:
    """Generate hash of file content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


def load_build_state(
    profile: str,
    lang: str,
    output_root: Optional[Path] = None,
) -> Optional[BuildState]:
    """
    Load previous build state from disk.
    
    Args:
        profile: Profile name.
        lang: Language code.
        output_root: Root output directory.
        
    Returns:
        BuildState if exists, None otherwise.
    """
    state_dir = get_state_dir(output_root)
    state_file = state_dir / f"{profile}_{lang}.json"
    
    if not state_file.exists():
        return None
    
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return BuildState.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def save_build_state(
    state: BuildState,
    output_root: Optional[Path] = None,
) -> Path:
    """
    Save build state to disk.
    
    Args:
        state: BuildState to save.
        output_root: Root output directory.
        
    Returns:
        Path to the saved state file.
    """
    state_dir = get_state_dir(output_root)
    state_dir.mkdir(parents=True, exist_ok=True)
    
    state_file = state_dir / f"{state.profile}_{state.lang}.json"
    
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
        f.write("\n")
    
    return state_file


def capture_tex_state(
    profile: str,
    lang: str,
    latex_dir: Path,
    pdf_path: Optional[Path] = None,
) -> BuildState:
    """
    Capture current state of TeX files for a build.
    
    Args:
        profile: Profile name.
        lang: Language code.
        latex_dir: Directory containing LaTeX files.
        pdf_path: Optional path to generated PDF.
        
    Returns:
        BuildState with current file contents and hashes.
    """
    tex_files: Dict[str, str] = {}
    tex_contents: Dict[str, str] = {}
    
    if latex_dir.exists():
        # Get main.tex and all section files
        tex_patterns = ["*.tex", "sections/*.tex"]
        for pattern in tex_patterns:
            for tex_file in latex_dir.glob(pattern):
                if tex_file.is_file():
                    content = tex_file.read_text(encoding="utf-8")
                    rel_path = tex_file.relative_to(latex_dir).as_posix()
                    tex_files[rel_path] = hash_content(content)
                    tex_contents[rel_path] = content
    
    return BuildState(
        profile=profile,
        lang=lang,
        timestamp=datetime.now().isoformat(),
        tex_files=tex_files,
        tex_contents=tex_contents,
        pdf_path=str(pdf_path) if pdf_path else None,
    )


def compute_diff(
    file_name: str,
    old_content: Optional[str],
    new_content: Optional[str],
) -> DiffResult:
    """
    Compute unified diff between two file contents.
    
    Args:
        file_name: Name of the file being compared.
        old_content: Previous file content (None if new file).
        new_content: Current file content (None if deleted file).
        
    Returns:
        DiffResult with diff information.
    """
    if old_content is None and new_content is None:
        return DiffResult(
            file_name=file_name,
            has_changes=False,
        )
    
    if old_content is None:
        # New file
        lines = new_content.split('\n') if new_content else []
        return DiffResult(
            file_name=file_name,
            has_changes=True,
            added_lines=len(lines),
            removed_lines=0,
            unified_diff=f"(new file with {len(lines)} lines)",
        )
    
    if new_content is None:
        # Deleted file
        lines = old_content.split('\n')
        return DiffResult(
            file_name=file_name,
            has_changes=True,
            added_lines=0,
            removed_lines=len(lines),
            unified_diff=f"(deleted file with {len(lines)} lines)",
        )
    
    # Both exist, compute diff
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff_lines = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{file_name}",
        tofile=f"b/{file_name}",
        lineterm="",
    ))
    
    if not diff_lines:
        return DiffResult(
            file_name=file_name,
            has_changes=False,
        )
    
    # Count added/removed lines
    added = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
    removed = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
    
    return DiffResult(
        file_name=file_name,
        has_changes=True,
        added_lines=added,
        removed_lines=removed,
        unified_diff="".join(diff_lines),
    )


def compare_builds(
    profile: str,
    lang: str,
    current_latex_dir: Path,
    output_root: Optional[Path] = None,
) -> DiffReport:
    """
    Compare current build against previous build.
    
    Args:
        profile: Profile name.
        lang: Language code.
        current_latex_dir: Directory containing current LaTeX files.
        output_root: Root output directory.
        
    Returns:
        DiffReport with comparison results.
    """
    # Load previous state
    previous_state = load_build_state(profile, lang, output_root)
    
    report = DiffReport(
        profile=profile,
        lang=lang,
        has_previous_build=previous_state is not None,
        previous_timestamp=previous_state.timestamp if previous_state else None,
    )
    
    if previous_state is None:
        return report
    
    # Get current file contents
    current_contents: Dict[str, str] = {}
    if current_latex_dir.exists():
        tex_patterns = ["*.tex", "sections/*.tex"]
        for pattern in tex_patterns:
            for tex_file in current_latex_dir.glob(pattern):
                if tex_file.is_file():
                    content = tex_file.read_text(encoding="utf-8")
                    rel_path = tex_file.relative_to(current_latex_dir).as_posix()
                    current_contents[rel_path] = content
    
    # Get all file names from both builds
    all_files = set(previous_state.tex_contents.keys()) | set(current_contents.keys())
    report.files_compared = len(all_files)
    
    for file_name in sorted(all_files):
        old_content = previous_state.tex_contents.get(file_name)
        new_content = current_contents.get(file_name)
        
        diff = compute_diff(file_name, old_content, new_content)
        report.diffs.append(diff)
        
        if diff.has_changes:
            if old_content is None:
                report.files_added += 1
            elif new_content is None:
                report.files_removed += 1
            else:
                report.files_changed += 1
    
    return report


def diff_command_handler(
    profile: str,
    lang: str,
    output_root: Optional[Path] = None,
    format: str = "text",
) -> Tuple[DiffReport, str]:
    """
    Handle the diff command execution.
    
    Args:
        profile: Profile name.
        lang: Language code.
        output_root: Root output directory.
        format: Output format ('text' or 'json').
        
    Returns:
        Tuple of (DiffReport, formatted output string).
    """
    if output_root is None:
        from .paths import get_default_output_path
        output_root = get_default_output_path()
    
    # Look for current LaTeX files
    latex_dir = output_root / "latex" / profile / lang
    
    report = compare_builds(profile, lang, latex_dir, output_root)
    
    if format == "json":
        output = report.to_json()
    else:
        if not report.has_previous_build:
            output = f"No previous build found for {profile}_{lang}.\n"
            output += "Run 'cvgen build --keep-latex' first to capture build state.\n"
        else:
            lines = [
                f"📊 Diff Report: {profile}_{lang}",
                f"   Previous build: {report.previous_timestamp}",
                f"   Current build:  {report.current_timestamp}",
                f"",
                f"   Files compared: {report.files_compared}",
                f"   Changed: {report.files_changed}",
                f"   Added: {report.files_added}",
                f"   Removed: {report.files_removed}",
                f"",
            ]
            
            if any(d.has_changes for d in report.diffs):
                lines.append("📝 Changes:")
                lines.append("")
                lines.append(report.format_unified_diff())
            else:
                lines.append("✅ No changes detected.")
            
            output = "\n".join(lines)
    
    return report, output
