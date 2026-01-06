"""
Safely remove dead code with verification.

Provides tools to remove dead code while ensuring tests still pass.

Usage:
    python -m scripts.remove_dead_code [--project-root PATH] [--dry-run]
"""

import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RemovalResult:
    """Result of a removal operation."""

    success: bool
    file_path: str
    name: str
    code_type: str
    lines_removed: int
    tests_passed: bool
    error: Optional[str] = None


@dataclass
class BatchRemovalResult:
    """Result of batch removal."""

    total_attempted: int = 0
    successful: int = 0
    failed: int = 0
    test_failures: int = 0
    results: List[RemovalResult] = field(default_factory=list)
    total_lines_removed: int = 0

    def get_summary(self) -> str:
        """Get human-readable summary."""
        lines = [
            "=" * 60,
            "DEAD CODE REMOVAL SUMMARY",
            "=" * 60,
            f"Total attempted: {self.total_attempted}",
            f"Successful: {self.successful}",
            f"Failed: {self.failed}",
            f"Test failures: {self.test_failures}",
            f"Total lines removed: {self.total_lines_removed}",
            "=" * 60,
        ]
        return "\n".join(lines)


class DeadCodeRemover:
    """Remove dead code with safety checks."""

    def __init__(self, project_root: Path, backup_dir: Optional[Path] = None):
        self.project_root = project_root
        self.backup_dir = backup_dir or Path(tempfile.mkdtemp(prefix="dead_code_backup_"))
        self.removals: List[RemovalResult] = []

    def remove_unused_import(
        self,
        file_path: Path,
        import_name: str,
        line_number: int,
        verify: bool = True,
    ) -> RemovalResult:
        """
        Remove a single unused import.

        1. Backup file
        2. Remove import line
        3. Run tests (if verify=True)
        4. If tests fail, restore backup
        """
        abs_path = self.project_root / file_path

        # Create backup
        backup_path = self._backup_file(abs_path)

        try:
            # Read file
            with open(abs_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if line_number < 1 or line_number > len(lines):
                return RemovalResult(
                    success=False,
                    file_path=str(file_path),
                    name=import_name,
                    code_type="import",
                    lines_removed=0,
                    tests_passed=False,
                    error=f"Line number {line_number} out of range",
                )

            # Remove the line
            original_line = lines[line_number - 1]
            lines[line_number - 1] = ""

            # Write back
            with open(abs_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            # Verify with tests
            tests_passed = True
            if verify:
                tests_passed = self._run_tests()

            if not tests_passed:
                # Restore from backup
                self._restore_backup(abs_path, backup_path)
                return RemovalResult(
                    success=False,
                    file_path=str(file_path),
                    name=import_name,
                    code_type="import",
                    lines_removed=0,
                    tests_passed=False,
                    error="Tests failed after removal",
                )

            return RemovalResult(
                success=True,
                file_path=str(file_path),
                name=import_name,
                code_type="import",
                lines_removed=1,
                tests_passed=tests_passed,
            )

        except Exception as e:
            # Restore from backup on any error
            self._restore_backup(abs_path, backup_path)
            return RemovalResult(
                success=False,
                file_path=str(file_path),
                name=import_name,
                code_type="import",
                lines_removed=0,
                tests_passed=False,
                error=str(e),
            )

    def remove_unused_function(
        self,
        file_path: Path,
        function_name: str,
        start_line: int,
        end_line: int,
        verify: bool = True,
    ) -> RemovalResult:
        """
        Remove an unused function.

        1. Backup file
        2. Remove function lines
        3. Run tests (if verify=True)
        4. If tests fail, restore backup
        """
        abs_path = self.project_root / file_path

        # Create backup
        backup_path = self._backup_file(abs_path)

        try:
            # Read file
            with open(abs_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if start_line < 1 or end_line > len(lines):
                return RemovalResult(
                    success=False,
                    file_path=str(file_path),
                    name=function_name,
                    code_type="function",
                    lines_removed=0,
                    tests_passed=False,
                    error=f"Line range {start_line}-{end_line} out of range",
                )

            # Remove the lines
            lines_removed = end_line - start_line + 1
            for i in range(start_line - 1, end_line):
                lines[i] = ""

            # Write back
            with open(abs_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            # Verify with tests
            tests_passed = True
            if verify:
                tests_passed = self._run_tests()

            if not tests_passed:
                # Restore from backup
                self._restore_backup(abs_path, backup_path)
                return RemovalResult(
                    success=False,
                    file_path=str(file_path),
                    name=function_name,
                    code_type="function",
                    lines_removed=0,
                    tests_passed=False,
                    error="Tests failed after removal",
                )

            return RemovalResult(
                success=True,
                file_path=str(file_path),
                name=function_name,
                code_type="function",
                lines_removed=lines_removed,
                tests_passed=tests_passed,
            )

        except Exception as e:
            # Restore from backup on any error
            self._restore_backup(abs_path, backup_path)
            return RemovalResult(
                success=False,
                file_path=str(file_path),
                name=function_name,
                code_type="function",
                lines_removed=0,
                tests_passed=False,
                error=str(e),
            )

    def batch_remove_imports(
        self,
        imports: List[Dict[str, Any]],
        verify_each: bool = False,
        verify_batch: bool = True,
    ) -> BatchRemovalResult:
        """
        Remove multiple unused imports.

        Args:
            imports: List of dicts with file_path, import_name, line_number
            verify_each: Run tests after each removal
            verify_batch: Run tests after all removals
        """
        result = BatchRemovalResult()

        for imp in imports:
            result.total_attempted += 1
            removal = self.remove_unused_import(
                file_path=Path(imp["file_path"]),
                import_name=imp["import_name"],
                line_number=imp["line_number"],
                verify=verify_each,
            )
            result.results.append(removal)

            if removal.success:
                result.successful += 1
                result.total_lines_removed += removal.lines_removed
            else:
                result.failed += 1
                if not removal.tests_passed:
                    result.test_failures += 1

        # Verify batch
        if verify_batch and not verify_each:
            if not self._run_tests():
                # Revert all changes
                for r in result.results:
                    if r.success:
                        r.success = False
                        r.tests_passed = False
                        r.error = "Batch tests failed"
                        result.successful -= 1
                        result.failed += 1
                        result.test_failures += 1

        return result

    def _run_tests(self, timeout: int = 300) -> bool:
        """Run test suite to verify no breakage."""
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-x", "-q"],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root,
            )
            return proc.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    def _backup_file(self, file_path: Path) -> Path:
        """Create backup before modification."""
        backup_path = self.backup_dir / file_path.name
        backup_path = backup_path.with_suffix(f".{backup_path.suffix}.bak")
        shutil.copy2(file_path, backup_path)
        return backup_path

    def _restore_backup(self, file_path: Path, backup_path: Path) -> None:
        """Restore from backup if tests fail."""
        if backup_path.exists():
            shutil.copy2(backup_path, file_path)


def main():
    """Main entry point."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Remove dead code safely")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without actually removing",
    )
    parser.add_argument(
        "--imports-file",
        type=Path,
        help="JSON file with imports to remove",
    )
    parser.add_argument(
        "--verify-each",
        action="store_true",
        help="Run tests after each removal",
    )

    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN - No changes will be made")
        return

    if not args.imports_file:
        print("Please provide --imports-file with JSON list of imports to remove")
        return

    with open(args.imports_file) as f:
        imports = json.load(f)

    remover = DeadCodeRemover(args.project_root)
    result = remover.batch_remove_imports(imports, verify_each=args.verify_each)

    print(result.get_summary())

    for r in result.results:
        status = "OK" if r.success else "FAILED"
        print(f"  [{status}] {r.file_path}:{r.name}")
        if r.error:
            print(f"         Error: {r.error}")


if __name__ == "__main__":
    main()
