"""
Reference Integrity Module for CV Generator.

Provides comprehensive integrity checks for:
- Stable entry IDs (missing, duplicate, dangling references)
- Person entity IDs
- Tag reference integrity (type_key → tag catalog)
- Cross-language linking

This module implements the "doctor/integrity" functionality required by WebUI-02.

Data Folder LOCKED:
==================
This module does NOT modify files in data/. All operations are read-only checks.
"""
import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from .db import get_db_path
from .errors import ConfigurationError
logger = logging.getLogger(__name__)
MAX_ISSUES_PER_CATEGORY = 20

class IssueSeverity(Enum):
    """Severity level of an integrity issue."""
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'

@dataclass
class IntegrityIssue:
    """
    Represents a single integrity issue.

    Attributes:
        category: Category of the issue (e.g., "stable_id", "tag_reference")
        severity: Severity level
        message: Human-readable description of the issue
        entity_type: Type of entity involved (e.g., "entry", "person")
        entity_id: ID of the affected entity (if applicable)
        details: Additional details about the issue
    """
    category: str
    severity: IssueSeverity
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {'category': self.category, 'severity': self.severity.value, 'message': self.message}
        if self.entity_type:
            result['entity_type'] = self.entity_type
        if self.entity_id:
            result['entity_id'] = self.entity_id
        if self.details:
            result['details'] = self.details
        return result

@dataclass
class IntegrityReport:
    """
    Complete integrity check report.

    Attributes:
        issues: List of integrity issues found
        stats: Statistics about the checks performed
    """
    issues: List[IntegrityIssue] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum((1 for i in self.issues if i.severity == IssueSeverity.ERROR))

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum((1 for i in self.issues if i.severity == IssueSeverity.WARNING))

    @property
    def info_count(self) -> int:
        """Count of info-level issues."""
        return sum((1 for i in self.issues if i.severity == IssueSeverity.INFO))

    @property
    def is_healthy(self) -> bool:
        """True if no error-level issues."""
        return self.error_count == 0

    def add_issue(self, issue: IntegrityIssue) -> None:
        """Add an issue to the report."""
        self.issues.append(issue)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {'healthy': self.is_healthy, 'summary': {'errors': self.error_count, 'warnings': self.warning_count, 'info': self.info_count, 'total': len(self.issues)}, 'stats': self.stats, 'issues': [i.to_dict() for i in self.issues]}

    def format_text(self, verbose: bool=False) -> str:
        """Format report as human-readable text."""
        lines = []
        status_emoji = '✅' if self.is_healthy else '❌'
        lines.append(f'\n{status_emoji} Reference Integrity Check')
        lines.append('=' * 40)
        lines.append(f'   Errors: {self.error_count} | Warnings: {self.warning_count} | Info: {self.info_count}')
        lines.append('')
        if self.stats:
            lines.append('📊 Statistics:')
            for key, value in self.stats.items():
                lines.append(f'   {key}: {value}')
            lines.append('')
        if self.issues:
            lines.append('🔍 Issues Found:')
            categories: Dict[str, List[IntegrityIssue]] = {}
            for issue in self.issues:
                if issue.category not in categories:
                    categories[issue.category] = []
                categories[issue.category].append(issue)
            for category, issues in categories.items():
                lines.append(f'\n   [{category.upper()}] ({len(issues)} issues)')
                for issue in issues[:10]:
                    icon = '❌' if issue.severity == IssueSeverity.ERROR else '⚠️'
                    if issue.severity == IssueSeverity.INFO:
                        icon = 'ℹ️'
                    lines.append(f'   {icon} {issue.message}')
                    if verbose and issue.details:
                        for key, val in issue.details.items():
                            lines.append(f'      {key}: {val}')
                if len(issues) > 10:
                    lines.append(f'   ... and {len(issues) - 10} more')
        else:
            lines.append('✅ No issues found!')
        return '\n'.join(lines)
UUID_PATTERN = re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)

def is_valid_uuid4(id_str: str) -> bool:
    """
    Check if a string is a valid UUID format.

    This validates the general UUID format (8-4-4-4-12 hex digits).
    While we generate UUID4 for new IDs, we accept any valid UUID format
    for backwards compatibility.

    Args:
        id_str: String to validate

    Returns:
        True if valid UUID format, False otherwise
    """
    if not id_str:
        return False
    return bool(UUID_PATTERN.match(id_str))

def check_stable_entry_ids(cursor: sqlite3.Cursor, report: IntegrityReport) -> None:
    """
    Check stable_entry table for integrity issues.

    Checks:
    - Missing stable IDs (entries without stable_id links)
    - Duplicate stable IDs (shouldn't happen with UUIDs)
    - Dangling stable_id references (stable_entry without linked entries)
    - Invalid stable_id format

    Args:
        cursor: Database cursor
        report: Report to add issues to
    """
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stable_entry'")
    if not cursor.fetchone():
        report.stats['stable_entry_table_exists'] = False
        report.add_issue(IntegrityIssue(category='stable_id', severity=IssueSeverity.INFO, message='stable_entry table does not exist (CRUD schema not initialized)'))
        return
    report.stats['stable_entry_table_exists'] = True
    cursor.execute('SELECT COUNT(*) FROM stable_entry')
    stable_count = cursor.fetchone()[0]
    report.stats['stable_entries'] = stable_count
    cursor.execute('SELECT id, section FROM stable_entry')
    invalid_format_count = 0
    for stable_id, section in cursor.fetchall():
        if not is_valid_uuid4(stable_id):
            invalid_format_count += 1
            if invalid_format_count <= MAX_ISSUES_PER_CATEGORY:
                report.add_issue(IntegrityIssue(category='stable_id', severity=IssueSeverity.ERROR, message=f'Invalid stable_id format: {stable_id[:20]}...', entity_type='stable_entry', entity_id=stable_id, details={'section': section}))
    if invalid_format_count > 0:
        report.stats['invalid_stable_id_format'] = invalid_format_count
    cursor.execute('SELECT id, COUNT(*) as cnt FROM stable_entry\n           GROUP BY id HAVING cnt > 1')
    duplicates = cursor.fetchall()
    if duplicates:
        report.stats['duplicate_stable_ids'] = len(duplicates)
        for stable_id, count in duplicates[:MAX_ISSUES_PER_CATEGORY]:
            report.add_issue(IntegrityIssue(category='stable_id', severity=IssueSeverity.ERROR, message=f'Duplicate stable_id found: {stable_id[:8]}... ({count} occurrences)', entity_type='stable_entry', entity_id=stable_id))
    cursor.execute('SELECT se.id, se.section, se.base_person\n           FROM stable_entry se\n           LEFT JOIN entry_lang_link ell ON se.id = ell.stable_id\n           WHERE ell.stable_id IS NULL')
    dangling = cursor.fetchall()
    if dangling:
        report.stats['dangling_stable_entries'] = len(dangling)
        for stable_id, section, base_person in dangling[:MAX_ISSUES_PER_CATEGORY]:
            report.add_issue(IntegrityIssue(category='stable_id', severity=IssueSeverity.WARNING, message=f'Stable entry has no linked entries: {stable_id[:8]}...', entity_type='stable_entry', entity_id=stable_id, details={'section': section, 'base_person': base_person}))

def check_entry_lang_links(cursor: sqlite3.Cursor, report: IntegrityReport) -> None:
    """
    Check entry_lang_link table for integrity issues.

    Checks:
    - Entries with multiple stable_id links (shouldn't happen)
    - Links to non-existent entries
    - Links to non-existent stable_entries

    Args:
        cursor: Database cursor
        report: Report to add issues to
    """
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entry_lang_link'")
    if not cursor.fetchone():
        report.stats['entry_lang_link_table_exists'] = False
        return
    report.stats['entry_lang_link_table_exists'] = True
    cursor.execute('SELECT COUNT(*) FROM entry_lang_link')
    link_count = cursor.fetchone()[0]
    report.stats['entry_lang_links'] = link_count
    cursor.execute('SELECT ell.entry_id, ell.stable_id, ell.language\n           FROM entry_lang_link ell\n           LEFT JOIN entry e ON ell.entry_id = e.id\n           WHERE e.id IS NULL')
    orphan_links = cursor.fetchall()
    if orphan_links:
        report.stats['orphan_entry_links'] = len(orphan_links)
        for entry_id, stable_id, language in orphan_links[:MAX_ISSUES_PER_CATEGORY]:
            report.add_issue(IntegrityIssue(category='entry_link', severity=IssueSeverity.ERROR, message=f'Entry link references deleted entry: {entry_id}', entity_type='entry_lang_link', entity_id=str(entry_id), details={'stable_id': stable_id[:8] + '...', 'language': language}))
    cursor.execute('SELECT ell.entry_id, ell.stable_id, ell.language\n           FROM entry_lang_link ell\n           LEFT JOIN stable_entry se ON ell.stable_id = se.id\n           WHERE se.id IS NULL')
    orphan_stable = cursor.fetchall()
    if orphan_stable:
        report.stats['orphan_stable_links'] = len(orphan_stable)
        for entry_id, stable_id, language in orphan_stable[:MAX_ISSUES_PER_CATEGORY]:
            report.add_issue(IntegrityIssue(category='entry_link', severity=IssueSeverity.ERROR, message=f'Entry link references deleted stable_entry: {stable_id[:8]}...', entity_type='entry_lang_link', entity_id=str(entry_id), details={'stable_id': stable_id, 'language': language}))
    cursor.execute('SELECT entry_id, COUNT(DISTINCT stable_id) as cnt\n           FROM entry_lang_link\n           GROUP BY entry_id\n           HAVING cnt > 1')
    multi_linked = cursor.fetchall()
    if multi_linked:
        report.stats['multi_linked_entries'] = len(multi_linked)
        for entry_id, count in multi_linked[:MAX_ISSUES_PER_CATEGORY]:
            report.add_issue(IntegrityIssue(category='entry_link', severity=IssueSeverity.ERROR, message=f'Entry linked to multiple stable IDs: {entry_id}', entity_type='entry', entity_id=str(entry_id), details={'stable_id_count': count}))

def check_person_entity_ids(cursor: sqlite3.Cursor, report: IntegrityReport) -> None:
    """
    Check person_entity table for ID integrity.

    Checks:
    - Invalid person_entity IDs (should be UUID4)
    - Orphan person_entity_variant links

    Args:
        cursor: Database cursor
        report: Report to add issues to
    """
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='person_entity'")
    if not cursor.fetchone():
        report.stats['person_entity_table_exists'] = False
        return
    report.stats['person_entity_table_exists'] = True
    cursor.execute('SELECT COUNT(*) FROM person_entity')
    entity_count = cursor.fetchone()[0]
    report.stats['person_entities'] = entity_count
    cursor.execute('SELECT id, display_name FROM person_entity')
    invalid_format_count = 0
    for entity_id, display_name in cursor.fetchall():
        if not is_valid_uuid4(entity_id):
            invalid_format_count += 1
            if invalid_format_count <= MAX_ISSUES_PER_CATEGORY:
                report.add_issue(IntegrityIssue(category='person_entity', severity=IssueSeverity.ERROR, message=f'Invalid person_entity ID format: {entity_id[:20]}...', entity_type='person_entity', entity_id=entity_id, details={'display_name': display_name}))
    if invalid_format_count > 0:
        report.stats['invalid_person_entity_id_format'] = invalid_format_count
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='person_entity_variant'")
    if not cursor.fetchone():
        return
    cursor.execute('SELECT pev.person_entity_id, pev.person_id, pev.language\n           FROM person_entity_variant pev\n           LEFT JOIN person_entity pe ON pev.person_entity_id = pe.id\n           WHERE pe.id IS NULL')
    orphan_links = cursor.fetchall()
    if orphan_links:
        report.stats['orphan_variant_links'] = len(orphan_links)
        for entity_id, person_id, language in orphan_links[:MAX_ISSUES_PER_CATEGORY]:
            report.add_issue(IntegrityIssue(category='person_entity', severity=IssueSeverity.ERROR, message=f'Variant link references deleted person_entity: {entity_id[:8]}...', entity_type='person_entity_variant', entity_id=str(person_id), details={'person_entity_id': entity_id, 'language': language}))
    cursor.execute('SELECT pev.person_entity_id, pev.person_id, pev.language\n           FROM person_entity_variant pev\n           LEFT JOIN person p ON pev.person_id = p.id\n           WHERE p.id IS NULL')
    orphan_person_links = cursor.fetchall()
    if orphan_person_links:
        report.stats['orphan_person_links'] = len(orphan_person_links)
        for entity_id, person_id, language in orphan_person_links[:MAX_ISSUES_PER_CATEGORY]:
            report.add_issue(IntegrityIssue(category='person_entity', severity=IssueSeverity.ERROR, message=f'Variant link references deleted person: {person_id}', entity_type='person_entity_variant', entity_id=str(person_id), details={'person_entity_id': entity_id[:8] + '...', 'language': language}))

def check_tag_references(cursor: sqlite3.Cursor, report: IntegrityReport) -> None:
    """
    Check tag references in entry data for integrity.

    Checks:
    - type_key values in entry data that don't exist in tag table
    - entry_tag links to non-existent tags

    Args:
        cursor: Database cursor
        report: Report to add issues to
    """
    cursor.execute('SELECT name FROM tag')
    existing_tags = {row[0] for row in cursor.fetchall()}
    report.stats['existing_tags'] = len(existing_tags)
    cursor.execute("SELECT e.id, e.section, p.slug, e.data_json\n           FROM entry e\n           JOIN person p ON e.person_id = p.id\n           WHERE e.data_json LIKE '%type_key%'")
    missing_tag_refs: Dict[str, List[str]] = {}
    for entry_id, section, person_slug, data_json in cursor.fetchall():
        try:
            data = json.loads(data_json)
            type_keys = data.get('type_key', [])
            if isinstance(type_keys, list):
                for tag_name in type_keys:
                    if tag_name and tag_name not in existing_tags:
                        if tag_name not in missing_tag_refs:
                            missing_tag_refs[tag_name] = []
                        missing_tag_refs[tag_name].append(str(entry_id))
        except (json.JSONDecodeError, TypeError):
            pass
    if missing_tag_refs:
        report.stats['missing_tag_references'] = len(missing_tag_refs)
        for tag_name, entry_ids in list(missing_tag_refs.items())[:MAX_ISSUES_PER_CATEGORY]:
            report.add_issue(IntegrityIssue(category='tag_reference', severity=IssueSeverity.WARNING, message=f"type_key references unknown tag: '{tag_name}'", entity_type='tag', entity_id=tag_name, details={'entry_ids': entry_ids[:5], 'entry_count': len(entry_ids)}))
    cursor.execute('SELECT et.entry_id, et.tag_id\n           FROM entry_tag et\n           LEFT JOIN tag t ON et.tag_id = t.id\n           WHERE t.id IS NULL')
    orphan_tag_links = cursor.fetchall()
    if orphan_tag_links:
        report.stats['orphan_tag_links'] = len(orphan_tag_links)
        for entry_id, tag_id in orphan_tag_links[:MAX_ISSUES_PER_CATEGORY]:
            report.add_issue(IntegrityIssue(category='tag_reference', severity=IssueSeverity.ERROR, message=f'Entry-tag link references deleted tag: {tag_id}', entity_type='entry_tag', entity_id=str(entry_id), details={'tag_id': tag_id}))

def check_entries_without_stable_ids(cursor: sqlite3.Cursor, report: IntegrityReport) -> None:
    """
    Check for entries that don't have stable IDs assigned.

    This is informational - entries imported before CRUD schema
    won't have stable IDs.

    Args:
        cursor: Database cursor
        report: Report to add issues to
    """
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entry_lang_link'")
    if not cursor.fetchone():
        return
    cursor.execute('SELECT e.id, e.section, p.slug\n           FROM entry e\n           JOIN person p ON e.person_id = p.id\n           LEFT JOIN entry_lang_link ell ON e.id = ell.entry_id\n           WHERE ell.entry_id IS NULL\n           AND e.order_idx >= 0')
    entries_without_ids = cursor.fetchall()
    if entries_without_ids:
        report.stats['entries_without_stable_ids'] = len(entries_without_ids)
        report.add_issue(IntegrityIssue(category='stable_id', severity=IssueSeverity.INFO, message=f"{len(entries_without_ids)} entries don't have stable IDs assigned", details={'hint': 'Use link_existing_entries() to assign stable IDs', 'sample_entries': [{'id': e[0], 'section': e[1], 'person': e[2]} for e in entries_without_ids[:5]]}))

def run_integrity_check(db_path: Optional[Path]=None) -> IntegrityReport:
    """
    Run comprehensive integrity checks on the database.

    Performs all available integrity checks and returns a complete report.

    Args:
        db_path: Path to the database file. Uses default if None.

    Returns:
        IntegrityReport with all findings

    Raises:
        ConfigurationError: If database doesn't exist.
    """
    db_path = get_db_path(db_path)
    if not db_path.exists():
        raise ConfigurationError(f'Database not found: {db_path}')
    logger.info(f'Running integrity check on: {db_path}')
    report = IntegrityReport()
    report.stats['database'] = str(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        check_stable_entry_ids(cursor, report)
        check_entry_lang_links(cursor, report)
        check_person_entity_ids(cursor, report)
        check_tag_references(cursor, report)
        check_entries_without_stable_ids(cursor, report)
        logger.info(f'Integrity check complete. Errors: {report.error_count}, Warnings: {report.warning_count}')
    finally:
        conn.close()
    return report

def validate_id_format(id_str: str) -> Dict[str, Any]:
    """
    Validate an ID string format.

    Args:
        id_str: ID string to validate

    Returns:
        Dict with validation result
    """
    if not id_str:
        return {'valid': False, 'format': None, 'error': 'Empty ID'}
    if is_valid_uuid4(id_str):
        return {'valid': True, 'format': 'uuid4'}
    if id_str.isdigit():
        return {'valid': True, 'format': 'integer', 'note': 'Legacy integer ID'}
    return {'valid': False, 'format': 'unknown', 'error': 'Invalid ID format'}
