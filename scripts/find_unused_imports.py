"""
Find and remove unused imports using multiple tools.

Integrates with:
- ruff (fast Python linter)
- vulture (dead code finder)

Usage:
    python -m scripts.find_unused_imports [--project-root PATH] [--fix]
"""

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class UnusedImport:
    """Represents an unused import."""

    file_path: str
    line_number: int
    import_name: str
    full_import: str
    tool: str  # Which tool found it

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "import_name": self.import_name,
            "full_import": self.full_import,
            "tool": self.tool,
        }


def run_ruff_unused(directory: Path) -> List[UnusedImport]:
    """
    Run ruff to find unused imports (F401).

    Args:
        directory: Directory to scan

    Returns:
        List of unused imports found
    """
    results = []
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                str(directory),
                "--select=F401",
                "--output-format=json",
            ],
            capture_output=True,
            text=True,
        )

        if proc.stdout:
            data = json.loads(proc.stdout)
            for item in data:
                results.append(
                    UnusedImport(
                        file_path=item.get("filename", ""),
                        line_number=item.get("location", {}).get("row", 0),
                        import_name=item.get("message", "").split("'")[1]
                        if "'" in item.get("message", "")
                        else "",
                        full_import=item.get("message", ""),
                        tool="ruff",
                    )
                )
    except (subprocess.SubprocessError, json.JSONDecodeError) as e:
        print(f"Warning: Error running ruff: {e}", file=sys.stderr)

    return results


def run_vulture_unused(directory: Path, min_confidence: int = 80) -> List[UnusedImport]:
    """
    Run vulture to find dead code including unused imports.

    Args:
        directory: Directory to scan
        min_confidence: Minimum confidence threshold (0-100)

    Returns:
        List of unused imports found
    """
    results = []
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "vulture",
                str(directory),
                f"--min-confidence={min_confidence}",
            ],
            capture_output=True,
            text=True,
        )

        # vulture outputs lines like:
        # path/file.py:10: unused import 'something' (100% confidence)
        for line in proc.stdout.strip().split("\n"):
            if not line or "unused import" not in line:
                continue

            parts = line.split(":")
            if len(parts) >= 2:
                file_path = parts[0]
                line_num = int(parts[1]) if parts[1].isdigit() else 0
                # Extract import name from message
                if "'" in line:
                    import_name = line.split("'")[1]
                else:
                    import_name = ""

                results.append(
                    UnusedImport(
                        file_path=file_path,
                        line_number=line_num,
                        import_name=import_name,
                        full_import=line,
                        tool="vulture",
                    )
                )
    except subprocess.SubprocessError as e:
        print(f"Warning: Error running vulture: {e}", file=sys.stderr)

    return results


def cross_reference_results(*results_lists: List[UnusedImport]) -> List[UnusedImport]:
    """
    Cross-reference results from multiple tools.

    Items found by 2+ tools have higher confidence.

    Args:
        results_lists: Multiple lists of unused imports

    Returns:
        Combined list with duplicates marked
    """
    # Create a key for each import
    seen: dict = {}

    for results in results_lists:
        for item in results:
            key = (item.file_path, item.line_number, item.import_name)
            if key in seen:
                seen[key]["tools"].add(item.tool)
            else:
                seen[key] = {
                    "item": item,
                    "tools": {item.tool},
                }

    # Return items, prioritizing those found by multiple tools
    combined = []
    for key, data in sorted(seen.items(), key=lambda x: -len(x[1]["tools"])):
        item = data["item"]
        if len(data["tools"]) > 1:
            item.tool = f"multiple ({', '.join(sorted(data['tools']))})"
        combined.append(item)

    return combined


def fix_unused_imports(directory: Path) -> str:
    """
    Use ruff to automatically fix unused imports.

    Args:
        directory: Directory to fix

    Returns:
        Output from ruff fix command
    """
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                str(directory),
                "--select=F401",
                "--fix",
            ],
            capture_output=True,
            text=True,
        )
        return proc.stdout + proc.stderr
    except subprocess.SubprocessError as e:
        return f"Error: {e}"


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Find unused imports")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix unused imports using ruff",
    )
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )

    args = parser.parse_args()

    src_dir = args.project_root / "src" / "cv_generator"

    if args.fix:
        print("Fixing unused imports...")
        output = fix_unused_imports(src_dir)
        print(output)
        return

    # Run both tools
    print("Scanning for unused imports...", file=sys.stderr)

    ruff_results = run_ruff_unused(src_dir)
    vulture_results = run_vulture_unused(src_dir)

    # Cross-reference
    combined = cross_reference_results(ruff_results, vulture_results)

    if args.output_format == "json":
        print(json.dumps([r.to_dict() for r in combined], indent=2))
    else:
        print(f"\nFound {len(combined)} unused imports:\n")
        for item in combined:
            print(f"  {item.file_path}:{item.line_number}")
            print(f"    Import: {item.import_name}")
            print(f"    Tool: {item.tool}")
            print()

        if combined:
            print("Run with --fix to automatically remove unused imports.")


if __name__ == "__main__":
    main()
