"""
Generate comprehensive audit report.

Combines results from all analysis tools into a single report.

Usage:
    python -m scripts.generate_audit_report [--project-root PATH] [--output PATH]
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def count_lines(project_root: Path) -> Dict[str, int]:
    """Count lines of code in the project."""
    src_dir = project_root / "src" / "cv_generator"
    total_lines = 0
    file_count = 0

    for py_file in src_dir.rglob("*.py"):
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                total_lines += sum(1 for _ in f)
                file_count += 1
        except Exception:
            pass

    return {
        "total_lines": total_lines,
        "file_count": file_count,
    }


def run_ruff_check(project_root: Path) -> Dict[str, Any]:
    """Run ruff to find issues."""
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                str(project_root / "src" / "cv_generator"),
                "--output-format=json",
            ],
            capture_output=True,
            text=True,
        )
        if proc.stdout:
            issues = json.loads(proc.stdout)
            return {
                "total_issues": len(issues),
                "unused_imports": len([i for i in issues if i.get("code") == "F401"]),
                "unused_variables": len([i for i in issues if i.get("code") == "F841"]),
                "import_order": len([i for i in issues if i.get("code") == "I001"]),
                "other": len(
                    [i for i in issues if i.get("code") not in ("F401", "F841", "I001")]
                ),
                "issues": issues,
            }
    except Exception as e:
        return {"error": str(e)}
    return {"total_issues": 0}


def run_vulture_check(project_root: Path) -> Dict[str, Any]:
    """Run vulture to find dead code."""
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "vulture",
                str(project_root / "src" / "cv_generator"),
                "--min-confidence=80",
            ],
            capture_output=True,
            text=True,
        )
        issues = []
        for line in proc.stdout.strip().split("\n"):
            if line:
                issues.append(line)
        return {
            "total_issues": len(issues),
            "issues": issues,
        }
    except Exception as e:
        return {"error": str(e)}


def run_code_auditor(project_root: Path) -> Dict[str, Any]:
    """Run our custom code auditor."""
    try:
        # Import our auditor
        sys.path.insert(0, str(project_root / "scripts"))
        from code_audit import CodeAuditor

        auditor = CodeAuditor(project_root)
        report = auditor.audit()
        return report.to_dict()
    except Exception as e:
        return {"error": str(e)}


def run_function_analyzer(project_root: Path) -> Dict[str, Any]:
    """Run function usage analyzer."""
    try:
        sys.path.insert(0, str(project_root / "scripts"))
        from analyze_function_usage import FunctionUsageAnalyzer

        analyzer = FunctionUsageAnalyzer(project_root)
        report = analyzer.analyze()
        return {
            "total_functions": report.total_functions,
            "entry_points": report.entry_points,
            "reachable": report.reachable,
            "potentially_unreachable": len(report.unreachable_functions),
            "unreachable_functions": [
                {
                    "name": f.name,
                    "file": f.file_path,
                    "line": f.line_number,
                    "is_private": f.is_private,
                }
                for f in report.unreachable_functions[:20]  # Top 20
            ],
        }
    except Exception as e:
        return {"error": str(e)}


def run_duplicate_finder(project_root: Path) -> Dict[str, Any]:
    """Run duplicate code finder."""
    try:
        sys.path.insert(0, str(project_root / "scripts"))
        from find_duplicates import DuplicateFinder

        finder = DuplicateFinder(project_root, min_lines=5)
        duplicates = finder.find_exact_duplicates()
        similar_functions = finder.find_similar_functions()

        return {
            "exact_duplicates": len(duplicates),
            "similar_functions": len(similar_functions),
            "top_duplicates": [
                {
                    "hash": d.code_hash[:8],
                    "lines": d.line_count,
                    "occurrences": len(d.occurrences),
                    "locations": [
                        f"{loc.file_path}:{loc.start_line}"
                        for loc in d.occurrences
                    ],
                }
                for d in duplicates[:5]
            ],
            "top_similar": [
                {
                    "similarity": f"{s.similarity:.1%}",
                    "a": s.sample_code_a,
                    "b": s.sample_code_b,
                }
                for s in similar_functions[:5]
            ],
        }
    except Exception as e:
        return {"error": str(e)}


def generate_report(project_root: Path) -> Dict[str, Any]:
    """Generate full audit report."""
    report = {
        "generated_at": datetime.now().isoformat(),
        "project_root": str(project_root),
        "code_stats": count_lines(project_root),
        "ruff_analysis": run_ruff_check(project_root),
        "vulture_analysis": run_vulture_check(project_root),
        "code_audit": run_code_auditor(project_root),
        "function_analysis": run_function_analyzer(project_root),
        "duplicate_analysis": run_duplicate_finder(project_root),
    }

    # Calculate summary
    removable_lines = 0

    # Unused imports
    if "unused_imports" in report.get("ruff_analysis", {}):
        removable_lines += report["ruff_analysis"]["unused_imports"]

    # Unused variables
    if "unused_variables" in report.get("ruff_analysis", {}):
        removable_lines += report["ruff_analysis"]["unused_variables"]

    total_lines = report["code_stats"]["total_lines"]
    report["summary"] = {
        "total_lines": total_lines,
        "estimated_removable_lines": removable_lines,
        "potential_reduction_pct": (
            (removable_lines / total_lines * 100) if total_lines > 0 else 0
        ),
        "action_items": [],
    }

    # Generate action items
    if report["ruff_analysis"].get("unused_imports", 0) > 0:
        report["summary"]["action_items"].append(
            f"Remove {report['ruff_analysis']['unused_imports']} unused imports"
        )

    if report["ruff_analysis"].get("unused_variables", 0) > 0:
        report["summary"]["action_items"].append(
            f"Remove {report['ruff_analysis']['unused_variables']} unused variables"
        )

    if report["function_analysis"].get("potentially_unreachable", 0) > 0:
        report["summary"]["action_items"].append(
            f"Review {report['function_analysis']['potentially_unreachable']} potentially unused functions"
        )

    return report


def format_text_report(report: Dict[str, Any]) -> str:
    """Format report as human-readable text."""
    lines = [
        "=" * 70,
        "CV GENERATOR CODE AUDIT REPORT",
        f"Generated: {report['generated_at']}",
        "=" * 70,
        "",
        "CODE STATISTICS:",
        f"  Total Python files: {report['code_stats']['file_count']}",
        f"  Total lines of code: {report['code_stats']['total_lines']}",
        "",
        "RUFF ANALYSIS:",
        f"  Total issues: {report['ruff_analysis'].get('total_issues', 0)}",
        f"  - Unused imports (F401): {report['ruff_analysis'].get('unused_imports', 0)}",
        f"  - Unused variables (F841): {report['ruff_analysis'].get('unused_variables', 0)}",
        f"  - Import order (I001): {report['ruff_analysis'].get('import_order', 0)}",
        "",
        "VULTURE ANALYSIS:",
        f"  Dead code findings: {report['vulture_analysis'].get('total_issues', 0)}",
        "",
        "FUNCTION ANALYSIS:",
        f"  Total functions: {report['function_analysis'].get('total_functions', 0)}",
        f"  Entry points: {report['function_analysis'].get('entry_points', 0)}",
        f"  Reachable: {report['function_analysis'].get('reachable', 0)}",
        f"  Potentially unreachable: {report['function_analysis'].get('potentially_unreachable', 0)}",
        "",
        "DUPLICATE ANALYSIS:",
        f"  Exact duplicates: {report['duplicate_analysis'].get('exact_duplicates', 0)}",
        f"  Similar functions: {report['duplicate_analysis'].get('similar_functions', 0)}",
        "",
        "=" * 70,
        "SUMMARY",
        "=" * 70,
        f"  Estimated removable lines: {report['summary']['estimated_removable_lines']}",
        f"  Potential reduction: {report['summary']['potential_reduction_pct']:.1f}%",
        "",
        "ACTION ITEMS:",
    ]

    for item in report["summary"].get("action_items", []):
        lines.append(f"  - {item}")

    if not report["summary"].get("action_items"):
        lines.append("  (No action items)")

    lines.extend(["", "=" * 70])

    return "\n".join(lines)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate code audit report")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )

    args = parser.parse_args()

    print("Generating audit report...", file=sys.stderr)
    report = generate_report(args.project_root)

    if args.format == "json":
        output = json.dumps(report, indent=2)
    else:
        output = format_text_report(report)

    if args.output:
        args.output.write_text(output)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
