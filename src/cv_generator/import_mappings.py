"""
Field mapping configuration for JSON to DB import.

This module defines which JSON fields map to which DB columns,
separating invariant (shared across languages) from i18n (translated) fields.
"""

# Basics section - invariant fields stored in `persons` table
BASICS_INVARIANT = {
    "email": "email",
    "birthDate": "birth_date",
    # Phone is a nested object -> separate columns
}

BASICS_PHONE_MAPPING = {
    "countryCode": "phone_country_code",
    "number": "phone_number",
    "formatted": "phone_formatted",
}

# Basics section - i18n fields stored in `person_i18n` table
BASICS_I18N = {
    "fname": "fname",
    "lname": "lname",
    "summary": "summary",
}

# Basics location - invariant fields stored in `person_locations` table
LOCATION_INVARIANT = {
    "postalCode": "postal_code",
}

# Basics location - i18n fields stored in `person_location_i18n` table
LOCATION_I18N = {
    "address": "address",
    "city": "city",
    "region": "region",
    "country": "country",
}

# Person pictures - stored in `person_pictures` table
PICTURES_MAPPING = {
    "type_of": "type_of",
    "URL": "url",
}

# Profile accounts - invariant fields in `profile_accounts`
PROFILE_INVARIANT = {
    "username": "username",
    "url": "url",
    "uuid": "uuid",
}

# Profile accounts - i18n fields in `profile_account_i18n`
PROFILE_I18N = {
    "network": "network_display",
}

# Education - invariant fields in `education_items`
EDUCATION_INVARIANT = {
    "startDate": "start_date",
    "endDate": "end_date",
    "gpa": "gpa",
    "logo_url": "logo_url",
}

# Education - i18n fields in `education_i18n`
EDUCATION_I18N = {
    "institution": "institution",
    "location": "location",
    "area": "area",
    "studyType": "study_type",
}

# Spoken languages - invariant fields in `spoken_language_items`
SPOKEN_LANGUAGE_INVARIANT = {
    # `language` is also stored for proficiency tracking
    "proficiency.CEFR": "proficiency_cefr",
}

# Spoken languages - i18n fields in `spoken_language_i18n`
SPOKEN_LANGUAGE_I18N = {
    "language": "language_name",
    "proficiency.level": "proficiency_level",
    "proficiency.status": "proficiency_status",
}

# Spoken language certifications - invariant fields in `spoken_language_certs`
SPOKEN_LANGUAGE_CERT_INVARIANT = {
    "overall": "overall",
    "reading": "reading",
    "writing": "writing",
    "listening": "listening",
    "speaking": "speaking",
    "maxScore": "max_score",
    "minScore": "min_score",
    "examDate": "exam_date",
    "URL": "url",
}

# Spoken language certifications - i18n fields in `spoken_language_cert_i18n`
SPOKEN_LANGUAGE_CERT_I18N = {
    "test": "test_name",
    "organization": "organization",
}

# Cert issuers - invariant fields (slug derived from issuer name)
# i18n fields in `cert_issuer_i18n`
CERT_ISSUER_I18N = {
    "issuer": "issuer_name",
}

# Certifications - invariant fields in `certifications`
CERTIFICATION_INVARIANT = {
    "certificate": "is_certificate",
    "date": "date",
    "URL": "url",
}

# Certifications - i18n fields in `certification_i18n`
CERTIFICATION_I18N = {
    "name": "name",
    "duration": "duration",
}

# Skills - category i18n
SKILL_CATEGORY_I18N = {
    "category_name": "name",
}

# Skills - subcategory i18n
SKILL_SUBCATEGORY_I18N = {
    "subcategory_name": "name",
}

# Skills - item i18n
SKILL_ITEM_I18N = {
    "long_name": "long_name",
    "short_name": "short_name",
}

# Experiences - invariant fields in `experience_items`
EXPERIENCE_INVARIANT = {
    "startDate": "start_date",
    "endDate": "end_date",
}

# Experiences - i18n fields in `experience_i18n`
EXPERIENCE_I18N = {
    "duration": "duration_text",
    "role": "role",
    "institution": "institution",
    "primary_focus": "primary_focus",
    "description": "description",
}

# Projects - invariant fields in `project_items`
PROJECT_INVARIANT = {
    "url": "url",
}

# Projects - i18n fields in `project_i18n`
PROJECT_I18N = {
    "title": "title",
    "description": "description",
}

# Publications - invariant fields in `publication_items`
PUBLICATION_INVARIANT = {
    "year": "year",
    "month": "month",
    "day": "day",
    "date": "date",
    "submissionDate": "submission_date",
    "access_date": "access_date",
    "doi": "doi",
    "isbn": "isbn",
    "issn": "issn",
    "url": "url",
    "URL": "url",
    "repository_url": "repository_url",
}

# Additional publication identifiers from nested `identifiers` object
PUBLICATION_IDENTIFIERS = {
    "doi": "doi",
    "isbn": "isbn",
    "issn": "issn",
    "pmid": "pmid",
    "pmcid": "pmcid",
    "arxiv": "arxiv",
}

# Publications - i18n fields in `publication_i18n`
PUBLICATION_I18N = {
    "title": "title",
    "type": "pub_type",
    "status": "status",
    "language": "language",
    "notes": "notes",
    "journal": "journal",
    "volume": "volume",
    "issue": "issue",
    "pages": "pages",
    "article_number": "article_number",
    "book_title": "book_title",
    "chapter_pages": "chapter_pages",
    "conference": "conference",
    "publisher": "publisher",
    "place": "place",
    "edition": "edition",
    "degree_type": "degree_type",
    "correspondent": "correspondent",
    "institution": "institution",
    "faculty": "faculty",
    "school": "school",
}

# References - invariant fields in `reference_items`
REFERENCE_INVARIANT = {
    "phone": "phone",
    "URL": "url",
}

# References - i18n fields in `reference_i18n`
REFERENCE_I18N = {
    "name": "name",
    "position": "position",
    "department": "department",
    "institution": "institution",
    "location": "location",
}

# Supported languages
SUPPORTED_LANGUAGES = ["en", "de", "fa"]

# Default language for files without config
DEFAULT_LANGUAGE = "en"
