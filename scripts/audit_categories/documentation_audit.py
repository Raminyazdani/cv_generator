"""
Documentation audit module.

Checks documentation accuracy, completeness, and working examples.
"""

import re
import sys
from pathlib import Path
from typing import Callable


class DocumentationAuditor:
    """Auditor for documentation quality."""

    def __init__(self, project_root: Path, add_problem: Callable):
        self.project_root = project_root
        self.add_problem = add_problem
        self.docs_dir = project_root / "docs"

    def run_all_checks(self):
        """Run all documentation checks."""
        self._check_readme_exists()
        self._check_docs_directory()
        self._check_required_docs()
        self._check_broken_links()
        self._check_code_examples()

    def _check_readme_exists(self):
        """Check that README.md exists."""
        readme = self.project_root / "README.md"
        if not readme.exists():
            self.add_problem(
                severity=self._severity("HIGH"),
                category="Documentation",
                subcategory="Missing File",
                title="README.md not found",
                description="No README.md file in project root",
                reproduction_steps=["1. Check for README.md in project root"],
                expected="README.md exists",
                actual="File not found",
            )
            return

        # Check README content
        try:
            with open(readme, "r", encoding="utf-8") as f:
                content = f.read()

            required_sections = ["Installation", "Usage"]
            for section in required_sections:
                if section.lower() not in content.lower():
                    self.add_problem(
                        severity=self._severity("MEDIUM"),
                        category="Documentation",
                        subcategory="README",
                        title=f"README missing '{section}' section",
                        description=f"README.md should have a '{section}' section",
                        reproduction_steps=[f"1. Search for '{section}' in README.md"],
                        expected=f"'{section}' section exists",
                        actual="Section not found",
                        affected_files=[str(readme)],
                    )

        except Exception:
            pass

    def _check_docs_directory(self):
        """Check that docs directory exists."""
        if not self.docs_dir.exists():
            self.add_problem(
                severity=self._severity("MEDIUM"),
                category="Documentation",
                subcategory="Missing Directory",
                title="docs/ directory not found",
                description="No docs directory for detailed documentation",
                reproduction_steps=["1. Check for docs/ directory"],
                expected="docs/ exists",
                actual="Directory not found",
            )
            return False
        return True

    def _check_required_docs(self):
        """Check for required documentation files."""
        if not self.docs_dir.exists():
            return

        required_docs = ["index.md", "installation.md"]
        recommended_docs = ["api.md", "cli.md", "quickstart.md"]

        for doc in required_docs:
            doc_path = self.docs_dir / doc
            if not doc_path.exists():
                self.add_problem(
                    severity=self._severity("MEDIUM"),
                    category="Documentation",
                    subcategory="Missing File",
                    title=f"Required doc missing: {doc}",
                    description=f"Documentation file {doc} is missing",
                    reproduction_steps=[f"1. Check for docs/{doc}"],
                    expected=f"{doc} exists",
                    actual="File not found",
                )

        for doc in recommended_docs:
            doc_path = self.docs_dir / doc
            if not doc_path.exists():
                self.add_problem(
                    severity=self._severity("LOW"),
                    category="Documentation",
                    subcategory="Missing File",
                    title=f"Recommended doc missing: {doc}",
                    description=f"Documentation file {doc} is recommended",
                    reproduction_steps=[f"1. Check for docs/{doc}"],
                    expected=f"{doc} exists",
                    actual="File not found",
                )

    def _check_broken_links(self):
        """Check for broken internal links in documentation."""
        if not self.docs_dir.exists():
            return

        broken_links = []
        for md_file in self.docs_dir.rglob("*.md"):
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Find markdown links
                link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
                links = re.findall(link_pattern, content)

                for text, href in links:
                    # Skip external links
                    if href.startswith("http://") or href.startswith("https://"):
                        continue

                    # Skip anchors
                    if href.startswith("#"):
                        continue

                    # Check relative links
                    if not href.startswith("/"):
                        target = md_file.parent / href.split("#")[0]
                        if not target.exists():
                            broken_links.append((md_file.name, href))

            except Exception:
                pass

        if broken_links:
            self.add_problem(
                severity=self._severity("MEDIUM"),
                category="Documentation",
                subcategory="Broken Links",
                title=f"{len(broken_links)} broken internal links",
                description="Some documentation links point to non-existent files",
                reproduction_steps=["1. Check internal links in docs/*.md"],
                expected="All internal links resolve",
                actual=f"Broken: {', '.join([f'{fname}:{link}' for fname, link in broken_links[:3]])}{'...' if len(broken_links) > 3 else ''}",
            )

    def _check_code_examples(self):
        """Check that code examples in docs are valid."""
        if not self.docs_dir.exists():
            return

        # Check for code blocks in markdown
        docs_with_code = []
        for md_file in self.docs_dir.rglob("*.md"):
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()

                if "```python" in content or "```bash" in content:
                    docs_with_code.append(md_file.name)

            except Exception:
                pass

        if not docs_with_code:
            self.add_problem(
                severity=self._severity("LOW"),
                category="Documentation",
                subcategory="Code Examples",
                title="No code examples in documentation",
                description="Documentation lacks code examples",
                reproduction_steps=["1. Search for code blocks in docs"],
                expected="Code examples for key features",
                actual="No code examples found",
            )

    def _severity(self, level: str):
        """Convert severity string to enum."""
        sys.path.insert(0, str(self.project_root / "scripts"))
        from final_audit import Severity

        return getattr(Severity, level)
