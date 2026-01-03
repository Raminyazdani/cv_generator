#!/usr/bin/env python3
"""
create_lang.py - Generate and merge lang.json from CV JSON keys.

This script extracts all unique JSON key names from a CV JSON file
and produces/updates a language dictionary file (lang.json) with
translation slots for each discovered key.

Usage:
    python -m cv_generator.lang_engine.create_lang --cv data/cvs/ramin.json --out lang.json --langs de,en,fa
    python -m cv_generator.lang_engine.create_lang --dry-run --verbose
    python -m cv_generator.lang_engine.create_lang --cv data/cvs/ramin.json --out lang.json --langs de,en,fa --from-lang en

Options:
    --from-lang <lang>: Auto-populate the specified language slot with the key name itself
                        for any empty/missing translation slot. E.g., --from-lang en will set
                        "en": "fname" for key "fname" if the en slot is empty.
                        The specified language is automatically added to the languages list.

Notes:
    - For the top-level "skills" object, we apply special handling:
      - The "skills" key itself is included.
      - Category label keys (immediate children of skills) are EXCLUDED.
      - Subcategory label keys (children of categories) are EXCLUDED.
      - Skill item object keys (e.g., long_name, short_name, type_key) ARE INCLUDED.
    - This allows translation of skill item fields while avoiding dynamic category/subcategory names.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from cv_generator.paths import get_repo_root

_HERE = Path(__file__).resolve().parent


def collect_keys(obj: Any, exclude_skills_descendants: bool = True) -> set[str]:
    """
    Recursively traverse the CV JSON and collect all unique key names.

    Rules:
    - If node is a dict: add each key to the set and recurse into values
    - If node is a list: recurse into every element
    - If node is a scalar (str/int/float/bool/null): stop (don't add values)

    Key names are case-sensitive ("Pictures" != "pictures").

    Special handling for "skills" (when exclude_skills_descendants=True):
    - The "skills" key itself is included.
    - Category label keys (immediate children of skills dict) are EXCLUDED.
    - Subcategory label keys (children of categories) are EXCLUDED.
    - Skill item object keys (e.g., long_name, short_name, type_key) ARE INCLUDED.

    The skills structure is expected to be:
        skills -> category(dict) -> subcategory(dict) -> list[skill_item_dicts]
    """
    out_set: set[str] = set()
    _collect_keys_recursive(obj, out_set, exclude_skills_descendants)
    return out_set


def _collect_skills_items(obj: Any, out_set: set[str]) -> None:
    """
    Collect keys from skill item objects within the skills subtree.

    This function is called for lists at the subcategory level of skills.
    It collects keys from dict items in those lists (skill items).
    """
    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                # This is a skill item dict - collect its keys
                for key, value in item.items():
                    out_set.add(key)
                    # Recurse normally into the value (for nested dicts/lists)
                    _collect_keys_recursive(value, out_set, exclude_skills_descendants=False)
    elif isinstance(obj, dict):
        # If somehow we encounter a dict, collect its keys normally
        for key, value in obj.items():
            out_set.add(key)
            _collect_keys_recursive(value, out_set, exclude_skills_descendants=False)


def _collect_keys_recursive(
    obj: Any,
    out_set: set[str],
    exclude_skills_descendants: bool = True,
) -> None:
    """Internal recursive helper for collect_keys."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            out_set.add(key)

            # Check if this key is "skills" - apply special handling
            if key == "skills" and exclude_skills_descendants:
                # For the skills value, we need to:
                # 1. Skip category keys (direct children)
                # 2. Skip subcategory keys (children of categories)
                # 3. Collect skill item keys (dicts in lists at subcategory level)
                _handle_skills_subtree(value, out_set)
            else:
                _collect_keys_recursive(value, out_set, exclude_skills_descendants)
    elif isinstance(obj, list):
        for item in obj:
            _collect_keys_recursive(item, out_set, exclude_skills_descendants)
    # Scalars: do nothing (we only collect keys, not values)


def _handle_skills_subtree(skills_value: Any, out_set: set[str]) -> None:
    """
    Handle the skills subtree with special traversal rules.

    Structure expected:
        skills_value (dict of categories) ->
            category_value (dict of subcategories) ->
                subcategory_value (list of skill item dicts)

    We skip category and subcategory KEYS but descend into their values
    to find and collect skill item dict keys.
    """
    if isinstance(skills_value, dict):
        # skills_value is a dict of categories (e.g., "Programming & Scripting": {...})
        for category_key, category_value in skills_value.items():
            # Don't add category_key to out_set (skip category labels)
            if isinstance(category_value, dict):
                # category_value is a dict of subcategories
                for subcategory_key, subcategory_value in category_value.items():
                    # Don't add subcategory_key to out_set (skip subcategory labels)
                    # Now look for skill item lists
                    _collect_skills_items(subcategory_value, out_set)
            elif isinstance(category_value, list):
                # Robust handling: if categories directly contain lists
                _collect_skills_items(category_value, out_set)
    elif isinstance(skills_value, list):
        # Robust handling: if skills is directly a list
        _collect_skills_items(skills_value, out_set)


def _is_translation_dict(d: dict[str, Any]) -> bool:
    """
    Detect a dict that looks like a translation leaf.

    A translation dict has only string values and all keys look like language codes
    (2-3 character lowercase strings).
    """
    if not isinstance(d, dict) or len(d) == 0:
        return False

    # Check if all values are strings (or empty)
    if not all(isinstance(v, str) for v in d.values()):
        return False

    # Check if all keys look like language codes (2-3 chars, lowercase)
    for k in d.keys():
        if not isinstance(k, str) or not (2 <= len(k) <= 3) or not k.islower():
            return False

    return True


def merge_lang_data(
    existing: dict[str, Any],
    discovered_keys: set[str],
    languages: list[str],
    from_lang: str | None = None,
) -> tuple[dict[str, dict[str, str]], dict[str, int]]:
    """
    Merge discovered keys into existing lang data without overwriting non-empty translations.

    Behavior:
    - If key exists and has non-empty translation for a language: keep it
    - If key exists but language is missing: add the language with ""
    - If key is new: add it with all languages set to ""
    - If existing file has extra languages not in requested list: keep them
    - Do not delete keys from existing lang.json just because they're not in CV
    - If from_lang is specified and that language slot is empty/missing,
      set it to the key name itself (auto-populate source language)

    Returns:
        (merged_dict, stats) where stats has counts for reporting
    """
    merged: dict[str, dict[str, str]] = {}
    stats = {
        "keys_discovered": len(discovered_keys),
        "keys_added": 0,
        "lang_slots_filled": 0,
        "translations_preserved": 0,
        "from_lang_populated": 0,
    }

    all_keys = set(existing.keys()) | discovered_keys
    requested_langs = set(languages)

    for key in all_keys:
        existing_entry = existing.get(key, {})

        # Determine if this is a new key
        is_new_key = key not in existing
        if is_new_key:
            stats["keys_added"] += 1

        # Build the merged entry
        new_entry: dict[str, str] = {}

        # Get all languages to include (existing + requested)
        if isinstance(existing_entry, dict) and _is_translation_dict(existing_entry):
            all_langs_for_key = set(existing_entry.keys()) | requested_langs
        else:
            all_langs_for_key = requested_langs

        for lang in all_langs_for_key:
            if isinstance(existing_entry, dict):
                existing_value = existing_entry.get(lang)
            else:
                existing_value = None

            if isinstance(existing_value, str) and existing_value.strip():
                # Preserve non-empty translation
                new_entry[lang] = existing_value
                stats["translations_preserved"] += 1
            else:
                # Slot is empty/missing - check if we should auto-populate from key
                if from_lang and lang == from_lang:
                    # Auto-populate with key name
                    new_entry[lang] = key
                    stats["from_lang_populated"] += 1
                else:
                    # Set to empty string (new or was empty/missing)
                    new_entry[lang] = ""
                    # Only count lang_slots_filled for empty slots, not auto-populated ones
                    if lang in requested_langs and not is_new_key:
                        if isinstance(existing_entry, dict) and lang not in existing_entry:
                            stats["lang_slots_filled"] += 1

        merged[key] = new_entry

    return merged, stats


def update_lang_json(
    cv_path: Path,
    lang_path: Path,
    languages: list[str],
    dry_run: bool = False,
    verbose: bool = False,
    from_lang: str | None = None,
) -> dict[str, int]:
    """
    Main function to update lang.json from a CV JSON file.

    Args:
        cv_path: Path to the CV JSON file
        lang_path: Path to the lang.json output file
        languages: List of language codes (e.g., ["de", "en", "fa"])
        dry_run: If True, don't write file, just print summary
        verbose: If True, print detailed output
        from_lang: If specified, auto-populate this language slot with the key name
                   for any empty/missing translation slot

    Returns:
        Statistics dict with counts
    """
    # Load CV data
    if not cv_path.exists():
        raise FileNotFoundError(f"CV file not found: {cv_path}")

    try:
        cv_data = json.loads(cv_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in CV file: {e}")

    # Collect all keys from CV (excluding skills descendants)
    discovered_keys = collect_keys(cv_data, exclude_skills_descendants=True)

    if verbose:
        print(f"Discovered {len(discovered_keys)} unique keys from CV")
        sample_keys = sorted(discovered_keys)[:10]
        print(f"Sample keys: {sample_keys}")

    # Load existing lang.json if present
    existing: dict[str, Any] = {}
    if lang_path.exists():
        try:
            raw = lang_path.read_text(encoding="utf-8").strip()
            if raw:
                existing = json.loads(raw)
        except json.JSONDecodeError:
            if verbose:
                print(f"Warning: Could not parse existing {lang_path}, starting fresh")
            existing = {}

    # Merge
    merged, stats = merge_lang_data(existing, discovered_keys, languages, from_lang=from_lang)

    # Sort keys alphabetically for deterministic output
    sorted_merged = dict(sorted(merged.items()))

    # Also sort language keys within each entry for consistency
    for key in sorted_merged:
        sorted_merged[key] = dict(sorted(sorted_merged[key].items()))

    # Output
    if dry_run:
        print("\n[DRY RUN] Would write to:", lang_path)
        print(f"Total keys: {len(sorted_merged)}")
    else:
        lang_path.parent.mkdir(parents=True, exist_ok=True)
        lang_path.write_text(
            json.dumps(sorted_merged, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if verbose:
            print(f"Written to: {lang_path}")

    # Print summary
    print("\n--- Summary ---")
    print(f"Keys discovered in CV:    {stats['keys_discovered']}")
    print(f"Keys newly added:         {stats['keys_added']}")
    print(f"Language slots filled:    {stats['lang_slots_filled']}")
    print(f"Translations preserved:   {stats['translations_preserved']}")
    if from_lang:
        print(f"From-lang populated:      {stats['from_lang_populated']}")
    print(f"Total keys in output:     {len(sorted_merged)}")

    return stats


def parse_languages(langs_str: str) -> list[str]:
    """Parse comma-separated language string into a list."""
    return [lang.strip() for lang in langs_str.split(",") if lang.strip()]


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate and merge lang.json from CV JSON keys.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m cv_generator.lang_engine.create_lang --cv data/cvs/ramin.json --out lang.json --langs de,en,fa
    python -m cv_generator.lang_engine.create_lang --dry-run --verbose
    python -m cv_generator.lang_engine.create_lang --langs de,en,fa,it  # Add Italian language slots
    python -m cv_generator.lang_engine.create_lang --cv data/cvs/ramin.json --out lang.json --langs de,en,fa --from-lang en

Notes:
    - Keys inside the top-level "skills" object are excluded from key discovery.
    - The --from-lang option auto-populates empty translation slots with the key name.
        """,
    )

    parser.add_argument(
        "--cv",
        type=Path,
        default=get_repo_root() / "data" / "cvs" / "ramin.json",
        help="Path to CV JSON file (default: data/cvs/ramin.json)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_HERE / "lang.json",
        help="Path to output lang.json file (default: src/cv_generator/lang_engine/lang.json)",
    )
    parser.add_argument(
        "--langs",
        type=str,
        default="de,en,fa",
        help="Comma-separated list of language codes (default: de,en,fa)",
    )
    parser.add_argument(
        "--from-lang",
        type=str,
        default=None,
        metavar="LANG",
        help="Auto-populate empty slots for this language with the key name itself. "
             "E.g., --from-lang en sets 'en': 'fname' for key 'fname' if empty. "
             "The specified language is automatically added to the languages list.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary without writing file",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output including sample keys",
    )

    args = parser.parse_args()

    # Parse languages
    languages = parse_languages(args.langs)
    if not languages:
        print("Error: No valid languages specified", file=sys.stderr)
        return 1

    # Handle --from-lang: auto-add to languages list if not present
    from_lang = args.from_lang
    if from_lang:
        from_lang = from_lang.strip()
        if from_lang and from_lang not in languages:
            languages.append(from_lang)
            if args.verbose:
                print(f"Note: Added '{from_lang}' to languages list (from --from-lang)")

    if args.verbose:
        print(f"CV file:    {args.cv}")
        print(f"Output:     {args.out}")
        print(f"Languages:  {languages}")
        if from_lang:
            print(f"From-lang:  {from_lang}")
        print()

    try:
        update_lang_json(
            cv_path=args.cv,
            lang_path=args.out,
            languages=languages,
            dry_run=args.dry_run,
            verbose=args.verbose,
            from_lang=from_lang,
        )
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
