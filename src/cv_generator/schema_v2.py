"""
ERD-driven SQLite database schema v2 for CV Generator.

This module implements the complete i18n-first schema based on erd.txt.
All tables, indices, and relationships are designed to support multi-language
CV data with the new config.ID and config.lang fields for reliable grouping.

Key concepts:
- resume_sets: Groups all language variants for one person (keyed by resume_key = config.ID)
- resume_versions: One record per (resume_key × lang_code) combination
- *_i18n tables: Store all translatable strings for every language
- tag_codes: Stable tag identifiers with i18n support

Non-negotiable constraints:
- LaTeX JSON contract is LOCKED: Export must produce exact JSON structure for LaTeX
- Zero data loss: Migration must preserve all existing data
- ERD compliance: Every table/column/index from erd.txt is implemented exactly
"""

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Schema version for v2 migrations
SCHEMA_VERSION_V2 = 2

# Complete SQL DDL for all ERD tables
SCHEMA_V2_SQL = """
-- ============================================================================
-- Core Infrastructure Tables
-- ============================================================================

-- App Languages
-- Supported languages (en, de, fa, etc.)
CREATE TABLE IF NOT EXISTS app_languages (
    code VARCHAR PRIMARY KEY,
    name_en VARCHAR NOT NULL,
    direction VARCHAR NOT NULL CHECK (direction IN ('ltr', 'rtl'))
);

-- Resume Sets (one per person, keyed by config.ID)
-- Groups all language variants for one person
CREATE TABLE IF NOT EXISTS resume_sets (
    resume_key VARCHAR PRIMARY KEY,
    base_lang_code VARCHAR NOT NULL REFERENCES app_languages(code),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

-- Resume Versions (one per language variant)
CREATE TABLE IF NOT EXISTS resume_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_key VARCHAR NOT NULL REFERENCES resume_sets(resume_key) ON DELETE CASCADE,
    lang_code VARCHAR NOT NULL REFERENCES app_languages(code),
    is_base BOOLEAN NOT NULL DEFAULT 0,
    is_published BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE(resume_key, lang_code)
);

CREATE INDEX IF NOT EXISTS idx_resume_versions_resume_key ON resume_versions(resume_key);
CREATE INDEX IF NOT EXISTS idx_resume_versions_lang_code ON resume_versions(lang_code);

-- ============================================================================
-- Tags System (type_key arrays)
-- ============================================================================

-- Tag Codes (stable app codes: 'full_cv', 'academic', etc.)
CREATE TABLE IF NOT EXISTS tag_codes (
    code VARCHAR PRIMARY KEY,
    group_code VARCHAR,
    is_system BOOLEAN
);

-- Tag i18n (translated tag labels per language)
CREATE TABLE IF NOT EXISTS tag_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_code VARCHAR NOT NULL REFERENCES tag_codes(code) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    label VARCHAR,
    UNIQUE(tag_code, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_tag_i18n_tag_code ON tag_i18n(tag_code);
CREATE INDEX IF NOT EXISTS idx_tag_i18n_resume_version_id ON tag_i18n(resume_version_id);

-- ============================================================================
-- Basics (single person per resume_set)
-- ============================================================================

-- Persons (invariant data)
CREATE TABLE IF NOT EXISTS persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_key VARCHAR NOT NULL UNIQUE REFERENCES resume_sets(resume_key) ON DELETE CASCADE,
    email VARCHAR,
    birth_date DATE,
    phone_country_code VARCHAR,
    phone_number VARCHAR,
    phone_formatted VARCHAR,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_persons_resume_key ON persons(resume_key);

-- Person i18n (translatable person data)
CREATE TABLE IF NOT EXISTS person_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    fname VARCHAR,
    lname VARCHAR,
    summary TEXT,
    UNIQUE(person_id, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_person_i18n_person_id ON person_i18n(person_id);
CREATE INDEX IF NOT EXISTS idx_person_i18n_resume_version_id ON person_i18n(resume_version_id);

-- Person Locations
CREATE TABLE IF NOT EXISTS person_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    sort_order INTEGER,
    postal_code VARCHAR,
    UNIQUE(person_id, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_person_locations_person_id ON person_locations(person_id);

-- Person Location i18n
CREATE TABLE IF NOT EXISTS person_location_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER NOT NULL REFERENCES person_locations(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    address VARCHAR,
    city VARCHAR,
    region VARCHAR,
    country VARCHAR,
    UNIQUE(location_id, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_person_location_i18n_location_id ON person_location_i18n(location_id);
CREATE INDEX IF NOT EXISTS idx_person_location_i18n_resume_version_id ON person_location_i18n(resume_version_id);

-- Person Pictures
CREATE TABLE IF NOT EXISTS person_pictures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    sort_order INTEGER,
    type_of VARCHAR,
    url VARCHAR,
    UNIQUE(person_id, type_of)
);

CREATE INDEX IF NOT EXISTS idx_person_pictures_person_id ON person_pictures(person_id);

-- Person Labels
CREATE TABLE IF NOT EXISTS person_labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    sort_order INTEGER,
    label_key VARCHAR,
    UNIQUE(person_id, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_person_labels_person_id ON person_labels(person_id);

-- Person Label i18n
CREATE TABLE IF NOT EXISTS person_label_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label_id INTEGER NOT NULL REFERENCES person_labels(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    label_text VARCHAR,
    UNIQUE(label_id, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_person_label_i18n_label_id ON person_label_i18n(label_id);
CREATE INDEX IF NOT EXISTS idx_person_label_i18n_resume_version_id ON person_label_i18n(resume_version_id);

-- ============================================================================
-- Profiles (social links)
-- ============================================================================

-- Profile Accounts
CREATE TABLE IF NOT EXISTS profile_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_key VARCHAR NOT NULL REFERENCES resume_sets(resume_key) ON DELETE CASCADE,
    sort_order INTEGER,
    network_code VARCHAR,
    username VARCHAR,
    url VARCHAR,
    uuid VARCHAR,
    UNIQUE(resume_key, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_profile_accounts_resume_key ON profile_accounts(resume_key);

-- Profile Account i18n
CREATE TABLE IF NOT EXISTS profile_account_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_account_id INTEGER NOT NULL REFERENCES profile_accounts(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    network_display VARCHAR,
    UNIQUE(profile_account_id, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_profile_account_i18n_profile_account_id ON profile_account_i18n(profile_account_id);
CREATE INDEX IF NOT EXISTS idx_profile_account_i18n_resume_version_id ON profile_account_i18n(resume_version_id);

-- ============================================================================
-- Education
-- ============================================================================

-- Education Items
CREATE TABLE IF NOT EXISTS education_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_key VARCHAR NOT NULL REFERENCES resume_sets(resume_key) ON DELETE CASCADE,
    sort_order INTEGER,
    start_date DATE,
    end_date DATE,
    end_date_text VARCHAR,
    gpa VARCHAR,
    logo_url VARCHAR,
    UNIQUE(resume_key, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_education_items_resume_key ON education_items(resume_key);

-- Education i18n
CREATE TABLE IF NOT EXISTS education_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    education_item_id INTEGER NOT NULL REFERENCES education_items(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    institution VARCHAR,
    location VARCHAR,
    area VARCHAR,
    study_type VARCHAR,
    UNIQUE(education_item_id, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_education_i18n_education_item_id ON education_i18n(education_item_id);
CREATE INDEX IF NOT EXISTS idx_education_i18n_resume_version_id ON education_i18n(resume_version_id);

-- Education Item Tags (junction table)
CREATE TABLE IF NOT EXISTS education_item_tags (
    education_item_id INTEGER NOT NULL REFERENCES education_items(id) ON DELETE CASCADE,
    tag_code VARCHAR NOT NULL REFERENCES tag_codes(code) ON DELETE CASCADE,
    PRIMARY KEY (education_item_id, tag_code)
);

CREATE INDEX IF NOT EXISTS idx_education_item_tags_education_item_id ON education_item_tags(education_item_id);
CREATE INDEX IF NOT EXISTS idx_education_item_tags_tag_code ON education_item_tags(tag_code);

-- ============================================================================
-- Spoken Languages (the "Languages" section)
-- ============================================================================

-- Spoken Language Items
CREATE TABLE IF NOT EXISTS spoken_language_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_key VARCHAR NOT NULL REFERENCES resume_sets(resume_key) ON DELETE CASCADE,
    sort_order INTEGER,
    described_language_code VARCHAR,
    proficiency_cefr VARCHAR,
    UNIQUE(resume_key, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_spoken_language_items_resume_key ON spoken_language_items(resume_key);

-- Spoken Language i18n
CREATE TABLE IF NOT EXISTS spoken_language_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spoken_language_item_id INTEGER NOT NULL REFERENCES spoken_language_items(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    language_name VARCHAR,
    proficiency_level VARCHAR,
    proficiency_status VARCHAR,
    UNIQUE(spoken_language_item_id, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_spoken_language_i18n_spoken_language_item_id ON spoken_language_i18n(spoken_language_item_id);
CREATE INDEX IF NOT EXISTS idx_spoken_language_i18n_resume_version_id ON spoken_language_i18n(resume_version_id);

-- Spoken Language Certs
CREATE TABLE IF NOT EXISTS spoken_language_certs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spoken_language_item_id INTEGER NOT NULL REFERENCES spoken_language_items(id) ON DELETE CASCADE,
    sort_order INTEGER,
    overall REAL,
    reading REAL,
    writing REAL,
    listening REAL,
    speaking REAL,
    max_score REAL,
    min_score REAL,
    exam_date DATE,
    url VARCHAR,
    UNIQUE(spoken_language_item_id, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_spoken_language_certs_spoken_language_item_id ON spoken_language_certs(spoken_language_item_id);

-- Spoken Language Cert i18n
CREATE TABLE IF NOT EXISTS spoken_language_cert_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cert_id INTEGER NOT NULL REFERENCES spoken_language_certs(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    test_name VARCHAR,
    organization VARCHAR,
    UNIQUE(cert_id, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_spoken_language_cert_i18n_cert_id ON spoken_language_cert_i18n(cert_id);
CREATE INDEX IF NOT EXISTS idx_spoken_language_cert_i18n_resume_version_id ON spoken_language_cert_i18n(resume_version_id);

-- ============================================================================
-- Workshops & Certifications
-- ============================================================================

-- Cert Issuers
CREATE TABLE IF NOT EXISTS cert_issuers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_key VARCHAR NOT NULL REFERENCES resume_sets(resume_key) ON DELETE CASCADE,
    sort_order INTEGER,
    issuer_slug VARCHAR,
    UNIQUE(resume_key, issuer_slug),
    UNIQUE(resume_key, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_cert_issuers_resume_key ON cert_issuers(resume_key);

-- Cert Issuer i18n
CREATE TABLE IF NOT EXISTS cert_issuer_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issuer_id INTEGER NOT NULL REFERENCES cert_issuers(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    issuer_name VARCHAR,
    UNIQUE(issuer_id, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_cert_issuer_i18n_issuer_id ON cert_issuer_i18n(issuer_id);
CREATE INDEX IF NOT EXISTS idx_cert_issuer_i18n_resume_version_id ON cert_issuer_i18n(resume_version_id);

-- Certifications
CREATE TABLE IF NOT EXISTS certifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issuer_id INTEGER NOT NULL REFERENCES cert_issuers(id) ON DELETE CASCADE,
    sort_order INTEGER,
    is_certificate BOOLEAN,
    date_text VARCHAR,
    date DATE,
    url VARCHAR,
    UNIQUE(issuer_id, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_certifications_issuer_id ON certifications(issuer_id);

-- Certification i18n
CREATE TABLE IF NOT EXISTS certification_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certification_id INTEGER NOT NULL REFERENCES certifications(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    name VARCHAR,
    duration VARCHAR,
    UNIQUE(certification_id, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_certification_i18n_certification_id ON certification_i18n(certification_id);
CREATE INDEX IF NOT EXISTS idx_certification_i18n_resume_version_id ON certification_i18n(resume_version_id);

-- Certification Tags (junction table)
CREATE TABLE IF NOT EXISTS certification_tags (
    certification_id INTEGER NOT NULL REFERENCES certifications(id) ON DELETE CASCADE,
    tag_code VARCHAR NOT NULL REFERENCES tag_codes(code) ON DELETE CASCADE,
    PRIMARY KEY (certification_id, tag_code)
);

CREATE INDEX IF NOT EXISTS idx_certification_tags_certification_id ON certification_tags(certification_id);
CREATE INDEX IF NOT EXISTS idx_certification_tags_tag_code ON certification_tags(tag_code);

-- ============================================================================
-- Skills
-- ============================================================================

-- Skill Categories
CREATE TABLE IF NOT EXISTS skill_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_key VARCHAR NOT NULL REFERENCES resume_sets(resume_key) ON DELETE CASCADE,
    sort_order INTEGER,
    category_code VARCHAR,
    UNIQUE(resume_key, category_code),
    UNIQUE(resume_key, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_skill_categories_resume_key ON skill_categories(resume_key);

-- Skill Category i18n
CREATE TABLE IF NOT EXISTS skill_category_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES skill_categories(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    name VARCHAR,
    UNIQUE(category_id, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_skill_category_i18n_category_id ON skill_category_i18n(category_id);
CREATE INDEX IF NOT EXISTS idx_skill_category_i18n_resume_version_id ON skill_category_i18n(resume_version_id);

-- Skill Subcategories
CREATE TABLE IF NOT EXISTS skill_subcategories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES skill_categories(id) ON DELETE CASCADE,
    sort_order INTEGER,
    subcategory_code VARCHAR,
    UNIQUE(category_id, subcategory_code),
    UNIQUE(category_id, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_skill_subcategories_category_id ON skill_subcategories(category_id);

-- Skill Subcategory i18n
CREATE TABLE IF NOT EXISTS skill_subcategory_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subcategory_id INTEGER NOT NULL REFERENCES skill_subcategories(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    name VARCHAR,
    UNIQUE(subcategory_id, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_skill_subcategory_i18n_subcategory_id ON skill_subcategory_i18n(subcategory_id);
CREATE INDEX IF NOT EXISTS idx_skill_subcategory_i18n_resume_version_id ON skill_subcategory_i18n(resume_version_id);

-- Skill Items
CREATE TABLE IF NOT EXISTS skill_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subcategory_id INTEGER NOT NULL REFERENCES skill_subcategories(id) ON DELETE CASCADE,
    sort_order INTEGER,
    UNIQUE(subcategory_id, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_skill_items_subcategory_id ON skill_items(subcategory_id);

-- Skill Item i18n
CREATE TABLE IF NOT EXISTS skill_item_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_item_id INTEGER NOT NULL REFERENCES skill_items(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    long_name VARCHAR,
    short_name VARCHAR,
    UNIQUE(skill_item_id, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_skill_item_i18n_skill_item_id ON skill_item_i18n(skill_item_id);
CREATE INDEX IF NOT EXISTS idx_skill_item_i18n_resume_version_id ON skill_item_i18n(resume_version_id);

-- Skill Item Tags (junction table)
CREATE TABLE IF NOT EXISTS skill_item_tags (
    skill_item_id INTEGER NOT NULL REFERENCES skill_items(id) ON DELETE CASCADE,
    tag_code VARCHAR NOT NULL REFERENCES tag_codes(code) ON DELETE CASCADE,
    PRIMARY KEY (skill_item_id, tag_code)
);

CREATE INDEX IF NOT EXISTS idx_skill_item_tags_skill_item_id ON skill_item_tags(skill_item_id);
CREATE INDEX IF NOT EXISTS idx_skill_item_tags_tag_code ON skill_item_tags(tag_code);

-- ============================================================================
-- Experiences
-- ============================================================================

-- Experience Items
CREATE TABLE IF NOT EXISTS experience_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_key VARCHAR NOT NULL REFERENCES resume_sets(resume_key) ON DELETE CASCADE,
    sort_order INTEGER,
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN,
    UNIQUE(resume_key, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_experience_items_resume_key ON experience_items(resume_key);

-- Experience i18n
CREATE TABLE IF NOT EXISTS experience_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experience_item_id INTEGER NOT NULL REFERENCES experience_items(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    duration_text VARCHAR,
    role VARCHAR,
    institution VARCHAR,
    primary_focus VARCHAR,
    description TEXT,
    UNIQUE(experience_item_id, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_experience_i18n_experience_item_id ON experience_i18n(experience_item_id);
CREATE INDEX IF NOT EXISTS idx_experience_i18n_resume_version_id ON experience_i18n(resume_version_id);

-- ============================================================================
-- Projects
-- ============================================================================

-- Project Items
CREATE TABLE IF NOT EXISTS project_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_key VARCHAR NOT NULL REFERENCES resume_sets(resume_key) ON DELETE CASCADE,
    sort_order INTEGER,
    url VARCHAR,
    UNIQUE(resume_key, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_project_items_resume_key ON project_items(resume_key);

-- Project i18n
CREATE TABLE IF NOT EXISTS project_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_item_id INTEGER NOT NULL REFERENCES project_items(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    title VARCHAR,
    description TEXT,
    UNIQUE(project_item_id, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_project_i18n_project_item_id ON project_i18n(project_item_id);
CREATE INDEX IF NOT EXISTS idx_project_i18n_resume_version_id ON project_i18n(resume_version_id);

-- Project Tags (junction table)
CREATE TABLE IF NOT EXISTS project_tags (
    project_item_id INTEGER NOT NULL REFERENCES project_items(id) ON DELETE CASCADE,
    tag_code VARCHAR NOT NULL REFERENCES tag_codes(code) ON DELETE CASCADE,
    PRIMARY KEY (project_item_id, tag_code)
);

CREATE INDEX IF NOT EXISTS idx_project_tags_project_item_id ON project_tags(project_item_id);
CREATE INDEX IF NOT EXISTS idx_project_tags_tag_code ON project_tags(tag_code);

-- ============================================================================
-- Publications
-- ============================================================================

-- Publication Items
CREATE TABLE IF NOT EXISTS publication_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_key VARCHAR NOT NULL REFERENCES resume_sets(resume_key) ON DELETE CASCADE,
    sort_order INTEGER,
    year INTEGER,
    month INTEGER,
    day INTEGER,
    date DATE,
    submission_date DATE,
    access_date DATE,
    doi VARCHAR,
    isbn VARCHAR,
    issn VARCHAR,
    pmid VARCHAR,
    pmcid VARCHAR,
    arxiv VARCHAR,
    url VARCHAR,
    url_caps VARCHAR,
    repository_url VARCHAR,
    UNIQUE(resume_key, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_publication_items_resume_key ON publication_items(resume_key);

-- Publication i18n
CREATE TABLE IF NOT EXISTS publication_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    publication_id INTEGER NOT NULL REFERENCES publication_items(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    title TEXT,
    pub_type VARCHAR,
    status VARCHAR,
    language VARCHAR,
    notes TEXT,
    journal VARCHAR,
    volume VARCHAR,
    issue VARCHAR,
    pages VARCHAR,
    article_number VARCHAR,
    book_title VARCHAR,
    chapter_pages VARCHAR,
    conference VARCHAR,
    publisher VARCHAR,
    place VARCHAR,
    edition VARCHAR,
    degree_type VARCHAR,
    correspondent VARCHAR,
    institution VARCHAR,
    faculty VARCHAR,
    school VARCHAR,
    UNIQUE(publication_id, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_publication_i18n_publication_id ON publication_i18n(publication_id);
CREATE INDEX IF NOT EXISTS idx_publication_i18n_resume_version_id ON publication_i18n(resume_version_id);

-- Publication Authors
CREATE TABLE IF NOT EXISTS publication_authors (
    publication_id INTEGER NOT NULL REFERENCES publication_items(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    sort_order INTEGER NOT NULL,
    author_literal VARCHAR,
    PRIMARY KEY (publication_id, resume_version_id, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_publication_authors_publication_id ON publication_authors(publication_id);
CREATE INDEX IF NOT EXISTS idx_publication_authors_resume_version_id ON publication_authors(resume_version_id);

-- Publication Editors
CREATE TABLE IF NOT EXISTS publication_editors (
    publication_id INTEGER NOT NULL REFERENCES publication_items(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    sort_order INTEGER NOT NULL,
    editor_literal VARCHAR,
    PRIMARY KEY (publication_id, resume_version_id, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_publication_editors_publication_id ON publication_editors(publication_id);
CREATE INDEX IF NOT EXISTS idx_publication_editors_resume_version_id ON publication_editors(resume_version_id);

-- Publication Supervisors
CREATE TABLE IF NOT EXISTS publication_supervisors (
    publication_id INTEGER NOT NULL REFERENCES publication_items(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    sort_order INTEGER NOT NULL,
    supervisor_literal VARCHAR,
    PRIMARY KEY (publication_id, resume_version_id, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_publication_supervisors_publication_id ON publication_supervisors(publication_id);
CREATE INDEX IF NOT EXISTS idx_publication_supervisors_resume_version_id ON publication_supervisors(resume_version_id);

-- Publication Tags (junction table)
CREATE TABLE IF NOT EXISTS publication_tags (
    publication_id INTEGER NOT NULL REFERENCES publication_items(id) ON DELETE CASCADE,
    tag_code VARCHAR NOT NULL REFERENCES tag_codes(code) ON DELETE CASCADE,
    PRIMARY KEY (publication_id, tag_code)
);

CREATE INDEX IF NOT EXISTS idx_publication_tags_publication_id ON publication_tags(publication_id);
CREATE INDEX IF NOT EXISTS idx_publication_tags_tag_code ON publication_tags(tag_code);

-- ============================================================================
-- References
-- ============================================================================

-- Reference Items
CREATE TABLE IF NOT EXISTS reference_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_key VARCHAR NOT NULL REFERENCES resume_sets(resume_key) ON DELETE CASCADE,
    sort_order INTEGER,
    phone VARCHAR,
    url VARCHAR,
    UNIQUE(resume_key, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_reference_items_resume_key ON reference_items(resume_key);

-- Reference i18n
CREATE TABLE IF NOT EXISTS reference_i18n (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference_id INTEGER NOT NULL REFERENCES reference_items(id) ON DELETE CASCADE,
    resume_version_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    name VARCHAR,
    position VARCHAR,
    department VARCHAR,
    institution VARCHAR,
    location VARCHAR,
    UNIQUE(reference_id, resume_version_id)
);

CREATE INDEX IF NOT EXISTS idx_reference_i18n_reference_id ON reference_i18n(reference_id);
CREATE INDEX IF NOT EXISTS idx_reference_i18n_resume_version_id ON reference_i18n(resume_version_id);

-- Reference Emails
CREATE TABLE IF NOT EXISTS reference_emails (
    reference_id INTEGER NOT NULL REFERENCES reference_items(id) ON DELETE CASCADE,
    sort_order INTEGER NOT NULL,
    email VARCHAR,
    PRIMARY KEY (reference_id, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_reference_emails_reference_id ON reference_emails(reference_id);

-- Reference Tags (junction table)
CREATE TABLE IF NOT EXISTS reference_tags (
    reference_id INTEGER NOT NULL REFERENCES reference_items(id) ON DELETE CASCADE,
    tag_code VARCHAR NOT NULL REFERENCES tag_codes(code) ON DELETE CASCADE,
    PRIMARY KEY (reference_id, tag_code)
);

CREATE INDEX IF NOT EXISTS idx_reference_tags_reference_id ON reference_tags(reference_id);
CREATE INDEX IF NOT EXISTS idx_reference_tags_tag_code ON reference_tags(tag_code);

-- ============================================================================
-- Meta table for schema version tracking (shared with v1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

# Default languages to seed
DEFAULT_LANGUAGES = [
    ("en", "English", "ltr"),
    ("de", "German", "ltr"),
    ("fa", "Persian", "rtl"),
]

# List of all tables defined in the ERD
ERD_TABLES = [
    # Core infrastructure
    "app_languages",
    "resume_sets",
    "resume_versions",
    # Tags
    "tag_codes",
    "tag_i18n",
    # Basics/Person
    "persons",
    "person_i18n",
    "person_locations",
    "person_location_i18n",
    "person_pictures",
    "person_labels",
    "person_label_i18n",
    # Profiles
    "profile_accounts",
    "profile_account_i18n",
    # Education
    "education_items",
    "education_i18n",
    "education_item_tags",
    # Spoken Languages
    "spoken_language_items",
    "spoken_language_i18n",
    "spoken_language_certs",
    "spoken_language_cert_i18n",
    # Certifications
    "cert_issuers",
    "cert_issuer_i18n",
    "certifications",
    "certification_i18n",
    "certification_tags",
    # Skills
    "skill_categories",
    "skill_category_i18n",
    "skill_subcategories",
    "skill_subcategory_i18n",
    "skill_items",
    "skill_item_i18n",
    "skill_item_tags",
    # Experiences
    "experience_items",
    "experience_i18n",
    # Projects
    "project_items",
    "project_i18n",
    "project_tags",
    # Publications
    "publication_items",
    "publication_i18n",
    "publication_authors",
    "publication_editors",
    "publication_supervisors",
    "publication_tags",
    # References
    "reference_items",
    "reference_i18n",
    "reference_emails",
    "reference_tags",
    # Meta
    "meta",
]


def _utcnow() -> str:
    """Return current UTC time as ISO format string."""
    return datetime.now(timezone.utc).isoformat()


def init_db_v2(db_path: Path, force: bool = False) -> Path:
    """
    Initialize the database with v2 schema.

    Args:
        db_path: Path to the database file.
        force: If True, recreate the database even if it exists.

    Returns:
        Path to the created database file.

    Raises:
        ValueError: If database exists and force is False but version mismatch.
    """
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        if force:
            logger.info(f"[SCHEMA] Removing existing database: {db_path}")
            db_path.unlink()
        else:
            # Check existing version
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='meta'"
                )
                if cursor.fetchone():
                    cursor.execute("SELECT value FROM meta WHERE key = 'schema_version'")
                    row = cursor.fetchone()
                    if row:
                        existing_version = int(row[0])
                        if existing_version == SCHEMA_VERSION_V2:
                            logger.info(
                                f"[SCHEMA] Database already at version {SCHEMA_VERSION_V2}: {db_path}"
                            )
                            return db_path
                        else:
                            logger.warning(
                                f"[SCHEMA] Schema version mismatch: DB has v{existing_version}, "
                                f"expected v{SCHEMA_VERSION_V2}"
                            )
            finally:
                conn.close()

    logger.info(f"[SCHEMA] Creating v2 database: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        # Enable foreign key constraint enforcement for this connection.
        # Note: SQLite has foreign keys disabled by default. Each new connection
        # must explicitly enable them with PRAGMA foreign_keys = ON.
        conn.execute("PRAGMA foreign_keys = ON")

        cursor = conn.cursor()

        # Execute schema DDL
        cursor.executescript(SCHEMA_V2_SQL)
        logger.info(f"[SCHEMA] Created {len(ERD_TABLES)} tables")

        # Set schema version
        now = _utcnow()
        cursor.execute(
            "INSERT OR REPLACE INTO meta (key, value, updated_at) VALUES (?, ?, ?)",
            ("schema_version", str(SCHEMA_VERSION_V2), now),
        )

        # Seed app_languages
        seed_languages(cursor)

        conn.commit()
        logger.info(f"[SCHEMA] Database initialized with schema version {SCHEMA_VERSION_V2}")

    except Exception as e:
        conn.rollback()
        logger.error(f"[SCHEMA] Failed to initialize database: {e}")
        raise
    finally:
        conn.close()

    return db_path


def seed_languages(cursor: sqlite3.Cursor) -> None:
    """
    Seed the app_languages table with default languages.

    Args:
        cursor: Database cursor.
    """
    for code, name_en, direction in DEFAULT_LANGUAGES:
        cursor.execute(
            """INSERT OR IGNORE INTO app_languages (code, name_en, direction)
               VALUES (?, ?, ?)""",
            (code, name_en, direction),
        )
    logger.info(f"[SCHEMA] Seeded {len(DEFAULT_LANGUAGES)} languages: en, de, fa")


def get_schema_version(db_path: Path) -> Optional[int]:
    """
    Get the current schema version from the database.

    Args:
        db_path: Path to the database file.

    Returns:
        Schema version number or None if not found.
    """
    if not db_path.exists():
        return None

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='meta'"
        )
        if not cursor.fetchone():
            return None

        cursor.execute("SELECT value FROM meta WHERE key = 'schema_version'")
        row = cursor.fetchone()
        return int(row[0]) if row else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def list_tables(db_path: Path) -> List[str]:
    """
    List all tables in the database.

    Args:
        db_path: Path to the database file.

    Returns:
        List of table names.
    """
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()


def verify_erd_tables(db_path: Path) -> Tuple[List[str], List[str]]:
    """
    Verify that all ERD tables exist in the database.

    Args:
        db_path: Path to the database file.

    Returns:
        Tuple of (existing_tables, missing_tables).
    """
    existing = set(list_tables(db_path))
    expected = set(ERD_TABLES)

    existing_erd = sorted(existing & expected)
    missing = sorted(expected - existing)

    return existing_erd, missing
