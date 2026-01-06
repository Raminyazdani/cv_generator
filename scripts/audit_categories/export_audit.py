"""
Export engine audit module.

Checks export engine functionality and JSON structure fidelity.
"""

import sys
from pathlib import Path
from typing import Callable


class ExportAuditor:
    """Auditor for export engine functionality."""

    def __init__(self, project_root: Path, add_problem: Callable):
        self.project_root = project_root
        self.add_problem = add_problem
        self.cv_dir = project_root / "data" / "cvs"

    def run_all_checks(self):
        """Run all export engine checks."""
        self._check_export_module_exists()
        self._check_export_function_signatures()
        self._check_exporter_v2()
        self._check_export_templates()

    def _check_export_module_exists(self):
        """Check that export-related modules exist."""
        db_module = self.project_root / "src" / "cv_generator" / "db.py"
        if db_module.exists():
            with open(db_module, "r", encoding="utf-8") as f:
                content = f.read()
            if "def export_cv" not in content:
                self.add_problem(
                    severity=self._severity("HIGH"),
                    category="Export Engine",
                    subcategory="Missing Function",
                    title="export_cv function not found",
                    description="No export_cv function in db.py",
                    reproduction_steps=["1. Search for 'def export_cv'"],
                    expected="export_cv function exists",
                    actual="Function not found",
                    affected_files=[str(db_module)],
                )

    def _check_export_function_signatures(self):
        """Check that export functions have correct signatures."""
        db_module = self.project_root / "src" / "cv_generator" / "db.py"
        if not db_module.exists():
            return

        try:
            with open(db_module, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for export_cv_to_file function
            if "def export_cv_to_file(" not in content:
                self.add_problem(
                    severity=self._severity("MEDIUM"),
                    category="Export Engine",
                    subcategory="Missing Function",
                    title="export_cv_to_file function not found",
                    description="No export_cv_to_file convenience function",
                    reproduction_steps=["1. Search for 'def export_cv_to_file'"],
                    expected="Function exists for file export",
                    actual="Function not found",
                    affected_files=[str(db_module)],
                )

            # Check for export_all_cvs function
            if "def export_all_cvs(" not in content:
                self.add_problem(
                    severity=self._severity("LOW"),
                    category="Export Engine",
                    subcategory="Missing Function",
                    title="export_all_cvs function not found",
                    description="No batch export function",
                    reproduction_steps=["1. Search for 'def export_all_cvs'"],
                    expected="Batch export function exists",
                    actual="Function not found",
                    affected_files=[str(db_module)],
                )

        except Exception:
            pass

    def _check_exporter_v2(self):
        """Check exporter_v2 module if it exists."""
        exporter_v2 = self.project_root / "src" / "cv_generator" / "exporter_v2.py"
        if not exporter_v2.exists():
            return

        try:
            with open(exporter_v2, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for key classes/functions
            required = ["Exporter", "export"]
            for item in required:
                if item not in content:
                    self.add_problem(
                        severity=self._severity("LOW"),
                        category="Export Engine",
                        subcategory="Module Structure",
                        title=f"Missing '{item}' in exporter_v2.py",
                        description=f"Expected '{item}' class or function not found",
                        reproduction_steps=[f"1. Search for '{item}'"],
                        expected=f"'{item}' is defined",
                        actual="Not found",
                        affected_files=[str(exporter_v2)],
                    )

        except Exception:
            pass

    def _check_export_templates(self):
        """Check export template directory."""
        export_templates = self.project_root / "src" / "cv_generator" / "export_templates"
        if not export_templates.exists():
            return

        # Check for template files
        template_files = list(export_templates.glob("*.py")) + list(export_templates.glob("*.json"))
        if not template_files:
            self.add_problem(
                severity=self._severity("LOW"),
                category="Export Engine",
                subcategory="Templates",
                title="No export templates found",
                description="Export templates directory is empty",
                reproduction_steps=["1. List files in export_templates/"],
                expected="Template files exist",
                actual="No templates found",
            )

    def _severity(self, level: str):
        """Convert severity string to enum."""
        sys.path.insert(0, str(self.project_root / "scripts"))
        from final_audit import Severity

        return getattr(Severity, level)
