# scripts/make_translate_csv.py

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


SENSITIVE_KEY_RX = re.compile(r"(url|uri|email|phone|doi|issn|isbn)", re.IGNORECASE)
SENSITIVE_VALUE_RX = re.compile(
    r"(https?://|www\.|@|cloudinary\.com|github\.com|taylorfrancis\.com)",
    re.IGNORECASE,
)


def _blank_leaf(value: Any) -> Any:
    """Blank a leaf while preserving the intent of the type."""
    if value is None:
        return None
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return 0
    if isinstance(value, float):
        return 0.0
    if isinstance(value, str):
        return ""
    return ""


def _looks_like_skill_item(x: Any) -> bool:
    """Heuristic: a skill entry is usually a dict with long_name/short_name/type_key."""
    return isinstance(x, dict) and (
        "short_name" in x or "long_name" in x or "type_key" in x
    )


def _trim_lists(obj: Any, max_items: int, path: tuple[str, ...] = ()) -> Any:
    """
    Trim lists but preserve the intended *skills* shape:
    - Under `skills`: keep all group/subheading dict keys.
    - Only trim the leaf lists that contain skill items.
    """
    if isinstance(obj, dict):
        return {k: _trim_lists(v, max_items, path + (str(k),)) for k, v in obj.items()}

    if isinstance(obj, list):
        in_skills = "skills" in path
        if in_skills and obj and _looks_like_skill_item(obj[0]):
            items = obj[:max_items]
        else:
            items = obj[:max_items] if not in_skills else obj
        return [_trim_lists(v, max_items, path) for v in items]

    return obj


def _anonymize_keep_shape(obj: Any) -> Any:
    """Blank all leaves, keep full structure."""
    if isinstance(obj, dict):
        return {k: _anonymize_keep_shape(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_anonymize_keep_shape(v) for v in obj]
    return _blank_leaf(obj)


def _override_sensitive(obj: Any) -> Any:
    """
    Force blanking for sensitive keys and values even if they appear as non-leaves.
    - If key looks sensitive => blank it (preserve None vs non-None intent loosely).
    - If string value looks like a link/email => blank it.
    """
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if SENSITIVE_KEY_RX.search(k or ""):
                out[k] = None if v is None else ""
            else:
                out[k] = _override_sensitive(v)
        return out

    if isinstance(obj, list):
        return [_override_sensitive(v) for v in obj]

    if isinstance(obj, str) and SENSITIVE_VALUE_RX.search(obj):
        return ""

    return obj


_HERE = Path(__file__).resolve().parent


def make_empty_example(
    src_path: Path = _HERE.parent / "data" / "cvs" / "ramin.json",
    dst_path: Path = _HERE.parent / "scripts" / "example" / "empty.json",
    max_list_items: int = 1,
) -> None:
    data = json.loads(src_path.read_text(encoding="utf-8"))

    trimmed = _trim_lists(deepcopy(data), max_items=max_list_items)
    empty = _anonymize_keep_shape(trimmed)
    empty = _override_sensitive(empty)

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text(
        json.dumps(empty, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def make_minimal_example(
    src_path: Path = _HERE.parent / "data" / "cvs" / "ramin.json",
    dst_path: Path = _HERE.parent / "scripts" / "example" / "minimal.json",
    max_list_items: int = 1,
) -> None:
    """
    Write a minimal-but-real example:
    - Keep original values (do not blank content)
    - Trim repeated list entries to `max_list_items`
    - Blank sensitive fields/values
    """
    data = json.loads(src_path.read_text(encoding="utf-8"))

    minimal = _trim_lists(deepcopy(data), max_items=max_list_items)
    minimal = _override_sensitive(minimal)

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text(
        json.dumps(minimal, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _is_translation_dict(d: dict[str, Any]) -> bool:
    """Detect a dict that looks like a translation leaf, e.g. {"en":"","de":"","fa":""}."""
    if not isinstance(d, dict):
        return False
    keys = set(d.keys())
    return bool(keys) and keys.issubset({"en", "de", "fa"})


def _make_translation_leaf(langs: tuple[str, ...] = ("en", "de", "fa")) -> dict[str, str]:
    return {k: "" for k in langs}


def _normalize_path_parts(parts: list[str]) -> str:
    """Join JSON path parts into a stable dot-path; list indices are represented as []."""
    out: list[str] = []
    for p in parts:
        if p == "[]":
            # attach to previous segment as suffix if possible
            if out:
                out[-1] = f"{out[-1]}[]"
            else:
                out.append("[]")
        else:
            out.append(p)
    return ".".join(out)


def _collect_leaf_paths(obj: Any, parts: list[str] | None = None) -> set[str]:
    """Return set of dot-paths for all leaf values in obj."""
    if parts is None:
        parts = []

    if isinstance(obj, dict):
        paths: set[str] = set()
        for k, v in obj.items():
            paths |= _collect_leaf_paths(v, parts + [str(k)])
        return paths

    if isinstance(obj, list):
        # We don’t want index-specific keys; represent list traversal as []
        if not obj:
            # Consider empty list as a leaf container (so translation key exists)
            return { _normalize_path_parts(parts + ["[]"]) } if parts else set()
        paths: set[str] = set()
        for item in obj:
            paths |= _collect_leaf_paths(item, parts + ["[]"])
        return paths

    # primitive leaf
    if not parts:
        return set()
    return { _normalize_path_parts(parts) }


def _extract_existing_flat(existing: Any, langs: tuple[str, ...] = ("en", "de", "fa")) -> dict[str, dict[str, str]]:
    """Accept either an already-flat lang.json or an older structural one and return a flat map."""
    if not isinstance(existing, dict):
        return {}

    # If it's already flat (values are translation dicts), keep it.
    if any(isinstance(v, dict) and _is_translation_dict(v) for v in existing.values()):
        out: dict[str, dict[str, str]] = {}
        for k, v in existing.items():
            if isinstance(v, dict) and _is_translation_dict(v):
                out[k] = {lang: v.get(lang, "") for lang in langs}
        return out

    # Otherwise treat it as a structural skeleton and flatten leaf translation dicts.
    flat: dict[str, dict[str, str]] = {}

    def walk(node: Any, parts: list[str]) -> None:
        if isinstance(node, dict) and _is_translation_dict(node):
            flat[_normalize_path_parts(parts)] = {lang: node.get(lang, "") for lang in langs}
            return
        if isinstance(node, dict):
            for kk, vv in node.items():
                walk(vv, parts + [str(kk)])
            return
        if isinstance(node, list):
            if not node:
                return
            # structural skeleton stores representative element at [0]
            walk(node[0], parts + ["[]"])

    walk(existing, [])
    return flat


def _merge_flat_lang(
    existing: dict[str, Any],
    new_paths: set[str],
    langs: tuple[str, ...] = ("en", "de", "fa"),
) -> dict[str, Any]:
    """Merge flattened paths into existing lang dict without overwriting non-empty translations."""
    out: dict[str, Any] = {}

    existing_flat = _extract_existing_flat(existing, langs)
    out.update(existing_flat)

    for p in sorted(new_paths):
        current = out.get(p)
        if isinstance(current, dict) and _is_translation_dict(current):
            out[p] = {k: current.get(k, "") for k in langs}
        else:
            out[p] = {k: "" for k in langs}

    return out


def _collect_all_paths(obj: Any, parts: list[str] | None = None, *, include_root: bool = False) -> set[str]:
    """
    Collect dot-paths for every node in the JSON including containers and leaves.

    Examples:
      basics                  (container)
      basics[]                (list container)
      basics[].phone          (container)
      basics[].phone.number   (leaf)

    We still never copy actual values; these paths are only IDs for translation.
    """
    if parts is None:
        parts = []

    paths: set[str] = set()

    if include_root and parts:
        paths.add(_normalize_path_parts(parts))

    if isinstance(obj, dict):
        # Add container path for this dict (except empty root)
        if parts:
            paths.add(_normalize_path_parts(parts))
        for k, v in obj.items():
            child_parts = parts + [str(k)]
            # Add the key path itself (container or leaf)
            paths.add(_normalize_path_parts(child_parts))
            paths |= _collect_all_paths(v, child_parts)
        return paths

    if isinstance(obj, list):
        # Add container path for the list itself
        if parts:
            paths.add(_normalize_path_parts(parts))

        list_parts = parts + ["[]"]
        # Add list-marker path (e.g., basics[])
        if parts:
            paths.add(_normalize_path_parts(list_parts))

        if not obj:
            return paths

        for item in obj:
            paths |= _collect_all_paths(item, list_parts)
        return paths

    # Primitive leaf: the leaf path itself is already added by parent loop, but ensure it.
    if parts:
        paths.add(_normalize_path_parts(parts))

    return paths


def update_lang_json_from_ramin(
    src_path: Path = _HERE.parent / "data" / "cvs" / "ramin.json",
    lang_path: Path = _HERE / "lang.json",
    langs: tuple[str, ...] = ("en", "de", "fa"),
) -> None:
    """
    Read ramin.json and update lang.json with *flattened* keys (level 1).

    This includes paths for:
    - containers (dict/list)
    - leaves

    Example keys:
      "basics"
      "basics[]"
      "basics[].phone"
      "basics[].phone.number"

    Existing non-empty translations are preserved.
    """
    data = json.loads(src_path.read_text(encoding="utf-8"))
    paths = _collect_all_paths(data)

    existing: dict[str, Any] = {}
    if lang_path.exists():
        try:
            raw = lang_path.read_text(encoding="utf-8").strip()
            existing = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            existing = {}

    merged = _merge_flat_lang(existing, paths, langs)

    lang_path.parent.mkdir(parents=True, exist_ok=True)
    lang_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    # Preserve existing behavior.
    make_empty_example()
    make_minimal_example()

    # Also generate/extend Lang_engine/lang.json skeleton.
    update_lang_json_from_ramin()
