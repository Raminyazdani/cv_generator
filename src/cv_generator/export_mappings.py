"""
Field mapping configuration for DB to JSON export.

This module defines exact JSON field names for each DB column,
ensuring exported JSON matches the exact structure that LaTeX templates expect.

Key principles:
- Field names match JSON exactly (case-sensitive): fname, Pictures, startDate
- Section order must be preserved
- Array items ordered by sort_order columns
- Null values preserved as null, not omitted
- Empty arrays [] preserved, not omitted
"""
from collections import OrderedDict
from typing import Any, Dict, List
SECTION_ORDER = ['config', 'basics', 'profiles', 'education', 'languages', 'workshop_and_certifications', 'skills', 'experiences', 'projects', 'publications', 'references']
BASICS_FIELD_ORDER = ['fname', 'lname', 'label', 'email', 'phone', 'birthDate', 'summary', 'location', 'Pictures']
PHONE_FIELD_ORDER = ['countryCode', 'number', 'formatted']
LOCATION_FIELD_ORDER = ['address', 'postalCode', 'city', 'region', 'country']
PICTURE_FIELD_ORDER = ['type_of', 'URL']
PROFILE_FIELD_ORDER = ['network', 'username', 'url', 'uuid']
EDUCATION_FIELD_ORDER = ['institution', 'location', 'area', 'studyType', 'startDate', 'endDate', 'gpa', 'logo_url', 'type_key']
LANGUAGE_FIELD_ORDER = ['language', 'proficiency', 'certifications']
PROFICIENCY_FIELD_ORDER = ['level', 'CEFR', 'status']
LANGUAGE_CERT_FIELD_ORDER = ['test', 'organization', 'overall', 'reading', 'writing', 'listening', 'speaking', 'maxScore', 'minScore', 'examDate', 'URL']
CERT_ISSUER_FIELD_ORDER = ['issuer', 'certifications']
CERTIFICATION_FIELD_ORDER = ['name', 'date', 'duration', 'certificate', 'URL', 'type_key']
SKILL_ITEM_FIELD_ORDER = ['long_name', 'short_name', 'type_key']
EXPERIENCE_FIELD_ORDER = ['role', 'institution', 'duration', 'primaryFocus', 'description']
PROJECT_FIELD_ORDER = ['title', 'description', 'url', 'type_key']
PUBLICATION_FIELD_ORDER = ['title', 'authors', 'authors_structured', 'type', 'status', 'year', 'month', 'day', 'date', 'journal', 'volume', 'issue', 'pages', 'article_number', 'doi', 'issn', 'url', 'access_date', 'language', 'publisher', 'place', 'editors', 'book_title', 'chapter_pages', 'edition', 'conference', 'degree_type', 'repository_url', 'correspondent', 'supervisors', 'institution', 'faculty', 'school', 'isbn', 'submissionDate', 'identifiers', 'notes', 'URL', 'type_key']
REFERENCE_FIELD_ORDER = ['name', 'position', 'department', 'institution', 'location', 'email', 'phone', 'URL', 'type_key']
DB_TO_JSON = {'birth_date': 'birthDate', 'phone_country_code': 'countryCode', 'phone_number': 'number', 'phone_formatted': 'formatted', 'postal_code': 'postalCode', 'url': 'URL', 'network_display': 'network', 'start_date': 'startDate', 'end_date': 'endDate', 'study_type': 'studyType', 'language_name': 'language', 'proficiency_level': 'level', 'proficiency_status': 'status', 'proficiency_cefr': 'CEFR', 'test_name': 'test', 'max_score': 'maxScore', 'min_score': 'minScore', 'exam_date': 'examDate', 'issuer_name': 'issuer', 'is_certificate': 'certificate', 'date_text': 'date', 'duration_text': 'duration', 'primary_focus': 'primaryFocus', 'pub_type': 'type', 'submission_date': 'submissionDate'}
JSON_TO_DB = {v: k for k, v in DB_TO_JSON.items()}

def ordered_dict_from_mapping(data: Dict[str, Any], field_order: List[str], include_none: bool=True, include_missing: bool=False) -> OrderedDict:
    """
    Create OrderedDict with specified field order.

    Args:
        data: Source dictionary
        field_order: List of field names in desired order
        include_none: Whether to include fields with None values
        include_missing: Whether to include fields that are in field_order but not in data

    Returns:
        OrderedDict with fields in specified order
        Fields not in field_order are appended at the end.
    """
    result = OrderedDict()
    for field in field_order:
        if field in data:
            value = data[field]
            if include_none or value is not None:
                result[field] = value
        elif include_missing:
            result[field] = None
    for key, value in data.items():
        if key not in result:
            if include_none or value is not None:
                result[key] = value
    return result

def build_ordered_cv(sections: Dict[str, Any], include_empty: bool=True) -> OrderedDict:
    """
    Build a complete CV dictionary with sections in correct order.

    Args:
        sections: Dictionary of section name -> section data
        include_empty: Whether to include empty arrays/dicts

    Returns:
        OrderedDict with sections in SECTION_ORDER
    """
    result = OrderedDict()
    for section in SECTION_ORDER:
        if section in sections:
            value = sections[section]
            if include_empty:
                result[section] = value
            elif value:
                result[section] = value
    for key, value in sections.items():
        if key not in result:
            result[key] = value
    return result
