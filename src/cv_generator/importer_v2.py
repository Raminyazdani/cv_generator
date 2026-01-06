"""
Lossless JSON to DB import engine for CV Generator.

This module implements a bulletproof import engine that parses CV JSON files
(with the new config block), correctly identifies the person and language,
and populates ALL tables in the ERD-defined schema with zero data loss.

Key features:
- Config-first identification: config.ID determines resume_key; config.lang determines version
- Lossless import: Every field from JSON is stored in DB
- Idempotent imports: Re-importing the same file doesn't create duplicates
- Legacy support: Files without config block can still import via filename inference
- Atomic transactions: Each file import is all-or-nothing
- Tag normalization: All type_key values stored in tag_codes with canonical lowercase keys
- Order preservation: sort_order columns reflect original JSON array order

Usage:
    importer = CVImporter(db_path)
    result = importer.import_file(json_path, dry_run=False)
    # or
    results = importer.import_directory(dir_path, dry_run=False)
"""

import json
import logging
import re
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .import_mappings import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    """Return current UTC time as ISO format string."""
    return datetime.now(timezone.utc).isoformat()


def _slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '_', text)
    return text


def _parse_date(date_str: Optional[str]) -> Optional[str]:
    """Parse date string to ISO format, handling various formats."""
    if not date_str or date_str in ("present", "Present", "current", "Recent"):
        return None

    # Try common date formats
    formats = [
        "%Y-%m-%d",
        "%Y-%m",
        "%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Handle dates like "2020-9-31" (invalid day)
    try:
        parts = date_str.split("-")
        if len(parts) == 3:
            year, month, day = int(parts[0]), int(parts[1]), min(int(parts[2]), 28)
            return f"{year:04d}-{month:02d}-{day:02d}"
    except (ValueError, IndexError):
        pass

    return None


@dataclass
class ImportResult:
    """Result of importing a single JSON file."""

    success: bool
    resume_key: str
    lang_code: str
    file_path: Path

    # Counts per section
    stats: Dict[str, int] = field(default_factory=dict)

    # Any warnings (non-fatal)
    warnings: List[str] = field(default_factory=list)

    # Error details if failed
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    # Timing
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON/logging."""
        return {
            "success": self.success,
            "resume_key": self.resume_key,
            "lang_code": self.lang_code,
            "file_path": str(self.file_path),
            "stats": self.stats,
            "warnings": self.warnings,
            "error": self.error,
            "error_details": self.error_details,
            "duration_ms": self.duration_ms,
        }


@dataclass
class BatchImportResult:
    """Result of importing multiple JSON files."""

    total_files: int
    successful: int
    failed: int
    results: List[ImportResult] = field(default_factory=list)
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


class CVImporter:
    """
    Lossless JSON to DB import engine.

    Usage:
        importer = CVImporter(db_path)
        result = importer.import_file(json_path, dry_run=False)
        # or
        results = importer.import_directory(dir_path, dry_run=False)
    """

    def __init__(self, db_path: Path):
        """Initialize importer with database connection."""
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    def _connect(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def _close(self) -> None:
        """Close database connection if open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def import_file(
        self,
        json_path: Path,
        dry_run: bool = False,
        overwrite: bool = False,
    ) -> ImportResult:
        """
        Import a single JSON file into the database.

        Args:
            json_path: Path to the CV JSON file
            dry_run: If True, validate without committing
            overwrite: If True, replace existing data; else merge

        Returns:
            ImportResult with success status, stats, and any errors
        """
        start_time = time.time()
        json_path = Path(json_path)

        result = ImportResult(
            success=False,
            resume_key="",
            lang_code="",
            file_path=json_path,
            stats={},
            warnings=[],
        )

        try:
            # Load JSON data
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Parse config to get resume_key and lang_code
            resume_key, lang_code = self._import_config(data, json_path)
            result.resume_key = resume_key
            result.lang_code = lang_code

            logger.info(f"[IMPORT] Starting import: {json_path.name}")
            logger.info(f"[IMPORT] Parsed config: resume_key={resume_key}, lang={lang_code}")

            # Open connection and begin transaction
            conn = self._connect()
            cursor = conn.cursor()

            try:
                # Ensure resume_set exists
                is_base = self._ensure_resume_set(cursor, resume_key, lang_code)
                logger.info(f"[IMPORT] Created/found resume_set: {resume_key}")

                # Ensure resume_version exists
                version_id = self._ensure_resume_version(
                    cursor, resume_key, lang_code, is_base
                )
                logger.info(f"[IMPORT] Created/found resume_version: id={version_id}")

                # If overwrite, delete existing data for this version
                if overwrite:
                    self._delete_version_data(cursor, version_id, resume_key)

                # Import each section
                stats = {}

                if "basics" in data:
                    count = self._import_basics(cursor, data["basics"], resume_key, version_id)
                    stats["basics"] = count

                if "profiles" in data:
                    count = self._import_profiles(cursor, data["profiles"], resume_key, version_id)
                    stats["profiles"] = count

                if "education" in data:
                    count = self._import_education(cursor, data["education"], resume_key, version_id)
                    stats["education"] = count

                if "languages" in data:
                    count = self._import_languages(cursor, data["languages"], resume_key, version_id)
                    stats["languages"] = count

                if "workshop_and_certifications" in data:
                    count = self._import_certifications(
                        cursor, data["workshop_and_certifications"], resume_key, version_id
                    )
                    stats["certifications"] = count

                if "skills" in data:
                    cat, subcat, items = self._import_skills(
                        cursor, data["skills"], resume_key, version_id
                    )
                    stats["skill_categories"] = cat
                    stats["skill_subcategories"] = subcat
                    stats["skill_items"] = items

                if "experiences" in data:
                    count = self._import_experiences(
                        cursor, data["experiences"], resume_key, version_id
                    )
                    stats["experiences"] = count

                if "projects" in data:
                    count = self._import_projects(cursor, data["projects"], resume_key, version_id)
                    stats["projects"] = count

                if "publications" in data:
                    count = self._import_publications(
                        cursor, data["publications"], resume_key, version_id
                    )
                    stats["publications"] = count

                if "references" in data:
                    count = self._import_references(
                        cursor, data["references"], resume_key, version_id
                    )
                    stats["references"] = count

                result.stats = stats

                if dry_run:
                    conn.rollback()
                    logger.info("[IMPORT] Dry run - changes rolled back")
                else:
                    conn.commit()
                    logger.info(f"[IMPORT] Complete: {sum(stats.values())} records")

                result.success = True

            except Exception:
                conn.rollback()
                raise

        except json.JSONDecodeError as e:
            result.error = f"Invalid JSON: {e}"
            result.error_details = {"line": e.lineno, "column": e.colno}
            logger.error(f"[IMPORT] {result.error}")

        except FileNotFoundError:
            result.error = f"File not found: {json_path}"
            logger.error(f"[IMPORT] {result.error}")

        except Exception as e:
            result.error = str(e)
            logger.error(f"[IMPORT] Error: {e}")

        finally:
            self._close()

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    def import_directory(
        self,
        dir_path: Path,
        pattern: str = "*.json",
        dry_run: bool = False,
    ) -> BatchImportResult:
        """Import all matching JSON files from a directory."""
        start_time = time.time()
        dir_path = Path(dir_path)

        result = BatchImportResult(
            total_files=0,
            successful=0,
            failed=0,
            results=[],
        )

        json_files = sorted(dir_path.glob(pattern))
        result.total_files = len(json_files)

        for json_path in json_files:
            import_result = self.import_file(json_path, dry_run=dry_run)
            result.results.append(import_result)

            if import_result.success:
                result.successful += 1
            else:
                result.failed += 1

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    def _import_config(self, data: Dict[str, Any], json_path: Path) -> Tuple[str, str]:
        """Extract resume_key and lang_code from config block or filename."""
        config = data.get("config", {})

        resume_key = config.get("ID")
        lang_code = config.get("lang")

        if not resume_key or not lang_code:
            stem = json_path.stem
            parts = stem.rsplit("_", 1)

            if len(parts) == 2 and parts[1] in SUPPORTED_LANGUAGES:
                inferred_key = parts[0]
                inferred_lang = parts[1]
            else:
                inferred_key = stem
                inferred_lang = "en"

            if not resume_key:
                resume_key = inferred_key
            if not lang_code:
                lang_code = inferred_lang

        if lang_code not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language code: {lang_code}")

        return resume_key, lang_code

    def _ensure_resume_set(self, cursor: sqlite3.Cursor, resume_key: str, lang_code: str) -> bool:
        """Ensure resume_set exists, return True if this is the base language."""
        now = _utcnow()

        cursor.execute(
            "SELECT resume_key, base_lang_code FROM resume_sets WHERE resume_key = ?",
            (resume_key,),
        )
        row = cursor.fetchone()

        if row:
            return row[1] == lang_code
        else:
            cursor.execute(
                """INSERT INTO resume_sets (resume_key, base_lang_code, created_at, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (resume_key, lang_code, now, now),
            )
            return True

    def _ensure_resume_version(
        self, cursor: sqlite3.Cursor, resume_key: str, lang_code: str, is_base: bool
    ) -> int:
        """Ensure resume_version exists, return version_id."""
        now = _utcnow()

        cursor.execute(
            "SELECT id FROM resume_versions WHERE resume_key = ? AND lang_code = ?",
            (resume_key, lang_code),
        )
        row = cursor.fetchone()

        if row:
            return row[0]
        else:
            cursor.execute(
                """INSERT INTO resume_versions
                   (resume_key, lang_code, is_base, is_published, created_at, updated_at)
                   VALUES (?, ?, ?, 0, ?, ?)""",
                (resume_key, lang_code, 1 if is_base else 0, now, now),
            )
            return cursor.lastrowid

    def _delete_version_data(self, cursor: sqlite3.Cursor, version_id: int, resume_key: str) -> None:
        """Delete existing data for a version (for overwrite mode)."""
        i18n_tables = [
            "person_i18n", "person_location_i18n", "person_label_i18n",
            "profile_account_i18n", "education_i18n", "spoken_language_i18n",
            "spoken_language_cert_i18n", "cert_issuer_i18n", "certification_i18n",
            "skill_category_i18n", "skill_subcategory_i18n", "skill_item_i18n",
            "experience_i18n", "project_i18n", "publication_i18n",
            "reference_i18n", "tag_i18n",
        ]

        for table in i18n_tables:
            cursor.execute(f"DELETE FROM {table} WHERE resume_version_id = ?", (version_id,))

        cursor.execute("DELETE FROM publication_authors WHERE resume_version_id = ?", (version_id,))
        cursor.execute("DELETE FROM publication_editors WHERE resume_version_id = ?", (version_id,))
        cursor.execute("DELETE FROM publication_supervisors WHERE resume_version_id = ?", (version_id,))

    def _import_basics(
        self, cursor: sqlite3.Cursor, basics: List[Dict[str, Any]], resume_key: str, version_id: int
    ) -> int:
        """Import basics section."""
        if not basics:
            return 0

        basic = basics[0]
        now = _utcnow()

        cursor.execute("SELECT id FROM persons WHERE resume_key = ?", (resume_key,))
        person_row = cursor.fetchone()

        if person_row:
            person_id = person_row[0]
        else:
            phone = basic.get("phone", {})
            cursor.execute(
                """INSERT INTO persons
                   (resume_key, email, birth_date, phone_country_code, phone_number,
                    phone_formatted, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    resume_key, basic.get("email"), _parse_date(basic.get("birthDate")),
                    phone.get("countryCode") if isinstance(phone, dict) else None,
                    phone.get("number") if isinstance(phone, dict) else None,
                    phone.get("formatted") if isinstance(phone, dict) else None,
                    now, now,
                ),
            )
            person_id = cursor.lastrowid

        cursor.execute(
            "SELECT id FROM person_i18n WHERE person_id = ? AND resume_version_id = ?",
            (person_id, version_id),
        )
        if not cursor.fetchone():
            cursor.execute(
                """INSERT INTO person_i18n (person_id, resume_version_id, fname, lname, summary)
                   VALUES (?, ?, ?, ?, ?)""",
                (person_id, version_id, basic.get("fname"), basic.get("lname"), basic.get("summary")),
            )

        for idx, loc in enumerate(basic.get("location", [])):
            cursor.execute(
                "SELECT id FROM person_locations WHERE person_id = ? AND sort_order = ?",
                (person_id, idx),
            )
            loc_row = cursor.fetchone()

            if loc_row:
                location_id = loc_row[0]
            else:
                cursor.execute(
                    "INSERT INTO person_locations (person_id, sort_order, postal_code) VALUES (?, ?, ?)",
                    (person_id, idx, loc.get("postalCode")),
                )
                location_id = cursor.lastrowid

            cursor.execute(
                "SELECT id FROM person_location_i18n WHERE location_id = ? AND resume_version_id = ?",
                (location_id, version_id),
            )
            if not cursor.fetchone():
                cursor.execute(
                    """INSERT INTO person_location_i18n
                       (location_id, resume_version_id, address, city, region, country)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (location_id, version_id, loc.get("address"), loc.get("city"),
                     loc.get("region"), loc.get("country")),
                )

        for idx, pic in enumerate(basic.get("Pictures", [])):
            cursor.execute(
                "SELECT id FROM person_pictures WHERE person_id = ? AND type_of = ?",
                (person_id, pic.get("type_of")),
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO person_pictures (person_id, sort_order, type_of, url) VALUES (?, ?, ?, ?)",
                    (person_id, idx, pic.get("type_of"), pic.get("URL")),
                )

        for idx, label_text in enumerate(basic.get("label", [])):
            cursor.execute(
                "SELECT id FROM person_labels WHERE person_id = ? AND sort_order = ?",
                (person_id, idx),
            )
            label_row = cursor.fetchone()

            if label_row:
                label_id = label_row[0]
            else:
                cursor.execute(
                    "INSERT INTO person_labels (person_id, sort_order, label_key) VALUES (?, ?, ?)",
                    (person_id, idx, _slugify(label_text) if label_text else None),
                )
                label_id = cursor.lastrowid

            cursor.execute(
                "SELECT id FROM person_label_i18n WHERE label_id = ? AND resume_version_id = ?",
                (label_id, version_id),
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO person_label_i18n (label_id, resume_version_id, label_text) VALUES (?, ?, ?)",
                    (label_id, version_id, label_text),
                )

        return 1

    def _import_profiles(
        self, cursor: sqlite3.Cursor, profiles: List[Dict[str, Any]], resume_key: str, version_id: int
    ) -> int:
        """Import profiles section."""
        if not profiles:
            return 0

        count = 0
        for idx, profile in enumerate(profiles):
            cursor.execute(
                "SELECT id FROM profile_accounts WHERE resume_key = ? AND sort_order = ?",
                (resume_key, idx),
            )
            row = cursor.fetchone()

            if row:
                profile_id = row[0]
            else:
                cursor.execute(
                    """INSERT INTO profile_accounts
                       (resume_key, sort_order, network_code, username, url, uuid)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (resume_key, idx, _slugify(profile.get("network", "")),
                     profile.get("username"), profile.get("url"), profile.get("uuid")),
                )
                profile_id = cursor.lastrowid
                count += 1

            cursor.execute(
                "SELECT id FROM profile_account_i18n WHERE profile_account_id = ? AND resume_version_id = ?",
                (profile_id, version_id),
            )
            if not cursor.fetchone():
                cursor.execute(
                    """INSERT INTO profile_account_i18n
                       (profile_account_id, resume_version_id, network_display)
                       VALUES (?, ?, ?)""",
                    (profile_id, version_id, profile.get("network")),
                )

        return count or len(profiles)

    def _import_education(
        self, cursor: sqlite3.Cursor, education: List[Dict[str, Any]], resume_key: str, version_id: int
    ) -> int:
        """Import education section."""
        if not education:
            return 0

        count = 0
        for idx, edu in enumerate(education):
            cursor.execute(
                "SELECT id FROM education_items WHERE resume_key = ? AND sort_order = ?",
                (resume_key, idx),
            )
            row = cursor.fetchone()

            if row:
                edu_id = row[0]
            else:
                end_date_raw = edu.get("endDate")
                end_date = _parse_date(end_date_raw)
                end_date_text = end_date_raw if end_date is None and end_date_raw else None

                cursor.execute(
                    """INSERT INTO education_items
                       (resume_key, sort_order, start_date, end_date, end_date_text, gpa, logo_url)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (resume_key, idx, _parse_date(edu.get("startDate")), end_date,
                     end_date_text, edu.get("gpa"), edu.get("logo_url")),
                )
                edu_id = cursor.lastrowid
                count += 1

            cursor.execute(
                "SELECT id FROM education_i18n WHERE education_item_id = ? AND resume_version_id = ?",
                (edu_id, version_id),
            )
            if not cursor.fetchone():
                cursor.execute(
                    """INSERT INTO education_i18n
                       (education_item_id, resume_version_id, institution, location, area, study_type)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (edu_id, version_id, edu.get("institution"), edu.get("location"),
                     edu.get("area"), edu.get("studyType")),
                )

            for tag_name in edu.get("type_key", []):
                tag_code = self._get_or_create_tag(cursor, tag_name, version_id)
                cursor.execute(
                    "INSERT OR IGNORE INTO education_item_tags (education_item_id, tag_code) VALUES (?, ?)",
                    (edu_id, tag_code),
                )

        return count or len(education)

    def _import_languages(
        self, cursor: sqlite3.Cursor, languages: List[Dict[str, Any]], resume_key: str, version_id: int
    ) -> int:
        """Import languages section."""
        if not languages:
            return 0

        count = 0
        for idx, lang in enumerate(languages):
            cursor.execute(
                "SELECT id FROM spoken_language_items WHERE resume_key = ? AND sort_order = ?",
                (resume_key, idx),
            )
            row = cursor.fetchone()

            proficiency = lang.get("proficiency", {})
            if isinstance(proficiency, str):
                proficiency = {"level": proficiency}

            if row:
                lang_id = row[0]
            else:
                lang_name = lang.get("language", "")
                cursor.execute(
                    """INSERT INTO spoken_language_items
                       (resume_key, sort_order, described_language_code, proficiency_cefr)
                       VALUES (?, ?, ?, ?)""",
                    (resume_key, idx, self._infer_language_code(lang_name), proficiency.get("CEFR")),
                )
                lang_id = cursor.lastrowid
                count += 1

            cursor.execute(
                "SELECT id FROM spoken_language_i18n WHERE spoken_language_item_id = ? AND resume_version_id = ?",
                (lang_id, version_id),
            )
            if not cursor.fetchone():
                cursor.execute(
                    """INSERT INTO spoken_language_i18n
                       (spoken_language_item_id, resume_version_id, language_name, proficiency_level, proficiency_status)
                       VALUES (?, ?, ?, ?, ?)""",
                    (lang_id, version_id, lang.get("language"), proficiency.get("level"), proficiency.get("status")),
                )

            for cert_idx, cert in enumerate(lang.get("certifications", [])):
                if not cert.get("test") and not cert.get("overall"):
                    continue

                cursor.execute(
                    "SELECT id FROM spoken_language_certs WHERE spoken_language_item_id = ? AND sort_order = ?",
                    (lang_id, cert_idx),
                )
                cert_row = cursor.fetchone()

                if cert_row:
                    cert_id = cert_row[0]
                else:
                    cursor.execute(
                        """INSERT INTO spoken_language_certs
                           (spoken_language_item_id, sort_order, overall, reading, writing,
                            listening, speaking, max_score, min_score, exam_date, url)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (lang_id, cert_idx, cert.get("overall"), cert.get("reading"), cert.get("writing"),
                         cert.get("listening"), cert.get("speaking"), cert.get("maxScore"), cert.get("minScore"),
                         _parse_date(cert.get("examDate")), cert.get("URL")),
                    )
                    cert_id = cursor.lastrowid

                cursor.execute(
                    "SELECT id FROM spoken_language_cert_i18n WHERE cert_id = ? AND resume_version_id = ?",
                    (cert_id, version_id),
                )
                if not cursor.fetchone():
                    cursor.execute(
                        """INSERT INTO spoken_language_cert_i18n (cert_id, resume_version_id, test_name, organization)
                           VALUES (?, ?, ?, ?)""",
                        (cert_id, version_id, cert.get("test"), cert.get("organization")),
                    )

        return count or len(languages)

    def _import_certifications(
        self, cursor: sqlite3.Cursor, certifications: List[Dict[str, Any]], resume_key: str, version_id: int
    ) -> int:
        """Import certifications section."""
        if not certifications:
            return 0

        total = 0
        for issuer_idx, issuer_group in enumerate(certifications):
            issuer_name = issuer_group.get("issuer", "")
            issuer_slug = _slugify(issuer_name)

            # First try to find by sort_order (position in array - same across languages)
            cursor.execute(
                "SELECT id FROM cert_issuers WHERE resume_key = ? AND sort_order = ?",
                (resume_key, issuer_idx),
            )
            row = cursor.fetchone()

            if row:
                issuer_id = row[0]
            else:
                # Try by slug (for backwards compatibility)
                cursor.execute(
                    "SELECT id FROM cert_issuers WHERE resume_key = ? AND issuer_slug = ?",
                    (resume_key, issuer_slug),
                )
                row = cursor.fetchone()
                if row:
                    issuer_id = row[0]
                else:
                    cursor.execute(
                        "INSERT INTO cert_issuers (resume_key, sort_order, issuer_slug) VALUES (?, ?, ?)",
                        (resume_key, issuer_idx, issuer_slug),
                    )
                    issuer_id = cursor.lastrowid

            cursor.execute(
                "SELECT id FROM cert_issuer_i18n WHERE issuer_id = ? AND resume_version_id = ?",
                (issuer_id, version_id),
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO cert_issuer_i18n (issuer_id, resume_version_id, issuer_name) VALUES (?, ?, ?)",
                    (issuer_id, version_id, issuer_name),
                )

            for cert_idx, cert in enumerate(issuer_group.get("certifications", [])):
                cursor.execute(
                    "SELECT id FROM certifications WHERE issuer_id = ? AND sort_order = ?",
                    (issuer_id, cert_idx),
                )
                cert_row = cursor.fetchone()

                if cert_row:
                    cert_id = cert_row[0]
                else:
                    date_raw = cert.get("date")
                    cursor.execute(
                        """INSERT INTO certifications
                           (issuer_id, sort_order, is_certificate, date_text, date, url)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (issuer_id, cert_idx, 1 if cert.get("certificate") else 0,
                         date_raw, _parse_date(date_raw), cert.get("URL")),
                    )
                    cert_id = cursor.lastrowid
                    total += 1

                cursor.execute(
                    "SELECT id FROM certification_i18n WHERE certification_id = ? AND resume_version_id = ?",
                    (cert_id, version_id),
                )
                if not cursor.fetchone():
                    cursor.execute(
                        """INSERT INTO certification_i18n (certification_id, resume_version_id, name, duration)
                           VALUES (?, ?, ?, ?)""",
                        (cert_id, version_id, cert.get("name"), cert.get("duration")),
                    )

                for tag_name in cert.get("type_key", []):
                    tag_code = self._get_or_create_tag(cursor, tag_name, version_id)
                    cursor.execute(
                        "INSERT OR IGNORE INTO certification_tags (certification_id, tag_code) VALUES (?, ?)",
                        (cert_id, tag_code),
                    )

        return total

    def _import_skills(
        self, cursor: sqlite3.Cursor, skills: Dict[str, Dict[str, List[Dict[str, Any]]]],
        resume_key: str, version_id: int
    ) -> Tuple[int, int, int]:
        """Import skills section."""
        if not skills:
            return 0, 0, 0

        cat_count = subcat_count = item_count = 0

        for cat_idx, (cat_name, subcategories) in enumerate(skills.items()):
            cat_code = _slugify(cat_name)

            # First try by sort_order (position in array - same across languages)
            cursor.execute(
                "SELECT id FROM skill_categories WHERE resume_key = ? AND sort_order = ?",
                (resume_key, cat_idx),
            )
            row = cursor.fetchone()

            if row:
                cat_id = row[0]
            else:
                # Try by category_code
                cursor.execute(
                    "SELECT id FROM skill_categories WHERE resume_key = ? AND category_code = ?",
                    (resume_key, cat_code),
                )
                row = cursor.fetchone()
                if row:
                    cat_id = row[0]
                else:
                    cursor.execute(
                        "INSERT INTO skill_categories (resume_key, sort_order, category_code) VALUES (?, ?, ?)",
                        (resume_key, cat_idx, cat_code),
                    )
                    cat_id = cursor.lastrowid
                    cat_count += 1

            cursor.execute(
                "SELECT id FROM skill_category_i18n WHERE category_id = ? AND resume_version_id = ?",
                (cat_id, version_id),
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO skill_category_i18n (category_id, resume_version_id, name) VALUES (?, ?, ?)",
                    (cat_id, version_id, cat_name),
                )

            for subcat_idx, (subcat_name, items) in enumerate(subcategories.items()):
                subcat_code = _slugify(subcat_name)

                # First try by sort_order
                cursor.execute(
                    "SELECT id FROM skill_subcategories WHERE category_id = ? AND sort_order = ?",
                    (cat_id, subcat_idx),
                )
                subcat_row = cursor.fetchone()

                if subcat_row:
                    subcat_id = subcat_row[0]
                else:
                    # Try by subcategory_code
                    cursor.execute(
                        "SELECT id FROM skill_subcategories WHERE category_id = ? AND subcategory_code = ?",
                        (cat_id, subcat_code),
                    )
                    subcat_row = cursor.fetchone()
                    if subcat_row:
                        subcat_id = subcat_row[0]
                    else:
                        cursor.execute(
                            """INSERT INTO skill_subcategories (category_id, sort_order, subcategory_code)
                               VALUES (?, ?, ?)""",
                            (cat_id, subcat_idx, subcat_code),
                        )
                        subcat_id = cursor.lastrowid
                        subcat_count += 1

                cursor.execute(
                    "SELECT id FROM skill_subcategory_i18n WHERE subcategory_id = ? AND resume_version_id = ?",
                    (subcat_id, version_id),
                )
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO skill_subcategory_i18n (subcategory_id, resume_version_id, name) VALUES (?, ?, ?)",
                        (subcat_id, version_id, subcat_name),
                    )

                for item_idx, item in enumerate(items):
                    cursor.execute(
                        "SELECT id FROM skill_items WHERE subcategory_id = ? AND sort_order = ?",
                        (subcat_id, item_idx),
                    )
                    item_row = cursor.fetchone()

                    if item_row:
                        item_id = item_row[0]
                    else:
                        cursor.execute(
                            "INSERT INTO skill_items (subcategory_id, sort_order) VALUES (?, ?)",
                            (subcat_id, item_idx),
                        )
                        item_id = cursor.lastrowid
                        item_count += 1

                    cursor.execute(
                        "SELECT id FROM skill_item_i18n WHERE skill_item_id = ? AND resume_version_id = ?",
                        (item_id, version_id),
                    )
                    if not cursor.fetchone():
                        cursor.execute(
                            """INSERT INTO skill_item_i18n (skill_item_id, resume_version_id, long_name, short_name)
                               VALUES (?, ?, ?, ?)""",
                            (item_id, version_id, item.get("long_name"), item.get("short_name")),
                        )

                    for tag_name in item.get("type_key", []):
                        tag_code = self._get_or_create_tag(cursor, tag_name, version_id)
                        cursor.execute(
                            "INSERT OR IGNORE INTO skill_item_tags (skill_item_id, tag_code) VALUES (?, ?)",
                            (item_id, tag_code),
                        )

        return cat_count, subcat_count, item_count

    def _import_experiences(
        self, cursor: sqlite3.Cursor, experiences: List[Dict[str, Any]], resume_key: str, version_id: int
    ) -> int:
        """Import experiences section."""
        if not experiences:
            return 0

        count = 0
        for idx, exp in enumerate(experiences):
            cursor.execute(
                "SELECT id FROM experience_items WHERE resume_key = ? AND sort_order = ?",
                (resume_key, idx),
            )
            row = cursor.fetchone()

            if row:
                exp_id = row[0]
            else:
                duration = exp.get("duration", "")
                start_date = end_date = None
                is_current = False

                if " - " in duration:
                    parts = duration.split(" - ")
                    if len(parts) == 2:
                        start_date = _parse_date(parts[0].strip())
                        end_part = parts[1].strip()
                        if end_part.lower() in ("present", "recent", "current"):
                            is_current = True
                        else:
                            end_date = _parse_date(end_part)

                cursor.execute(
                    """INSERT INTO experience_items (resume_key, sort_order, start_date, end_date, is_current)
                       VALUES (?, ?, ?, ?, ?)""",
                    (resume_key, idx, start_date, end_date, 1 if is_current else 0),
                )
                exp_id = cursor.lastrowid
                count += 1

            cursor.execute(
                "SELECT id FROM experience_i18n WHERE experience_item_id = ? AND resume_version_id = ?",
                (exp_id, version_id),
            )
            if not cursor.fetchone():
                cursor.execute(
                    """INSERT INTO experience_i18n
                       (experience_item_id, resume_version_id, duration_text, role, institution, primary_focus, description)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (exp_id, version_id, exp.get("duration"), exp.get("role"),
                     exp.get("institution"), exp.get("primary_focus"), exp.get("description")),
                )

        return count or len(experiences)

    def _import_projects(
        self, cursor: sqlite3.Cursor, projects: List[Dict[str, Any]], resume_key: str, version_id: int
    ) -> int:
        """Import projects section."""
        if not projects:
            return 0

        count = 0
        for idx, proj in enumerate(projects):
            cursor.execute(
                "SELECT id FROM project_items WHERE resume_key = ? AND sort_order = ?",
                (resume_key, idx),
            )
            row = cursor.fetchone()

            if row:
                proj_id = row[0]
            else:
                cursor.execute(
                    "INSERT INTO project_items (resume_key, sort_order, url) VALUES (?, ?, ?)",
                    (resume_key, idx, proj.get("url")),
                )
                proj_id = cursor.lastrowid
                count += 1

            cursor.execute(
                "SELECT id FROM project_i18n WHERE project_item_id = ? AND resume_version_id = ?",
                (proj_id, version_id),
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO project_i18n (project_item_id, resume_version_id, title, description) VALUES (?, ?, ?, ?)",
                    (proj_id, version_id, proj.get("title"), proj.get("description")),
                )

            for tag_name in proj.get("type_key", []):
                tag_code = self._get_or_create_tag(cursor, tag_name, version_id)
                cursor.execute(
                    "INSERT OR IGNORE INTO project_tags (project_item_id, tag_code) VALUES (?, ?)",
                    (proj_id, tag_code),
                )

        return count or len(projects)

    def _import_publications(
        self, cursor: sqlite3.Cursor, publications: List[Dict[str, Any]], resume_key: str, version_id: int
    ) -> int:
        """Import publications section."""
        if not publications:
            return 0

        count = 0
        for idx, pub in enumerate(publications):
            cursor.execute(
                "SELECT id FROM publication_items WHERE resume_key = ? AND sort_order = ?",
                (resume_key, idx),
            )
            row = cursor.fetchone()

            if row:
                pub_id = row[0]
            else:
                identifiers = pub.get("identifiers", {})
                cursor.execute(
                    """INSERT INTO publication_items
                       (resume_key, sort_order, year, month, day, date, submission_date,
                        access_date, doi, isbn, issn, pmid, pmcid, arxiv, url, url_caps, repository_url)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (resume_key, idx, pub.get("year"), pub.get("month"), pub.get("day"),
                     _parse_date(pub.get("date")), _parse_date(pub.get("submissionDate")),
                     _parse_date(pub.get("access_date")),
                     pub.get("doi") or identifiers.get("doi"),
                     pub.get("isbn") or identifiers.get("isbn"),
                     pub.get("issn") or identifiers.get("issn"),
                     identifiers.get("pmid"), identifiers.get("pmcid"), identifiers.get("arxiv"),
                     pub.get("url") or pub.get("URL"), pub.get("url_caps"), pub.get("repository_url")),
                )
                pub_id = cursor.lastrowid
                count += 1

            cursor.execute(
                "SELECT id FROM publication_i18n WHERE publication_id = ? AND resume_version_id = ?",
                (pub_id, version_id),
            )
            if not cursor.fetchone():
                cursor.execute(
                    """INSERT INTO publication_i18n
                       (publication_id, resume_version_id, title, pub_type, status, language,
                        notes, journal, volume, issue, pages, article_number, book_title,
                        chapter_pages, conference, publisher, place, edition, degree_type,
                        correspondent, institution, faculty, school)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (pub_id, version_id, pub.get("title"), pub.get("type"), pub.get("status"),
                     pub.get("language"), pub.get("notes"), pub.get("journal"), pub.get("volume"),
                     pub.get("issue"), pub.get("pages"), pub.get("article_number"),
                     pub.get("book_title"), pub.get("chapter_pages"), pub.get("conference"),
                     pub.get("publisher"), pub.get("place"), pub.get("edition"), pub.get("degree_type"),
                     pub.get("correspondent"), pub.get("institution"), pub.get("faculty"), pub.get("school")),
                )

            self._import_pub_people(cursor, pub_id, version_id, pub, "authors_structured", "authors",
                                    "publication_authors", "author_literal")
            self._import_pub_people(cursor, pub_id, version_id, pub, None, "editors",
                                    "publication_editors", "editor_literal")
            self._import_pub_people(cursor, pub_id, version_id, pub, None, "supervisors",
                                    "publication_supervisors", "supervisor_literal")

            for tag_name in pub.get("type_key", []):
                tag_code = self._get_or_create_tag(cursor, tag_name, version_id)
                cursor.execute(
                    "INSERT OR IGNORE INTO publication_tags (publication_id, tag_code) VALUES (?, ?)",
                    (pub_id, tag_code),
                )

        return count or len(publications)

    def _import_pub_people(
        self, cursor: sqlite3.Cursor, pub_id: int, version_id: int, pub: Dict[str, Any],
        structured_key: Optional[str], fallback_key: str, table_name: str, column_name: str
    ) -> None:
        """Import authors/editors/supervisors for a publication."""
        people = []
        if structured_key and pub.get(structured_key):
            for person in pub[structured_key]:
                if isinstance(person, dict):
                    people.append(person.get("literal", ""))
                else:
                    people.append(str(person))
        elif pub.get(fallback_key):
            data = pub[fallback_key]
            if isinstance(data, list):
                people = [str(p) for p in data]

        if not people:
            return

        cursor.execute(
            f"DELETE FROM {table_name} WHERE publication_id = ? AND resume_version_id = ?",
            (pub_id, version_id),
        )

        for idx, person in enumerate(people):
            cursor.execute(
                f"INSERT INTO {table_name} (publication_id, resume_version_id, sort_order, {column_name}) VALUES (?, ?, ?, ?)",
                (pub_id, version_id, idx, person),
            )

    def _import_references(
        self, cursor: sqlite3.Cursor, references: List[Dict[str, Any]], resume_key: str, version_id: int
    ) -> int:
        """Import references section."""
        if not references:
            return 0

        count = 0
        for idx, ref in enumerate(references):
            cursor.execute(
                "SELECT id FROM reference_items WHERE resume_key = ? AND sort_order = ?",
                (resume_key, idx),
            )
            row = cursor.fetchone()

            if row:
                ref_id = row[0]
            else:
                # Handle phone - can be string, None, or list of phone objects
                phone_raw = ref.get("phone")
                phone_str = None
                if isinstance(phone_raw, str):
                    phone_str = phone_raw
                elif isinstance(phone_raw, list) and phone_raw:
                    # Take the formatted phone from the first phone object
                    first_phone = phone_raw[0]
                    if isinstance(first_phone, dict):
                        phone_str = first_phone.get("formatted")
                    else:
                        phone_str = str(first_phone)

                cursor.execute(
                    "INSERT INTO reference_items (resume_key, sort_order, phone, url) VALUES (?, ?, ?, ?)",
                    (resume_key, idx, phone_str, ref.get("URL")),
                )
                ref_id = cursor.lastrowid
                count += 1

            cursor.execute(
                "SELECT id FROM reference_i18n WHERE reference_id = ? AND resume_version_id = ?",
                (ref_id, version_id),
            )
            if not cursor.fetchone():
                cursor.execute(
                    """INSERT INTO reference_i18n
                       (reference_id, resume_version_id, name, position, department, institution, location)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (ref_id, version_id, ref.get("name"), ref.get("position"), ref.get("department"),
                     ref.get("institution"), ref.get("location")),
                )

            emails = ref.get("email", [])
            if isinstance(emails, str):
                emails = [emails]

            cursor.execute("DELETE FROM reference_emails WHERE reference_id = ?", (ref_id,))

            for email_idx, email in enumerate(emails):
                if email:
                    cursor.execute(
                        "INSERT INTO reference_emails (reference_id, sort_order, email) VALUES (?, ?, ?)",
                        (ref_id, email_idx, email),
                    )

            for tag_name in ref.get("type_key", []):
                tag_code = self._get_or_create_tag(cursor, tag_name, version_id)
                cursor.execute(
                    "INSERT OR IGNORE INTO reference_tags (reference_id, tag_code) VALUES (?, ?)",
                    (ref_id, tag_code),
                )

        return count or len(references)

    def _get_or_create_tag(self, cursor: sqlite3.Cursor, tag_name: str, version_id: int) -> str:
        """Get or create tag_code, add tag_i18n for this version."""
        tag_code = _slugify(tag_name)
        if not tag_code:
            tag_code = "unknown"

        cursor.execute("SELECT code FROM tag_codes WHERE code = ?", (tag_code,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO tag_codes (code, is_system) VALUES (?, ?)", (tag_code, 0))

        cursor.execute(
            "SELECT id FROM tag_i18n WHERE tag_code = ? AND resume_version_id = ?",
            (tag_code, version_id),
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO tag_i18n (tag_code, resume_version_id, label) VALUES (?, ?, ?)",
                (tag_code, version_id, tag_name),
            )

        return tag_code

    def _infer_language_code(self, language_name: str) -> Optional[str]:
        """Infer ISO language code from language name."""
        mapping = {
            "english": "en", "german": "de", "deutsch": "de", "persian": "fa",
            "farsi": "fa", "french": "fr", "spanish": "es", "italian": "it",
            "arabic": "ar", "chinese": "zh", "japanese": "ja", "korean": "ko",
            "russian": "ru", "portuguese": "pt",
        }
        return mapping.get(language_name.lower())
