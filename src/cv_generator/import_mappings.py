"""
Field mapping configuration for JSON to DB import.

This module defines which JSON fields map to which DB columns,
separating invariant (shared across languages) from i18n (translated) fields.
"""
BASICS_INVARIANT = {'email': 'email', 'birthDate': 'birth_date'}
BASICS_PHONE_MAPPING = {'countryCode': 'phone_country_code', 'number': 'phone_number', 'formatted': 'phone_formatted'}
BASICS_I18N = {'fname': 'fname', 'lname': 'lname', 'summary': 'summary'}
LOCATION_INVARIANT = {'postalCode': 'postal_code'}
LOCATION_I18N = {'address': 'address', 'city': 'city', 'region': 'region', 'country': 'country'}
PICTURES_MAPPING = {'type_of': 'type_of', 'URL': 'url'}
PROFILE_INVARIANT = {'username': 'username', 'url': 'url', 'uuid': 'uuid'}
PROFILE_I18N = {'network': 'network_display'}
EDUCATION_INVARIANT = {'startDate': 'start_date', 'endDate': 'end_date', 'gpa': 'gpa', 'logo_url': 'logo_url'}
EDUCATION_I18N = {'institution': 'institution', 'location': 'location', 'area': 'area', 'studyType': 'study_type'}
SPOKEN_LANGUAGE_INVARIANT = {'proficiency.CEFR': 'proficiency_cefr'}
SPOKEN_LANGUAGE_I18N = {'language': 'language_name', 'proficiency.level': 'proficiency_level', 'proficiency.status': 'proficiency_status'}
SPOKEN_LANGUAGE_CERT_INVARIANT = {'overall': 'overall', 'reading': 'reading', 'writing': 'writing', 'listening': 'listening', 'speaking': 'speaking', 'maxScore': 'max_score', 'minScore': 'min_score', 'examDate': 'exam_date', 'URL': 'url'}
SPOKEN_LANGUAGE_CERT_I18N = {'test': 'test_name', 'organization': 'organization'}
CERT_ISSUER_I18N = {'issuer': 'issuer_name'}
CERTIFICATION_INVARIANT = {'certificate': 'is_certificate', 'date': 'date', 'URL': 'url'}
CERTIFICATION_I18N = {'name': 'name', 'duration': 'duration'}
SKILL_CATEGORY_I18N = {'category_name': 'name'}
SKILL_SUBCATEGORY_I18N = {'subcategory_name': 'name'}
SKILL_ITEM_I18N = {'long_name': 'long_name', 'short_name': 'short_name'}
EXPERIENCE_INVARIANT = {'startDate': 'start_date', 'endDate': 'end_date'}
EXPERIENCE_I18N = {'duration': 'duration_text', 'role': 'role', 'institution': 'institution', 'primary_focus': 'primary_focus', 'description': 'description'}
PROJECT_INVARIANT = {'url': 'url'}
PROJECT_I18N = {'title': 'title', 'description': 'description'}
PUBLICATION_INVARIANT = {'year': 'year', 'month': 'month', 'day': 'day', 'date': 'date', 'submissionDate': 'submission_date', 'access_date': 'access_date', 'doi': 'doi', 'isbn': 'isbn', 'issn': 'issn', 'url': 'url', 'URL': 'url', 'repository_url': 'repository_url'}
PUBLICATION_IDENTIFIERS = {'doi': 'doi', 'isbn': 'isbn', 'issn': 'issn', 'pmid': 'pmid', 'pmcid': 'pmcid', 'arxiv': 'arxiv'}
PUBLICATION_I18N = {'title': 'title', 'type': 'pub_type', 'status': 'status', 'language': 'language', 'notes': 'notes', 'journal': 'journal', 'volume': 'volume', 'issue': 'issue', 'pages': 'pages', 'article_number': 'article_number', 'book_title': 'book_title', 'chapter_pages': 'chapter_pages', 'conference': 'conference', 'publisher': 'publisher', 'place': 'place', 'edition': 'edition', 'degree_type': 'degree_type', 'correspondent': 'correspondent', 'institution': 'institution', 'faculty': 'faculty', 'school': 'school'}
REFERENCE_INVARIANT = {'phone': 'phone', 'URL': 'url'}
REFERENCE_I18N = {'name': 'name', 'position': 'position', 'department': 'department', 'institution': 'institution', 'location': 'location'}
SUPPORTED_LANGUAGES = ['en', 'de', 'fa']
DEFAULT_LANGUAGE = 'en'
