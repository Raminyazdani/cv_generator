"""
Web UI audit module.

Checks web routes, forms, and UI functionality.
"""

import sys
from pathlib import Path
from typing import Callable


class WebUIAuditor:
    """Auditor for web UI functionality."""

    def __init__(self, project_root: Path, add_problem: Callable):
        self.project_root = project_root
        self.add_problem = add_problem
        self.web_module = project_root / "src" / "cv_generator" / "web.py"

    def run_all_checks(self):
        """Run all web UI checks."""
        self._check_web_module_exists()
        self._check_flask_app()
        self._check_routes()
        self._check_templates()
        self._check_csrf_protection()
        self._check_error_handlers()

    def _check_web_module_exists(self):
        """Check that web module exists."""
        if not self.web_module.exists():
            self.add_problem(
                severity=self._severity("HIGH"),
                category="Web UI",
                subcategory="Missing Module",
                title="Web module not found",
                description="The web.py module is missing",
                reproduction_steps=["1. Check for src/cv_generator/web.py"],
                expected="web.py exists",
                actual="File not found",
                affected_files=[str(self.web_module)],
            )
            return False
        return True

    def _check_flask_app(self):
        """Check Flask app configuration."""
        if not self.web_module.exists():
            return

        try:
            with open(self.web_module, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for Flask import
            if "from flask import" not in content and "import flask" not in content:
                self.add_problem(
                    severity=self._severity("CRITICAL"),
                    category="Web UI",
                    subcategory="Missing Import",
                    title="Flask not imported",
                    description="Flask is not imported in web.py",
                    reproduction_steps=["1. Check imports in web.py"],
                    expected="Flask is imported",
                    actual="Import not found",
                    affected_files=[str(self.web_module)],
                )

            # Check for app creation
            if "Flask(" not in content:
                self.add_problem(
                    severity=self._severity("CRITICAL"),
                    category="Web UI",
                    subcategory="App Creation",
                    title="Flask app not created",
                    description="No Flask() app initialization found",
                    reproduction_steps=["1. Search for 'Flask(' in web.py"],
                    expected="Flask app is created",
                    actual="Flask() not found",
                    affected_files=[str(self.web_module)],
                )

        except Exception as e:
            self.add_problem(
                severity=self._severity("MEDIUM"),
                category="Web UI",
                subcategory="Parse Error",
                title="Cannot parse web.py",
                description=str(e),
                reproduction_steps=["1. Try to read web.py"],
                expected="File is readable",
                actual=f"Exception: {type(e).__name__}",
                affected_files=[str(self.web_module)],
                error_message=str(e),
            )

    def _check_routes(self):
        """Check that essential routes are defined."""
        if not self.web_module.exists():
            return

        try:
            with open(self.web_module, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for @app.route or @blueprint.route decorators
            if "@" not in content or "route" not in content:
                self.add_problem(
                    severity=self._severity("HIGH"),
                    category="Web UI",
                    subcategory="Routes",
                    title="No route decorators found",
                    description="No @route decorators in web.py",
                    reproduction_steps=["1. Search for '@' and 'route' in web.py"],
                    expected="Route decorators exist",
                    actual="No route decorators found",
                    affected_files=[str(self.web_module)],
                )

        except Exception:
            pass

    def _check_templates(self):
        """Check that template directory exists."""
        templates_dir = self.project_root / "src" / "cv_generator" / "templates"
        if not templates_dir.exists():
            self.add_problem(
                severity=self._severity("MEDIUM"),
                category="Web UI",
                subcategory="Templates",
                title="Templates directory not found",
                description="No templates directory in cv_generator module",
                reproduction_steps=["1. Check for src/cv_generator/templates/"],
                expected="Templates directory exists",
                actual="Directory not found",
            )
            return

        # Check for base template
        template_files = list(templates_dir.rglob("*.html"))
        if not template_files:
            self.add_problem(
                severity=self._severity("MEDIUM"),
                category="Web UI",
                subcategory="Templates",
                title="No HTML templates found",
                description="Templates directory has no .html files",
                reproduction_steps=["1. List .html files in templates/"],
                expected="HTML templates exist",
                actual="No .html files found",
            )

    def _check_csrf_protection(self):
        """Check for CSRF protection."""
        if not self.web_module.exists():
            return

        try:
            with open(self.web_module, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for CSRF protection
            has_csrf = any([
                "CSRFProtect" in content,
                "csrf" in content.lower(),
                "WTF" in content,
            ])

            # Check for POST/PUT/DELETE routes
            has_mutating_routes = any([
                'methods=["POST"]' in content,
                "methods=['POST']" in content,
                'methods=["PUT"]' in content,
                'methods=["DELETE"]' in content,
            ])

            if has_mutating_routes and not has_csrf:
                self.add_problem(
                    severity=self._severity("MEDIUM"),
                    category="Web UI",
                    subcategory="Security",
                    title="No CSRF protection detected",
                    description="POST routes exist but no CSRF protection found",
                    reproduction_steps=[
                        "1. Find POST routes in web.py",
                        "2. Check for CSRFProtect or similar",
                    ],
                    expected="CSRF protection for mutating routes",
                    actual="No CSRF protection found",
                    affected_files=[str(self.web_module)],
                    suggested_fix="Add Flask-WTF or similar CSRF protection",
                )

        except Exception:
            pass

    def _check_error_handlers(self):
        """Check for error handlers."""
        if not self.web_module.exists():
            return

        try:
            with open(self.web_module, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for error handlers
            if "@" in content and "errorhandler" in content:
                pass  # Error handlers exist
            else:
                self.add_problem(
                    severity=self._severity("LOW"),
                    category="Web UI",
                    subcategory="Error Handling",
                    title="No error handlers found",
                    description="No @errorhandler decorators in web.py",
                    reproduction_steps=["1. Search for 'errorhandler' in web.py"],
                    expected="Error handlers for 404, 500, etc.",
                    actual="No error handlers found",
                    affected_files=[str(self.web_module)],
                    suggested_fix="Add @app.errorhandler decorators",
                )

        except Exception:
            pass

    def _severity(self, level: str):
        """Convert severity string to enum."""
        sys.path.insert(0, str(self.project_root / "scripts"))
        from final_audit import Severity

        return getattr(Severity, level)
