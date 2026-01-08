from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

SUPPORTED_LANGUAGES = ["en", "de", "fa"]

SECTION_ORDER = [
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

SECTION_LABELS = {
    "basics": "Basics",
    "profiles": "Profiles",
    "education": "Education",
    "languages": "Languages",
    "workshop_and_certifications": "Workshops & Certifications",
    "skills": "Skills",
    "experiences": "Experiences",
    "projects": "Projects",
    "publications": "Publications",
    "references": "References",
}

SECTION_ICONS = {
    "basics": "👤",
    "profiles": "🔗",
    "education": "🎓",
    "languages": "🗣️",
    "workshop_and_certifications": "📜",
    "skills": "🧰",
    "experiences": "💼",
    "projects": "🧪",
    "publications": "🧾",
    "references": "🤝",
}


@dataclass
class FieldInfo:
    label: str
    input_type: str = "text"
    multiline: bool = False
    shared: bool = False
    placeholder: str = ""
    canonical_key: Optional[str] = None
    localized_label: Optional[str] = None


# Minimal field maps per section (you can extend this easily).
# shared=True means you *usually* want the same value across languages (URL/dates/etc.)
SECTION_FIELDS: Dict[str, Dict[str, FieldInfo]] = {
    "basics": {
        "fname": FieldInfo("First Name"),
        "lname": FieldInfo("Last Name"),
        "label": FieldInfo("Label / Title"),
        "headline": FieldInfo("Headline"),
        "email": FieldInfo("Email", shared=True),
        "summary": FieldInfo("Summary", multiline=True),
        "birthDate": FieldInfo("Birth Date", shared=True, placeholder="YYYY-MM-DD"),
    },
    "profiles": {
        "network": FieldInfo("Network", shared=True),
        "username": FieldInfo("Username", shared=True),
        "url": FieldInfo("URL", shared=True),
    },
    "education": {
        "institution": FieldInfo("Institution"),
        "location": FieldInfo("Location", shared=True),
        "area": FieldInfo("Area / Field"),
        "studyType": FieldInfo("Study Type"),
        "startDate": FieldInfo("Start Date", shared=True, placeholder="YYYY-MM-DD"),
        "endDate": FieldInfo("End Date", shared=True, placeholder="YYYY-MM-DD"),
        "gpa": FieldInfo("GPA", shared=True),
        "logo_url": FieldInfo("Logo URL", shared=True),
    },
    "languages": {
        "language": FieldInfo("Language", shared=True),
        "proficiency": FieldInfo("Proficiency"),
    },
    "experiences": {
        "role": FieldInfo("Role"),
        "institution": FieldInfo("Institution"),
        "duration": FieldInfo("Duration", shared=True),
        "description": FieldInfo("Description", multiline=True),
        "primaryFocus": FieldInfo("Primary Focus", shared=True),
    },
    "projects": {
        "title": FieldInfo("Title"),
        "description": FieldInfo("Description", multiline=True),
        "url": FieldInfo("URL", shared=True),
    },
    "publications": {
        "title": FieldInfo("Title"),
        "authors": FieldInfo("Authors", shared=True),
        "journal": FieldInfo("Journal", shared=True),
        "year": FieldInfo("Year", shared=True),
        "doi": FieldInfo("DOI", shared=True),
        "url": FieldInfo("URL", shared=True),
        "notes": FieldInfo("Notes", multiline=True),
    },
    "references": {
        "name": FieldInfo("Name", shared=True),
        "position": FieldInfo("Position", shared=True),
        "department": FieldInfo("Department", shared=True),
        "institution": FieldInfo("Institution", shared=True),
        "location": FieldInfo("Location", shared=True),
        "URL": FieldInfo("URL", shared=True),
    },
    # skills & workshop entries are treated specially (flattened)
    "skills": {
        "long_name": FieldInfo("Skill", shared=True),
        "short_name": FieldInfo("Short Name", shared=True),
        "parent_category": FieldInfo("Parent Category", shared=True),
        "sub_category": FieldInfo("Sub Category", shared=True),
    },
    "workshop_and_certifications": {
        "issuer": FieldInfo("Issuer", shared=True),
        "name": FieldInfo("Certification Name"),
        "date": FieldInfo("Date", shared=True),
        "duration": FieldInfo("Duration", shared=True),
        "URL": FieldInfo("Certificate URL", shared=True),
    },
}


def get_section_label(section: str) -> str:
    return SECTION_LABELS.get(section, section.replace("_", " ").title())


def get_section_icon(section: str) -> str:
    return SECTION_ICONS.get(section, "📄")



def slugify(text: str) -> str:
    original = text.strip()
    text = original.lower()
    # replace Persian/Arabic spaces etc with dash
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9\-\_]+", "", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    # If the result is empty or just "tag" (non-Latin scripts), use a hash to make unique
    if not text or text == "tag":
        # Use a short hash of the original text to make it unique
        hash_suffix = hashlib.md5(original.encode("utf-8")).hexdigest()[:8]
        return f"tag-{hash_suffix}"
    return text


_NS = uuid.UUID("f23a5c6e-2c60-44f8-8e8b-2d3a2f1d4b7a")


def stable_uuid(resume_key: str, section: str, key: str) -> str:
    return str(uuid.uuid5(_NS, f"{resume_key}:{section}:{key}"))


def infer_lang_from_filename(name: str) -> str:
    n = name.lower()
    if n.endswith("_fa.json") or n.endswith(".fa.json") or "_fa." in n:
        return "fa"
    if n.endswith("_de.json") or n.endswith(".de.json") or "_de." in n:
        return "de"
    return "en"


def infer_resume_key_from_filename(name: str) -> str:
    base = name
    if base.lower().endswith(".json"):
        base = base[:-5]
    base = re.sub(r"(_fa|_de|_en)$", "", base, flags=re.IGNORECASE)
    base = re.sub(r"\s+", "_", base.strip())
    return base


def summarize_entry(section: str, data: Dict[str, Any]) -> str:
    try:
        if section == "basics":
            fn = data.get("fname", "") or ""
            ln = data.get("lname", "") or ""
            headline = data.get("headline", "") or data.get("label", "") or ""
            return f"{(fn + ' ' + ln).strip()} — {headline}".strip(" —")
        if section == "education":
            inst = data.get("institution", "")
            st = data.get("studyType", "")
            area = data.get("area", "")
            return " / ".join([x for x in [st, area, inst] if x]) or inst or "Education"
        if section == "profiles":
            net = data.get("network", "")
            usr = data.get("username", "")
            return f"{net}: {usr}".strip(": ") or net or "Profile"
        if section == "languages":
            return f"{data.get('language','')} — {data.get('proficiency','')}".strip(" —") or "Language"
        if section == "experiences":
            role = data.get("role", "")
            inst = data.get("institution", "")
            return f"{role} @ {inst}".strip(" @") or role or inst or "Experience"
        if section == "projects":
            return data.get("title") or "Project"
        if section == "publications":
            return data.get("title") or "Publication"
        if section == "references":
            nm = data.get("name", "")
            inst = data.get("institution", "")
            return f"{nm} — {inst}".strip(" —") or nm or "Reference"
        if section == "skills":
            return data.get("long_name") or data.get("short_name") or "Skill"
        if section == "workshop_and_certifications":
            issuer = data.get("issuer", "")
            nm = data.get("name", "")
            return f"{nm} — {issuer}".strip(" —") or nm or "Certification"
    except Exception:
        pass
    return section


def default_entry_data(section: str) -> Dict[str, Any]:
    if section in SECTION_FIELDS:
        out: Dict[str, Any] = {}
        for k in SECTION_FIELDS[section].keys():
            out[k] = ""
        return out
    return {}


def skills_flatten(skills_obj: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert the nested dict (Parent -> Sub -> [items]) into a flat list.
    Each returned item includes parent_category & sub_category.
    """
    out: List[Dict[str, Any]] = []
    for parent_cat, sub_map in (skills_obj or {}).items():
        if not isinstance(sub_map, dict):
            continue
        for sub_cat, items in sub_map.items():
            if not isinstance(items, list):
                continue
            for it in items:
                if not isinstance(it, dict):
                    continue
                d = dict(it)
                d["parent_category"] = parent_cat
                d["sub_category"] = sub_cat
                out.append(d)
    return out


def skills_group(entries: List[Any]) -> Dict[str, Dict[str, List[Any]]]:
    """
    Group Entry-like objects with .data dict into parent/sub category.
    """
    grouped: Dict[str, Dict[str, List[Any]]] = {}
    for e in entries:
        d = getattr(e, "data", {}) or {}
        p = d.get("parent_category", "Other")
        s = d.get("sub_category", "Other")
        grouped.setdefault(p, {}).setdefault(s, []).append(e)
    return grouped
