"""
Multilingual CV JSON consistency checker.

This module provides functionality to verify that multilingual CV JSON files
have consistent schema structure and properly translated content.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Exit code for validation failures
EXIT_ENSURE_ERROR = 2


@dataclass
class EnsureIssue:
    """Represents a single consistency issue found during validation."""

    lang: str
    path: str
    issue_type: str  # 'missing', 'extra', 'mapping_missing', 'schema_key_translated'
    expected: Optional[str] = None
    found: Optional[str] = None
    hint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        result = {
            "lang": self.lang,
            "path": self.path,
            "issue_type": self.issue_type,
        }
        if self.expected is not None:
            result["expected"] = self.expected
        if self.found is not None:
            result["found"] = self.found
        if self.hint is not None:
            result["hint"] = self.hint
        return result


@dataclass
class EnsureReport:
    """Report of all consistency issues found."""

    missing: List[EnsureIssue] = field(default_factory=list)
    extra: List[EnsureIssue] = field(default_factory=list)
    mapping_missing: List[EnsureIssue] = field(default_factory=list)
    schema_key_errors: List[EnsureIssue] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        """Total number of issues found."""
        return (len(self.missing) + len(self.extra) +
                len(self.mapping_missing) + len(self.schema_key_errors))

    @property
    def is_valid(self) -> bool:
        """Returns True if no issues were found."""
        return self.total_issues == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "missing": [i.to_dict() for i in self.missing],
            "extra": [i.to_dict() for i in self.extra],
            "mapping_missing": [i.to_dict() for i in self.mapping_missing],
            "schema_key_errors": [i.to_dict() for i in self.schema_key_errors],
            "summary": {
                "total_issues": self.total_issues,
                "missing_count": len(self.missing),
                "extra_count": len(self.extra),
                "mapping_missing_count": len(self.mapping_missing),
                "schema_key_errors_count": len(self.schema_key_errors),
            }
        }

    def format_text(self) -> str:
        """Format report as human-readable text."""
        lines = []

        if self.is_valid:
            lines.append("✓ All language files are consistent!")
            return "\n".join(lines)

        lines.append(f"Found {self.total_issues} issue(s):\n")

        if self.missing:
            lines.append("=== Missing Keys/Paths ===")
            for issue in self.missing:
                hint_str = f" (hint: {issue.hint})" if issue.hint else ""
                lines.append(f"  [{issue.lang}] {issue.path}{hint_str}")
            lines.append("")

        if self.extra:
            lines.append("=== Extra Keys/Paths ===")
            for issue in self.extra:
                found_str = f" (found: {issue.found})" if issue.found else ""
                lines.append(f"  [{issue.lang}] {issue.path}{found_str}")
            lines.append("")

        if self.schema_key_errors:
            lines.append("=== Schema Key Translation Errors ===")
            for issue in self.schema_key_errors:
                exp = issue.expected or ""
                fnd = issue.found or ""
                lines.append(f"  [{issue.lang}] {issue.path}: expected '{exp}', found '{fnd}'")
            lines.append("")

        if self.mapping_missing:
            lines.append("=== Missing Translation Mappings ===")
            for issue in self.mapping_missing:
                lines.append(f"  [{issue.lang}] {issue.path}: {issue.hint}")
            lines.append("")

        lines.append(f"Summary: {len(self.missing)} missing, {len(self.extra)} extra, "
                    f"{len(self.schema_key_errors)} schema errors, "
                    f"{len(self.mapping_missing)} mapping issues")

        return "\n".join(lines)


# Top-level schema keys that should never be translated (English CV structure)
SCHEMA_KEYS = {
    # Top-level sections
    "basics", "profiles", "education", "experiences", "skills",
    "projects", "publications", "references", "languages",
    "workshop_and_certifications",
    # Common object field keys
    "type_key", "long_name", "short_name",
    "fname", "lname", "label", "email", "phone", "birthDate", "summary",
    "location", "Pictures", "address", "postalCode", "city", "region", "country",
    "type_of", "URL", "url",
    "network", "username",
    "institution", "area", "studyType", "startDate", "endDate", "gpa", "logo_url",
    "language", "proficiency", "certifications", "level", "CEFR", "status",
    "test", "organization", "overall", "reading", "writing", "listening",
    "speaking", "maxScore", "minScore", "examDate",
    "issuer", "name", "date", "duration", "certificate",
    "role", "duration", "description", "primaryFocus",
    "title", "authors", "authors_structured", "type", "year", "month", "day",
    "journal", "volume", "issue", "pages", "article_number", "doi", "issn",
    "access_date", "publisher", "place", "editors", "book_title",
    "chapter_pages", "edition", "conference", "degree_type", "repository_url",
    "correspondent", "supervisors", "faculty", "school", "isbn",
    "submissionDate", "identifiers", "pmid", "pmcid", "arxiv", "notes",
    "position", "department", "countryCode", "number", "formatted",
    "literal",
}


def get_item_identity(item: Dict[str, Any], context: str) -> Optional[str]:
    """
    Get a stable identity for a list item to match across languages.

    Args:
        item: The dictionary item
        context: The context path (e.g., 'projects', 'experiences')

    Returns:
        A stable identity string, or None if no identity can be determined.
    """
    if not isinstance(item, dict):
        return None

    # For projects: prefer url, then title
    if "url" in item and item["url"]:
        return f"url:{item['url']}"
    if "URL" in item and item["URL"]:
        return f"url:{item['URL']}"
    if "title" in item and item["title"]:
        return f"title:{item['title']}"

    # For experiences: role + institution + duration
    if all(k in item for k in ("role", "institution", "duration")):
        return f"exp:{item['role']}|{item['institution']}|{item['duration']}"

    # For publications: doi or title
    if "doi" in item and item["doi"]:
        return f"doi:{item['doi']}"

    # For references: email or name
    if "email" in item and item["email"]:
        emails = item["email"] if isinstance(item["email"], list) else [item["email"]]
        if emails:
            return f"email:{emails[0]}"
    if "name" in item:
        return f"name:{item['name']}"

    return None


def match_list_items(
    en_list: List[Any],
    other_list: List[Any],
    context: str
) -> List[Tuple[int, Optional[int], Optional[str]]]:
    """
    Match items between English and another language list.

    Returns:
        List of tuples (en_index, other_index or None, match_method)
        If other_index is None, the item is missing.
    """
    matches = []
    used_other_indices: Set[int] = set()

    for en_idx, en_item in enumerate(en_list):
        en_identity = get_item_identity(en_item, context) if isinstance(en_item, dict) else None

        matched_idx = None
        match_method = None

        if en_identity:
            # Try to find by identity
            for other_idx, other_item in enumerate(other_list):
                if other_idx in used_other_indices:
                    continue
                other_identity = get_item_identity(other_item, context) if isinstance(other_item, dict) else None
                if other_identity == en_identity:
                    matched_idx = other_idx
                    match_method = "identity"
                    break

        # Fall back to index matching
        if matched_idx is None and en_idx < len(other_list):
            if en_idx not in used_other_indices:
                matched_idx = en_idx
                match_method = "index"

        if matched_idx is not None:
            used_other_indices.add(matched_idx)

        matches.append((en_idx, matched_idx, match_method))

    return matches


def compare_cv_structure(
    en_data: Dict[str, Any],
    other_data: Dict[str, Any],
    lang: str,
    lang_map: Optional[Dict[str, Dict[str, str]]] = None,
    path: str = "",
    report: Optional[EnsureReport] = None,
    max_errors: Optional[int] = None,
    fail_fast: bool = False,
) -> EnsureReport:
    """
    Compare English CV data structure with another language.

    Args:
        en_data: English (canonical) CV data
        other_data: Other language CV data
        lang: Language code (e.g., 'de', 'fa')
        lang_map: Translation mapping for skill headings
        path: Current JSON path (for recursion)
        report: Existing report to add issues to
        max_errors: Maximum number of errors before stopping
        fail_fast: If True, stop after first batch of errors

    Returns:
        EnsureReport with all issues found
    """
    if report is None:
        report = EnsureReport()

    if max_errors and report.total_issues >= max_errors:
        return report

    if isinstance(en_data, dict) and isinstance(other_data, dict):
        _compare_dicts(en_data, other_data, lang, lang_map, path, report, max_errors, fail_fast)
    elif isinstance(en_data, list) and isinstance(other_data, list):
        _compare_lists(en_data, other_data, lang, lang_map, path, report, max_errors, fail_fast)

    return report


def _compare_dicts(
    en_dict: Dict[str, Any],
    other_dict: Dict[str, Any],
    lang: str,
    lang_map: Optional[Dict[str, Dict[str, str]]],
    path: str,
    report: EnsureReport,
    max_errors: Optional[int],
    fail_fast: bool,
) -> None:
    """Compare two dictionaries."""

    if max_errors and report.total_issues >= max_errors:
        return

    # Check if this is a skills section with translatable heading keys
    is_skills_section = path.startswith("skills") or "/skills" in path

    # Get keys from both
    en_keys = set(en_dict.keys())
    other_keys = set(other_dict.keys())

    # For skills section with nested category headings, we need special handling
    if is_skills_section and lang_map and _is_heading_level(en_dict):
        _compare_skills_headings(en_dict, other_dict, lang, lang_map, path, report, max_errors, fail_fast)
        return

    # Find missing keys (in English but not in other)
    for key in en_keys:
        if max_errors and report.total_issues >= max_errors:
            return

        current_path = f"{path}.{key}" if path else key

        if key not in other_keys:
            report.missing.append(EnsureIssue(
                lang=lang,
                path=current_path,
                issue_type="missing",
                expected=key,
                hint=f"Key '{key}' missing in {lang} version"
            ))
            if fail_fast:
                return
        else:
            # Recurse into the value
            compare_cv_structure(
                en_dict[key], other_dict[key], lang, lang_map,
                current_path, report, max_errors, fail_fast
            )

    # Find extra keys (in other but not in English)
    for key in other_keys:
        if max_errors and report.total_issues >= max_errors:
            return

        current_path = f"{path}.{key}" if path else key

        if key not in en_keys:
            report.extra.append(EnsureIssue(
                lang=lang,
                path=current_path,
                issue_type="extra",
                found=key,
                hint=f"Unexpected key '{key}' in {lang} version"
            ))
            if fail_fast:
                return


def _compare_lists(
    en_list: List[Any],
    other_list: List[Any],
    lang: str,
    lang_map: Optional[Dict[str, Dict[str, str]]],
    path: str,
    report: EnsureReport,
    max_errors: Optional[int],
    fail_fast: bool,
) -> None:
    """Compare two lists."""

    if max_errors and report.total_issues >= max_errors:
        return

    # Get context for identity matching
    context = path.split(".")[-1] if path else ""

    # Match items between lists
    matches = match_list_items(en_list, other_list, context)

    for en_idx, other_idx, match_method in matches:
        if max_errors and report.total_issues >= max_errors:
            return

        current_path = f"{path}[{en_idx}]"

        if other_idx is None:
            report.missing.append(EnsureIssue(
                lang=lang,
                path=current_path,
                issue_type="missing",
                hint=f"List item at index {en_idx} missing in {lang} version"
            ))
            if fail_fast:
                return
        else:
            # Recurse into matched items
            compare_cv_structure(
                en_list[en_idx], other_list[other_idx], lang, lang_map,
                current_path, report, max_errors, fail_fast
            )

    # Check for extra items in other list
    matched_other_indices = {m[1] for m in matches if m[1] is not None}
    for other_idx in range(len(other_list)):
        if other_idx not in matched_other_indices:
            report.extra.append(EnsureIssue(
                lang=lang,
                path=f"{path}[{other_idx}]",
                issue_type="extra",
                hint=f"Extra list item at index {other_idx} in {lang} version"
            ))


def _is_heading_level(data: Dict[str, Any]) -> bool:
    """
    Check if a dict appears to be a heading level in skills section.

    Heading levels have string keys that map to dicts or lists of skill items.
    Returns True only if there's positive evidence this is a heading level.
    """
    if not data:
        return False

    # Check if all values are either dicts or lists of dicts with skill items
    has_heading_evidence = False

    for key, value in data.items():
        # Schema keys indicate this is not a heading level
        if key in SCHEMA_KEYS:
            return False
        # If value is a list with dicts containing 'long_name', it's a heading
        if isinstance(value, list):
            if value and isinstance(value[0], dict) and "long_name" in value[0]:
                has_heading_evidence = True
        # If value is a dict, could be nested heading
        elif isinstance(value, dict) and value:
            first_val = next(iter(value.values()))
            if isinstance(first_val, (list, dict)):
                has_heading_evidence = True

    return has_heading_evidence


def _compare_skills_headings(
    en_dict: Dict[str, Any],
    other_dict: Dict[str, Any],
    lang: str,
    lang_map: Dict[str, Dict[str, str]],
    path: str,
    report: EnsureReport,
    max_errors: Optional[int],
    fail_fast: bool,
) -> None:
    """
    Compare skills section headings using translation mapping.
    """
    if max_errors and report.total_issues >= max_errors:
        return

    # Build a mapping of expected translations for this language
    en_to_other = {}
    for en_key, translations in lang_map.items():
        if lang in translations:
            en_to_other[en_key] = translations[lang]

    # Also build reverse mapping
    other_to_en = {v: k for k, v in en_to_other.items()}

    # Check each English key
    for en_key, en_value in en_dict.items():
        if max_errors and report.total_issues >= max_errors:
            return

        current_path = f"{path}.{en_key}" if path else en_key

        # Find the expected translation
        expected_other_key = en_to_other.get(en_key, en_key)

        if expected_other_key in other_dict:
            # Key found with correct translation
            other_value = other_dict[expected_other_key]

            # Recurse into the value
            compare_cv_structure(
                en_value, other_value, lang, lang_map,
                current_path, report, max_errors, fail_fast
            )
        elif en_key not in lang_map:
            # Key not in mapping - report missing mapping
            # But first check if the English key exists directly
            if en_key in other_dict:
                # Key exists but wasn't translated - might be intentional
                compare_cv_structure(
                    en_value, other_dict[en_key], lang, lang_map,
                    current_path, report, max_errors, fail_fast
                )
            else:
                # Key truly missing
                report.mapping_missing.append(EnsureIssue(
                    lang=lang,
                    path=current_path,
                    issue_type="mapping_missing",
                    expected=en_key,
                    hint=f"No translation mapping for '{en_key}' and key not found in {lang}"
                ))
        else:
            # We have a mapping but the translated key is not found
            report.missing.append(EnsureIssue(
                lang=lang,
                path=current_path,
                issue_type="missing",
                expected=expected_other_key,
                hint=f"Expected translated key '{expected_other_key}' for English key '{en_key}'"
            ))

    # Check for extra keys in other dict
    for other_key in other_dict.keys():
        if other_key in other_to_en:
            # This key is a valid translation
            continue
        if other_key in en_dict:
            # This is an English key that wasn't translated
            continue

        # Check if it might be a translation we don't know about
        current_path = f"{path}.{other_key}" if path else other_key
        report.extra.append(EnsureIssue(
            lang=lang,
            path=current_path,
            issue_type="extra",
            found=other_key,
            hint=f"Unexpected key '{other_key}' - not a known translation"
        ))


def find_cv_files(
    name: str,
    langs: List[str],
    cvs_dir: Optional[Path] = None,
    paths: Optional[Dict[str, Path]] = None,
) -> Dict[str, Path]:
    """
    Find CV files for a person in the given languages.

    Args:
        name: Person's name (e.g., 'ramin')
        langs: List of language codes (e.g., ['en', 'de', 'fa'])
        cvs_dir: Base directory for CV files
        paths: Optional explicit paths per language

    Returns:
        Dict mapping language code to file path
    """
    if paths:
        return paths

    if cvs_dir is None:
        from .paths import get_default_cvs_path
        cvs_dir = get_default_cvs_path()

    result = {}

    for lang in langs:
        # Try different naming conventions
        candidates = [
            # Direct directory structure (when --dir is specified)
            cvs_dir / f"cv.{lang}.json",
            # Preferred: i18n directory structure
            cvs_dir / "i18n" / name / f"cv.{lang}.json",
            # Alias: flat structure with language suffix
            cvs_dir / f"{name}.{lang}.json",
            cvs_dir / f"{name}_{lang}.json",
        ]

        # Special case: 'en' might be the base file without suffix
        if lang == "en":
            candidates.append(cvs_dir / f"{name}.json")

        for candidate in candidates:
            if candidate.exists():
                result[lang] = candidate
                break

    return result


def load_lang_mapping(
    name: str,
    cvs_dir: Optional[Path] = None,
    mapping_path: Optional[Path] = None,
) -> Dict[str, Dict[str, str]]:
    """
    Load language mapping file for a person.

    The mapping file maps English keys to their translations.
    Format: {"English Key": {"de": "German Translation", "fa": "Persian Translation"}}

    Args:
        name: Person's name
        cvs_dir: Base directory for CV files
        mapping_path: Optional explicit path to mapping file

    Returns:
        Mapping dictionary
    """
    if mapping_path and mapping_path.exists():
        with open(mapping_path, "r", encoding="utf-8") as f:
            return json.load(f)

    if cvs_dir is None:
        from .paths import get_default_cvs_path
        cvs_dir = get_default_cvs_path()

    # Try different locations
    from .paths import get_lang_engine_path
    candidates = [
        cvs_dir / "i18n" / name / "lang.json",
        cvs_dir / f"{name}_lang.json",
        cvs_dir / "lang.json",  # Global mapping in cvs dir
        get_lang_engine_path() / "lang.json",  # Main lang_engine mapping
    ]

    for candidate in candidates:
        if candidate.exists():
            with open(candidate, "r", encoding="utf-8") as f:
                return json.load(f)

    return {}


def run_ensure(
    name: str,
    langs: List[str],
    cvs_dir: Optional[Path] = None,
    paths: Optional[Dict[str, Path]] = None,
    lang_map: Optional[Dict[str, Dict[str, str]]] = None,
    max_errors: Optional[int] = None,
    fail_fast: bool = False,
) -> EnsureReport:
    """
    Run the ensure check for a person's CV files.

    Args:
        name: Person's name
        langs: Languages to check (first should be 'en' or canonical)
        cvs_dir: Base directory for CV files
        paths: Optional explicit paths per language
        lang_map: Optional language mapping for skill headings
        max_errors: Maximum number of errors before stopping
        fail_fast: If True, stop at first error

    Returns:
        EnsureReport with all issues found
    """
    report = EnsureReport()

    # Find CV files
    cv_files = find_cv_files(name, langs, cvs_dir, paths)

    # Determine canonical language (should be 'en' or first in list)
    canonical_lang = "en" if "en" in langs else langs[0]

    if canonical_lang not in cv_files:
        report.missing.append(EnsureIssue(
            lang=canonical_lang,
            path="",
            issue_type="missing",
            hint=f"Canonical ({canonical_lang}) CV file not found for '{name}'"
        ))
        return report

    # Load canonical data
    with open(cv_files[canonical_lang], "r", encoding="utf-8") as f:
        canonical_data = json.load(f)

    # Load language mapping if not provided
    if lang_map is None:
        lang_map = load_lang_mapping(name, cvs_dir)

    # Compare each other language against canonical
    other_langs = [lang for lang in langs if lang != canonical_lang]

    for lang in other_langs:
        if max_errors and report.total_issues >= max_errors:
            break

        if lang not in cv_files:
            report.missing.append(EnsureIssue(
                lang=lang,
                path="",
                issue_type="missing",
                hint=f"CV file not found for language '{lang}'"
            ))
            continue

        # Load other language data
        with open(cv_files[lang], "r", encoding="utf-8") as f:
            other_data = json.load(f)

        # Compare structures
        compare_cv_structure(
            canonical_data, other_data, lang, lang_map,
            "", report, max_errors, fail_fast
        )

    return report
