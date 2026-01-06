"""
Markdown exporter for CV Generator.

Generates a Markdown file from CV data.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from .base import Exporter, ExportResult, register_exporter

logger = logging.getLogger(__name__)


@register_exporter
class MarkdownExporter(Exporter):
    """
    Export CV data to Markdown format.

    Creates a plain text Markdown file with the CV content.
    """

    @property
    def format_name(self) -> str:
        return "md"

    @property
    def file_extension(self) -> str:
        return "md"

    def export(
        self,
        cv_data: Dict[str, Any],
        output_dir: Path,
        profile_name: str,
        lang: str,
        **_opts: Any
    ) -> ExportResult:
        """
        Export CV data to Markdown.

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

            # Render Markdown content
            md_content = self._render_markdown(cv_data, profile_name, lang)

            # Write to file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            logger.info(f"✅ Markdown exported: {output_path}")
            return ExportResult(
                format_name=self.format_name,
                success=True,
                output_path=output_path
            )
        except Exception as e:
            logger.error(f"Markdown export failed: {e}")
            return ExportResult(
                format_name=self.format_name,
                success=False,
                error=str(e)
            )

    def _render_markdown(
        self,
        cv_data: Dict[str, Any],
        profile_name: str,
        lang: str
    ) -> str:
        """Render CV data to Markdown string."""
        lines: List[str] = []

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

        # Header
        lines.append(f"# {full_name}")
        lines.append("")

        if title:
            lines.append(f"**{title}**")
            lines.append("")

        # Contact info
        contact_parts = []
        if email:
            contact_parts.append(f"📧 {email}")
        if phone_formatted:
            contact_parts.append(f"📞 {phone_formatted}")
        if location_str:
            contact_parts.append(f"📍 {location_str}")

        if contact_parts:
            lines.append(" | ".join(contact_parts))
            lines.append("")

        lines.append("---")
        lines.append("")

        # Add sections
        self._add_section_md(lines, cv_data, "experiences", "Experience", self._render_experience)
        self._add_section_md(lines, cv_data, "education", "Education", self._render_education)
        self._add_skills_md(lines, cv_data)
        self._add_section_md(lines, cv_data, "projects", "Projects", self._render_project)
        self._add_languages_md(lines, cv_data)
        self._add_section_md(lines, cv_data, "publications", "Publications", self._render_publication)
        self._add_section_md(
            lines, cv_data, "workshop_and_certifications",
            "Certifications & Training", self._render_certification
        )

        return "\n".join(lines)

    def _add_section_md(
        self,
        lines: List[str],
        cv_data: Dict[str, Any],
        key: str,
        title: str,
        renderer
    ) -> None:
        """Add a section to the Markdown output."""
        items = cv_data.get(key, [])
        if not items:
            return

        lines.append(f"## {title}")
        lines.append("")

        for item in items:
            renderer(lines, item)

        lines.append("")

    def _render_experience(self, lines: List[str], item: Dict[str, Any]) -> None:
        """Render an experience entry."""
        role = item.get("role", "")
        institution = item.get("institution", "")
        duration = item.get("duration", "")
        description = item.get("description", "")

        if role:
            lines.append(f"### {role}")
        if institution or duration:
            meta_parts = []
            if institution:
                meta_parts.append(f"**{institution}**")
            if duration:
                meta_parts.append(f"*{duration}*")
            lines.append(" | ".join(meta_parts))
        if description:
            lines.append("")
            lines.append(description)
        lines.append("")

    def _render_education(self, lines: List[str], item: Dict[str, Any]) -> None:
        """Render an education entry."""
        institution = item.get("institution", "")
        area = item.get("area", "")
        study_type = item.get("studyType", "")
        duration = item.get("duration", item.get("startDate", ""))

        title = f"{study_type} in {area}" if study_type and area else area or study_type
        if title:
            lines.append(f"### {title}")
        if institution or duration:
            meta_parts = []
            if institution:
                meta_parts.append(f"**{institution}**")
            if duration:
                meta_parts.append(f"*{duration}*")
            lines.append(" | ".join(meta_parts))
        lines.append("")

    def _render_project(self, lines: List[str], item: Dict[str, Any]) -> None:
        """Render a project entry."""
        title = item.get("title", "")
        description = item.get("description", "")
        url = item.get("url", "")

        if title:
            if url:
                lines.append(f"### [{title}]({url})")
            else:
                lines.append(f"### {title}")
        if description:
            lines.append(description)
        lines.append("")

    def _render_publication(self, lines: List[str], item: Dict[str, Any]) -> None:
        """Render a publication entry."""
        title = item.get("title", item.get("name", ""))
        authors = item.get("authors", "")
        # Handle authors as list or string
        if isinstance(authors, list):
            authors = ", ".join(str(a) for a in authors if a)
        venue = item.get("venue", item.get("publisher", item.get("journal", "")))
        year = item.get("year", item.get("releaseDate", ""))
        url = item.get("url", item.get("URL", ""))

        if title:
            if url:
                lines.append(f"- [{title}]({url})")
            else:
                lines.append(f"- **{title}**")
            meta_parts = []
            if authors:
                meta_parts.append(str(authors))
            if venue:
                meta_parts.append(str(venue))
            if year:
                meta_parts.append(str(year))
            if meta_parts:
                lines.append(f"  *{', '.join(meta_parts)}*")

    def _render_certification(self, lines: List[str], item: Dict[str, Any]) -> None:
        """Render a certification entry."""
        name = item.get("name", item.get("title", ""))
        issuer = item.get("issuer", item.get("organization", ""))
        date = item.get("date", item.get("year", ""))

        if name:
            lines.append(f"- **{name}**")
            meta_parts = []
            if issuer:
                meta_parts.append(issuer)
            if date:
                meta_parts.append(str(date))
            if meta_parts:
                lines.append(f"  *{', '.join(meta_parts)}*")

    def _add_skills_md(self, lines: List[str], cv_data: Dict[str, Any]) -> None:
        """Add skills section to Markdown."""
        skills = cv_data.get("skills", {})
        if not skills:
            return

        lines.append("## Skills")
        lines.append("")

        for category, subcategories in skills.items():
            if not isinstance(subcategories, dict):
                continue

            lines.append(f"### {category}")
            lines.append("")

            for subcat_name, skill_list in subcategories.items():
                if not isinstance(skill_list, list):
                    continue

                skill_names = []
                for skill in skill_list:
                    if isinstance(skill, dict):
                        name = skill.get("short_name") or skill.get("long_name", "")
                        if name:
                            skill_names.append(name)

                if skill_names:
                    lines.append(f"**{subcat_name}:** {', '.join(skill_names)}")

            lines.append("")

    def _add_languages_md(self, lines: List[str], cv_data: Dict[str, Any]) -> None:
        """Add languages section to Markdown."""
        languages = cv_data.get("languages", [])
        if not languages:
            return

        lines.append("## Languages")
        lines.append("")

        for lang_item in languages:
            if isinstance(lang_item, dict):
                name = lang_item.get("language", lang_item.get("name", ""))
                level = lang_item.get("fluency", lang_item.get("level", ""))
                if name:
                    display = f"- **{name}**: {level}" if level else f"- {name}"
                    lines.append(display)

        lines.append("")
