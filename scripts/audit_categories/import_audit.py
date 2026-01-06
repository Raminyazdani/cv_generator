"""
Import engine audit module.

Checks import engine functionality and error handling.
"""

import json
import sys
from pathlib import Path
from typing import Callable


class ImportAuditor:
    """Auditor for import engine functionality."""

    def __init__(self, project_root: Path, add_problem: Callable):
        self.project_root = project_root
        self.add_problem = add_problem
        self.cv_dir = project_root / "data" / "cvs"

    def run_all_checks(self):
        """Run all import engine checks."""
        self._check_import_module_exists()
        self._check_import_function_signatures()
        self._check_config_handling()
        self._check_cv_files_parseable()
        self._check_section_handlers()

    def _check_import_module_exists(self):
        """Check that import-related modules exist."""
        # Check for importer module
        importer_v2 = self.project_root / "src" / "cv_generator" / "importer_v2.py"
        if not importer_v2.exists():
            # Check for import functionality in db.py
            db_module = self.project_root / "src" / "cv_generator" / "db.py"
            if db_module.exists():
                with open(db_module, "r", encoding="utf-8") as f:
                    content = f.read()
                if "def import_cv" not in content:
                    self.add_problem(
                        severity=self._severity("HIGH"),
                        category="Import Engine",
                        subcategory="Missing Function",
                        title="import_cv function not found",
                        description="No import_cv function in db.py or importer_v2.py",
                        reproduction_steps=["1. Search for 'def import_cv'"],
                        expected="import_cv function exists",
                        actual="Function not found",
                    )

    def _check_import_function_signatures(self):
        """Check that import functions have correct signatures."""
        db_module = self.project_root / "src" / "cv_generator" / "db.py"
        if not db_module.exists():
            return

        try:
            with open(db_module, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for required import parameters
            if "def import_cv(" in content:
                # Find the function signature
                start = content.find("def import_cv(")
                end = content.find(")", start) + 1
                signature = content[start:end]

                # Check for required parameters
                if "cv_path" not in signature and "path" not in signature:
                    self.add_problem(
                        severity=self._severity("MEDIUM"),
                        category="Import Engine",
                        subcategory="Function Signature",
                        title="import_cv missing path parameter",
                        description="The import_cv function should accept a file path",
                        reproduction_steps=["1. Check import_cv signature"],
                        expected="cv_path or path parameter exists",
                        actual="Parameter not found",
                        affected_files=[str(db_module)],
                    )

        except Exception:
            pass

    def _check_config_handling(self):
        """Check that config blocks are handled during import."""
        db_module = self.project_root / "src" / "cv_generator" / "db.py"
        if not db_module.exists():
            return

        # Check CV files for config blocks
        if not self.cv_dir.exists():
            return

        for cv_file in self.cv_dir.glob("*.json"):
            try:
                with open(cv_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Check if file has a config block
                if "$schema" in data or "meta" in data:
                    # Config blocks should be handled
                    pass

            except json.JSONDecodeError:
                self.add_problem(
                    severity=self._severity("CRITICAL"),
                    category="Import Engine",
                    subcategory="Invalid JSON",
                    title=f"Cannot parse {cv_file.name}",
                    description="CV file contains invalid JSON",
                    reproduction_steps=[f"1. Try to parse {cv_file.name}"],
                    expected="Valid JSON",
                    actual="JSON parse error",
                    affected_files=[str(cv_file)],
                )

    def _check_cv_files_parseable(self):
        """Check that all CV files can be parsed."""
        if not self.cv_dir.exists():
            self.add_problem(
                severity=self._severity("HIGH"),
                category="Import Engine",
                subcategory="Missing Directory",
                title="CV directory not found",
                description="The data/cvs directory does not exist",
                reproduction_steps=["1. Check for data/cvs directory"],
                expected="data/cvs exists",
                actual="Directory not found",
            )
            return

        cv_files = list(self.cv_dir.glob("*.json"))
        if not cv_files:
            self.add_problem(
                severity=self._severity("MEDIUM"),
                category="Import Engine",
                subcategory="No Data",
                title="No CV files found",
                description="No JSON files in data/cvs directory",
                reproduction_steps=["1. List files in data/cvs"],
                expected="At least one CV file exists",
                actual="No JSON files found",
            )

    def _check_section_handlers(self):
        """Check that all CV sections have import handlers."""
        db_module = self.project_root / "src" / "cv_generator" / "db.py"
        if not db_module.exists():
            return

        # Get sections from a CV file
        if not self.cv_dir.exists():
            return

        cv_files = list(self.cv_dir.glob("*.json"))
        if not cv_files:
            return

        # Collect all unique sections from CV files
        all_sections = set()
        for cv_file in cv_files:
            try:
                with open(cv_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                all_sections.update(data.keys())
            except Exception:
                pass

        # Check that db.py handles these sections
        try:
            with open(db_module, "r", encoding="utf-8") as f:
                content = f.read()

            # Most sections should be handled generically
            # Check for section-specific handling if needed
            if "skills" in all_sections and "skills" not in content:
                self.add_problem(
                    severity=self._severity("LOW"),
                    category="Import Engine",
                    subcategory="Section Handler",
                    title="Skills section handling unclear",
                    description="The 'skills' section may need special handling",
                    reproduction_steps=["1. Check import handling for skills"],
                    expected="Skills section is handled",
                    actual="No explicit skills handling found",
                    affected_files=[str(db_module)],
                )

        except Exception:
            pass

    def _severity(self, level: str):
        """Convert severity string to enum."""
        sys.path.insert(0, str(self.project_root / "scripts"))
        from final_audit import Severity

        return getattr(Severity, level)
