"""
Security audit module.

Checks for security vulnerabilities and best practices.
"""

import re
import sys
from pathlib import Path
from typing import Callable


class SecurityAuditor:
    """Auditor for security considerations."""

    def __init__(self, project_root: Path, add_problem: Callable):
        self.project_root = project_root
        self.add_problem = add_problem
        self.src_dir = project_root / "src" / "cv_generator"

    def run_all_checks(self):
        """Run all security checks."""
        self._check_secret_key()
        self._check_sql_injection()
        self._check_path_traversal()
        self._check_hardcoded_secrets()
        self._check_debug_mode()

    def _check_secret_key(self):
        """Check that Flask secret key is not hardcoded."""
        web_module = self.src_dir / "web.py"
        if not web_module.exists():
            return

        try:
            with open(web_module, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for hardcoded secret key
            hardcoded_patterns = [
                r'secret_key\s*=\s*["\'][^"\']+["\']',
                r'SECRET_KEY\s*=\s*["\'][^"\']+["\']',
            ]

            for pattern in hardcoded_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Check if it's using environment variable
                    if "os.environ" not in match and "getenv" not in match:
                        if "dev" not in match.lower() and "example" not in match.lower():
                            self.add_problem(
                                severity=self._severity("HIGH"),
                                category="Security",
                                subcategory="Secret Key",
                                title="Hardcoded secret key detected",
                                description="Flask secret key appears to be hardcoded",
                                reproduction_steps=["1. Search for 'secret_key' in web.py"],
                                expected="Secret key from environment variable",
                                actual="Hardcoded secret key",
                                affected_files=[str(web_module)],
                                suggested_fix="Use os.environ.get('SECRET_KEY')",
                            )
                            break

        except Exception:
            pass

    def _check_sql_injection(self):
        """Check for potential SQL injection vulnerabilities."""
        if not self.src_dir.exists():
            return

        for py_file in self.src_dir.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for string formatting in SQL
                dangerous_patterns = [
                    r'execute\([^)]*%\s*\(',  # execute("..." % (...))
                    r'execute\([^)]*\.format\(',  # execute("...".format(...))
                    r'execute\([^)]*f["\']',  # execute(f"...")
                ]

                for pattern in dangerous_patterns:
                    if re.search(pattern, content):
                        self.add_problem(
                            severity=self._severity("CRITICAL"),
                            category="Security",
                            subcategory="SQL Injection",
                            title=f"Potential SQL injection in {py_file.name}",
                            description="SQL query uses string formatting instead of parameters",
                            reproduction_steps=[f"1. Check SQL queries in {py_file.name}"],
                            expected="Parameterized queries (cursor.execute(sql, params))",
                            actual="String formatting detected in SQL",
                            affected_files=[str(py_file)],
                            suggested_fix="Use parameterized queries",
                        )
                        break

            except Exception:
                pass

    def _check_path_traversal(self):
        """Check for potential path traversal vulnerabilities."""
        if not self.src_dir.exists():
            return

        for py_file in self.src_dir.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for user input in file paths without sanitization
                dangerous_patterns = [
                    r'open\([^)]*request\.',
                    r'Path\([^)]*request\.',
                ]

                for pattern in dangerous_patterns:
                    if re.search(pattern, content):
                        self.add_problem(
                            severity=self._severity("HIGH"),
                            category="Security",
                            subcategory="Path Traversal",
                            title=f"Potential path traversal in {py_file.name}",
                            description="User input may be used directly in file path",
                            reproduction_steps=[f"1. Check file operations in {py_file.name}"],
                            expected="Path sanitization before file operations",
                            actual="Direct use of request data in paths",
                            affected_files=[str(py_file)],
                            suggested_fix="Validate and sanitize file paths",
                        )
                        break

            except Exception:
                pass

    def _check_hardcoded_secrets(self):
        """Check for hardcoded passwords, API keys, etc."""
        if not self.src_dir.exists():
            return

        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded password"),
            (r'api_key\s*=\s*["\'][^"\']{16,}["\']', "Hardcoded API key"),
            (r'token\s*=\s*["\'][^"\']{16,}["\']', "Hardcoded token"),
        ]

        for py_file in self.src_dir.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                for pattern, issue_type in secret_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Skip if it looks like a placeholder
                        if "example" in match.lower() or "xxx" in match.lower():
                            continue
                        if "test" in match.lower() or "placeholder" in match.lower():
                            continue

                        self.add_problem(
                            severity=self._severity("HIGH"),
                            category="Security",
                            subcategory="Secrets",
                            title=f"{issue_type} in {py_file.name}",
                            description=f"Potential {issue_type.lower()} detected",
                            reproduction_steps=[f"1. Search for credentials in {py_file.name}"],
                            expected="Secrets from environment variables",
                            actual="Hardcoded secret detected",
                            affected_files=[str(py_file)],
                            suggested_fix="Use environment variables for secrets",
                        )
                        break

            except Exception:
                pass

    def _check_debug_mode(self):
        """Check that debug mode is not enabled in production code."""
        web_module = self.src_dir / "web.py"
        if not web_module.exists():
            return

        try:
            with open(web_module, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for debug=True
            if "debug=True" in content or "DEBUG = True" in content:
                # Check if it's conditional
                if "os.environ" not in content and "getenv" not in content:
                    self.add_problem(
                        severity=self._severity("MEDIUM"),
                        category="Security",
                        subcategory="Debug Mode",
                        title="Debug mode may be enabled",
                        description="Flask debug mode should not be hardcoded to True",
                        reproduction_steps=["1. Search for 'debug=True' in web.py"],
                        expected="Debug mode from environment variable",
                        actual="Debug mode appears hardcoded",
                        affected_files=[str(web_module)],
                        suggested_fix="Use os.environ.get('DEBUG', 'false').lower() == 'true'",
                    )

        except Exception:
            pass

    def _severity(self, level: str):
        """Convert severity string to enum."""
        sys.path.insert(0, str(self.project_root / "scripts"))
        from final_audit import Severity

        return getattr(Severity, level)
