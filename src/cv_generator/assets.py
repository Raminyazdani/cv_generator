"""
Asset management module for CV Generator.

Provides asset validation, logo library resolver, and optional image optimization.
This module is read-only for data/ and writes only to output/ or user-specified directories.

Features:
- Asset reference discovery from CV JSON
- Asset existence validation
- Logo library with JSON mapping
- Optional image optimization (requires pillow)
"""

import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from .paths import get_repo_root

logger = logging.getLogger(__name__)

# Allowed image extensions for assets
ALLOWED_IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".pdf"}

# Default logo map location (outside data/)
DEFAULT_LOGO_MAP_PATH = "assets/logo_map.json"


class AssetType(Enum):
    """Type of asset reference."""

    PHOTO = "photo"
    LOGO = "logo"
    CERTIFICATE = "certificate"
    REFERENCE = "reference"
    OTHER = "other"


@dataclass
class AssetReference:
    """
    A reference to an asset in CV JSON.

    Attributes:
        path: Path or URL to the asset.
        asset_type: Type of asset (photo, logo, etc.).
        source_section: JSON section containing the reference (e.g., "basics", "education").
        source_key: JSON key or path to the field (e.g., "Pictures[0].URL").
        is_url: Whether the reference is a URL (http/https).
        is_local: Whether the reference is a local file path.
    """

    path: str
    asset_type: AssetType
    source_section: str
    source_key: str
    is_url: bool = False
    is_local: bool = False

    def __post_init__(self):
        """Determine if path is URL or local."""
        if self.path:
            parsed = urlparse(self.path)
            self.is_url = parsed.scheme in ("http", "https")
            self.is_local = not self.is_url and bool(self.path)


@dataclass
class AssetValidationResult:
    """
    Result of validating a single asset.

    Attributes:
        asset: The asset reference that was validated.
        exists: Whether the asset exists (for local files).
        readable: Whether the asset is readable.
        valid_extension: Whether the extension is in the allowed list.
        error: Error message if validation failed.
    """

    asset: AssetReference
    exists: bool = True
    readable: bool = True
    valid_extension: bool = True
    error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """True if asset passes all checks."""
        return self.exists and self.readable and self.valid_extension and self.error is None


@dataclass
class AssetValidationReport:
    """
    Complete asset validation report.

    Attributes:
        profile: Profile name.
        lang: Language code.
        results: List of validation results.
    """

    profile: str = ""
    lang: str = ""
    results: List[AssetValidationResult] = field(default_factory=list)

    @property
    def total_assets(self) -> int:
        """Total number of assets checked."""
        return len(self.results)

    @property
    def valid_count(self) -> int:
        """Number of valid assets."""
        return sum(1 for r in self.results if r.is_valid)

    @property
    def invalid_count(self) -> int:
        """Number of invalid assets."""
        return sum(1 for r in self.results if not r.is_valid)

    @property
    def missing_count(self) -> int:
        """Number of missing local assets."""
        return sum(1 for r in self.results if r.asset.is_local and not r.exists)

    @property
    def is_valid(self) -> bool:
        """True if all assets are valid."""
        return self.invalid_count == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "profile": self.profile,
            "lang": self.lang,
            "valid": self.is_valid,
            "summary": {
                "total": self.total_assets,
                "valid": self.valid_count,
                "invalid": self.invalid_count,
                "missing": self.missing_count,
            },
            "assets": [
                {
                    "path": r.asset.path,
                    "type": r.asset.asset_type.value,
                    "section": r.asset.source_section,
                    "key": r.asset.source_key,
                    "is_url": r.asset.is_url,
                    "valid": r.is_valid,
                    "error": r.error,
                }
                for r in self.results
            ],
        }

    def format_text(self, verbose: bool = False) -> str:
        """Format as human-readable text."""
        lines = []
        status_icon = "✅" if self.is_valid else "❌"

        header = f"{status_icon} Asset Validation"
        if self.profile:
            header += f" - {self.profile}"
            if self.lang:
                header += f"_{self.lang}"

        lines.append(header)
        lines.append("=" * 40)
        lines.append(
            f"   Total: {self.total_assets} | Valid: {self.valid_count} | Invalid: {self.invalid_count}"
        )
        lines.append("")

        # Show invalid assets first
        invalid_results = [r for r in self.results if not r.is_valid]
        if invalid_results:
            lines.append("❌ Missing/Invalid Assets:")
            for result in invalid_results:
                lines.append(f"   • {result.asset.path}")
                lines.append(f"     Section: {result.asset.source_section}.{result.asset.source_key}")
                if result.error:
                    lines.append(f"     Error: {result.error}")
                if result.asset.is_local and not result.exists:
                    # Provide hint for local files
                    lines.append(f"     💡 Expected at: {_get_expected_path(result.asset.path)}")
            lines.append("")

        # Show valid assets if verbose
        if verbose:
            valid_results = [r for r in self.results if r.is_valid]
            if valid_results:
                lines.append("✅ Valid Assets:")
                for result in valid_results:
                    icon = "🌐" if result.asset.is_url else "📁"
                    lines.append(f"   {icon} {result.asset.path}")

        return "\n".join(lines)


def _get_expected_path(path: str) -> str:
    """Get the expected full path for a relative asset path."""
    repo_root = get_repo_root()
    # Common asset directories
    candidates = [
        repo_root / "data" / "pics" / path,
        repo_root / "data" / "assets" / path,
        repo_root / "assets" / path,
        repo_root / path,
    ]
    return str(candidates[0])  # Return the most likely location


def discover_asset_references(cv_data: Dict[str, Any]) -> List[AssetReference]:
    """
    Discover all asset references in CV JSON data.

    Scans the CV data for known asset reference fields:
    - basics[].Pictures[].URL - profile photos
    - education[].logo_url - institution logos
    - workshop_and_certifications[].certifications[].URL - certificate files
    - references[].URL - reference letters

    Args:
        cv_data: Parsed CV JSON data.

    Returns:
        List of AssetReference objects found in the data.
    """
    assets = []

    # 1. Profile pictures in basics
    for i, basic in enumerate(cv_data.get("basics", [])):
        for j, pic in enumerate(basic.get("Pictures", [])):
            url = pic.get("URL")
            if url:
                pic_type = pic.get("type_of", "profile")
                assets.append(
                    AssetReference(
                        path=url,
                        asset_type=AssetType.PHOTO,
                        source_section="basics",
                        source_key=f"basics[{i}].Pictures[{j}].URL ({pic_type})",
                    )
                )

    # 2. Institution logos in education
    for i, edu in enumerate(cv_data.get("education", [])):
        logo_url = edu.get("logo_url")
        if logo_url:
            institution = edu.get("institution", "unknown")
            assets.append(
                AssetReference(
                    path=logo_url,
                    asset_type=AssetType.LOGO,
                    source_section="education",
                    source_key=f"education[{i}].logo_url ({institution})",
                )
            )

    # 3. Certificates in workshop_and_certifications
    for i, workshop in enumerate(cv_data.get("workshop_and_certifications", [])):
        issuer = workshop.get("issuer", "unknown")
        for j, cert in enumerate(workshop.get("certifications", [])):
            cert_url = cert.get("URL")
            if cert_url:
                cert_name = cert.get("name", "unknown")
                assets.append(
                    AssetReference(
                        path=cert_url,
                        asset_type=AssetType.CERTIFICATE,
                        source_section="workshop_and_certifications",
                        source_key=f"certifications[{i}][{j}].URL ({issuer}: {cert_name})",
                    )
                )

    # 4. Reference letters in references
    for i, ref in enumerate(cv_data.get("references", [])):
        ref_url = ref.get("URL")
        if ref_url:
            ref_name = ref.get("name", "unknown")
            assets.append(
                AssetReference(
                    path=ref_url,
                    asset_type=AssetType.REFERENCE,
                    source_section="references",
                    source_key=f"references[{i}].URL ({ref_name})",
                )
            )

    # 5. Language certifications
    for i, lang in enumerate(cv_data.get("languages", [])):
        lang_name = lang.get("language", "unknown")
        for j, cert in enumerate(lang.get("certifications", [])):
            cert_url = cert.get("URL")
            if cert_url:
                test_name = cert.get("test", "unknown")
                assets.append(
                    AssetReference(
                        path=cert_url,
                        asset_type=AssetType.CERTIFICATE,
                        source_section="languages",
                        source_key=f"languages[{i}].certifications[{j}].URL ({lang_name}: {test_name})",
                    )
                )

    return assets


def validate_asset(
    asset: AssetReference,
    base_dirs: Optional[List[Path]] = None,
) -> AssetValidationResult:
    """
    Validate a single asset reference.

    For URLs, only validates that the URL is well-formed.
    For local files, checks existence and extension.

    Args:
        asset: The asset reference to validate.
        base_dirs: List of base directories to search for local files.

    Returns:
        AssetValidationResult with validation status.
    """
    result = AssetValidationResult(asset=asset)

    # Skip validation for empty paths
    if not asset.path:
        result.error = "Empty asset path"
        result.exists = False
        return result

    # URLs are assumed valid if well-formed
    if asset.is_url:
        # Basic URL validation already done in AssetReference.__post_init__
        # We don't actually fetch URLs - that would be intrusive
        return result

    # Local file validation
    if base_dirs is None:
        repo_root = get_repo_root()
        base_dirs = [
            repo_root / "data" / "pics",
            repo_root / "data" / "assets",
            repo_root / "assets",
            repo_root,
        ]

    # Try to find the file
    asset_path = Path(asset.path)

    # If path is absolute, check directly
    if asset_path.is_absolute():
        if asset_path.exists():
            result.exists = True
            result.readable = os.access(asset_path, os.R_OK)
        else:
            result.exists = False
            result.error = f"File not found: {asset_path}"
    else:
        # Search in base directories
        found = False
        for base_dir in base_dirs:
            full_path = base_dir / asset_path
            if full_path.exists():
                found = True
                result.exists = True
                result.readable = os.access(full_path, os.R_OK)
                break

        if not found:
            result.exists = False
            result.error = f"File not found in any of: {', '.join(str(d) for d in base_dirs)}"

    # Check extension if file exists
    if result.exists:
        ext = asset_path.suffix.lower()
        if ext and ext not in ALLOWED_IMAGE_EXTENSIONS:
            result.valid_extension = False
            result.error = f"Invalid extension '{ext}'. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"

    return result


def check_assets(
    cv_data: Dict[str, Any],
    profile: str = "",
    lang: str = "",
    base_dirs: Optional[List[Path]] = None,
) -> AssetValidationReport:
    """
    Check all assets in CV data.

    This is the main entry point for asset validation.

    Args:
        cv_data: Parsed CV JSON data.
        profile: Profile name for reporting.
        lang: Language code for reporting.
        base_dirs: Optional list of directories to search for local files.

    Returns:
        AssetValidationReport with all validation results.
    """
    report = AssetValidationReport(profile=profile, lang=lang)

    # Discover all asset references
    assets = discover_asset_references(cv_data)

    # Validate each asset
    for asset in assets:
        result = validate_asset(asset, base_dirs)
        report.results.append(result)

    return report


class LogoResolver:
    """
    Resolve institution names to logo paths using a mapping file.

    The logo map is a JSON file with structure:
    {
        "mapping": {
            "Institution Name": "path/to/logo.png",
            "Another University": "logos/another.png"
        },
        "default": "logos/default.png"
    }
    """

    def __init__(self, map_path: Optional[Path] = None):
        """
        Initialize the logo resolver.

        Args:
            map_path: Path to logo map JSON file. Defaults to assets/logo_map.json.
        """
        if map_path is None:
            map_path = get_repo_root() / DEFAULT_LOGO_MAP_PATH

        self.map_path = Path(map_path)
        self._mapping: Dict[str, str] = {}
        self._default: Optional[str] = None
        self._loaded = False

    def _load(self) -> None:
        """Load the mapping file if it exists."""
        if self._loaded:
            return

        if self.map_path.exists():
            try:
                with open(self.map_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._mapping = data.get("mapping", {})
                self._default = data.get("default")
                logger.debug(f"Loaded {len(self._mapping)} logo mappings from {self.map_path}")
            except Exception as e:
                logger.warning(f"Failed to load logo map: {e}")

        self._loaded = True

    def resolve(self, institution: str) -> Optional[str]:
        """
        Resolve an institution name to a logo path.

        Uses a deterministic matching strategy:
        1. Exact match (case-insensitive)
        2. Partial match (institution contains key or vice versa)
        3. Default logo if configured

        Args:
            institution: Institution name to look up.

        Returns:
            Path to logo file, or None if no match found.
        """
        self._load()

        if not institution:
            return self._default

        institution_lower = institution.lower().strip()

        # 1. Exact match (case-insensitive)
        for key, path in self._mapping.items():
            if key.lower() == institution_lower:
                return path

        # 2. Partial match
        for key, path in self._mapping.items():
            key_lower = key.lower()
            if key_lower in institution_lower or institution_lower in key_lower:
                return path

        # 3. Default
        return self._default

    def list_mappings(self) -> Dict[str, str]:
        """Return all available mappings."""
        self._load()
        return dict(self._mapping)


def optimize_assets(
    cv_data: Dict[str, Any],
    output_dir: Path,
    max_width: int = 800,
    max_height: int = 800,
    quality: int = 85,
) -> Dict[str, Any]:
    """
    Optimize images from CV data and copy to output directory.

    This function NEVER modifies files in data/.
    It copies and optionally resizes images to the output directory.

    Args:
        cv_data: Parsed CV JSON data.
        output_dir: Directory to write optimized assets.
        max_width: Maximum width for resized images.
        max_height: Maximum height for resized images.
        quality: JPEG quality (1-100).

    Returns:
        Dictionary with optimization results.

    Raises:
        ValueError: If output_dir is under data/.
    """
    # Safety check: refuse to write under data/
    repo_root = get_repo_root()
    data_dir = repo_root / "data"
    output_dir = Path(output_dir).resolve()

    if str(output_dir).startswith(str(data_dir)):
        raise ValueError(
            f"Refusing to write to {output_dir} - output must not be under data/. "
            "Use a path outside data/, such as output/assets_optimized/"
        )

    # Try to import Pillow
    try:
        from PIL import Image

        has_pillow = True
    except ImportError:
        has_pillow = False
        logger.warning("Pillow not installed. Image optimization will only copy files.")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Discover local assets
    assets = discover_asset_references(cv_data)
    local_assets = [a for a in assets if a.is_local]

    results = {
        "output_dir": str(output_dir),
        "processed": 0,
        "optimized": 0,
        "copied": 0,
        "skipped": 0,
        "errors": [],
        "files": [],
    }

    if not local_assets:
        logger.info("No local assets found to optimize")
        return results

    # Base directories to search for source files
    base_dirs = [
        repo_root / "data" / "pics",
        repo_root / "data" / "assets",
        repo_root / "assets",
        repo_root,
    ]

    for asset in local_assets:
        asset_path = Path(asset.path)
        source_path = None

        # Find source file
        if asset_path.is_absolute():
            if asset_path.exists():
                source_path = asset_path
        else:
            for base_dir in base_dirs:
                candidate = base_dir / asset_path
                if candidate.exists():
                    source_path = candidate
                    break

        if source_path is None:
            results["skipped"] += 1
            results["errors"].append(f"Source not found: {asset.path}")
            continue

        # Determine output path
        dest_path = output_dir / asset_path.name

        try:
            # Check if we can optimize (image file and pillow available)
            ext = source_path.suffix.lower()
            can_optimize = has_pillow and ext in {".jpg", ".jpeg", ".png"}

            if can_optimize:
                # Optimize with Pillow
                with Image.open(source_path) as img:
                    # Calculate new size maintaining aspect ratio
                    orig_width, orig_height = img.size
                    ratio = min(max_width / orig_width, max_height / orig_height, 1.0)

                    if ratio < 1.0:
                        new_size = (int(orig_width * ratio), int(orig_height * ratio))
                        img = img.resize(new_size, Image.Resampling.LANCZOS)

                    # Convert to RGB if necessary (for JPEG)
                    if ext in {".jpg", ".jpeg"} and img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")

                    # Save optimized image
                    img.save(dest_path, quality=quality, optimize=True)

                results["optimized"] += 1
            else:
                # Just copy the file
                shutil.copy2(source_path, dest_path)
                results["copied"] += 1

            results["processed"] += 1
            results["files"].append({
                "source": str(source_path),
                "dest": str(dest_path),
                "optimized": can_optimize,
            })

        except Exception as e:
            results["skipped"] += 1
            results["errors"].append(f"Error processing {asset.path}: {e}")
            logger.warning(f"Failed to process {asset.path}: {e}")

    return results
