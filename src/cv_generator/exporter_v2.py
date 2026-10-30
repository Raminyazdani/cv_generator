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
    cv_data = exporter.export(resume_key="example_person", lang_code="en")

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
from .export_mappings import BASICS_FIELD_ORDER, CERT_ISSUER_FIELD_ORDER, CERTIFICATION_FIELD_ORDER, EDUCATION_FIELD_ORDER, EXPERIENCE_FIELD_ORDER, LANGUAGE_CERT_FIELD_ORDER, LANGUAGE_FIELD_ORDER, LOCATION_FIELD_ORDER, PICTURE_FIELD_ORDER, PROFICIENCY_FIELD_ORDER, PROFILE_FIELD_ORDER, PROJECT_FIELD_ORDER, PUBLICATION_FIELD_ORDER, REFERENCE_FIELD_ORDER, SKILL_ITEM_FIELD_ORDER, build_ordered_cv, ordered_dict_from_mapping
logger = logging.getLogger(__name__)

@dataclass
class ExportResult:
    """Result of exporting a single CV variant."""
    success: bool
    resume_key: str
    lang_code: str
    output_path: Optional[Path] = None
    stats: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON/logging."""
        return {'success': self.success, 'resume_key': self.resume_key, 'lang_code': self.lang_code, 'output_path': str(self.output_path) if self.output_path else None, 'stats': self.stats, 'warnings': self.warnings, 'error': self.error, 'duration_ms': self.duration_ms}

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
        return {'total_files': self.total_files, 'successful': self.successful, 'failed': self.failed, 'results': [r.to_dict() for r in self.results], 'duration_ms': self.duration_ms}

class CVExporter:
    """
    Lossless DB to JSON export engine.

    Usage:
        exporter = CVExporter(db_path)

        # Export to dict
        cv_data = exporter.export(resume_key="example_person", lang_code="en")

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
            self._conn.execute('PRAGMA foreign_keys = ON')
        return self._conn

    def _close(self) -> None:
        """Close database connection if open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def export(self, resume_key: str, lang_code: str) -> dict:
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
            version_id = self._get_version_id(conn, resume_key, lang_code)
            if version_id is None:
                raise ValueError(f'No resume version found for resume_key={resume_key}, lang_code={lang_code}')
            logger.info(f'[EXPORT] Starting export: resume_key={resume_key}, lang={lang_code}')
            logger.info(f'[EXPORT] Found resume_version: id={version_id}')
            sections = {}
            logger.info('[EXPORT] Exporting config block...')
            sections['config'] = self._export_config(resume_key, lang_code)
            logger.info('[EXPORT] Exporting basics...')
            sections['basics'] = self._export_basics(conn, resume_key, version_id)
            logger.info('[EXPORT] Exporting profiles...')
            sections['profiles'] = self._export_profiles(conn, resume_key, version_id)
            logger.info('[EXPORT] Exporting education...')
            sections['education'] = self._export_education(conn, resume_key, version_id)
            logger.info('[EXPORT] Exporting languages...')
            sections['languages'] = self._export_languages(conn, resume_key, version_id)
            logger.info('[EXPORT] Exporting certifications...')
            sections['workshop_and_certifications'] = self._export_certifications(conn, resume_key, version_id)
            logger.info('[EXPORT] Exporting skills...')
            sections['skills'] = self._export_skills(conn, resume_key, version_id)
            logger.info('[EXPORT] Exporting experiences...')
            sections['experiences'] = self._export_experiences(conn, resume_key, version_id)
            logger.info('[EXPORT] Exporting projects...')
            sections['projects'] = self._export_projects(conn, resume_key, version_id)
            logger.info('[EXPORT] Exporting publications...')
            sections['publications'] = self._export_publications(conn, resume_key, version_id)
            logger.info('[EXPORT] Exporting references...')
            sections['references'] = self._export_references(conn, resume_key, version_id)
            result = build_ordered_cv(sections)
            duration = (time.time() - start_time) * 1000
            logger.info(f'[EXPORT] Complete: {len(sections)} sections exported in {duration:.0f}ms')
            return dict(result)
        finally:
            self._close()

    def export_to_file(self, resume_key: str, lang_code: str, output_path: Path, pretty: bool=True, ensure_ascii: bool=False) -> ExportResult:
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
        result = ExportResult(success=False, resume_key=resume_key, lang_code=lang_code)
        try:
            cv_data = self.export(resume_key, lang_code)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(cv_data, f, indent=2 if pretty else None, ensure_ascii=ensure_ascii)
            result.success = True
            result.output_path = output_path
            size = output_path.stat().st_size
            logger.info(f'[EXPORT] Written to: {output_path} ({size:,} bytes)')
        except Exception as e:
            result.error = str(e)
            logger.error(f'[EXPORT] Error: {e}')
        result.duration_ms = (time.time() - start_time) * 1000
        return result

    def export_all_variants(self, resume_key: str, output_dir: Path) -> List[ExportResult]:
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
            cursor.execute('SELECT lang_code FROM resume_versions WHERE resume_key = ? ORDER BY lang_code', (resume_key,))
            rows = cursor.fetchall()
            for row in rows:
                lang_code = row['lang_code']
                if lang_code == 'en':
                    filename = f"{resume_key.replace('_', '')}.json"
                else:
                    filename = f"{resume_key.replace('_', '')}_{lang_code}.json"
                output_path = output_dir / filename
                self._close()
                result = self.export_to_file(resume_key, lang_code, output_path)
                results.append(result)
        finally:
            self._close()
        return results

    def export_all(self, output_dir: Path) -> ExportBatchResult:
        """
        Export all CVs in the database.

        Args:
            output_dir: Directory to write files to

        Returns:
            ExportBatchResult with summary and individual results
        """
        start_time = time.time()
        output_dir = Path(output_dir)
        result = ExportBatchResult(total_files=0, successful=0, failed=0, results=[])
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT resume_key FROM resume_sets ORDER BY resume_key')
            resume_keys = [row['resume_key'] for row in cursor.fetchall()]
            self._close()
            for resume_key in resume_keys:
                variant_results = self.export_all_variants(resume_key, output_dir)
                result.results.extend(variant_results)
            result.total_files = len(result.results)
            result.successful = sum((1 for r in result.results if r.success))
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
            cursor.execute('SELECT resume_key, lang_code FROM resume_versions ORDER BY resume_key, lang_code')
            return [(row['resume_key'], row['lang_code']) for row in cursor.fetchall()]
        finally:
            self._close()

    def _get_version_id(self, conn: sqlite3.Connection, resume_key: str, lang_code: str) -> Optional[int]:
        """Get resume_version.id for a given resume_key and lang_code."""
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM resume_versions WHERE resume_key = ? AND lang_code = ?', (resume_key, lang_code))
        row = cursor.fetchone()
        return row['id'] if row else None

    def _export_config(self, resume_key: str, lang_code: str) -> OrderedDict:
        """Build the config block."""
        return OrderedDict([('lang', lang_code), ('ID', resume_key)])

    def _export_basics(self, conn: sqlite3.Connection, resume_key: str, version_id: int) -> List[OrderedDict]:
        """Export basics section with all nested structures."""
        cursor = conn.cursor()
        cursor.execute('\n            SELECT p.*, pi.fname, pi.lname, pi.summary\n            FROM persons p\n            LEFT JOIN person_i18n pi ON p.id = pi.person_id AND pi.resume_version_id = ?\n            WHERE p.resume_key = ?\n            ', (version_id, resume_key))
        person_row = cursor.fetchone()
        if not person_row:
            return []
        person_id = person_row['id']
        phone = OrderedDict()
        if person_row['phone_country_code'] is not None:
            phone['countryCode'] = person_row['phone_country_code']
        if person_row['phone_number'] is not None:
            phone['number'] = person_row['phone_number']
        if person_row['phone_formatted'] is not None:
            phone['formatted'] = person_row['phone_formatted']
        if not phone:
            phone = OrderedDict([('countryCode', None), ('number', None), ('formatted', None)])
        cursor.execute('\n            SELECT pli.label_text\n            FROM person_labels pl\n            JOIN person_label_i18n pli ON pl.id = pli.label_id AND pli.resume_version_id = ?\n            WHERE pl.person_id = ?\n            ORDER BY pl.sort_order\n            ', (version_id, person_id))
        labels = [row['label_text'] for row in cursor.fetchall()]
        cursor.execute('\n            SELECT pl.postal_code, pli.address, pli.city, pli.region, pli.country\n            FROM person_locations pl\n            LEFT JOIN person_location_i18n pli ON pl.id = pli.location_id AND pli.resume_version_id = ?\n            WHERE pl.person_id = ?\n            ORDER BY pl.sort_order\n            ', (version_id, person_id))
        locations = []
        for loc_row in cursor.fetchall():
            loc = ordered_dict_from_mapping({'address': loc_row['address'], 'postalCode': loc_row['postal_code'], 'city': loc_row['city'], 'region': loc_row['region'], 'country': loc_row['country']}, LOCATION_FIELD_ORDER)
            locations.append(loc)
        cursor.execute('\n            SELECT type_of, url\n            FROM person_pictures\n            WHERE person_id = ?\n            ORDER BY sort_order\n            ', (person_id,))
        pictures = []
        for pic_row in cursor.fetchall():
            pic = ordered_dict_from_mapping({'type_of': pic_row['type_of'], 'URL': pic_row['url']}, PICTURE_FIELD_ORDER)
            pictures.append(pic)
        basic = ordered_dict_from_mapping({'fname': person_row['fname'], 'lname': person_row['lname'], 'label': labels, 'email': person_row['email'], 'phone': phone if phone else None, 'birthDate': person_row['birth_date'], 'summary': person_row['summary'], 'location': locations, 'Pictures': pictures}, BASICS_FIELD_ORDER)
        return [basic]

    def _export_profiles(self, conn: sqlite3.Connection, resume_key: str, version_id: int) -> List[OrderedDict]:
        """Export profiles section."""
        cursor = conn.cursor()
        cursor.execute('\n            SELECT pa.username, pa.url, pa.uuid, pai.network_display\n            FROM profile_accounts pa\n            LEFT JOIN profile_account_i18n pai ON pa.id = pai.profile_account_id\n                AND pai.resume_version_id = ?\n            WHERE pa.resume_key = ?\n            ORDER BY pa.sort_order\n            ', (version_id, resume_key))
        profiles = []
        for row in cursor.fetchall():
            profile_data = {'network': row['network_display'], 'username': row['username'], 'url': row['url']}
            if row['uuid']:
                profile_data['uuid'] = row['uuid']
            profile = ordered_dict_from_mapping(profile_data, PROFILE_FIELD_ORDER, include_none=False)
            profiles.append(profile)
        return profiles

    def _export_education(self, conn: sqlite3.Connection, resume_key: str, version_id: int) -> List[OrderedDict]:
        """Export education section with tags."""
        cursor = conn.cursor()
        cursor.execute('\n            SELECT ei.id, ei.start_date, ei.end_date, ei.end_date_text, ei.gpa, ei.logo_url,\n                   edu.institution, edu.location, edu.area, edu.study_type\n            FROM education_items ei\n            LEFT JOIN education_i18n edu ON ei.id = edu.education_item_id\n                AND edu.resume_version_id = ?\n            WHERE ei.resume_key = ?\n            ORDER BY ei.sort_order\n            ', (version_id, resume_key))
        education = []
        for row in cursor.fetchall():
            tags = self._get_tags_for_entity(conn, 'education', row['id'], version_id)
            end_date = row['end_date']
            if end_date is None and row['end_date_text']:
                end_date = row['end_date_text']
            edu = ordered_dict_from_mapping({'institution': row['institution'], 'location': row['location'], 'area': row['area'], 'studyType': row['study_type'], 'startDate': row['start_date'], 'endDate': end_date, 'gpa': row['gpa'] if row['gpa'] else '', 'logo_url': row['logo_url'] if row['logo_url'] else '', 'type_key': tags}, EDUCATION_FIELD_ORDER)
            education.append(edu)
        return education

    def _export_languages(self, conn: sqlite3.Connection, resume_key: str, version_id: int) -> List[OrderedDict]:
        """Export languages section with nested certifications."""
        cursor = conn.cursor()
        cursor.execute('\n            SELECT sli.id, sli.proficiency_cefr,\n                   sln.language_name, sln.proficiency_level, sln.proficiency_status\n            FROM spoken_language_items sli\n            LEFT JOIN spoken_language_i18n sln ON sli.id = sln.spoken_language_item_id\n                AND sln.resume_version_id = ?\n            WHERE sli.resume_key = ?\n            ORDER BY sli.sort_order\n            ', (version_id, resume_key))
        languages = []
        for lang_row in cursor.fetchall():
            lang_id = lang_row['id']
            proficiency = ordered_dict_from_mapping({'level': lang_row['proficiency_level'], 'CEFR': lang_row['proficiency_cefr'], 'status': lang_row['proficiency_status']}, PROFICIENCY_FIELD_ORDER)
            cursor.execute('\n                SELECT slc.overall, slc.reading, slc.writing, slc.listening, slc.speaking,\n                       slc.max_score, slc.min_score, slc.exam_date, slc.url,\n                       sci.test_name, sci.organization\n                FROM spoken_language_certs slc\n                LEFT JOIN spoken_language_cert_i18n sci ON slc.id = sci.cert_id\n                    AND sci.resume_version_id = ?\n                WHERE slc.spoken_language_item_id = ?\n                ORDER BY slc.sort_order\n                ', (version_id, lang_id))
            certifications = []
            for cert_row in cursor.fetchall():
                cert_data = {'test': cert_row['test_name'], 'organization': cert_row['organization'], 'overall': cert_row['overall'], 'reading': cert_row['reading'], 'writing': cert_row['writing'], 'listening': cert_row['listening'], 'speaking': cert_row['speaking'], 'maxScore': cert_row['max_score'], 'minScore': cert_row['min_score'], 'examDate': cert_row['exam_date'], 'URL': cert_row['url']}
                cert = ordered_dict_from_mapping(cert_data, LANGUAGE_CERT_FIELD_ORDER)
                certifications.append(cert)
            lang = ordered_dict_from_mapping({'language': lang_row['language_name'], 'proficiency': proficiency, 'certifications': certifications}, LANGUAGE_FIELD_ORDER)
            languages.append(lang)
        return languages

    def _export_certifications(self, conn: sqlite3.Connection, resume_key: str, version_id: int) -> List[OrderedDict]:
        """Export workshop_and_certifications with issuer grouping."""
        cursor = conn.cursor()
        cursor.execute('\n            SELECT ci.id, cii.issuer_name\n            FROM cert_issuers ci\n            LEFT JOIN cert_issuer_i18n cii ON ci.id = cii.issuer_id\n                AND cii.resume_version_id = ?\n            WHERE ci.resume_key = ?\n            ORDER BY ci.sort_order\n            ', (version_id, resume_key))
        issuer_groups = []
        for issuer_row in cursor.fetchall():
            issuer_id = issuer_row['id']
            cursor.execute('\n                SELECT c.id, c.is_certificate, c.date_text, c.date, c.url,\n                       ci.name, ci.duration\n                FROM certifications c\n                LEFT JOIN certification_i18n ci ON c.id = ci.certification_id\n                    AND ci.resume_version_id = ?\n                WHERE c.issuer_id = ?\n                ORDER BY c.sort_order\n                ', (version_id, issuer_id))
            certifications = []
            for cert_row in cursor.fetchall():
                tags = self._get_tags_for_entity(conn, 'certification', cert_row['id'], version_id)
                date_value = cert_row['date_text']
                if date_value is None:
                    date_value = cert_row['date']
                cert_data = {'name': cert_row['name'], 'date': date_value, 'duration': cert_row['duration'], 'certificate': bool(cert_row['is_certificate']), 'URL': cert_row['url']}
                if tags:
                    cert_data['type_key'] = tags
                cert = ordered_dict_from_mapping(cert_data, CERTIFICATION_FIELD_ORDER)
                certifications.append(cert)
            issuer_group = ordered_dict_from_mapping({'issuer': issuer_row['issuer_name'], 'certifications': certifications}, CERT_ISSUER_FIELD_ORDER)
            issuer_groups.append(issuer_group)
        return issuer_groups

    def _export_skills(self, conn: sqlite3.Connection, resume_key: str, version_id: int) -> OrderedDict:
        """Export skills as nested dict structure."""
        cursor = conn.cursor()
        cursor.execute('\n            SELECT sc.id, sci.name\n            FROM skill_categories sc\n            LEFT JOIN skill_category_i18n sci ON sc.id = sci.category_id\n                AND sci.resume_version_id = ?\n            WHERE sc.resume_key = ?\n            ORDER BY sc.sort_order\n            ', (version_id, resume_key))
        skills = OrderedDict()
        for cat_row in cursor.fetchall():
            cat_id = cat_row['id']
            cat_name = cat_row['name']
            cursor.execute('\n                SELECT ss.id, ssi.name\n                FROM skill_subcategories ss\n                LEFT JOIN skill_subcategory_i18n ssi ON ss.id = ssi.subcategory_id\n                    AND ssi.resume_version_id = ?\n                WHERE ss.category_id = ?\n                ORDER BY ss.sort_order\n                ', (version_id, cat_id))
            subcategories = OrderedDict()
            for subcat_row in cursor.fetchall():
                subcat_id = subcat_row['id']
                subcat_name = subcat_row['name']
                cursor.execute('\n                    SELECT si.id, sii.long_name, sii.short_name\n                    FROM skill_items si\n                    LEFT JOIN skill_item_i18n sii ON si.id = sii.skill_item_id\n                        AND sii.resume_version_id = ?\n                    WHERE si.subcategory_id = ?\n                    ORDER BY si.sort_order\n                    ', (version_id, subcat_id))
                items = []
                for item_row in cursor.fetchall():
                    tags = self._get_tags_for_entity(conn, 'skill_item', item_row['id'], version_id)
                    item_data = {'long_name': item_row['long_name'], 'short_name': item_row['short_name']}
                    if tags:
                        item_data['type_key'] = tags
                    item = ordered_dict_from_mapping(item_data, SKILL_ITEM_FIELD_ORDER)
                    items.append(item)
                subcategories[subcat_name] = items
            skills[cat_name] = subcategories
        return skills

    def _export_experiences(self, conn: sqlite3.Connection, resume_key: str, version_id: int) -> List[OrderedDict]:
        """Export experiences section."""
        cursor = conn.cursor()
        cursor.execute('\n            SELECT ei.id, ei.start_date, ei.end_date, ei.is_current,\n                   exp.duration_text, exp.role, exp.institution, exp.primary_focus, exp.description\n            FROM experience_items ei\n            LEFT JOIN experience_i18n exp ON ei.id = exp.experience_item_id\n                AND exp.resume_version_id = ?\n            WHERE ei.resume_key = ?\n            ORDER BY ei.sort_order\n            ', (version_id, resume_key))
        experiences = []
        for row in cursor.fetchall():
            exp_data = {'role': row['role'], 'institution': row['institution'], 'duration': row['duration_text']}
            if row['primary_focus']:
                exp_data['primaryFocus'] = row['primary_focus']
            exp_data['description'] = row['description']
            exp = ordered_dict_from_mapping(exp_data, EXPERIENCE_FIELD_ORDER, include_none=False)
            experiences.append(exp)
        return experiences

    def _export_projects(self, conn: sqlite3.Connection, resume_key: str, version_id: int) -> List[OrderedDict]:
        """Export projects section with tags."""
        cursor = conn.cursor()
        cursor.execute('\n            SELECT pi.id, pi.url, proj.title, proj.description\n            FROM project_items pi\n            LEFT JOIN project_i18n proj ON pi.id = proj.project_item_id\n                AND proj.resume_version_id = ?\n            WHERE pi.resume_key = ?\n            ORDER BY pi.sort_order\n            ', (version_id, resume_key))
        projects = []
        for row in cursor.fetchall():
            tags = self._get_tags_for_entity(conn, 'project', row['id'], version_id)
            proj_data = {'title': row['title'], 'description': row['description'], 'url': row['url']}
            if tags:
                proj_data['type_key'] = tags
            proj = ordered_dict_from_mapping(proj_data, PROJECT_FIELD_ORDER)
            projects.append(proj)
        return projects

    def _export_publications(self, conn: sqlite3.Connection, resume_key: str, version_id: int) -> List[OrderedDict]:
        """Export publications with authors, editors, supervisors."""
        cursor = conn.cursor()
        cursor.execute('\n            SELECT pi.id, pi.year, pi.month, pi.day, pi.date, pi.submission_date, pi.access_date,\n                   pi.doi, pi.isbn, pi.issn, pi.pmid, pi.pmcid, pi.arxiv,\n                   pi.url, pi.url_caps, pi.repository_url,\n                   pub.title, pub.pub_type, pub.status, pub.language, pub.notes,\n                   pub.journal, pub.volume, pub.issue, pub.pages, pub.article_number,\n                   pub.book_title, pub.chapter_pages, pub.conference, pub.publisher,\n                   pub.place, pub.edition, pub.degree_type, pub.correspondent,\n                   pub.institution, pub.faculty, pub.school\n            FROM publication_items pi\n            LEFT JOIN publication_i18n pub ON pi.id = pub.publication_id\n                AND pub.resume_version_id = ?\n            WHERE pi.resume_key = ?\n            ORDER BY pi.sort_order\n            ', (version_id, resume_key))
        publications = []
        for row in cursor.fetchall():
            pub_id = row['id']
            cursor.execute('\n                SELECT author_literal\n                FROM publication_authors\n                WHERE publication_id = ? AND resume_version_id = ?\n                ORDER BY sort_order\n                ', (pub_id, version_id))
            authors = [r['author_literal'] for r in cursor.fetchall()]
            authors_structured = [{'literal': a} for a in authors] if authors else None
            cursor.execute('\n                SELECT editor_literal\n                FROM publication_editors\n                WHERE publication_id = ? AND resume_version_id = ?\n                ORDER BY sort_order\n                ', (pub_id, version_id))
            editors = [r['editor_literal'] for r in cursor.fetchall()]
            cursor.execute('\n                SELECT supervisor_literal\n                FROM publication_supervisors\n                WHERE publication_id = ? AND resume_version_id = ?\n                ORDER BY sort_order\n                ', (pub_id, version_id))
            supervisors = [r['supervisor_literal'] for r in cursor.fetchall()]
            tags = self._get_tags_for_entity(conn, 'publication', pub_id, version_id)
            identifiers = OrderedDict([('doi', row['doi']), ('isbn', row['isbn']), ('issn', row['issn']), ('pmid', row['pmid']), ('pmcid', row['pmcid']), ('arxiv', row['arxiv'])])
            pub_data = {'title': row['title'], 'authors': authors if authors else None, 'authors_structured': authors_structured, 'type': row['pub_type'], 'status': row['status'], 'year': row['year'], 'month': row['month'], 'day': row['day'], 'date': row['date'], 'journal': row['journal'], 'volume': row['volume'], 'issue': row['issue'], 'pages': row['pages'], 'article_number': row['article_number'], 'doi': row['doi'], 'issn': row['issn'], 'url': row['url'], 'access_date': row['access_date'], 'language': row['language'], 'publisher': row['publisher'], 'place': row['place'], 'editors': editors if editors else None, 'book_title': row['book_title'], 'chapter_pages': row['chapter_pages'], 'edition': row['edition'], 'conference': row['conference'], 'degree_type': row['degree_type'], 'repository_url': row['repository_url'], 'correspondent': row['correspondent'], 'supervisors': supervisors if supervisors else None, 'institution': row['institution'], 'faculty': row['faculty'], 'school': row['school'], 'isbn': row['isbn'], 'submissionDate': row['submission_date'], 'identifiers': identifiers, 'notes': row['notes'], 'URL': row['url_caps'] if row['url_caps'] else row['url'], 'type_key': tags if tags else None}
            pub = ordered_dict_from_mapping(pub_data, PUBLICATION_FIELD_ORDER)
            publications.append(pub)
        return publications

    def _export_references(self, conn: sqlite3.Connection, resume_key: str, version_id: int) -> List[OrderedDict]:
        """Export references with email arrays."""
        cursor = conn.cursor()
        cursor.execute('\n            SELECT ri.id, ri.phone, ri.url,\n                   ref.name, ref.position, ref.department, ref.institution, ref.location\n            FROM reference_items ri\n            LEFT JOIN reference_i18n ref ON ri.id = ref.reference_id\n                AND ref.resume_version_id = ?\n            WHERE ri.resume_key = ?\n            ORDER BY ri.sort_order\n            ', (version_id, resume_key))
        references = []
        for row in cursor.fetchall():
            ref_id = row['id']
            cursor.execute('\n                SELECT email\n                FROM reference_emails\n                WHERE reference_id = ?\n                ORDER BY sort_order\n                ', (ref_id,))
            emails = [r['email'] for r in cursor.fetchall()]
            tags = self._get_tags_for_entity(conn, 'reference', ref_id, version_id)
            phone_raw = row['phone']
            phone_value = None
            if phone_raw is not None:
                try:
                    phone_value = json.loads(phone_raw)
                except (json.JSONDecodeError, TypeError):
                    phone_value = phone_raw
            ref_data = {'name': row['name'], 'position': row['position'], 'department': row['department'], 'institution': row['institution'], 'location': row['location'], 'email': emails if emails else None, 'phone': phone_value, 'URL': row['url']}
            if tags:
                ref_data['type_key'] = tags
            ref = ordered_dict_from_mapping(ref_data, REFERENCE_FIELD_ORDER)
            references.append(ref)
        return references

    def _get_tags_for_entity(self, conn: sqlite3.Connection, entity_type: str, entity_id: int, version_id: int) -> List[str]:
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
        queries = {'education': '\n                SELECT ti.label\n                FROM education_item_tags et\n                JOIN tag_i18n ti ON et.tag_code = ti.tag_code AND ti.resume_version_id = ?\n                WHERE et.education_item_id = ?\n                ORDER BY ti.label\n            ', 'certification': '\n                SELECT ti.label\n                FROM certification_tags et\n                JOIN tag_i18n ti ON et.tag_code = ti.tag_code AND ti.resume_version_id = ?\n                WHERE et.certification_id = ?\n                ORDER BY ti.label\n            ', 'skill_item': '\n                SELECT ti.label\n                FROM skill_item_tags et\n                JOIN tag_i18n ti ON et.tag_code = ti.tag_code AND ti.resume_version_id = ?\n                WHERE et.skill_item_id = ?\n                ORDER BY ti.label\n            ', 'project': '\n                SELECT ti.label\n                FROM project_tags et\n                JOIN tag_i18n ti ON et.tag_code = ti.tag_code AND ti.resume_version_id = ?\n                WHERE et.project_item_id = ?\n                ORDER BY ti.label\n            ', 'publication': '\n                SELECT ti.label\n                FROM publication_tags et\n                JOIN tag_i18n ti ON et.tag_code = ti.tag_code AND ti.resume_version_id = ?\n                WHERE et.publication_id = ?\n                ORDER BY ti.label\n            ', 'reference': '\n                SELECT ti.label\n                FROM reference_tags et\n                JOIN tag_i18n ti ON et.tag_code = ti.tag_code AND ti.resume_version_id = ?\n                WHERE et.reference_id = ?\n                ORDER BY ti.label\n            '}
        if entity_type not in queries:
            return []
        cursor.execute(queries[entity_type], (version_id, entity_id))
        return [row['label'] for row in cursor.fetchall()]
