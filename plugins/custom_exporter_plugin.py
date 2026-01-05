"""
Custom Exporter Plugin for CV Generator.

This plugin demonstrates how to create a custom export format (JSON Resume).
It shows how to:
1. Create a custom exporter class
2. Register the exporter with the system
3. Transform CV data to a different format

The JSON Resume format is a standardized JSON schema for resumes/CVs.
See: https://jsonresume.org/

To use this plugin:
1. Place in <repository>/plugins/ or ~/.cv_generator/plugins/
2. Export CVs using: cvgen export --format jsonresume --name <profile>

Example output:
{
    "basics": {
        "name": "Ramin Yazdani",
        "label": "Data Scientist",
        "email": "user@example.com",
        ...
    },
    "work": [...],
    "education": [...],
    ...
}
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from cv_generator.exporters.base import Exporter, ExportResult, register_exporter

logger = logging.getLogger(__name__)


@register_exporter
class JsonResumeExporter(Exporter):
    """
    Exporter for JSON Resume format.

    Converts CV Generator's JSON format to the standard JSON Resume schema.
    This allows CVs to be used with JSON Resume-compatible tools and viewers.
    """

    @property
    def format_name(self) -> str:
        """Return the format name."""
        return "jsonresume"

    @property
    def file_extension(self) -> str:
        """Return the file extension."""
        return "json"

    def export(
        self,
        cv_data: Dict[str, Any],
        output_dir: Path,
        profile_name: str,
        lang: str,
        **opts: Any
    ) -> ExportResult:
        """
        Export CV data to JSON Resume format.

        Args:
            cv_data: Dictionary containing CV data.
            output_dir: Directory to write output files.
            profile_name: Name of the CV profile.
            lang: Language code.
            **opts: Additional options:
                - indent: JSON indentation (default: 2)
                - include_meta: Include metadata section (default: True)

        Returns:
            ExportResult with success status and output path.
        """
        try:
            # Transform to JSON Resume format
            json_resume = self._transform(cv_data, profile_name, lang)

            # Get output path
            output_path = self.get_output_path(output_dir, profile_name, lang)

            # Write JSON file
            indent = opts.get("indent", 2)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(json_resume, f, indent=indent, ensure_ascii=False)

            logger.info(f"Exported JSON Resume: {output_path}")

            return ExportResult(
                format_name=self.format_name,
                success=True,
                output_path=output_path,
            )

        except Exception as e:
            logger.error(f"JSON Resume export failed: {e}")
            return ExportResult(
                format_name=self.format_name,
                success=False,
                error=str(e),
            )

    def _transform(
        self,
        cv_data: Dict[str, Any],
        profile_name: str,
        lang: str
    ) -> Dict[str, Any]:
        """
        Transform CV Generator format to JSON Resume format.

        Args:
            cv_data: CV Generator format data.
            profile_name: Profile name.
            lang: Language code.

        Returns:
            JSON Resume format data.
        """
        json_resume: Dict[str, Any] = {}

        # Transform basics section
        json_resume["basics"] = self._transform_basics(cv_data)

        # Transform work experience
        json_resume["work"] = self._transform_work(cv_data)

        # Transform education
        json_resume["education"] = self._transform_education(cv_data)

        # Transform skills
        json_resume["skills"] = self._transform_skills(cv_data)

        # Transform languages
        json_resume["languages"] = self._transform_languages(cv_data)

        # Transform publications
        json_resume["publications"] = self._transform_publications(cv_data)

        # Transform projects
        json_resume["projects"] = self._transform_projects(cv_data)

        # Transform certificates
        json_resume["certificates"] = self._transform_certificates(cv_data)

        # Add metadata
        json_resume["meta"] = {
            "canonical": "https://jsonresume.org/schema",
            "version": "v1.0.0",
            "lastModified": "",  # Could be filled by the generator
            "source": "cv_generator",
            "profile": profile_name,
            "language": lang,
        }

        return json_resume

    def _transform_basics(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform basics section."""
        basics_list = cv_data.get("basics", [])
        if not basics_list:
            return {}

        basics = basics_list[0] if isinstance(basics_list, list) else basics_list

        result: Dict[str, Any] = {}

        # Name
        fname = basics.get("fname", "")
        lname = basics.get("lname", "")
        result["name"] = f"{fname} {lname}".strip()

        # Label (job title)
        label = basics.get("label", [])
        if isinstance(label, list):
            result["label"] = " | ".join(label)
        else:
            result["label"] = str(label)

        # Contact info
        result["email"] = basics.get("email", "")

        phone = basics.get("phone", {})
        if isinstance(phone, dict):
            result["phone"] = phone.get("formatted", "")
        else:
            result["phone"] = str(phone)

        # Location
        location_list = basics.get("location", [])
        if location_list:
            loc = location_list[0] if isinstance(location_list, list) else location_list
            result["location"] = {
                "city": loc.get("city", ""),
                "region": loc.get("region", ""),
                "postalCode": loc.get("postalCode", ""),
                "countryCode": loc.get("country", ""),
            }

        # Profiles (social links)
        profiles = cv_data.get("profiles", [])
        result["profiles"] = []
        for profile in profiles:
            result["profiles"].append({
                "network": profile.get("network", ""),
                "username": profile.get("username", ""),
                "url": profile.get("url", ""),
            })

        return result

    def _transform_work(self, cv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform work experience section."""
        experiences = cv_data.get("experiences", [])
        result = []

        for exp in experiences:
            work_item = {
                "name": exp.get("institution", ""),
                "position": exp.get("role", ""),
                "location": exp.get("location", ""),
                "summary": exp.get("primaryFocus", ""),
                "description": exp.get("description", ""),
            }

            # Parse duration if available
            duration = exp.get("duration", "")
            if duration:
                work_item["startDate"] = ""  # Would need parsing
                work_item["endDate"] = ""

            result.append(work_item)

        return result

    def _transform_education(self, cv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform education section."""
        education = cv_data.get("education", [])
        result = []

        for edu in education:
            edu_item = {
                "institution": edu.get("institution", ""),
                "area": edu.get("area", ""),
                "studyType": edu.get("studyType", ""),
                "startDate": edu.get("startDate", ""),
                "endDate": edu.get("endDate", ""),
            }

            # GPA if available
            if "gpa" in edu:
                edu_item["score"] = str(edu["gpa"])

            result.append(edu_item)

        return result

    def _transform_skills(self, cv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform skills section."""
        skills_data = cv_data.get("skills", {})
        result = []

        # Skills in CV Generator are nested: category -> subcategory -> items
        for category, subcategories in skills_data.items():
            if not isinstance(subcategories, dict):
                continue

            for subcategory, items in subcategories.items():
                if not isinstance(items, list):
                    continue

                keywords = []
                for item in items:
                    if isinstance(item, dict):
                        keywords.append(item.get("short_name", ""))
                    elif isinstance(item, str):
                        keywords.append(item)

                if keywords:
                    result.append({
                        "name": subcategory,
                        "level": "",
                        "keywords": keywords,
                    })

        return result

    def _transform_languages(self, cv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform languages section."""
        languages = cv_data.get("languages", [])
        result = []

        for lang in languages:
            result.append({
                "language": lang.get("language", ""),
                "fluency": lang.get("fluency", ""),
            })

        return result

    def _transform_publications(self, cv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform publications section."""
        publications = cv_data.get("publications", [])
        result = []

        for pub in publications:
            result.append({
                "name": pub.get("title", ""),
                "publisher": pub.get("journal", pub.get("venue", "")),
                "releaseDate": pub.get("date", pub.get("year", "")),
                "summary": pub.get("abstract", ""),
            })

        return result

    def _transform_projects(self, cv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform projects section."""
        projects = cv_data.get("projects", [])
        result = []

        for proj in projects:
            result.append({
                "name": proj.get("name", proj.get("title", "")),
                "description": proj.get("description", ""),
                "url": proj.get("url", ""),
            })

        return result

    def _transform_certificates(self, cv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform certificates section."""
        certs = cv_data.get("workshop_and_certifications", [])
        result = []

        for cert in certs:
            result.append({
                "name": cert.get("name", cert.get("title", "")),
                "issuer": cert.get("issuer", cert.get("organization", "")),
                "date": cert.get("date", ""),
            })

        return result


def register(registry, hook_manager):
    """
    Register plugin components.

    This function is called when the plugin is loaded.
    The exporter is auto-registered via the @register_exporter decorator
    when the module is imported.

    Args:
        registry: The SectionRegistry instance (not used here).
        hook_manager: The HookManager instance (not used here).
    """
    logger.info("Custom Exporter Plugin: JSON Resume exporter registered")
    logger.info("Usage: cvgen export --format jsonresume --name <profile>")


def unregister():
    """
    Clean up plugin resources.

    This function is called when the plugin is unloaded.
    """
    logger.info("Custom Exporter Plugin: Unloaded")
