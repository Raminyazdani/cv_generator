"""
Entry Path Module for CV Generator.

Provides canonical, stable entry paths for identifying taggable items in CVs,
including nested structures like skills.

Entry Path Format:
- For list sections: <section>/<index>
- For skill items: skills/<parent_category>/<sub_category>/<skill_key>

Where skill_key is determined by:
1. short_name if unique within the subcategory
2. short_name with disambiguator if duplicates exist
3. index as fallback

This module handles collision detection and disambiguation automatically.
"""

import hashlib
from typing import Any, Dict, Iterator, List, Optional, Tuple
from urllib.parse import quote, unquote


def _safe_path_component(value: str) -> str:
    """
    Make a string safe for use as a path component.

    Encodes special characters but keeps it readable.

    Args:
        value: The string to encode.

    Returns:
        URL-safe path component.
    """
    # Replace forward slashes which would break path parsing
    value = value.replace("/", "∕")  # Use division slash U+2215
    # URL encode for safety but keep most chars readable
    return quote(value, safe="-_.~")


def _decode_path_component(value: str) -> str:
    """
    Decode a path component back to its original value.

    Args:
        value: The encoded path component.

    Returns:
        Original string value.
    """
    decoded = unquote(value)
    # Restore forward slashes
    decoded = decoded.replace("∕", "/")
    return decoded


def _compute_skill_key(
    skill_item: Dict[str, Any],
    index: int,
    seen_keys: Dict[str, int]
) -> str:
    """
    Compute a unique skill key for a skill item.

    Priority:
    1. short_name if present and unique
    2. short_name with suffix if duplicates
    3. long_name if short_name not present
    4. index as fallback

    Args:
        skill_item: The skill dictionary.
        index: The index of this skill in the list.
        seen_keys: Dictionary tracking seen keys and their counts.

    Returns:
        Unique skill key string.
    """
    # Get the primary name
    short_name = skill_item.get("short_name", "").strip()
    long_name = skill_item.get("long_name", "").strip()

    if short_name:
        base_key = short_name
    elif long_name:
        base_key = long_name
    else:
        # No name available, use index
        return f"idx_{index}"

    # Track occurrences for collision handling
    if base_key in seen_keys:
        # Collision detected - add suffix
        seen_keys[base_key] += 1
        count = seen_keys[base_key]

        # Try to disambiguate with long_name hash if available
        if long_name and short_name and long_name != short_name:
            # Use first 6 chars of hash for disambiguation
            hash_suffix = hashlib.md5(long_name.encode()).hexdigest()[:6]
            return f"{base_key}_{hash_suffix}"
        else:
            # Use occurrence count
            return f"{base_key}_{count}"
    else:
        seen_keys[base_key] = 1
        return base_key


def generate_skill_entry_path(
    parent_category: str,
    sub_category: str,
    skill_key: str
) -> str:
    """
    Generate an entry path for a skill item.

    Args:
        parent_category: The top-level skill category.
        sub_category: The sub-category within the parent.
        skill_key: The unique skill identifier within the sub-category.

    Returns:
        Entry path string like "skills/Programming%20%26%20Scripting/Programming%20Languages/Python"
        (URL-encoded for safety in storage and URLs).
    """
    parts = [
        "skills",
        _safe_path_component(parent_category),
        _safe_path_component(sub_category),
        _safe_path_component(skill_key)
    ]
    return "/".join(parts)


def parse_skill_entry_path(entry_path: str) -> Optional[Tuple[str, str, str]]:
    """
    Parse a skill entry path into its components.

    Args:
        entry_path: The entry path string.

    Returns:
        Tuple of (parent_category, sub_category, skill_key) or None if not a skill path.
    """
    if not entry_path.startswith("skills/"):
        return None

    parts = entry_path.split("/", 3)
    if len(parts) != 4:
        return None

    return (
        _decode_path_component(parts[1]),
        _decode_path_component(parts[2]),
        _decode_path_component(parts[3])
    )


def enumerate_skills(
    skills_data: Dict[str, Any]
) -> Iterator[Tuple[str, str, str, str, Dict[str, Any]]]:
    """
    Enumerate all skill items in a nested skills structure.

    Yields tuples of:
    - entry_path: Canonical path for this skill
    - parent_category: Top-level category name
    - sub_category: Sub-category name
    - skill_key: Unique key for this skill
    - skill_item: The actual skill data dict

    Args:
        skills_data: The nested skills dictionary.

    Yields:
        Tuples of (entry_path, parent_category, sub_category, skill_key, skill_item)
    """
    for parent_category, sub_categories in skills_data.items():
        if not isinstance(sub_categories, dict):
            continue

        for sub_category, skill_list in sub_categories.items():
            if not isinstance(skill_list, list):
                continue

            # Track seen keys for collision handling within this subcategory
            seen_keys: Dict[str, int] = {}

            for idx, skill_item in enumerate(skill_list):
                if not isinstance(skill_item, dict):
                    continue

                skill_key = _compute_skill_key(skill_item, idx, seen_keys)
                entry_path = generate_skill_entry_path(
                    parent_category, sub_category, skill_key
                )

                yield entry_path, parent_category, sub_category, skill_key, skill_item


def get_skill_display_name(skill_item: Dict[str, Any]) -> str:
    """
    Get a display name for a skill item.

    Args:
        skill_item: The skill dictionary.

    Returns:
        Human-readable display name.
    """
    short_name = skill_item.get("short_name", "").strip()
    long_name = skill_item.get("long_name", "").strip()

    if short_name and long_name and short_name != long_name:
        return f"{short_name} ({long_name})"
    elif short_name:
        return short_name
    elif long_name:
        return long_name
    else:
        return "Unknown Skill"


def reconstruct_skills_from_entries(
    entries: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Reconstruct a nested skills dictionary from individual skill entries.

    Args:
        entries: List of entry dicts, each with 'identity_key' (entry_path)
                 and 'data' (skill item dict).

    Returns:
        Nested skills dictionary matching original structure.
    """
    skills: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    # Group entries by their path structure
    for entry in entries:
        entry_path = entry.get("identity_key", "")
        parsed = parse_skill_entry_path(entry_path)
        if not parsed:
            continue

        parent_category, sub_category, skill_key = parsed
        data = entry.get("data", {})

        if parent_category not in skills:
            skills[parent_category] = {}

        if sub_category not in skills[parent_category]:
            skills[parent_category][sub_category] = []

        skills[parent_category][sub_category].append(data)

    return skills
