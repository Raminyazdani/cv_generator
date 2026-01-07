"""
Field mapping configuration for DB to JSON export.

This module defines exact JSON field names for each DB column,
ensuring exported JSON matches the exact structure that was imported.

Key principles:
- Field names match JSON exactly (case-sensitive): fname, Pictures, startDate
- Section order must be preserved
- Array items ordered by sort_order columns
- Null values preserved as null, not omitted
- Empty arrays [] preserved, not omitted
"""

from collections import OrderedDict
from typing import Any, Dict, List

# Section order in the exported JSON
SECTION_ORDER = [
    "config",
    "basics",
    "profiles",
    "education",
    "languages",
    "workshop_and_certifications",
    "skills",
    "experiences",
    "projects",
    "publications",
    "references",
]

# Basics section field order
BASICS_FIELD_ORDER = [
    "fname",
    "lname",
    "label",
    "email",
    "phone",
    "birthDate",
    "summary",
    "location",
    "Pictures",
]

# Phone object field order
PHONE_FIELD_ORDER = [
    "countryCode",
    "number",
    "formatted",
]

# Location object field order
LOCATION_FIELD_ORDER = [
    "address",
    "postalCode",
    "city",
    "region",
    "country",
]

# Pictures object field order
PICTURE_FIELD_ORDER = [
    "type_of",
    "URL",
]

# Profile field order
PROFILE_FIELD_ORDER = [
    "network",
    "username",
    "url",
    "uuid",
]

# Education field order
EDUCATION_FIELD_ORDER = [
    "institution",
    "location",
    "area",
    "studyType",
    "startDate",
    "endDate",
    "gpa",
    "logo_url",
    "type_key",
]

# Languages field order
LANGUAGE_FIELD_ORDER = [
    "language",
    "proficiency",
    "certifications",
]

# Proficiency object field order
PROFICIENCY_FIELD_ORDER = [
    "level",
    "CEFR",
    "status",
]

# Language certification field order
LANGUAGE_CERT_FIELD_ORDER = [
    "test",
    "organization",
    "overall",
    "reading",
    "writing",
    "listening",
    "speaking",
    "maxScore",
    "minScore",
    "examDate",
    "URL",
]

# Certification issuer group field order
CERT_ISSUER_FIELD_ORDER = [
    "issuer",
    "certifications",
]

# Certification field order
CERTIFICATION_FIELD_ORDER = [
    "name",
    "date",
    "duration",
    "certificate",
    "URL",
    "type_key",
]

# Skill item field order
SKILL_ITEM_FIELD_ORDER = [
    "long_name",
    "short_name",
    "type_key",
]

# Experience field order
EXPERIENCE_FIELD_ORDER = [
    "role",
    "institution",
    "duration",
    "primaryFocus",
    "description",
]

# Project field order
PROJECT_FIELD_ORDER = [
    "title",
    "description",
    "url",
    "type_key",
]

# Publication field order (comprehensive)
PUBLICATION_FIELD_ORDER = [
    "title",
    "authors",
    "authors_structured",
    "type",
    "status",
    "year",
    "month",
    "day",
    "date",
    "journal",
    "volume",
    "issue",
    "pages",
    "article_number",
    "doi",
    "issn",
    "url",
    "access_date",
    "language",
    "publisher",
    "place",
    "editors",
    "book_title",
    "chapter_pages",
    "edition",
    "conference",
    "degree_type",
    "repository_url",
    "correspondent",
    "supervisors",
    "institution",
    "faculty",
    "school",
    "isbn",
    "submissionDate",
    "identifiers",
    "notes",
    "URL",
    "type_key",
]

# Reference field order
REFERENCE_FIELD_ORDER = [
    "name",
    "position",
    "department",
    "institution",
    "location",
    "email",
    "phone",
    "URL",
    "type_key",
]

# Database column to JSON key mappings (where they differ)
# Format: "db_column": "json_key"
DB_TO_JSON = {
    # Person/Basics
    "birth_date": "birthDate",
    "phone_country_code": "countryCode",
    "phone_number": "number",
    "phone_formatted": "formatted",
    "postal_code": "postalCode",
    # Pictures - note capital P and URL
    "url": "URL",  # For pictures and some other tables
    # Profiles
    "network_display": "network",
    # Education
    "start_date": "startDate",
    "end_date": "endDate",
    "study_type": "studyType",
    # Languages
    "language_name": "language",
    "proficiency_level": "level",
    "proficiency_status": "status",
    "proficiency_cefr": "CEFR",
    # Language certs
    "test_name": "test",
    "max_score": "maxScore",
    "min_score": "minScore",
    "exam_date": "examDate",
    # Certifications
    "issuer_name": "issuer",
    "is_certificate": "certificate",
    "date_text": "date",  # Use date_text for display, fallback to date
    # Experiences
    "duration_text": "duration",
    "primary_focus": "primaryFocus",
    # Publications
    "pub_type": "type",
    "submission_date": "submissionDate",
}

# JSON to Database column mappings (inverse of DB_TO_JSON)
JSON_TO_DB = {v: k for k, v in DB_TO_JSON.items()}


def ordered_dict_from_mapping(
    data: Dict[str, Any],
    field_order: List[str],
    include_none: bool = True,
    include_missing: bool = False,
) -> OrderedDict:
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

    # Add fields in specified order
    for field in field_order:
        if field in data:
            value = data[field]
            if include_none or value is not None:
                result[field] = value
        elif include_missing:
            result[field] = None

    # Add any remaining fields not in field_order
    for key, value in data.items():
        if key not in result:
            if include_none or value is not None:
                result[key] = value

    return result


def build_ordered_cv(
    sections: Dict[str, Any],
    include_empty: bool = True,
) -> OrderedDict:
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
            elif value:  # Only include non-empty
                result[section] = value

    # Add any sections not in SECTION_ORDER (shouldn't happen, but safe)
    for key, value in sections.items():
        if key not in result:
            result[key] = value

    return result
