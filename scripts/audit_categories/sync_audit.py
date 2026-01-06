"""
Sync engine audit module.

Checks multi-language sync, invariant field sync, and conflict handling.
"""

import sys
from pathlib import Path
from typing import Callable


class SyncAuditor:
    """Auditor for sync engine functionality."""

    def __init__(self, project_root: Path, add_problem: Callable):
        self.project_root = project_root
        self.add_problem = add_problem
        self.sync_module = project_root / "src" / "cv_generator" / "sync_engine.py"

    def run_all_checks(self):
        """Run all sync engine checks."""
        self._check_sync_module_exists()
        self._check_sync_functions()
        self._check_invariant_fields()
        self._check_conflict_handling()

    def _check_sync_module_exists(self):
        """Check that sync engine module exists."""
        if not self.sync_module.exists():
            self.add_problem(
                severity=self._severity("HIGH"),
                category="Sync Engine",
                subcategory="Missing Module",
                title="Sync engine module not found",
                description="The sync_engine.py module is missing",
                reproduction_steps=["1. Check for src/cv_generator/sync_engine.py"],
                expected="sync_engine.py exists",
                actual="File not found",
                affected_files=[str(self.sync_module)],
            )
            return False
        return True

    def _check_sync_functions(self):
        """Check that sync functions are defined."""
        if not self.sync_module.exists():
            return

        try:
            with open(self.sync_module, "r", encoding="utf-8") as f:
                content = f.read()

            # Required functions for sync engine
            required_functions = [
                "sync",
                "get_sync_status",
            ]

            for func in required_functions:
                if f"def {func}" not in content and f"class {func}" not in content.title():
                    self.add_problem(
                        severity=self._severity("MEDIUM"),
                        category="Sync Engine",
                        subcategory="Missing Function",
                        title=f"Missing function: {func}",
                        description=f"Function '{func}' not found in sync_engine.py",
                        reproduction_steps=[f"1. Search for 'def {func}' in sync_engine.py"],
                        expected=f"Function '{func}' is defined",
                        actual="Function not found",
                        affected_files=[str(self.sync_module)],
                    )

        except Exception as e:
            self.add_problem(
                severity=self._severity("MEDIUM"),
                category="Sync Engine",
                subcategory="Parse Error",
                title="Cannot parse sync_engine.py",
                description=str(e),
                reproduction_steps=["1. Try to read sync_engine.py"],
                expected="File is readable",
                actual=f"Exception: {type(e).__name__}",
                affected_files=[str(self.sync_module)],
                error_message=str(e),
            )

    def _check_invariant_fields(self):
        """Check that invariant field sync is handled."""
        if not self.sync_module.exists():
            return

        try:
            with open(self.sync_module, "r", encoding="utf-8") as f:
                content = f.read()

            # Invariant fields that should be synced
            invariant_indicators = [
                "invariant",
                "shared",
                "email",
                "phone",
                "url",
                "date",
            ]

            has_invariant_handling = any(ind in content.lower() for ind in invariant_indicators)

            if not has_invariant_handling:
                self.add_problem(
                    severity=self._severity("MEDIUM"),
                    category="Sync Engine",
                    subcategory="Invariant Fields",
                    title="No invariant field handling detected",
                    description="Sync engine may not handle invariant fields",
                    reproduction_steps=["1. Check sync_engine.py for invariant handling"],
                    expected="Invariant fields are synced across variants",
                    actual="No invariant field handling found",
                    affected_files=[str(self.sync_module)],
                )

        except Exception:
            pass

    def _check_conflict_handling(self):
        """Check that conflicts are handled."""
        if not self.sync_module.exists():
            return

        try:
            with open(self.sync_module, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for conflict handling
            conflict_indicators = [
                "conflict",
                "Conflict",
                "merge",
                "resolve",
            ]

            has_conflict_handling = any(ind in content for ind in conflict_indicators)

            if not has_conflict_handling:
                self.add_problem(
                    severity=self._severity("LOW"),
                    category="Sync Engine",
                    subcategory="Conflict Handling",
                    title="No conflict handling detected",
                    description="Sync engine may not handle conflicts",
                    reproduction_steps=["1. Check sync_engine.py for conflict handling"],
                    expected="Conflicts are detected and resolved",
                    actual="No conflict handling found",
                    affected_files=[str(self.sync_module)],
                )

        except Exception:
            pass

    def _severity(self, level: str):
        """Convert severity string to enum."""
        sys.path.insert(0, str(self.project_root / "scripts"))
        from final_audit import Severity

        return getattr(Severity, level)
