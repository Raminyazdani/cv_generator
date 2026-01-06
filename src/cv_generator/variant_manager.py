"""
Variant Manager for CV Generator.

Manages adding, removing, and linking language variants for CV data.
All language variants with the same `config.ID` (resume_key) are linked together
via `resume_sets` and `resume_versions`.

Non-negotiable Constraints:
- `config.ID` = `resume_key`: This mapping is absolute and unchangeable.
- Orphan prevention: Cannot delete last variant without deleting entire resume_set.
- Audit trail: All variant operations logged for debugging.
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .db import get_db_path
from .errors import ConfigurationError, ValidationError

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    """Return current UTC time as ISO format string."""
    return datetime.now(timezone.utc).isoformat()


# Supported language codes
SUPPORTED_LANGUAGES = ["en", "de", "fa"]
DEFAULT_LANGUAGE = "en"


@dataclass
class AddVariantResult:
    """Result of adding a new language variant."""
    success: bool
    resume_key: str
    lang_code: str
    version_id: int = 0
    copied_from: Optional[str] = None
    records_created: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "resume_key": self.resume_key,
            "lang_code": self.lang_code,
            "version_id": self.version_id,
            "copied_from": self.copied_from,
            "records_created": self.records_created,
            "error": self.error,
        }


@dataclass
class RemoveVariantResult:
    """Result of removing a language variant."""
    success: bool
    resume_key: str
    lang_code: str
    records_deleted: int = 0
    was_last_variant: bool = False
    resume_set_deleted: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "resume_key": self.resume_key,
            "lang_code": self.lang_code,
            "records_deleted": self.records_deleted,
            "was_last_variant": self.was_last_variant,
            "resume_set_deleted": self.resume_set_deleted,
            "error": self.error,
        }


@dataclass
class LinkResult:
    """Result of linking a variant to a resume_set."""
    success: bool
    version_id: int
    target_resume_key: str
    previous_resume_key: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "version_id": self.version_id,
            "target_resume_key": self.target_resume_key,
            "previous_resume_key": self.previous_resume_key,
            "error": self.error,
        }


@dataclass
class UnlinkResult:
    """Result of unlinking a variant from a resume_set."""
    success: bool
    version_id: int
    original_resume_key: str
    new_resume_key: Optional[str] = None
    variant_deleted: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "version_id": self.version_id,
            "original_resume_key": self.original_resume_key,
            "new_resume_key": self.new_resume_key,
            "variant_deleted": self.variant_deleted,
            "error": self.error,
        }


@dataclass
class MergeResult:
    """Result of merging two resume_sets."""
    success: bool
    source_resume_key: str
    target_resume_key: str
    variants_moved: int = 0
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    source_deleted: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "source_resume_key": self.source_resume_key,
            "target_resume_key": self.target_resume_key,
            "variants_moved": self.variants_moved,
            "conflicts": self.conflicts,
            "source_deleted": self.source_deleted,
            "error": self.error,
        }


@dataclass
class OrphanedVariant:
    """A variant that might be incorrectly linked."""
    version_id: int
    lang_code: str
    resume_key: str
    person_name: str  # From person_i18n
    possible_matches: List[str] = field(default_factory=list)  # Other resume_keys

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "version_id": self.version_id,
            "lang_code": self.lang_code,
            "resume_key": self.resume_key,
            "person_name": self.person_name,
            "possible_matches": self.possible_matches,
        }


@dataclass
class DuplicateCandidate:
    """Resume sets that might be the same person."""
    resume_key_1: str
    resume_key_2: str
    similarity_score: float
    matching_fields: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "resume_key_1": self.resume_key_1,
            "resume_key_2": self.resume_key_2,
            "similarity_score": self.similarity_score,
            "matching_fields": self.matching_fields,
        }


class VariantManager:
    """
    Manages adding, removing, and linking language variants.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize with database."""
        self.db_path = get_db_path(db_path)

        if not self.db_path.exists():
            raise ConfigurationError(f"Database not found: {self.db_path}")

    def _connect(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def add_variant(
        self,
        resume_key: str,
        lang_code: str,
        copy_from: Optional[str] = None
    ) -> AddVariantResult:
        """
        Add a new language variant for a person.

        Creates:
        - resume_version record
        - All *_i18n records (empty or copied from source language)

        Args:
            resume_key: Person identifier (config.ID)
            lang_code: New language to add (en, de, fa)
            copy_from: If specified, copy translatable fields from this language

        Returns:
            AddVariantResult with creation details
        """
        result = AddVariantResult(
            success=False,
            resume_key=resume_key,
            lang_code=lang_code,
            copied_from=copy_from,
        )

        # Validate language code
        if lang_code not in SUPPORTED_LANGUAGES:
            result.error = f"Unsupported language: {lang_code}. Supported: {SUPPORTED_LANGUAGES}"
            return result

        logger.info(
            f"[VARIANT] Adding variant: resume_key={resume_key}, lang={lang_code}, "
            f"copy_from={copy_from}"
        )

        conn = self._connect()
        try:
            cursor = conn.cursor()

            # Check if resume_set exists
            cursor.execute(
                "SELECT resume_key, base_lang_code FROM resume_sets WHERE resume_key = ?",
                (resume_key,)
            )
            resume_set = cursor.fetchone()
            if not resume_set:
                result.error = f"Resume set not found: {resume_key}"
                return result

            # Check if variant already exists
            cursor.execute(
                "SELECT id FROM resume_versions WHERE resume_key = ? AND lang_code = ?",
                (resume_key, lang_code)
            )
            if cursor.fetchone():
                result.error = f"Variant already exists: {resume_key}/{lang_code}"
                return result

            # Create resume_version
            now = _utcnow()
            is_base = 1 if lang_code == resume_set[1] else 0
            cursor.execute(
                """INSERT INTO resume_versions
                   (resume_key, lang_code, is_base, is_published, created_at, updated_at)
                   VALUES (?, ?, ?, 0, ?, ?)""",
                (resume_key, lang_code, is_base, now, now)
            )
            version_id = cursor.lastrowid
            result.version_id = version_id
            result.records_created += 1

            # Get source version ID if copying
            source_version_id: Optional[int] = None
            if copy_from:
                cursor.execute(
                    "SELECT id FROM resume_versions WHERE resume_key = ? AND lang_code = ?",
                    (resume_key, copy_from)
                )
                source_row = cursor.fetchone()
                if source_row:
                    source_version_id = source_row[0]
                else:
                    logger.warning(
                        f"[VARIANT] Source language {copy_from} not found, creating empty variant"
                    )

            # Create i18n records for all related entities
            records_created = self._create_i18n_records(
                cursor, resume_key, version_id, source_version_id
            )
            result.records_created += records_created

            # Update resume_set timestamp
            cursor.execute(
                "UPDATE resume_sets SET updated_at = ? WHERE resume_key = ?",
                (now, resume_key)
            )

            conn.commit()
            result.success = True

            logger.info(
                f"[VARIANT] Added variant: version_id={version_id}, "
                f"records_created={result.records_created}"
            )

        except Exception as e:
            conn.rollback()
            result.error = str(e)
            logger.error(f"[VARIANT] Failed to add variant: {e}")
        finally:
            conn.close()

        return result

    def _create_i18n_records(
        self,
        cursor: sqlite3.Cursor,
        resume_key: str,
        version_id: int,
        source_version_id: Optional[int]
    ) -> int:
        """
        Create i18n records for a new language variant.

        Args:
            cursor: Database cursor
            resume_key: Person identifier
            version_id: New version ID
            source_version_id: Source version ID to copy from (or None for empty)

        Returns:
            Number of records created
        """
        count = 0

        # Person i18n
        cursor.execute("SELECT id FROM persons WHERE resume_key = ?", (resume_key,))
        person = cursor.fetchone()
        if person:
            person_id = person[0]
            if source_version_id:
                cursor.execute(
                    """INSERT INTO person_i18n (person_id, resume_version_id, fname, lname, summary)
                       SELECT ?, ?, fname, lname, summary
                       FROM person_i18n WHERE person_id = ? AND resume_version_id = ?""",
                    (person_id, version_id, person_id, source_version_id)
                )
            else:
                cursor.execute(
                    """INSERT INTO person_i18n (person_id, resume_version_id, fname, lname, summary)
                       VALUES (?, ?, NULL, NULL, NULL)""",
                    (person_id, version_id)
                )
            count += 1

            # Person locations i18n
            cursor.execute(
                "SELECT id FROM person_locations WHERE person_id = ?",
                (person_id,)
            )
            for loc in cursor.fetchall():
                loc_id = loc[0]
                if source_version_id:
                    cursor.execute(
                        """INSERT INTO person_location_i18n
                           (location_id, resume_version_id, address, city, region, country)
                           SELECT ?, ?, address, city, region, country
                           FROM person_location_i18n
                           WHERE location_id = ? AND resume_version_id = ?""",
                        (loc_id, version_id, loc_id, source_version_id)
                    )
                else:
                    cursor.execute(
                        """INSERT INTO person_location_i18n
                           (location_id, resume_version_id, address, city, region, country)
                           VALUES (?, ?, NULL, NULL, NULL, NULL)""",
                        (loc_id, version_id)
                    )
                count += 1

            # Person labels i18n
            cursor.execute(
                "SELECT id FROM person_labels WHERE person_id = ?",
                (person_id,)
            )
            for label in cursor.fetchall():
                label_id = label[0]
                if source_version_id:
                    cursor.execute(
                        """INSERT INTO person_label_i18n
                           (label_id, resume_version_id, label_text)
                           SELECT ?, ?, label_text
                           FROM person_label_i18n
                           WHERE label_id = ? AND resume_version_id = ?""",
                        (label_id, version_id, label_id, source_version_id)
                    )
                else:
                    cursor.execute(
                        """INSERT INTO person_label_i18n
                           (label_id, resume_version_id, label_text)
                           VALUES (?, ?, NULL)""",
                        (label_id, version_id)
                    )
                count += 1

        # Profile accounts i18n
        cursor.execute(
            "SELECT id FROM profile_accounts WHERE resume_key = ?",
            (resume_key,)
        )
        for profile in cursor.fetchall():
            profile_id = profile[0]
            if source_version_id:
                cursor.execute(
                    """INSERT INTO profile_account_i18n
                       (profile_account_id, resume_version_id, network_display)
                       SELECT ?, ?, network_display
                       FROM profile_account_i18n
                       WHERE profile_account_id = ? AND resume_version_id = ?""",
                    (profile_id, version_id, profile_id, source_version_id)
                )
            else:
                cursor.execute(
                    """INSERT INTO profile_account_i18n
                       (profile_account_id, resume_version_id, network_display)
                       VALUES (?, ?, NULL)""",
                    (profile_id, version_id)
                )
            count += 1

        # Education i18n
        cursor.execute(
            "SELECT id FROM education_items WHERE resume_key = ?",
            (resume_key,)
        )
        for edu in cursor.fetchall():
            edu_id = edu[0]
            if source_version_id:
                cursor.execute(
                    """INSERT INTO education_i18n
                       (education_item_id, resume_version_id, institution, location, area, study_type)
                       SELECT ?, ?, institution, location, area, study_type
                       FROM education_i18n
                       WHERE education_item_id = ? AND resume_version_id = ?""",
                    (edu_id, version_id, edu_id, source_version_id)
                )
            else:
                cursor.execute(
                    """INSERT INTO education_i18n
                       (education_item_id, resume_version_id, institution, location, area, study_type)
                       VALUES (?, ?, NULL, NULL, NULL, NULL)""",
                    (edu_id, version_id)
                )
            count += 1

        # Experience i18n
        cursor.execute(
            "SELECT id FROM experience_items WHERE resume_key = ?",
            (resume_key,)
        )
        for exp in cursor.fetchall():
            exp_id = exp[0]
            if source_version_id:
                cursor.execute(
                    """INSERT INTO experience_i18n
                       (experience_item_id, resume_version_id, duration_text, role, institution, primary_focus, description)
                       SELECT ?, ?, duration_text, role, institution, primary_focus, description
                       FROM experience_i18n
                       WHERE experience_item_id = ? AND resume_version_id = ?""",
                    (exp_id, version_id, exp_id, source_version_id)
                )
            else:
                cursor.execute(
                    """INSERT INTO experience_i18n
                       (experience_item_id, resume_version_id, duration_text, role, institution, primary_focus, description)
                       VALUES (?, ?, NULL, NULL, NULL, NULL, NULL)""",
                    (exp_id, version_id)
                )
            count += 1

        # Project i18n
        cursor.execute(
            "SELECT id FROM project_items WHERE resume_key = ?",
            (resume_key,)
        )
        for proj in cursor.fetchall():
            proj_id = proj[0]
            if source_version_id:
                cursor.execute(
                    """INSERT INTO project_i18n
                       (project_item_id, resume_version_id, title, description)
                       SELECT ?, ?, title, description
                       FROM project_i18n
                       WHERE project_item_id = ? AND resume_version_id = ?""",
                    (proj_id, version_id, proj_id, source_version_id)
                )
            else:
                cursor.execute(
                    """INSERT INTO project_i18n
                       (project_item_id, resume_version_id, title, description)
                       VALUES (?, ?, NULL, NULL)""",
                    (proj_id, version_id)
                )
            count += 1

        # Publication i18n (simplified - just main fields)
        cursor.execute(
            "SELECT id FROM publication_items WHERE resume_key = ?",
            (resume_key,)
        )
        for pub in cursor.fetchall():
            pub_id = pub[0]
            if source_version_id:
                cursor.execute(
                    """INSERT INTO publication_i18n
                       (publication_id, resume_version_id, title, pub_type, status, language,
                        notes, journal, volume, issue, pages, article_number, book_title,
                        chapter_pages, conference, publisher, place, edition, degree_type,
                        correspondent, institution, faculty, school)
                       SELECT ?, ?, title, pub_type, status, language,
                              notes, journal, volume, issue, pages, article_number, book_title,
                              chapter_pages, conference, publisher, place, edition, degree_type,
                              correspondent, institution, faculty, school
                       FROM publication_i18n
                       WHERE publication_id = ? AND resume_version_id = ?""",
                    (pub_id, version_id, pub_id, source_version_id)
                )
            else:
                cursor.execute(
                    """INSERT INTO publication_i18n
                       (publication_id, resume_version_id, title)
                       VALUES (?, ?, NULL)""",
                    (pub_id, version_id)
                )
            count += 1

        # Reference i18n
        cursor.execute(
            "SELECT id FROM reference_items WHERE resume_key = ?",
            (resume_key,)
        )
        for ref in cursor.fetchall():
            ref_id = ref[0]
            if source_version_id:
                cursor.execute(
                    """INSERT INTO reference_i18n
                       (reference_id, resume_version_id, name, position, department, institution, location)
                       SELECT ?, ?, name, position, department, institution, location
                       FROM reference_i18n
                       WHERE reference_id = ? AND resume_version_id = ?""",
                    (ref_id, version_id, ref_id, source_version_id)
                )
            else:
                cursor.execute(
                    """INSERT INTO reference_i18n
                       (reference_id, resume_version_id, name, position, department, institution, location)
                       VALUES (?, ?, NULL, NULL, NULL, NULL, NULL)""",
                    (ref_id, version_id)
                )
            count += 1

        # Spoken language i18n
        cursor.execute(
            "SELECT id FROM spoken_language_items WHERE resume_key = ?",
            (resume_key,)
        )
        for lang in cursor.fetchall():
            lang_id = lang[0]
            if source_version_id:
                cursor.execute(
                    """INSERT INTO spoken_language_i18n
                       (spoken_language_item_id, resume_version_id, language_name, proficiency_level, proficiency_status)
                       SELECT ?, ?, language_name, proficiency_level, proficiency_status
                       FROM spoken_language_i18n
                       WHERE spoken_language_item_id = ? AND resume_version_id = ?""",
                    (lang_id, version_id, lang_id, source_version_id)
                )
            else:
                cursor.execute(
                    """INSERT INTO spoken_language_i18n
                       (spoken_language_item_id, resume_version_id, language_name, proficiency_level, proficiency_status)
                       VALUES (?, ?, NULL, NULL, NULL)""",
                    (lang_id, version_id)
                )
            count += 1

        return count

    def remove_variant(
        self,
        resume_key: str,
        lang_code: str,
        force: bool = False
    ) -> RemoveVariantResult:
        """
        Remove a language variant.

        Fails if this is the last/only variant (unless force=True).
        If force=True and this is the last variant, the entire resume_set is deleted.

        Args:
            resume_key: Person identifier
            lang_code: Language to remove
            force: If True, allow deleting the last variant (deletes entire resume_set)

        Returns:
            RemoveVariantResult with deletion details
        """
        result = RemoveVariantResult(
            success=False,
            resume_key=resume_key,
            lang_code=lang_code,
        )

        logger.info(
            f"[VARIANT] Removing variant: resume_key={resume_key}, lang={lang_code}, "
            f"force={force}"
        )

        conn = self._connect()
        try:
            cursor = conn.cursor()

            # Check if variant exists
            cursor.execute(
                "SELECT id FROM resume_versions WHERE resume_key = ? AND lang_code = ?",
                (resume_key, lang_code)
            )
            version_row = cursor.fetchone()
            if not version_row:
                result.error = f"Variant not found: {resume_key}/{lang_code}"
                return result

            version_id = version_row[0]

            # Count remaining variants
            cursor.execute(
                "SELECT COUNT(*) FROM resume_versions WHERE resume_key = ?",
                (resume_key,)
            )
            variant_count = cursor.fetchone()[0]

            if variant_count <= 1:
                result.was_last_variant = True
                if not force:
                    result.error = (
                        f"Cannot delete last variant for {resume_key}. "
                        f"Use force=True to delete entire resume_set."
                    )
                    return result

            # Delete all i18n records for this version
            records_deleted = self._delete_i18n_records(cursor, version_id)
            result.records_deleted = records_deleted

            # Delete the resume_version
            cursor.execute(
                "DELETE FROM resume_versions WHERE id = ?",
                (version_id,)
            )
            result.records_deleted += 1

            # If this was the last variant and force=True, delete the resume_set
            if result.was_last_variant and force:
                # Delete all base entities (cascades will handle related records)
                cursor.execute("DELETE FROM persons WHERE resume_key = ?", (resume_key,))
                cursor.execute("DELETE FROM profile_accounts WHERE resume_key = ?", (resume_key,))
                cursor.execute("DELETE FROM education_items WHERE resume_key = ?", (resume_key,))
                cursor.execute("DELETE FROM experience_items WHERE resume_key = ?", (resume_key,))
                cursor.execute("DELETE FROM project_items WHERE resume_key = ?", (resume_key,))
                cursor.execute("DELETE FROM publication_items WHERE resume_key = ?", (resume_key,))
                cursor.execute("DELETE FROM reference_items WHERE resume_key = ?", (resume_key,))
                cursor.execute("DELETE FROM spoken_language_items WHERE resume_key = ?", (resume_key,))
                cursor.execute("DELETE FROM skill_categories WHERE resume_key = ?", (resume_key,))

                # Delete cert_issuers (which cascades to certifications)
                cursor.execute("DELETE FROM cert_issuers WHERE resume_key = ?", (resume_key,))

                # Delete the resume_set itself
                cursor.execute("DELETE FROM resume_sets WHERE resume_key = ?", (resume_key,))
                result.resume_set_deleted = True

            conn.commit()
            result.success = True

            logger.info(
                f"[VARIANT] Removed variant: records_deleted={result.records_deleted}, "
                f"resume_set_deleted={result.resume_set_deleted}"
            )

        except Exception as e:
            conn.rollback()
            result.error = str(e)
            logger.error(f"[VARIANT] Failed to remove variant: {e}")
        finally:
            conn.close()

        return result

    def _delete_i18n_records(self, cursor: sqlite3.Cursor, version_id: int) -> int:
        """Delete all i18n records for a version."""
        count = 0

        tables = [
            "person_i18n", "person_location_i18n", "person_label_i18n",
            "profile_account_i18n", "education_i18n", "spoken_language_i18n",
            "spoken_language_cert_i18n", "cert_issuer_i18n", "certification_i18n",
            "skill_category_i18n", "skill_subcategory_i18n", "skill_item_i18n",
            "experience_i18n", "project_i18n", "publication_i18n",
            "reference_i18n", "tag_i18n"
        ]

        for table in tables:
            # Safe: table names come from hardcoded whitelist above
            cursor.execute(
                f"DELETE FROM {table} WHERE resume_version_id = ?",  # noqa: S608
                (version_id,)
            )
            count += cursor.rowcount

        # Also delete publication authors/editors/supervisors
        cursor.execute(
            "DELETE FROM publication_authors WHERE resume_version_id = ?",
            (version_id,)
        )
        count += cursor.rowcount

        cursor.execute(
            "DELETE FROM publication_editors WHERE resume_version_id = ?",
            (version_id,)
        )
        count += cursor.rowcount

        cursor.execute(
            "DELETE FROM publication_supervisors WHERE resume_version_id = ?",
            (version_id,)
        )
        count += cursor.rowcount

        return count

    def link_orphan_variant(
        self,
        orphan_version_id: int,
        target_resume_key: str
    ) -> LinkResult:
        """
        Link an orphaned variant to an existing resume_set.

        Used when import created a separate resume_set but should be linked
        to an existing person.

        Args:
            orphan_version_id: The resume_version ID of the orphan
            target_resume_key: The resume_key to link to

        Returns:
            LinkResult with linking details
        """
        result = LinkResult(
            success=False,
            version_id=orphan_version_id,
            target_resume_key=target_resume_key,
        )

        logger.info(
            f"[VARIANT] Linking orphan: version_id={orphan_version_id}, "
            f"target={target_resume_key}"
        )

        conn = self._connect()
        try:
            cursor = conn.cursor()

            # Get current version info
            cursor.execute(
                "SELECT resume_key, lang_code FROM resume_versions WHERE id = ?",
                (orphan_version_id,)
            )
            version_row = cursor.fetchone()
            if not version_row:
                result.error = f"Version not found: {orphan_version_id}"
                return result

            current_resume_key, lang_code = version_row
            result.previous_resume_key = current_resume_key

            if current_resume_key == target_resume_key:
                result.error = "Variant is already linked to target resume_key"
                return result

            # Check target resume_set exists
            cursor.execute(
                "SELECT resume_key FROM resume_sets WHERE resume_key = ?",
                (target_resume_key,)
            )
            if not cursor.fetchone():
                result.error = f"Target resume_set not found: {target_resume_key}"
                return result

            # Check if target already has this language
            cursor.execute(
                "SELECT id FROM resume_versions WHERE resume_key = ? AND lang_code = ?",
                (target_resume_key, lang_code)
            )
            if cursor.fetchone():
                result.error = (
                    f"Target {target_resume_key} already has {lang_code} variant. "
                    f"Consider merging instead."
                )
                return result

            # Update the version to point to target resume_key
            now = _utcnow()
            cursor.execute(
                "UPDATE resume_versions SET resume_key = ?, updated_at = ? WHERE id = ?",
                (target_resume_key, now, orphan_version_id)
            )

            # Clean up orphaned resume_set if it has no more variants
            cursor.execute(
                "SELECT COUNT(*) FROM resume_versions WHERE resume_key = ?",
                (current_resume_key,)
            )
            remaining = cursor.fetchone()[0]
            if remaining == 0:
                # Delete the empty resume_set
                cursor.execute(
                    "DELETE FROM resume_sets WHERE resume_key = ?",
                    (current_resume_key,)
                )
                logger.info(f"[VARIANT] Deleted empty resume_set: {current_resume_key}")

            conn.commit()
            result.success = True

            logger.info(
                f"[VARIANT] Linked orphan: version_id={orphan_version_id} "
                f"from {current_resume_key} to {target_resume_key}"
            )

        except Exception as e:
            conn.rollback()
            result.error = str(e)
            logger.error(f"[VARIANT] Failed to link orphan: {e}")
        finally:
            conn.close()

        return result

    def unlink_variant(
        self,
        resume_key: str,
        lang_code: str,
        create_new_resume_set: bool = True
    ) -> UnlinkResult:
        """
        Unlink a variant from its resume_set.

        If create_new_resume_set=True, creates a new resume_set for this variant.
        Otherwise, deletes the variant entirely.

        Args:
            resume_key: Current resume_key
            lang_code: Language of variant to unlink
            create_new_resume_set: If True, create new resume_set; else delete variant

        Returns:
            UnlinkResult with unlinking details
        """
        result = UnlinkResult(
            success=False,
            version_id=0,
            original_resume_key=resume_key,
        )

        logger.info(
            f"[VARIANT] Unlinking variant: resume_key={resume_key}, lang={lang_code}, "
            f"create_new={create_new_resume_set}"
        )

        conn = self._connect()
        try:
            cursor = conn.cursor()

            # Get version info
            cursor.execute(
                "SELECT id FROM resume_versions WHERE resume_key = ? AND lang_code = ?",
                (resume_key, lang_code)
            )
            version_row = cursor.fetchone()
            if not version_row:
                result.error = f"Variant not found: {resume_key}/{lang_code}"
                return result

            version_id = version_row[0]
            result.version_id = version_id

            if create_new_resume_set:
                # Generate a new resume_key
                import uuid
                new_resume_key = f"{resume_key}_{lang_code}_{uuid.uuid4().hex[:8]}"

                now = _utcnow()

                # Create new resume_set
                cursor.execute(
                    """INSERT INTO resume_sets (resume_key, base_lang_code, created_at, updated_at)
                       VALUES (?, ?, ?, ?)""",
                    (new_resume_key, lang_code, now, now)
                )

                # Update version to point to new resume_set
                cursor.execute(
                    "UPDATE resume_versions SET resume_key = ?, is_base = 1, updated_at = ? WHERE id = ?",
                    (new_resume_key, now, version_id)
                )

                result.new_resume_key = new_resume_key

                logger.info(f"[VARIANT] Created new resume_set: {new_resume_key}")

            else:
                # Delete the variant
                remove_result = self.remove_variant(resume_key, lang_code, force=False)
                if not remove_result.success:
                    result.error = remove_result.error
                    return result

                result.variant_deleted = True

            conn.commit()
            result.success = True

            logger.info(
                f"[VARIANT] Unlinked variant: new_key={result.new_resume_key}, "
                f"deleted={result.variant_deleted}"
            )

        except Exception as e:
            conn.rollback()
            result.error = str(e)
            logger.error(f"[VARIANT] Failed to unlink variant: {e}")
        finally:
            conn.close()

        return result

    def merge_resume_sets(
        self,
        source_resume_key: str,
        target_resume_key: str
    ) -> MergeResult:
        """
        Merge two resume_sets that should be one person.

        Moves all variants from source to target.
        Handles conflicts if both have the same language.

        Args:
            source_resume_key: Resume_key to merge from (will be deleted)
            target_resume_key: Resume_key to merge into (will remain)

        Returns:
            MergeResult with merge details
        """
        result = MergeResult(
            success=False,
            source_resume_key=source_resume_key,
            target_resume_key=target_resume_key,
        )

        if source_resume_key == target_resume_key:
            result.error = "Source and target resume_keys cannot be the same"
            return result

        logger.info(
            f"[VARIANT] Merging resume_sets: {source_resume_key} -> {target_resume_key}"
        )

        conn = self._connect()
        try:
            cursor = conn.cursor()

            # Check both resume_sets exist
            cursor.execute(
                "SELECT resume_key FROM resume_sets WHERE resume_key = ?",
                (source_resume_key,)
            )
            if not cursor.fetchone():
                result.error = f"Source resume_set not found: {source_resume_key}"
                return result

            cursor.execute(
                "SELECT resume_key FROM resume_sets WHERE resume_key = ?",
                (target_resume_key,)
            )
            if not cursor.fetchone():
                result.error = f"Target resume_set not found: {target_resume_key}"
                return result

            # Get source variants
            cursor.execute(
                "SELECT id, lang_code FROM resume_versions WHERE resume_key = ?",
                (source_resume_key,)
            )
            source_variants = cursor.fetchall()

            # Get target variants
            cursor.execute(
                "SELECT lang_code FROM resume_versions WHERE resume_key = ?",
                (target_resume_key,)
            )
            target_langs = {row[0] for row in cursor.fetchall()}

            # Move each source variant to target
            now = _utcnow()
            for version_id, lang_code in source_variants:
                if lang_code in target_langs:
                    # Conflict - both have this language
                    result.conflicts.append({
                        "lang_code": lang_code,
                        "source_version_id": version_id,
                        "message": f"Target already has {lang_code} variant"
                    })
                    logger.warning(
                        f"[VARIANT] Conflict: both have {lang_code}, skipping"
                    )
                    continue

                # Move variant to target
                cursor.execute(
                    "UPDATE resume_versions SET resume_key = ?, is_base = 0, updated_at = ? WHERE id = ?",
                    (target_resume_key, now, version_id)
                )
                result.variants_moved += 1

            # Delete source resume_set if all variants moved
            cursor.execute(
                "SELECT COUNT(*) FROM resume_versions WHERE resume_key = ?",
                (source_resume_key,)
            )
            remaining = cursor.fetchone()[0]
            if remaining == 0:
                # Delete the empty source resume_set
                cursor.execute(
                    "DELETE FROM resume_sets WHERE resume_key = ?",
                    (source_resume_key,)
                )
                result.source_deleted = True
                logger.info(f"[VARIANT] Deleted source resume_set: {source_resume_key}")

            conn.commit()
            result.success = True

            logger.info(
                f"[VARIANT] Merged: moved {result.variants_moved} variants, "
                f"conflicts={len(result.conflicts)}, source_deleted={result.source_deleted}"
            )

        except Exception as e:
            conn.rollback()
            result.error = str(e)
            logger.error(f"[VARIANT] Failed to merge: {e}")
        finally:
            conn.close()

        return result

    def get_orphaned_variants(self) -> List[OrphanedVariant]:
        """
        Find variants that might be incorrectly linked.

        Looks for:
        - Resume_sets with only one language variant (might be orphaned)
        - Variants where person name differs significantly from others

        Returns:
            List of potentially orphaned variants
        """
        orphans: List[OrphanedVariant] = []

        logger.info("[VARIANT] Searching for orphaned variants")

        conn = self._connect()
        try:
            cursor = conn.cursor()

            # Find resume_sets with only one variant
            cursor.execute(
                """SELECT rs.resume_key, rv.id, rv.lang_code,
                          COALESCE(pi.fname, '') || ' ' || COALESCE(pi.lname, '') as name
                   FROM resume_sets rs
                   JOIN resume_versions rv ON rs.resume_key = rv.resume_key
                   LEFT JOIN persons p ON rs.resume_key = p.resume_key
                   LEFT JOIN person_i18n pi ON p.id = pi.person_id AND rv.id = pi.resume_version_id
                   WHERE rs.resume_key IN (
                       SELECT resume_key FROM resume_versions
                       GROUP BY resume_key HAVING COUNT(*) = 1
                   )"""
            )

            for row in cursor.fetchall():
                resume_key, version_id, lang_code, person_name = row
                person_name = (person_name or "").strip()

                # Find possible matches (other resume_keys with similar names)
                possible_matches: List[str] = []
                if person_name:
                    # Simple matching: look for resume_sets with similar first name
                    first_name = person_name.split()[0] if person_name else ""
                    if first_name and len(first_name) > 2:
                        cursor.execute(
                            """SELECT DISTINCT rs.resume_key
                               FROM resume_sets rs
                               JOIN persons p ON rs.resume_key = p.resume_key
                               JOIN person_i18n pi ON p.id = pi.person_id
                               WHERE rs.resume_key != ? AND pi.fname LIKE ?""",
                            (resume_key, f"{first_name}%")
                        )
                        possible_matches = [r[0] for r in cursor.fetchall()]

                orphans.append(OrphanedVariant(
                    version_id=version_id,
                    lang_code=lang_code,
                    resume_key=resume_key,
                    person_name=person_name,
                    possible_matches=possible_matches[:5]  # Limit to top 5
                ))

            logger.info(f"[VARIANT] Found {len(orphans)} potential orphans")

        finally:
            conn.close()

        return orphans

    def get_duplicate_candidates(self) -> List[DuplicateCandidate]:
        """
        Find resume_sets that might be the same person.

        Looks for:
        - Same email address
        - Very similar names
        - Same phone number

        Returns:
            List of potential duplicate resume_sets
        """
        candidates: List[DuplicateCandidate] = []

        logger.info("[VARIANT] Searching for duplicate candidates")

        conn = self._connect()
        try:
            cursor = conn.cursor()

            # Find pairs with same email
            cursor.execute(
                """SELECT p1.resume_key, p2.resume_key, p1.email
                   FROM persons p1
                   JOIN persons p2 ON p1.email = p2.email AND p1.id < p2.id
                   WHERE p1.email IS NOT NULL AND p1.email != ''"""
            )

            for row in cursor.fetchall():
                key1, key2, email = row
                candidates.append(DuplicateCandidate(
                    resume_key_1=key1,
                    resume_key_2=key2,
                    similarity_score=1.0,
                    matching_fields=[f"email: {email}"]
                ))

            # Find pairs with same phone
            cursor.execute(
                """SELECT p1.resume_key, p2.resume_key, p1.phone_number
                   FROM persons p1
                   JOIN persons p2 ON p1.phone_number = p2.phone_number AND p1.id < p2.id
                   WHERE p1.phone_number IS NOT NULL AND p1.phone_number != ''"""
            )

            for row in cursor.fetchall():
                key1, key2, phone = row
                # Check if already added
                existing = next(
                    (c for c in candidates
                     if (c.resume_key_1 == key1 and c.resume_key_2 == key2)
                        or (c.resume_key_1 == key2 and c.resume_key_2 == key1)),
                    None
                )
                if existing:
                    existing.matching_fields.append(f"phone: {phone}")
                    existing.similarity_score = min(1.0, existing.similarity_score + 0.3)
                else:
                    candidates.append(DuplicateCandidate(
                        resume_key_1=key1,
                        resume_key_2=key2,
                        similarity_score=0.8,
                        matching_fields=[f"phone: {phone}"]
                    ))

            logger.info(f"[VARIANT] Found {len(candidates)} duplicate candidates")

        finally:
            conn.close()

        return candidates
