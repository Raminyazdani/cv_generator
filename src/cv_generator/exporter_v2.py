"""
Lossless DB to JSON export engine for CV Generator.

This module implements a precision JSON export engine that reconstructs CV JSON
files from the normalized database. The exported JSON must exactly match the
original schema that LaTeX templates consume — same field names, same nesting,
same array structures, same key ordering.

Key features:
- Exports any (resume_key, lang_code) combination to complete JSON
- Produces JSON structurally identical to original imported file
- Preserves field names (fname, Pictures, startDate, etc.)
- Maintains section order (config, basics, profiles, etc.)
- Preserves null values and empty arrays
- Translates tags per language from tag_i18n

Usage:
    exporter = CVExporter(db_path)

    # Export to dict
    cv_data = exporter.export(resume_key="ramin_yazdani", lang_code="en")

    # Export to file
    exporter.export_to_file(resume_key, lang_code, output_path)

    # Export all variants for a person
    exporter.export_all_variants(resume_key, output_dir)

    # Export everything
    exporter.export_all(output_dir)
"""

import json
import logging
import sqlite3
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .export_mappings import (
    BASICS_FIELD_ORDER,
    CERTIFICATION_FIELD_ORDER,
    CERT_ISSUER_FIELD_ORDER,
    EDUCATION_FIELD_ORDER,
    EXPERIENCE_FIELD_ORDER,
    LANGUAGE_CERT_FIELD_ORDER,
    LANGUAGE_FIELD_ORDER,
    LOCATION_FIELD_ORDER,
    PHONE_FIELD_ORDER,
    PICTURE_FIELD_ORDER,
    PROFILE_FIELD_ORDER,
    PROFICIENCY_FIELD_ORDER,
    PROJECT_FIELD_ORDER,
    PUBLICATION_FIELD_ORDER,
    REFERENCE_FIELD_ORDER,
    SKILL_ITEM_FIELD_ORDER,
    build_ordered_cv,
    ordered_dict_from_mapping,
)

logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    """Result of exporting a single CV variant."""

    success: bool
    resume_key: str
    lang_code: str
    output_path: Optional[Path] = None

    # Export stats
    stats: Dict[str, int] = field(default_factory=dict)

    # Any warnings (non-fatal)
    warnings: List[str] = field(default_factory=list)

    # Error details if failed
    error: Optional[str] = None

    # Timing
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON/logging."""
        return {
            "success": self.success,
            "resume_key": self.resume_key,
            "lang_code": self.lang_code,
            "output_path": str(self.output_path) if self.output_path else None,
            "stats": self.stats,
            "warnings": self.warnings,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class ExportBatchResult:
    """Result of exporting multiple CV variants."""

    total_files: int
    successful: int
    failed: int
    results: List[ExportResult] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON/logging."""
        return {
            "total_files": self.total_files,
            "successful": self.successful,
            "failed": self.failed,
            "results": [r.to_dict() for r in self.results],
            "duration_ms": self.duration_ms,
        }


class CVExporter:
    """
    Lossless DB to JSON export engine.

    Usage:
        exporter = CVExporter(db_path)

        # Export to dict
        cv_data = exporter.export(resume_key="ramin_yazdani", lang_code="en")

        # Export to file
        exporter.export_to_file(resume_key, lang_code, output_path)

        # Export all variants for a person
        exporter.export_all_variants(resume_key, output_dir)

        # Export everything
        exporter.export_all(output_dir)
    """

    def __init__(self, db_path: Path):
        """Initialize exporter with database connection."""
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    def _connect(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def _close(self) -> None:
        """Close database connection if open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def export(
        self,
        resume_key: str,
        lang_code: str,
    ) -> dict:
        """
        Export a single CV variant to a dictionary.

        Args:
            resume_key: The person identifier (config.ID)
            lang_code: Language code (en, de, fa)

        Returns:
            Complete CV dictionary matching original JSON structure
        """
        start_time = time.time()

        try:
            conn = self._connect()

            # Get version_id for this resume_key and lang_code
            version_id = self._get_version_id(conn, resume_key, lang_code)
            if version_id is None:
                raise ValueError(
                    f"No resume version found for resume_key={resume_key}, lang_code={lang_code}"
                )

            logger.info(f"[EXPORT] Starting export: resume_key={resume_key}, lang={lang_code}")
            logger.info(f"[EXPORT] Found resume_version: id={version_id}")

            sections = {}

            # Export config block
            logger.info("[EXPORT] Exporting config block...")
            sections["config"] = self._export_config(resume_key, lang_code)

            # Export basics
            logger.info("[EXPORT] Exporting basics...")
            sections["basics"] = self._export_basics(conn, resume_key, version_id)

            # Export profiles
            logger.info("[EXPORT] Exporting profiles...")
            sections["profiles"] = self._export_profiles(conn, resume_key, version_id)

            # Export education
            logger.info("[EXPORT] Exporting education...")
            sections["education"] = self._export_education(conn, resume_key, version_id)

            # Export languages
            logger.info("[EXPORT] Exporting languages...")
            sections["languages"] = self._export_languages(conn, resume_key, version_id)

            # Export certifications
            logger.info("[EXPORT] Exporting certifications...")
            sections["workshop_and_certifications"] = self._export_certifications(
                conn, resume_key, version_id
            )

            # Export skills
            logger.info("[EXPORT] Exporting skills...")
            sections["skills"] = self._export_skills(conn, resume_key, version_id)

            # Export experiences
            logger.info("[EXPORT] Exporting experiences...")
            sections["experiences"] = self._export_experiences(conn, resume_key, version_id)

            # Export projects
            logger.info("[EXPORT] Exporting projects...")
            sections["projects"] = self._export_projects(conn, resume_key, version_id)

            # Export publications
            logger.info("[EXPORT] Exporting publications...")
            sections["publications"] = self._export_publications(conn, resume_key, version_id)

            # Export references
            logger.info("[EXPORT] Exporting references...")
            sections["references"] = self._export_references(conn, resume_key, version_id)

            # Build ordered CV
            result = build_ordered_cv(sections)

            duration = (time.time() - start_time) * 1000
            logger.info(f"[EXPORT] Complete: {len(sections)} sections exported in {duration:.0f}ms")

            return dict(result)

        finally:
            self._close()

    def export_to_file(
        self,
        resume_key: str,
        lang_code: str,
        output_path: Path,
        pretty: bool = True,
        ensure_ascii: bool = False,
    ) -> ExportResult:
        """
        Export to a JSON file.

        Args:
            resume_key: The person identifier
            lang_code: Language code
            output_path: Output file path
            pretty: Whether to format JSON with indentation
            ensure_ascii: Whether to escape non-ASCII characters

        Returns:
            ExportResult with success status and file path
        """
        start_time = time.time()
        output_path = Path(output_path)

        result = ExportResult(
            success=False,
            resume_key=resume_key,
            lang_code=lang_code,
        )

        try:
            cv_data = self.export(resume_key, lang_code)

            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write JSON file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    cv_data,
                    f,
                    indent=2 if pretty else None,
                    ensure_ascii=ensure_ascii,
                )

            result.success = True
            result.output_path = output_path

            size = output_path.stat().st_size
            logger.info(f"[EXPORT] Written to: {output_path} ({size:,} bytes)")

        except Exception as e:
            result.error = str(e)
            logger.error(f"[EXPORT] Error: {e}")

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    def export_all_variants(
        self,
        resume_key: str,
        output_dir: Path,
    ) -> List[ExportResult]:
        """
        Export all language variants for a person.

        Args:
            resume_key: The person identifier
            output_dir: Directory to write files to

        Returns:
            List of ExportResult for each variant
        """
        results = []
        output_dir = Path(output_dir)

        try:
            conn = self._connect()
            cursor = conn.cursor()

            # Get all language variants for this resume_key
            cursor.execute(
                "SELECT lang_code FROM resume_versions WHERE resume_key = ? ORDER BY lang_code",
                (resume_key,),
            )
            rows = cursor.fetchall()

            for row in rows:
                lang_code = row["lang_code"]

                # Determine output filename
                if lang_code == "en":
                    filename = f"{resume_key.replace('_', '')}.json"
                else:
                    filename = f"{resume_key.replace('_', '')}_{lang_code}.json"

                output_path = output_dir / filename

                # Export this variant (this will close and reopen connection)
                self._close()
                result = self.export_to_file(resume_key, lang_code, output_path)
                results.append(result)

        finally:
            self._close()

        return results

    def export_all(
        self,
        output_dir: Path,
    ) -> ExportBatchResult:
        """
        Export all CVs in the database.

        Args:
            output_dir: Directory to write files to

        Returns:
            ExportBatchResult with summary and individual results
        """
        start_time = time.time()
        output_dir = Path(output_dir)

        result = ExportBatchResult(
            total_files=0,
            successful=0,
            failed=0,
            results=[],
        )

        try:
            conn = self._connect()
            cursor = conn.cursor()

            # Get all resume_keys
            cursor.execute("SELECT DISTINCT resume_key FROM resume_sets ORDER BY resume_key")
            resume_keys = [row["resume_key"] for row in cursor.fetchall()]

            self._close()

            for resume_key in resume_keys:
                variant_results = self.export_all_variants(resume_key, output_dir)
                result.results.extend(variant_results)

            result.total_files = len(result.results)
            result.successful = sum(1 for r in result.results if r.success)
            result.failed = result.total_files - result.successful

        finally:
            self._close()

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    def list_available(self) -> List[Tuple[str, str]]:
        """
        List all available (resume_key, lang_code) combinations.

        Returns:
            List of (resume_key, lang_code) tuples
        """
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT resume_key, lang_code FROM resume_versions ORDER BY resume_key, lang_code"
            )
            return [(row["resume_key"], row["lang_code"]) for row in cursor.fetchall()]
        finally:
            self._close()

    # =========================================================================
    # Private helper methods
    # =========================================================================

    def _get_version_id(
        self, conn: sqlite3.Connection, resume_key: str, lang_code: str
    ) -> Optional[int]:
        """Get resume_version.id for a given resume_key and lang_code."""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM resume_versions WHERE resume_key = ? AND lang_code = ?",
            (resume_key, lang_code),
        )
        row = cursor.fetchone()
        return row["id"] if row else None

    def _export_config(self, resume_key: str, lang_code: str) -> OrderedDict:
        """Build the config block."""
        return OrderedDict([("lang", lang_code), ("ID", resume_key)])

    def _export_basics(
        self, conn: sqlite3.Connection, resume_key: str, version_id: int
    ) -> List[OrderedDict]:
        """Export basics section with all nested structures."""
        cursor = conn.cursor()

        # Get person and person_i18n
        cursor.execute(
            """
            SELECT p.*, pi.fname, pi.lname, pi.summary
            FROM persons p
            LEFT JOIN person_i18n pi ON p.id = pi.person_id AND pi.resume_version_id = ?
            WHERE p.resume_key = ?
            """,
            (version_id, resume_key),
        )
        person_row = cursor.fetchone()

        if not person_row:
            return []

        person_id = person_row["id"]

        # Build phone object
        phone = OrderedDict()
        if person_row["phone_country_code"] is not None:
            phone["countryCode"] = person_row["phone_country_code"]
        if person_row["phone_number"] is not None:
            phone["number"] = person_row["phone_number"]
        if person_row["phone_formatted"] is not None:
            phone["formatted"] = person_row["phone_formatted"]

        # If phone has no fields, leave it as empty dict or set to appropriate structure
        if not phone:
            phone = OrderedDict([("countryCode", None), ("number", None), ("formatted", None)])

        # Get labels
        cursor.execute(
            """
            SELECT pli.label_text
            FROM person_labels pl
            JOIN person_label_i18n pli ON pl.id = pli.label_id AND pli.resume_version_id = ?
            WHERE pl.person_id = ?
            ORDER BY pl.sort_order
            """,
            (version_id, person_id),
        )
        labels = [row["label_text"] for row in cursor.fetchall()]

        # Get locations
        cursor.execute(
            """
            SELECT pl.postal_code, pli.address, pli.city, pli.region, pli.country
            FROM person_locations pl
            LEFT JOIN person_location_i18n pli ON pl.id = pli.location_id AND pli.resume_version_id = ?
            WHERE pl.person_id = ?
            ORDER BY pl.sort_order
            """,
            (version_id, person_id),
        )
        locations = []
        for loc_row in cursor.fetchall():
            loc = ordered_dict_from_mapping(
                {
                    "address": loc_row["address"],
                    "postalCode": loc_row["postal_code"],
                    "city": loc_row["city"],
                    "region": loc_row["region"],
                    "country": loc_row["country"],
                },
                LOCATION_FIELD_ORDER,
            )
            locations.append(loc)

        # Get pictures
        cursor.execute(
            """
            SELECT type_of, url
            FROM person_pictures
            WHERE person_id = ?
            ORDER BY sort_order
            """,
            (person_id,),
        )
        pictures = []
        for pic_row in cursor.fetchall():
            pic = ordered_dict_from_mapping(
                {
                    "type_of": pic_row["type_of"],
                    "URL": pic_row["url"],
                },
                PICTURE_FIELD_ORDER,
            )
            pictures.append(pic)

        # Build basic object
        basic = ordered_dict_from_mapping(
            {
                "fname": person_row["fname"],
                "lname": person_row["lname"],
                "label": labels,
                "email": person_row["email"],
                "phone": phone if phone else None,
                "birthDate": person_row["birth_date"],
                "summary": person_row["summary"],
                "location": locations,
                "Pictures": pictures,
            },
            BASICS_FIELD_ORDER,
        )

        return [basic]

    def _export_profiles(
        self, conn: sqlite3.Connection, resume_key: str, version_id: int
    ) -> List[OrderedDict]:
        """Export profiles section."""
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT pa.username, pa.url, pa.uuid, pai.network_display
            FROM profile_accounts pa
            LEFT JOIN profile_account_i18n pai ON pa.id = pai.profile_account_id 
                AND pai.resume_version_id = ?
            WHERE pa.resume_key = ?
            ORDER BY pa.sort_order
            """,
            (version_id, resume_key),
        )

        profiles = []
        for row in cursor.fetchall():
            profile_data = {
                "network": row["network_display"],
                "username": row["username"],
                "url": row["url"],
            }
            # Only include uuid if it exists
            if row["uuid"]:
                profile_data["uuid"] = row["uuid"]

            profile = ordered_dict_from_mapping(profile_data, PROFILE_FIELD_ORDER, include_none=False)
            profiles.append(profile)

        return profiles

    def _export_education(
        self, conn: sqlite3.Connection, resume_key: str, version_id: int
    ) -> List[OrderedDict]:
        """Export education section with tags."""
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT ei.id, ei.start_date, ei.end_date, ei.end_date_text, ei.gpa, ei.logo_url,
                   edu.institution, edu.location, edu.area, edu.study_type
            FROM education_items ei
            LEFT JOIN education_i18n edu ON ei.id = edu.education_item_id 
                AND edu.resume_version_id = ?
            WHERE ei.resume_key = ?
            ORDER BY ei.sort_order
            """,
            (version_id, resume_key),
        )

        education = []
        for row in cursor.fetchall():
            # Get tags for this education item
            tags = self._get_tags_for_entity(conn, "education", row["id"], version_id)

            # Determine end date - use end_date_text if end_date is null
            end_date = row["end_date"]
            if end_date is None and row["end_date_text"]:
                end_date = row["end_date_text"]

            edu = ordered_dict_from_mapping(
                {
                    "institution": row["institution"],
                    "location": row["location"],
                    "area": row["area"],
                    "studyType": row["study_type"],
                    "startDate": row["start_date"],
                    "endDate": end_date,
                    "gpa": row["gpa"] if row["gpa"] else "",
                    "logo_url": row["logo_url"] if row["logo_url"] else "",
                    "type_key": tags,
                },
                EDUCATION_FIELD_ORDER,
            )
            education.append(edu)

        return education

    def _export_languages(
        self, conn: sqlite3.Connection, resume_key: str, version_id: int
    ) -> List[OrderedDict]:
        """Export languages section with nested certifications."""
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT sli.id, sli.proficiency_cefr,
                   sln.language_name, sln.proficiency_level, sln.proficiency_status
            FROM spoken_language_items sli
            LEFT JOIN spoken_language_i18n sln ON sli.id = sln.spoken_language_item_id 
                AND sln.resume_version_id = ?
            WHERE sli.resume_key = ?
            ORDER BY sli.sort_order
            """,
            (version_id, resume_key),
        )

        languages = []
        for lang_row in cursor.fetchall():
            lang_id = lang_row["id"]

            # Build proficiency object
            proficiency = ordered_dict_from_mapping(
                {
                    "level": lang_row["proficiency_level"],
                    "CEFR": lang_row["proficiency_cefr"],
                    "status": lang_row["proficiency_status"],
                },
                PROFICIENCY_FIELD_ORDER,
            )

            # Get certifications for this language
            cursor.execute(
                """
                SELECT slc.overall, slc.reading, slc.writing, slc.listening, slc.speaking,
                       slc.max_score, slc.min_score, slc.exam_date, slc.url,
                       sci.test_name, sci.organization
                FROM spoken_language_certs slc
                LEFT JOIN spoken_language_cert_i18n sci ON slc.id = sci.cert_id 
                    AND sci.resume_version_id = ?
                WHERE slc.spoken_language_item_id = ?
                ORDER BY slc.sort_order
                """,
                (version_id, lang_id),
            )

            certifications = []
            for cert_row in cursor.fetchall():
                cert_data = {
                    "test": cert_row["test_name"],
                    "organization": cert_row["organization"],
                    "overall": cert_row["overall"],
                    "reading": cert_row["reading"],
                    "writing": cert_row["writing"],
                    "listening": cert_row["listening"],
                    "speaking": cert_row["speaking"],
                    "examDate": cert_row["exam_date"],
                    "URL": cert_row["url"],
                }
                # Include maxScore/minScore when there are actual score values
                # This is a heuristic: if any score field has a value, include the scale fields
                has_scores = any([
                    cert_row["overall"] is not None,
                    cert_row["reading"] is not None,
                    cert_row["writing"] is not None,
                    cert_row["listening"] is not None,
                    cert_row["speaking"] is not None,
                ])
                if has_scores or cert_row["max_score"] is not None or cert_row["min_score"] is not None:
                    cert_data["maxScore"] = cert_row["max_score"]
                    cert_data["minScore"] = cert_row["min_score"]

                cert = ordered_dict_from_mapping(cert_data, LANGUAGE_CERT_FIELD_ORDER)
                certifications.append(cert)

            lang = ordered_dict_from_mapping(
                {
                    "language": lang_row["language_name"],
                    "proficiency": proficiency,
                    "certifications": certifications,
                },
                LANGUAGE_FIELD_ORDER,
            )
            languages.append(lang)

        return languages

    def _export_certifications(
        self, conn: sqlite3.Connection, resume_key: str, version_id: int
    ) -> List[OrderedDict]:
        """Export workshop_and_certifications with issuer grouping."""
        cursor = conn.cursor()

        # Get all issuers for this resume
        cursor.execute(
            """
            SELECT ci.id, cii.issuer_name
            FROM cert_issuers ci
            LEFT JOIN cert_issuer_i18n cii ON ci.id = cii.issuer_id 
                AND cii.resume_version_id = ?
            WHERE ci.resume_key = ?
            ORDER BY ci.sort_order
            """,
            (version_id, resume_key),
        )

        issuer_groups = []
        for issuer_row in cursor.fetchall():
            issuer_id = issuer_row["id"]

            # Get certifications for this issuer
            cursor.execute(
                """
                SELECT c.id, c.is_certificate, c.date_text, c.date, c.url,
                       ci.name, ci.duration
                FROM certifications c
                LEFT JOIN certification_i18n ci ON c.id = ci.certification_id 
                    AND ci.resume_version_id = ?
                WHERE c.issuer_id = ?
                ORDER BY c.sort_order
                """,
                (version_id, issuer_id),
            )

            certifications = []
            for cert_row in cursor.fetchall():
                # Get tags for this certification
                tags = self._get_tags_for_entity(conn, "certification", cert_row["id"], version_id)

                # Determine date - prefer date_text, fallback to date
                date_value = cert_row["date_text"]
                if date_value is None:
                    date_value = cert_row["date"]

                cert_data = {
                    "name": cert_row["name"],
                    "date": date_value,
                    "duration": cert_row["duration"],
                    "certificate": bool(cert_row["is_certificate"]),
                    "URL": cert_row["url"],
                }

                # Only include type_key if there are tags
                if tags:
                    cert_data["type_key"] = tags

                cert = ordered_dict_from_mapping(cert_data, CERTIFICATION_FIELD_ORDER)
                certifications.append(cert)

            issuer_group = ordered_dict_from_mapping(
                {
                    "issuer": issuer_row["issuer_name"],
                    "certifications": certifications,
                },
                CERT_ISSUER_FIELD_ORDER,
            )
            issuer_groups.append(issuer_group)

        return issuer_groups

    def _export_skills(
        self, conn: sqlite3.Connection, resume_key: str, version_id: int
    ) -> OrderedDict:
        """Export skills as nested dict structure."""
        cursor = conn.cursor()

        # Get all categories for this resume
        cursor.execute(
            """
            SELECT sc.id, sci.name
            FROM skill_categories sc
            LEFT JOIN skill_category_i18n sci ON sc.id = sci.category_id 
                AND sci.resume_version_id = ?
            WHERE sc.resume_key = ?
            ORDER BY sc.sort_order
            """,
            (version_id, resume_key),
        )

        skills = OrderedDict()
        for cat_row in cursor.fetchall():
            cat_id = cat_row["id"]
            cat_name = cat_row["name"]

            # Get subcategories for this category
            cursor.execute(
                """
                SELECT ss.id, ssi.name
                FROM skill_subcategories ss
                LEFT JOIN skill_subcategory_i18n ssi ON ss.id = ssi.subcategory_id 
                    AND ssi.resume_version_id = ?
                WHERE ss.category_id = ?
                ORDER BY ss.sort_order
                """,
                (version_id, cat_id),
            )

            subcategories = OrderedDict()
            for subcat_row in cursor.fetchall():
                subcat_id = subcat_row["id"]
                subcat_name = subcat_row["name"]

                # Get items for this subcategory
                cursor.execute(
                    """
                    SELECT si.id, sii.long_name, sii.short_name
                    FROM skill_items si
                    LEFT JOIN skill_item_i18n sii ON si.id = sii.skill_item_id 
                        AND sii.resume_version_id = ?
                    WHERE si.subcategory_id = ?
                    ORDER BY si.sort_order
                    """,
                    (version_id, subcat_id),
                )

                items = []
                for item_row in cursor.fetchall():
                    # Get tags for this skill item
                    tags = self._get_tags_for_entity(conn, "skill_item", item_row["id"], version_id)

                    item_data = {
                        "long_name": item_row["long_name"],
                        "short_name": item_row["short_name"],
                    }

                    # Only include type_key if there are tags
                    if tags:
                        item_data["type_key"] = tags

                    item = ordered_dict_from_mapping(item_data, SKILL_ITEM_FIELD_ORDER)
                    items.append(item)

                subcategories[subcat_name] = items

            skills[cat_name] = subcategories

        return skills

    def _export_experiences(
        self, conn: sqlite3.Connection, resume_key: str, version_id: int
    ) -> List[OrderedDict]:
        """Export experiences section."""
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT ei.id, ei.start_date, ei.end_date, ei.is_current,
                   exp.duration_text, exp.role, exp.institution, exp.primary_focus, exp.description
            FROM experience_items ei
            LEFT JOIN experience_i18n exp ON ei.id = exp.experience_item_id 
                AND exp.resume_version_id = ?
            WHERE ei.resume_key = ?
            ORDER BY ei.sort_order
            """,
            (version_id, resume_key),
        )

        experiences = []
        for row in cursor.fetchall():
            exp_data = {
                "role": row["role"],
                "institution": row["institution"],
                "duration": row["duration_text"],
            }

            # Only include primaryFocus if it exists
            if row["primary_focus"]:
                exp_data["primaryFocus"] = row["primary_focus"]

            exp_data["description"] = row["description"]

            exp = ordered_dict_from_mapping(exp_data, EXPERIENCE_FIELD_ORDER, include_none=False)
            experiences.append(exp)

        return experiences

    def _export_projects(
        self, conn: sqlite3.Connection, resume_key: str, version_id: int
    ) -> List[OrderedDict]:
        """Export projects section with tags."""
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT pi.id, pi.url, proj.title, proj.description
            FROM project_items pi
            LEFT JOIN project_i18n proj ON pi.id = proj.project_item_id 
                AND proj.resume_version_id = ?
            WHERE pi.resume_key = ?
            ORDER BY pi.sort_order
            """,
            (version_id, resume_key),
        )

        projects = []
        for row in cursor.fetchall():
            # Get tags for this project
            tags = self._get_tags_for_entity(conn, "project", row["id"], version_id)

            proj_data = {
                "title": row["title"],
                "description": row["description"],
                "url": row["url"],
            }

            # Include type_key if there are tags
            if tags:
                proj_data["type_key"] = tags

            proj = ordered_dict_from_mapping(proj_data, PROJECT_FIELD_ORDER)
            projects.append(proj)

        return projects

    def _export_publications(
        self, conn: sqlite3.Connection, resume_key: str, version_id: int
    ) -> List[OrderedDict]:
        """Export publications with authors, editors, supervisors."""
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT pi.id, pi.year, pi.month, pi.day, pi.date, pi.submission_date, pi.access_date,
                   pi.doi, pi.isbn, pi.issn, pi.pmid, pi.pmcid, pi.arxiv,
                   pi.url, pi.url_caps, pi.repository_url,
                   pub.title, pub.pub_type, pub.status, pub.language, pub.notes,
                   pub.journal, pub.volume, pub.issue, pub.pages, pub.article_number,
                   pub.book_title, pub.chapter_pages, pub.conference, pub.publisher,
                   pub.place, pub.edition, pub.degree_type, pub.correspondent,
                   pub.institution, pub.faculty, pub.school
            FROM publication_items pi
            LEFT JOIN publication_i18n pub ON pi.id = pub.publication_id 
                AND pub.resume_version_id = ?
            WHERE pi.resume_key = ?
            ORDER BY pi.sort_order
            """,
            (version_id, resume_key),
        )

        publications = []
        for row in cursor.fetchall():
            pub_id = row["id"]

            # Get authors
            cursor.execute(
                """
                SELECT author_literal
                FROM publication_authors
                WHERE publication_id = ? AND resume_version_id = ?
                ORDER BY sort_order
                """,
                (pub_id, version_id),
            )
            authors = [r["author_literal"] for r in cursor.fetchall()]

            # Build authors_structured
            authors_structured = [{"literal": a} for a in authors] if authors else None

            # Get editors
            cursor.execute(
                """
                SELECT editor_literal
                FROM publication_editors
                WHERE publication_id = ? AND resume_version_id = ?
                ORDER BY sort_order
                """,
                (pub_id, version_id),
            )
            editors = [r["editor_literal"] for r in cursor.fetchall()]

            # Get supervisors
            cursor.execute(
                """
                SELECT supervisor_literal
                FROM publication_supervisors
                WHERE publication_id = ? AND resume_version_id = ?
                ORDER BY sort_order
                """,
                (pub_id, version_id),
            )
            supervisors = [r["supervisor_literal"] for r in cursor.fetchall()]

            # Get tags for this publication
            tags = self._get_tags_for_entity(conn, "publication", pub_id, version_id)

            # Build identifiers object
            identifiers = OrderedDict(
                [
                    ("doi", row["doi"]),
                    ("isbn", row["isbn"]),
                    ("issn", row["issn"]),
                    ("pmid", row["pmid"]),
                    ("pmcid", row["pmcid"]),
                    ("arxiv", row["arxiv"]),
                ]
            )

            # Build publication object - include all fields that might be in original
            pub_data = {
                "title": row["title"],
                "authors": authors if authors else None,
                "authors_structured": authors_structured,
                "type": row["pub_type"],
                "status": row["status"],
                "year": row["year"],
                "month": row["month"],
                "day": row["day"],
                "date": row["date"],
                "journal": row["journal"],
                "volume": row["volume"],
                "issue": row["issue"],
                "pages": row["pages"],
                "article_number": row["article_number"],
                "doi": row["doi"],
                "issn": row["issn"],
                "url": row["url"],
                "access_date": row["access_date"],
                "language": row["language"],
                "publisher": row["publisher"],
                "place": row["place"],
                "editors": editors if editors else None,
                "book_title": row["book_title"],
                "chapter_pages": row["chapter_pages"],
                "edition": row["edition"],
                "conference": row["conference"],
                "degree_type": row["degree_type"],
                "repository_url": row["repository_url"],
                "correspondent": row["correspondent"],
                "supervisors": supervisors if supervisors else None,
                "institution": row["institution"],
                "faculty": row["faculty"],
                "school": row["school"],
                "isbn": row["isbn"],
                "submissionDate": row["submission_date"],
                "identifiers": identifiers,
                "notes": row["notes"],
                "URL": row["url_caps"] if row["url_caps"] else row["url"],
                "type_key": tags if tags else None,
            }

            pub = ordered_dict_from_mapping(pub_data, PUBLICATION_FIELD_ORDER)
            publications.append(pub)

        return publications

    def _export_references(
        self, conn: sqlite3.Connection, resume_key: str, version_id: int
    ) -> List[OrderedDict]:
        """Export references with email arrays."""
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT ri.id, ri.phone, ri.url,
                   ref.name, ref.position, ref.department, ref.institution, ref.location
            FROM reference_items ri
            LEFT JOIN reference_i18n ref ON ri.id = ref.reference_id 
                AND ref.resume_version_id = ?
            WHERE ri.resume_key = ?
            ORDER BY ri.sort_order
            """,
            (version_id, resume_key),
        )

        references = []
        for row in cursor.fetchall():
            ref_id = row["id"]

            # Get emails
            cursor.execute(
                """
                SELECT email
                FROM reference_emails
                WHERE reference_id = ?
                ORDER BY sort_order
                """,
                (ref_id,),
            )
            emails = [r["email"] for r in cursor.fetchall()]

            # Get tags for this reference
            tags = self._get_tags_for_entity(conn, "reference", ref_id, version_id)

            # Handle phone - might be JSON string for array, plain string, or null
            phone_raw = row["phone"]
            phone_value = None
            if phone_raw is not None:
                # Try to parse as JSON (for phone arrays stored as JSON)
                try:
                    phone_value = json.loads(phone_raw)
                except (json.JSONDecodeError, TypeError):
                    # Not JSON, use as plain string
                    phone_value = phone_raw

            ref_data = {
                "name": row["name"],
                "position": row["position"],
                "department": row["department"],
                "institution": row["institution"],
                "location": row["location"],
                "email": emails if emails else None,
                "phone": phone_value,
                "URL": row["url"],
            }

            # Include type_key if there are tags
            if tags:
                ref_data["type_key"] = tags

            ref = ordered_dict_from_mapping(ref_data, REFERENCE_FIELD_ORDER)
            references.append(ref)

        return references

    def _get_tags_for_entity(
        self,
        conn: sqlite3.Connection,
        entity_type: str,
        entity_id: int,
        version_id: int,
    ) -> List[str]:
        """
        Get translated tag labels for an entity.

        Args:
            conn: Database connection
            entity_type: Type of entity (education, certification, skill_item, project, publication, reference)
            entity_id: ID of the entity
            version_id: Resume version ID for language-specific labels

        Returns:
            List of translated tag labels
        """
        cursor = conn.cursor()

        # Map entity_type to table and column names
        entity_tables = {
            "education": ("education_item_tags", "education_item_id"),
            "certification": ("certification_tags", "certification_id"),
            "skill_item": ("skill_item_tags", "skill_item_id"),
            "project": ("project_tags", "project_item_id"),
            "publication": ("publication_tags", "publication_id"),
            "reference": ("reference_tags", "reference_id"),
        }

        if entity_type not in entity_tables:
            return []

        table_name, id_column = entity_tables[entity_type]

        # Query to get tag labels for this entity
        # Safe: table_name and id_column are from hardcoded whitelist above
        cursor.execute(
            f"""
            SELECT ti.label
            FROM {table_name} et
            JOIN tag_i18n ti ON et.tag_code = ti.tag_code AND ti.resume_version_id = ?
            WHERE et.{id_column} = ?
            ORDER BY ti.label
            """,  # noqa: S608
            (version_id, entity_id),
        )

        return [row["label"] for row in cursor.fetchall()]
