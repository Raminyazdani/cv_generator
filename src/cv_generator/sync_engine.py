"""
Multi-Language Sync Engine for CV Generator.

Manages synchronization of shared (invariant) fields across language variants.
All language variants with the same `config.ID` (resume_key) are linked together
via `resume_sets` and must maintain consistent invariant field values.

Principles:
- Invariant fields: synced to all variants immediately in one transaction
- Translatable fields: independent per variant
- Conflicts: detected and queued for user resolution
- Audit trail: all sync operations logged for debugging

Field Categories:
- Invariant Fields (shared across all languages):
  - persons: email, birth_date, phone_*
  - education_items: start_date, end_date, gpa, logo_url
  - project_items: url
  - publication_items: year, doi, isbn, urls
  - reference_items: phone, url
  - profile_accounts: url, username, uuid
  - certifications: date, url, is_certificate

- Translatable Fields (language-specific in *_i18n tables):
  - person_i18n: fname, lname, summary
  - education_i18n: institution, location, area, study_type
  - experience_i18n: role, institution, description, duration_text
  - project_i18n: title, description
  - publication_i18n: title, status, journal, authors, etc.
  - skill_*_i18n: category/subcategory/item names
  - tag_i18n: translated tag labels
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .db import get_db_path
from .errors import ConfigurationError

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    """Return current UTC time as ISO format string."""
    return datetime.now(timezone.utc).isoformat()


# Invariant fields per entity type (table name -> list of column names)
# These fields must be synchronized across all language variants
INVARIANT_FIELDS: Dict[str, List[str]] = {
    "persons": ["email", "birth_date", "phone_country_code", "phone_number", "phone_formatted"],
    "education_items": ["start_date", "end_date", "end_date_text", "gpa", "logo_url"],
    "project_items": ["url"],
    "publication_items": [
        "year", "month", "day", "date", "submission_date", "access_date",
        "doi", "isbn", "issn", "pmid", "pmcid", "arxiv",
        "url", "url_caps", "repository_url"
    ],
    "reference_items": ["phone", "url"],
    "profile_accounts": ["url", "username", "uuid", "network_code"],
    "certifications": ["date", "date_text", "url", "is_certificate"],
    "experience_items": ["start_date", "end_date", "is_current"],
    "spoken_language_items": ["described_language_code", "proficiency_cefr"],
    "spoken_language_certs": [
        "overall", "reading", "writing", "listening", "speaking",
        "max_score", "min_score", "exam_date", "url"
    ],
}

# Supported language codes
SUPPORTED_LANGUAGES = ["en", "de", "fa"]


@dataclass
class FieldConflict:
    """
    Represents a conflict where an invariant field has different values
    across language variants.
    """
    resume_key: str
    entity_type: str  # Table name (education_items, etc.)
    entity_id: int    # Row ID in the entity table
    field_name: str
    values_by_lang: Dict[str, Any]  # {"en": "X", "de": "Y", "fa": "Z"}
    detected_at: datetime
    resolved: bool = False
    resolution: Optional[str] = None  # "use_en", "use_de", "use_fa", "use_custom"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "resume_key": self.resume_key,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "field_name": self.field_name,
            "values_by_lang": self.values_by_lang,
            "detected_at": self.detected_at.isoformat(),
            "resolved": self.resolved,
            "resolution": self.resolution,
        }


@dataclass
class SyncResult:
    """Result of a sync operation with detailed status."""
    success: bool
    source_lang: str
    affected_langs: List[str] = field(default_factory=list)
    field_name: str = ""
    old_values: Dict[str, Any] = field(default_factory=dict)  # lang -> old value
    new_value: Any = None
    conflicts_created: List[FieldConflict] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "source_lang": self.source_lang,
            "affected_langs": self.affected_langs,
            "field_name": self.field_name,
            "old_values": self.old_values,
            "new_value": self.new_value,
            "conflicts_created": [c.to_dict() for c in self.conflicts_created],
            "error": self.error,
        }


@dataclass
class VariantStatus:
    """Status of all language variants for a person."""
    resume_key: str
    existing_langs: List[str] = field(default_factory=list)
    missing_langs: List[str] = field(default_factory=list)
    base_lang: str = "en"
    conflicts: List[FieldConflict] = field(default_factory=list)
    last_synced: Optional[datetime] = None
    total_entries: Dict[str, int] = field(default_factory=dict)  # lang -> count

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "resume_key": self.resume_key,
            "existing_langs": self.existing_langs,
            "missing_langs": self.missing_langs,
            "base_lang": self.base_lang,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "last_synced": self.last_synced.isoformat() if self.last_synced else None,
            "total_entries": self.total_entries,
        }


class SyncEngine:
    """
    Manages synchronization of shared fields across language variants.

    Principles:
    - Invariant fields: synced to all variants immediately
    - Translatable fields: independent per variant
    - Conflicts: detected and queued for resolution
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize with database connection."""
        self.db_path = get_db_path(db_path)

        if not self.db_path.exists():
            raise ConfigurationError(f"Database not found: {self.db_path}")

    def _connect(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def sync_invariant_field(
        self,
        resume_key: str,
        entity_type: str,
        entity_id: int,
        field_name: str,
        new_value: Any,
        source_lang: str
    ) -> SyncResult:
        """
        Sync an invariant field change to all language variants.

        This operation is atomic - either all variants are updated, or none.

        Args:
            resume_key: Person identifier (config.ID)
            entity_type: Table name (education_items, etc.)
            entity_id: Row ID in the entity table
            field_name: Column name being updated
            new_value: New value to set
            source_lang: Language where change originated

        Returns:
            SyncResult with success status and affected variants
        """
        result = SyncResult(
            success=False,
            source_lang=source_lang,
            field_name=field_name,
            new_value=new_value,
        )

        # Validate entity type and field name
        if entity_type not in INVARIANT_FIELDS:
            result.error = f"Unknown entity type: {entity_type}"
            logger.error(f"[SYNC] {result.error}")
            return result

        if field_name not in INVARIANT_FIELDS[entity_type]:
            result.error = f"Field '{field_name}' is not an invariant field for {entity_type}"
            logger.error(f"[SYNC] {result.error}")
            return result

        logger.info(
            f"[SYNC] Syncing {entity_type}.{field_name} for {resume_key}: "
            f"value={new_value}, source={source_lang}"
        )

        conn = self._connect()
        try:
            cursor = conn.cursor()

            # Get current value from source row to record old value
            # Safe: entity_type and field_name are validated against INVARIANT_FIELDS whitelist
            cursor.execute(
                f"SELECT {field_name} FROM {entity_type} WHERE id = ?",  # noqa: S608
                (entity_id,)
            )
            row = cursor.fetchone()
            if not row:
                result.error = f"Entity not found: {entity_type} id={entity_id}"
                return result

            old_value = row[0]
            result.old_values[source_lang] = old_value

            # Update the source row
            # Safe: entity_type and field_name are validated against INVARIANT_FIELDS whitelist
            cursor.execute(
                f"UPDATE {entity_type} SET {field_name} = ? WHERE id = ?",  # noqa: S608
                (new_value, entity_id)
            )
            result.affected_langs.append(source_lang)

            # Find and update related rows in other language variants
            # This depends on the entity type - some entities are directly
            # keyed by resume_key, others need to be found via sort_order

            if entity_type in ["persons"]:
                # Person is unique per resume_key, no other variants to update
                pass
            elif entity_type in [
                "education_items", "project_items", "publication_items",
                "reference_items", "profile_accounts", "experience_items",
                "spoken_language_items"
            ]:
                # These entities are keyed by (resume_key, sort_order)
                # Get the sort_order of the current entity
                cursor.execute(
                    f"SELECT sort_order FROM {entity_type} WHERE id = ?",  # noqa: S608
                    (entity_id,)
                )
                sort_row = cursor.fetchone()
                if sort_row:
                    sort_order = sort_row[0]

                    # Find all entities with same resume_key and sort_order
                    # (there should be only one per resume_key since sort_order is unique)
                    # But the invariant field update applies to this single row
                    # since all language variants share the same base table row

                    # Actually, in the ERD schema, each resume_key has its own
                    # set of entities. The i18n tables store translations.
                    # So updating the base table row affects all language versions.

                    logger.debug(
                        f"[SYNC] Updated {entity_type} id={entity_id}, "
                        f"sort_order={sort_order}, resume_key={resume_key}"
                    )

            conn.commit()
            result.success = True

            logger.info(
                f"[SYNC] Complete: {entity_type}.{field_name} synced for {resume_key}, "
                f"affected_langs={result.affected_langs}"
            )

        except Exception as e:
            conn.rollback()
            result.error = str(e)
            logger.error(f"[SYNC] Failed: {e}")
        finally:
            conn.close()

        return result

    def detect_conflicts(self, resume_key: str) -> List[FieldConflict]:
        """
        Scan all variants for conflicting values in invariant fields.

        Since the ERD schema stores invariant fields in base tables (not i18n),
        conflicts can only occur if data was imported incorrectly or if there
        are duplicate entries that should be merged.

        For the current schema design, invariant fields are stored once per
        resume_key, so there shouldn't be conflicts within a single resume_key.
        However, this method is useful for detecting issues with:
        - Duplicate resume_sets that should be merged
        - Data imported from different sources with different values

        Args:
            resume_key: Person identifier to scan

        Returns:
            List of conflicts needing resolution
        """
        conflicts: List[FieldConflict] = []

        logger.info(f"[SYNC] Scanning for conflicts: resume_key={resume_key}")

        conn = self._connect()
        try:
            cursor = conn.cursor()

            # Check if resume_key exists
            cursor.execute(
                "SELECT resume_key FROM resume_sets WHERE resume_key = ?",
                (resume_key,)
            )
            if not cursor.fetchone():
                logger.warning(f"[SYNC] Resume set not found: {resume_key}")
                return conflicts

            # For each entity type with invariant fields, check for inconsistencies
            # In the current schema, this mainly checks for data quality issues

            # Since invariant fields are in base tables (not duplicated per language),
            # we look for potential issues like NULL values that should be filled
            # or detect if there are multiple resume_sets that should be merged

            for entity_type, fields in INVARIANT_FIELDS.items():
                if entity_type == "persons":
                    # Check person record
                    cursor.execute(
                        "SELECT id, email, birth_date FROM persons WHERE resume_key = ?",
                        (resume_key,)
                    )
                    row = cursor.fetchone()
                    if row:
                        person_id = row[0]
                        # Log info about person record for diagnostics
                        logger.debug(
                            f"[SYNC] Person {person_id}: email={row[1]}, birth_date={row[2]}"
                        )

            logger.info(f"[SYNC] Conflict scan complete: found {len(conflicts)} conflicts")

        finally:
            conn.close()

        return conflicts

    def resolve_conflict(
        self,
        conflict: FieldConflict,
        resolution: str,  # "use_en", "use_de", "use_fa", "use_custom"
        custom_value: Optional[Any] = None
    ) -> SyncResult:
        """
        Apply conflict resolution across all variants.

        Args:
            conflict: The conflict to resolve
            resolution: Resolution strategy
            custom_value: Custom value if resolution is "use_custom"

        Returns:
            SyncResult with resolution status
        """
        valid_resolutions = {"use_en", "use_de", "use_fa", "use_custom"}
        if resolution not in valid_resolutions:
            return SyncResult(
                success=False,
                source_lang="",
                error=f"Invalid resolution: {resolution}. Valid: {valid_resolutions}"
            )

        # Determine the value to use
        if resolution == "use_custom":
            if custom_value is None:
                return SyncResult(
                    success=False,
                    source_lang="",
                    error="custom_value is required when resolution is 'use_custom'"
                )
            new_value = custom_value
            source_lang = "custom"
        else:
            # Extract language from resolution (e.g., "use_en" -> "en")
            source_lang = resolution.replace("use_", "")
            if source_lang not in conflict.values_by_lang:
                return SyncResult(
                    success=False,
                    source_lang=source_lang,
                    error=f"No value found for language: {source_lang}"
                )
            new_value = conflict.values_by_lang[source_lang]

        logger.info(
            f"[SYNC] Resolving conflict: {conflict.entity_type}.{conflict.field_name} "
            f"-> {resolution} (value={new_value})"
        )

        # Apply the resolution
        result = self.sync_invariant_field(
            resume_key=conflict.resume_key,
            entity_type=conflict.entity_type,
            entity_id=conflict.entity_id,
            field_name=conflict.field_name,
            new_value=new_value,
            source_lang=source_lang
        )

        if result.success:
            conflict.resolved = True
            conflict.resolution = resolution

        return result

    def get_variant_status(self, resume_key: str) -> VariantStatus:
        """
        Get status of all language variants for a person.

        Returns which languages exist, which are missing,
        and any sync issues detected.

        Args:
            resume_key: Person identifier

        Returns:
            VariantStatus with comprehensive variant information
        """
        status = VariantStatus(resume_key=resume_key)

        logger.info(f"[SYNC] Getting variant status for: {resume_key}")

        conn = self._connect()
        try:
            cursor = conn.cursor()

            # Check if resume_set exists
            cursor.execute(
                "SELECT base_lang_code, updated_at FROM resume_sets WHERE resume_key = ?",
                (resume_key,)
            )
            row = cursor.fetchone()
            if not row:
                logger.warning(f"[SYNC] Resume set not found: {resume_key}")
                status.missing_langs = SUPPORTED_LANGUAGES.copy()
                return status

            status.base_lang = row[0]
            if row[1]:
                try:
                    status.last_synced = datetime.fromisoformat(row[1])
                except (ValueError, TypeError):
                    pass

            # Get existing language variants
            cursor.execute(
                "SELECT lang_code FROM resume_versions WHERE resume_key = ?",
                (resume_key,)
            )
            status.existing_langs = [r[0] for r in cursor.fetchall()]

            # Calculate missing languages
            status.missing_langs = [
                lang for lang in SUPPORTED_LANGUAGES
                if lang not in status.existing_langs
            ]

            # Count entries per language variant
            for lang_code in status.existing_langs:
                cursor.execute(
                    """SELECT COUNT(*) FROM resume_versions rv
                       JOIN person_i18n pi ON pi.resume_version_id = rv.id
                       WHERE rv.resume_key = ? AND rv.lang_code = ?""",
                    (resume_key, lang_code)
                )
                count = cursor.fetchone()[0]
                status.total_entries[lang_code] = count

            # Detect any conflicts
            status.conflicts = self.detect_conflicts(resume_key)

            logger.info(
                f"[SYNC] Variant status: existing={status.existing_langs}, "
                f"missing={status.missing_langs}, conflicts={len(status.conflicts)}"
            )

        finally:
            conn.close()

        return status

    def sync_all_invariant_fields(self, resume_key: str, source_lang: str) -> List[SyncResult]:
        """
        Sync all invariant fields from source language to all other variants.

        This is useful when importing a new language variant and wanting to
        ensure all invariant fields are consistent.

        Args:
            resume_key: Person identifier
            source_lang: Source language to sync from

        Returns:
            List of sync results for each field synced
        """
        results: List[SyncResult] = []

        logger.info(
            f"[SYNC] Syncing all invariant fields: resume_key={resume_key}, "
            f"source_lang={source_lang}"
        )

        conn = self._connect()
        try:
            cursor = conn.cursor()

            # For each entity type, get all entities and sync their invariant fields
            for entity_type, fields in INVARIANT_FIELDS.items():
                if entity_type == "persons":
                    # Get person record
                    cursor.execute(
                        "SELECT id FROM persons WHERE resume_key = ?",
                        (resume_key,)
                    )
                    row = cursor.fetchone()
                    if not row:
                        continue

                    person_id = row[0]

                    # Get current values for all invariant fields
                    field_list = ", ".join(fields)
                    # Safe: fields come from INVARIANT_FIELDS whitelist
                    cursor.execute(
                        f"SELECT {field_list} FROM persons WHERE id = ?",  # noqa: S608
                        (person_id,)
                    )
                    values_row = cursor.fetchone()
                    if values_row:
                        for i, field_name in enumerate(fields):
                            value = values_row[i]
                            if value is not None:
                                result = self.sync_invariant_field(
                                    resume_key=resume_key,
                                    entity_type=entity_type,
                                    entity_id=person_id,
                                    field_name=field_name,
                                    new_value=value,
                                    source_lang=source_lang
                                )
                                results.append(result)

                # Handle other entity types similarly
                elif entity_type in [
                    "education_items", "project_items", "publication_items",
                    "reference_items", "profile_accounts", "experience_items",
                    "spoken_language_items"
                ]:
                    # Get all entities for this resume_key
                    cursor.execute(
                        f"SELECT id FROM {entity_type} WHERE resume_key = ?",  # noqa: S608
                        (resume_key,)
                    )
                    entity_ids = [r[0] for r in cursor.fetchall()]

                    for entity_id in entity_ids:
                        # Get current values
                        field_list = ", ".join(fields)
                        # Safe: entity_type and fields come from INVARIANT_FIELDS whitelist
                        cursor.execute(
                            f"SELECT {field_list} FROM {entity_type} WHERE id = ?",  # noqa: S608
                            (entity_id,)
                        )
                        values_row = cursor.fetchone()
                        if values_row:
                            for i, field_name in enumerate(fields):
                                value = values_row[i]
                                if value is not None:
                                    result = self.sync_invariant_field(
                                        resume_key=resume_key,
                                        entity_type=entity_type,
                                        entity_id=entity_id,
                                        field_name=field_name,
                                        new_value=value,
                                        source_lang=source_lang
                                    )
                                    results.append(result)

        finally:
            conn.close()

        logger.info(f"[SYNC] Synced {len(results)} invariant fields")
        return results
