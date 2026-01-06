"""
HTML exporter for CV Generator.

Generates a simple HTML preview of the CV with styling.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, PackageLoader, select_autoescape

from .base import Exporter, ExportResult, register_exporter

logger = logging.getLogger(__name__)


@register_exporter
class HTMLExporter(Exporter):
    """
    Export CV data to HTML format.

    Creates a styled HTML file suitable for browser preview.
    """

    @property
    def format_name(self) -> str:
        return "html"

    def export(
        self,
        cv_data: Dict[str, Any],
        output_dir: Path,
        profile_name: str,
        lang: str,
        **_opts: Any
    ) -> ExportResult:
        """
        Export CV data to HTML.

        Args:
            cv_data: Dictionary containing CV data.
            output_dir: Directory to write output files.
            profile_name: Name of the CV profile.
            lang: Language code.
            **opts: Additional options (unused).

        Returns:
            ExportResult with success status and output path.
        """
        try:
            output_path = self.get_output_path(output_dir, profile_name, lang)

            # Render HTML content
            html_content = self._render_html(cv_data, profile_name, lang)

            # Write to file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.info(f"✅ HTML exported: {output_path}")
            return ExportResult(
                format_name=self.format_name,
                success=True,
                output_path=output_path
            )
        except Exception as e:
            logger.error(f"HTML export failed: {e}")
            return ExportResult(
                format_name=self.format_name,
                success=False,
                error=str(e)
            )

    def _render_html(
        self,
        cv_data: Dict[str, Any],
        profile_name: str,
        lang: str
    ) -> str:
        """Render CV data to HTML string."""
        # Try to use Jinja2 template if available
        try:
            env = Environment(
                loader=PackageLoader("cv_generator", "export_templates"),
                autoescape=select_autoescape(["html", "xml"])
            )
            template = env.get_template("cv.html")
            return template.render(
                cv=cv_data,
                profile_name=profile_name,
                lang=lang,
                is_rtl=lang == "fa"
            )
        except Exception:
            # Fall back to pure Python rendering
            return self._render_html_fallback(cv_data, profile_name, lang)

    def _render_html_fallback(
        self,
        cv_data: Dict[str, Any],
        profile_name: str,
        lang: str
    ) -> str:
        """Fallback HTML rendering without templates."""
        is_rtl = lang == "fa"
        direction = "rtl" if is_rtl else "ltr"

        # Extract basic info
        basics = cv_data.get("basics", [{}])
        basic = basics[0] if basics else {}
        fname = basic.get("fname", "")
        lname = basic.get("lname", "")
        full_name = f"{fname} {lname}".strip() or profile_name
        email = basic.get("email", "")
        phone = basic.get("phone", {})
        phone_formatted = phone.get("formatted", "") if isinstance(phone, dict) else str(phone)
        labels = basic.get("label", [])
        if isinstance(labels, list):
            title = ", ".join(str(label) for label in labels if label)
        else:
            title = str(labels) if labels else ""

        # Location
        locations = basic.get("location", [])
        location = locations[0] if locations else {}
        location_str = ", ".join(filter(None, [
            location.get("city", ""),
            location.get("region", ""),
            location.get("country", "")
        ]))

        # Build HTML
        lines = [
            "<!DOCTYPE html>",
            f'<html lang="{lang}" dir="{direction}">',
            "<head>",
            '  <meta charset="UTF-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f"  <title>CV - {self._escape_html(full_name)}</title>",
            "  <style>",
            "    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; ",
            f"           line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; direction: {direction}; }}",
            "    h1 { color: #2c3e50; margin-bottom: 5px; }",
            "    h2 { color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 5px; margin-top: 30px; }",
            "    h3 { color: #2c3e50; margin-bottom: 5px; }",
            "    .header { margin-bottom: 30px; }",
            "    .contact { color: #7f8c8d; margin-bottom: 20px; }",
            "    .title { color: #3498db; font-size: 1.2em; margin-bottom: 10px; }",
            "    .entry { margin-bottom: 20px; }",
            "    .entry-title { font-weight: bold; }",
            "    .entry-meta { color: #7f8c8d; font-size: 0.9em; }",
            "    .skills-category { margin-bottom: 15px; }",
            "    .skills-list { display: flex; flex-wrap: wrap; gap: 8px; list-style: none; padding: 0; }",
            "    .skill-item { background: #ecf0f1; padding: 4px 10px; border-radius: 4px; font-size: 0.9em; }",
            "  </style>",
            "</head>",
            "<body>",
            '  <header class="header">',
            f"    <h1>{self._escape_html(full_name)}</h1>",
        ]

        if title:
            lines.append(f'    <div class="title">{self._escape_html(title)}</div>')

        contact_parts = []
        if email:
            contact_parts.append(self._escape_html(email))
        if phone_formatted:
            contact_parts.append(self._escape_html(phone_formatted))
        if location_str:
            contact_parts.append(self._escape_html(location_str))

        if contact_parts:
            lines.append(f'    <div class="contact">{" • ".join(contact_parts)}</div>')

        lines.append("  </header>")
        lines.append("  <main>")

        # Add sections
        self._add_section_html(lines, cv_data, "experiences", "Experience", self._render_experience)
        self._add_section_html(lines, cv_data, "education", "Education", self._render_education)
        self._add_skills_html(lines, cv_data)
        self._add_section_html(lines, cv_data, "projects", "Projects", self._render_project)
        self._add_languages_html(lines, cv_data)

        lines.extend([
            "  </main>",
            "</body>",
            "</html>"
        ])

        return "\n".join(lines)

    def _add_section_html(
        self,
        lines: List[str],
        cv_data: Dict[str, Any],
        key: str,
        title: str,
        renderer
    ) -> None:
        """Add a section to the HTML output."""
        items = cv_data.get(key, [])
        if not items:
            return

        lines.append("    <section>")
        lines.append(f"      <h2>{self._escape_html(title)}</h2>")

        for item in items:
            renderer(lines, item)

        lines.append("    </section>")

    def _render_experience(self, lines: List[str], item: Dict[str, Any]) -> None:
        """Render an experience entry."""
        role = item.get("role", "")
        institution = item.get("institution", "")
        duration = item.get("duration", "")
        description = item.get("description", "")

        lines.append('      <div class="entry">')
        lines.append(f'        <div class="entry-title">{self._escape_html(role)}</div>')
        if institution or duration:
            meta_parts = []
            if institution:
                meta_parts.append(self._escape_html(institution))
            if duration:
                meta_parts.append(self._escape_html(duration))
            lines.append(f'        <div class="entry-meta">{" | ".join(meta_parts)}</div>')
        if description:
            lines.append(f"        <p>{self._escape_html(description)}</p>")
        lines.append("      </div>")

    def _render_education(self, lines: List[str], item: Dict[str, Any]) -> None:
        """Render an education entry."""
        institution = item.get("institution", "")
        area = item.get("area", "")
        study_type = item.get("studyType", "")
        duration = item.get("duration", item.get("startDate", ""))

        lines.append('      <div class="entry">')
        title = f"{study_type} in {area}" if study_type and area else area or study_type
        lines.append(f'        <div class="entry-title">{self._escape_html(title)}</div>')
        if institution or duration:
            meta_parts = []
            if institution:
                meta_parts.append(self._escape_html(institution))
            if duration:
                meta_parts.append(self._escape_html(duration))
            lines.append(f'        <div class="entry-meta">{" | ".join(meta_parts)}</div>')
        lines.append("      </div>")

    def _render_project(self, lines: List[str], item: Dict[str, Any]) -> None:
        """Render a project entry."""
        title = item.get("title", "")
        description = item.get("description", "")
        url = item.get("url", "")

        lines.append('      <div class="entry">')
        if url:
            lines.append(f'        <div class="entry-title"><a href="{self._escape_html(url)}">{self._escape_html(title)}</a></div>')
        else:
            lines.append(f'        <div class="entry-title">{self._escape_html(title)}</div>')
        if description:
            lines.append(f"        <p>{self._escape_html(description)}</p>")
        lines.append("      </div>")

    def _add_skills_html(self, lines: List[str], cv_data: Dict[str, Any]) -> None:
        """Add skills section to HTML."""
        skills = cv_data.get("skills", {})
        if not skills:
            return

        lines.append("    <section>")
        lines.append("      <h2>Skills</h2>")

        for category, subcategories in skills.items():
            if not isinstance(subcategories, dict):
                continue

            lines.append('      <div class="skills-category">')
            lines.append(f"        <h3>{self._escape_html(category)}</h3>")

            all_skills = []
            for subcat_name, skill_list in subcategories.items():
                if isinstance(skill_list, list):
                    for skill in skill_list:
                        if isinstance(skill, dict):
                            name = skill.get("short_name") or skill.get("long_name", "")
                            if name:
                                all_skills.append(name)

            if all_skills:
                lines.append('        <ul class="skills-list">')
                for skill in all_skills:
                    lines.append(f'          <li class="skill-item">{self._escape_html(skill)}</li>')
                lines.append("        </ul>")

            lines.append("      </div>")

        lines.append("    </section>")

    def _add_languages_html(self, lines: List[str], cv_data: Dict[str, Any]) -> None:
        """Add languages section to HTML."""
        languages = cv_data.get("languages", [])
        if not languages:
            return

        lines.append("    <section>")
        lines.append("      <h2>Languages</h2>")
        lines.append('      <ul class="skills-list">')

        for lang_item in languages:
            if isinstance(lang_item, dict):
                name = lang_item.get("language", lang_item.get("name", ""))
                level = lang_item.get("fluency", lang_item.get("level", ""))
                display = f"{name} ({level})" if level else name
                lines.append(f'        <li class="skill-item">{self._escape_html(display)}</li>')

        lines.append("      </ul>")
        lines.append("    </section>")

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )
