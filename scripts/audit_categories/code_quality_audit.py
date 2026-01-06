"""
Code quality audit module.

Checks for unused code, linting issues, and code complexity.
"""

import subprocess
import sys
from pathlib import Path
from typing import Callable


class CodeQualityAuditor:
    """Auditor for code quality metrics."""

    def __init__(self, project_root: Path, add_problem: Callable):
        self.project_root = project_root
        self.add_problem = add_problem
        self.src_dir = project_root / "src" / "cv_generator"

    def run_all_checks(self):
        """Run all code quality checks."""
        self._check_linting()
        self._check_type_hints()
        self._check_docstrings()
        self._check_file_length()

    def _check_linting(self):
        """Run ruff linter and report issues."""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "check",
                    str(self.src_dir),
                    "--output-format=json",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=60,
            )

            if result.stdout:
                import json

                try:
                    issues = json.loads(result.stdout)
                    if issues:
                        # Group by code
                        by_code = {}
                        for issue in issues:
                            code = issue.get("code", "unknown")
                            if code not in by_code:
                                by_code[code] = []
                            by_code[code].append(issue)

                        # Report significant issue types
                        for code, code_issues in by_code.items():
                            if len(code_issues) > 5:
                                # Only report if many occurrences
                                self.add_problem(
                                    severity=self._severity("LOW"),
                                    category="Code Quality",
                                    subcategory="Linting",
                                    title=f"{len(code_issues)} {code} linting issues",
                                    description=f"Ruff found {len(code_issues)} instances of {code}",
                                    reproduction_steps=[
                                        f"1. Run: ruff check src/cv_generator --select {code}",
                                    ],
                                    expected="No linting issues",
                                    actual=f"{len(code_issues)} issues of type {code}",
                                )
                except json.JSONDecodeError:
                    pass

        except subprocess.TimeoutExpired:
            pass
        except FileNotFoundError:
            # ruff not installed
            pass
        except Exception:
            pass

    def _check_type_hints(self):
        """Check for missing type hints in public functions."""
        if not self.src_dir.exists():
            return

        files_without_hints = []
        for py_file in self.src_dir.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for functions without type hints
                # Simple heuristic: look for def without ->
                lines = content.split("\n")
                for line in lines:
                    if line.strip().startswith("def ") and "->" not in line:
                        # Check if it's a public function
                        func_name = line.split("def ")[1].split("(")[0]
                        if not func_name.startswith("_"):
                            files_without_hints.append(str(py_file.relative_to(self.project_root)))
                            break

            except Exception:
                pass

        if len(files_without_hints) > 5:
            self.add_problem(
                severity=self._severity("LOW"),
                category="Code Quality",
                subcategory="Type Hints",
                title=f"{len(files_without_hints)} files with missing type hints",
                description="Some public functions lack return type annotations",
                reproduction_steps=["1. Check public functions for -> annotations"],
                expected="All public functions have type hints",
                actual=f"{len(files_without_hints)} files have functions without hints",
            )

    def _check_docstrings(self):
        """Check for missing docstrings in public modules."""
        if not self.src_dir.exists():
            return

        files_without_docstrings = []
        for py_file in self.src_dir.glob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for module docstring
                lines = content.strip().split("\n")
                if lines and not (lines[0].startswith('"""') or lines[0].startswith("'''")):
                    files_without_docstrings.append(py_file.name)

            except Exception:
                pass

        if files_without_docstrings:
            self.add_problem(
                severity=self._severity("LOW"),
                category="Code Quality",
                subcategory="Docstrings",
                title=f"{len(files_without_docstrings)} modules without docstrings",
                description="Some modules lack module-level docstrings",
                reproduction_steps=["1. Check for '\"\"\"' at start of each .py file"],
                expected="All modules have docstrings",
                actual=f"Missing in: {', '.join(files_without_docstrings[:5])}{'...' if len(files_without_docstrings) > 5 else ''}",
            )

    def _check_file_length(self):
        """Check for excessively long files."""
        if not self.src_dir.exists():
            return

        long_files = []
        for py_file in self.src_dir.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    line_count = sum(1 for _ in f)

                if line_count > 1000:
                    long_files.append((py_file.name, line_count))

            except Exception:
                pass

        for filename, lines in long_files:
            self.add_problem(
                severity=self._severity("LOW"),
                category="Code Quality",
                subcategory="File Length",
                title=f"File too long: {filename} ({lines} lines)",
                description="Consider splitting into smaller modules",
                reproduction_steps=[f"1. Count lines in {filename}"],
                expected="Files under 1000 lines",
                actual=f"{lines} lines",
                suggested_fix="Consider refactoring into smaller modules",
            )

    def _severity(self, level: str):
        """Convert severity string to enum."""
        sys.path.insert(0, str(self.project_root / "scripts"))
        from final_audit import Severity

        return getattr(Severity, level)
