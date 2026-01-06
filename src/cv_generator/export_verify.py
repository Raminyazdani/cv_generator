"""
Verification and diff tools for CV export accuracy.

This module provides tools to verify that exported JSON matches the original
files that were imported. It performs deep comparison and generates detailed
diff reports.

Key features:
- Deep structural comparison (same keys, same nesting)
- Value comparison with type awareness
- Order tracking for arrays and dict keys
- Human-readable diff reports
- Round-trip verification (import → export → compare)
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ValueDiff:
    """Represents a difference in value between original and exported."""

    path: str  # JSON path like "education[0].institution"
    original: Any
    exported: Any
    diff_type: str = "value"  # value, type, missing, extra

    def __str__(self) -> str:
        if self.diff_type == "missing":
            return f"{self.path}: MISSING in exported (was: {self.original!r})"
        elif self.diff_type == "extra":
            return f"{self.path}: EXTRA in exported (value: {self.exported!r})"
        elif self.diff_type == "type":
            return f"{self.path}: TYPE mismatch - original: {type(self.original).__name__}, exported: {type(self.exported).__name__}"
        else:
            return f"{self.path}: VALUE differs - original: {self.original!r}, exported: {self.exported!r}"


@dataclass
class VerificationResult:
    """Result of comparing exported data against original JSON file."""

    matches: bool
    original_path: Optional[Path] = None

    # Structural differences
    missing_keys: List[str] = field(default_factory=list)  # Keys in original but not exported
    extra_keys: List[str] = field(default_factory=list)  # Keys in exported but not original

    # Value differences
    value_diffs: List[ValueDiff] = field(default_factory=list)

    # Type differences
    type_diffs: List[ValueDiff] = field(default_factory=list)

    # Order differences (if tracking)
    order_diffs: List[str] = field(default_factory=list)

    def get_summary(self) -> str:
        """Generate human-readable summary."""
        if self.matches:
            return "✅ IDENTICAL - No differences found"

        lines = ["❌ DIFFERENCES FOUND"]

        if self.missing_keys:
            lines.append(f"\n  Missing keys ({len(self.missing_keys)}):")
            for key in self.missing_keys[:10]:
                lines.append(f"    - {key}")
            if len(self.missing_keys) > 10:
                lines.append(f"    ... and {len(self.missing_keys) - 10} more")

        if self.extra_keys:
            lines.append(f"\n  Extra keys ({len(self.extra_keys)}):")
            for key in self.extra_keys[:10]:
                lines.append(f"    - {key}")
            if len(self.extra_keys) > 10:
                lines.append(f"    ... and {len(self.extra_keys) - 10} more")

        if self.value_diffs:
            lines.append(f"\n  Value differences ({len(self.value_diffs)}):")
            for diff in self.value_diffs[:10]:
                lines.append(f"    - {diff}")
            if len(self.value_diffs) > 10:
                lines.append(f"    ... and {len(self.value_diffs) - 10} more")

        if self.type_diffs:
            lines.append(f"\n  Type differences ({len(self.type_diffs)}):")
            for diff in self.type_diffs[:10]:
                lines.append(f"    - {diff}")
            if len(self.type_diffs) > 10:
                lines.append(f"    ... and {len(self.type_diffs) - 10} more")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON output."""
        return {
            "matches": self.matches,
            "original_path": str(self.original_path) if self.original_path else None,
            "missing_keys": self.missing_keys,
            "extra_keys": self.extra_keys,
            "value_diffs": [
                {"path": d.path, "original": d.original, "exported": d.exported, "type": d.diff_type}
                for d in self.value_diffs
            ],
            "type_diffs": [
                {"path": d.path, "original": type(d.original).__name__, "exported": type(d.exported).__name__}
                for d in self.type_diffs
            ],
            "order_diffs": self.order_diffs,
        }


@dataclass
class RoundTripResult:
    """Result of full round-trip test: import file, export, compare."""

    original_path: Path
    resume_key: str
    lang_code: str

    import_success: bool
    export_success: bool
    verification: Optional[VerificationResult] = None

    import_error: Optional[str] = None
    export_error: Optional[str] = None

    duration_ms: float = 0.0

    @property
    def success(self) -> bool:
        """True if round-trip was completely successful."""
        return (
            self.import_success
            and self.export_success
            and self.verification is not None
            and self.verification.matches
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON output."""
        return {
            "original_path": str(self.original_path),
            "resume_key": self.resume_key,
            "lang_code": self.lang_code,
            "import_success": self.import_success,
            "export_success": self.export_success,
            "verification": self.verification.to_dict() if self.verification else None,
            "import_error": self.import_error,
            "export_error": self.export_error,
            "success": self.success,
            "duration_ms": self.duration_ms,
        }


@dataclass
class BatchVerificationResult:
    """Result of verifying multiple files."""

    total_files: int = 0
    passed: int = 0
    failed: int = 0
    results: List[VerificationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON output."""
        return {
            "total_files": self.total_files,
            "passed": self.passed,
            "failed": self.failed,
            "results": [r.to_dict() for r in self.results],
        }


class ExportVerifier:
    """Tools to verify export accuracy against original files."""

    def __init__(
        self,
        ignore_order: bool = False,
        ignore_whitespace: bool = True,
        ignore_type_key_order: bool = True,
    ):
        """
        Initialize verifier.

        Args:
            ignore_order: Whether to ignore key order differences
            ignore_whitespace: Whether to ignore whitespace in string values
            ignore_type_key_order: Whether to treat type_key arrays as sets (ignore order)
        """
        self.ignore_order = ignore_order
        self.ignore_whitespace = ignore_whitespace
        self.ignore_type_key_order = ignore_type_key_order

    def verify_export(
        self,
        original_path: Path,
        exported_data: dict,
    ) -> VerificationResult:
        """
        Compare exported data against original JSON file.

        Args:
            original_path: Path to original JSON file
            exported_data: Exported dictionary to compare

        Returns:
            VerificationResult with detailed diff report
        """
        original_path = Path(original_path)

        result = VerificationResult(
            matches=False,
            original_path=original_path,
        )

        try:
            with open(original_path, "r", encoding="utf-8") as f:
                original_data = json.load(f)

            logger.info(f"[VERIFY] Comparing: original={original_path.name}")

            # Perform deep comparison
            self._compare_values(original_data, exported_data, "", result)

            # Determine if they match
            result.matches = (
                len(result.missing_keys) == 0
                and len(result.extra_keys) == 0
                and len(result.value_diffs) == 0
                and len(result.type_diffs) == 0
            )

            if result.matches:
                logger.info("[VERIFY] Result: IDENTICAL ✓")
            else:
                logger.warning(f"[VERIFY] Result: {len(result.value_diffs)} differences found")

        except json.JSONDecodeError as e:
            logger.error(f"[VERIFY] Invalid JSON in original file: {e}")
            result.value_diffs.append(
                ValueDiff(path="", original="", exported="", diff_type="error")
            )
        except FileNotFoundError:
            logger.error(f"[VERIFY] Original file not found: {original_path}")
            result.value_diffs.append(
                ValueDiff(path="", original="", exported="", diff_type="error")
            )

        return result

    def verify_round_trip(
        self,
        json_path: Path,
        db_path: Path,
    ) -> RoundTripResult:
        """
        Full round-trip test: import file, export, compare.

        Args:
            json_path: Path to original JSON file
            db_path: Path to database (will be created if needed)

        Returns:
            RoundTripResult with success status and verification
        """
        import time

        from .importer_v2 import CVImporter
        from .exporter_v2 import CVExporter
        from .schema_v2 import init_db_v2

        start_time = time.time()
        json_path = Path(json_path)
        db_path = Path(db_path)

        result = RoundTripResult(
            original_path=json_path,
            resume_key="",
            lang_code="",
            import_success=False,
            export_success=False,
        )

        try:
            # Initialize database
            init_db_v2(db_path, force=True)

            # Import
            importer = CVImporter(db_path)
            import_result = importer.import_file(json_path)

            if not import_result.success:
                result.import_error = import_result.error
                return result

            result.import_success = True
            result.resume_key = import_result.resume_key
            result.lang_code = import_result.lang_code

            # Export
            exporter = CVExporter(db_path)
            try:
                exported_data = exporter.export(
                    resume_key=import_result.resume_key,
                    lang_code=import_result.lang_code,
                )
                result.export_success = True
            except Exception as e:
                result.export_error = str(e)
                return result

            # Verify
            result.verification = self.verify_export(json_path, exported_data)

        except Exception as e:
            logger.error(f"[VERIFY] Round-trip error: {e}")
            result.import_error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    def batch_verify(
        self,
        original_dir: Path,
        exported_dir: Path,
    ) -> BatchVerificationResult:
        """
        Verify all files in directories match.

        Args:
            original_dir: Directory with original JSON files
            exported_dir: Directory with exported JSON files

        Returns:
            BatchVerificationResult with results for each file
        """
        original_dir = Path(original_dir)
        exported_dir = Path(exported_dir)

        result = BatchVerificationResult()

        # Find all JSON files in original directory
        original_files = sorted(original_dir.glob("*.json"))
        result.total_files = len(original_files)

        for original_path in original_files:
            # Find corresponding exported file
            exported_path = exported_dir / original_path.name

            if not exported_path.exists():
                # Try alternate naming patterns
                alt_names = [
                    original_path.name,
                    original_path.stem.replace("_", "") + ".json",
                ]
                for alt in alt_names:
                    alt_path = exported_dir / alt
                    if alt_path.exists():
                        exported_path = alt_path
                        break

            if not exported_path.exists():
                ver_result = VerificationResult(
                    matches=False,
                    original_path=original_path,
                    missing_keys=["ENTIRE_FILE"],
                )
                result.results.append(ver_result)
                result.failed += 1
                continue

            # Load exported data and verify
            try:
                with open(exported_path, "r", encoding="utf-8") as f:
                    exported_data = json.load(f)

                ver_result = self.verify_export(original_path, exported_data)
                result.results.append(ver_result)

                if ver_result.matches:
                    result.passed += 1
                else:
                    result.failed += 1

            except Exception as e:
                ver_result = VerificationResult(
                    matches=False,
                    original_path=original_path,
                )
                ver_result.value_diffs.append(
                    ValueDiff(path="", original="", exported=str(e), diff_type="error")
                )
                result.results.append(ver_result)
                result.failed += 1

        return result

    def _compare_values(
        self,
        original: Any,
        exported: Any,
        path: str,
        result: VerificationResult,
    ) -> None:
        """
        Recursively compare two values and record differences.

        Args:
            original: Value from original JSON
            exported: Value from exported data
            path: Current JSON path for error reporting
            result: VerificationResult to populate
        """
        from collections import OrderedDict

        # Handle None values
        if original is None and exported is None:
            return

        if original is None:
            result.extra_keys.append(path)
            return

        if exported is None:
            result.missing_keys.append(path)
            return

        # Type comparison
        orig_type = type(original)
        exp_type = type(exported)

        # Treat OrderedDict as dict for comparison purposes
        if orig_type == OrderedDict:
            orig_type = dict
        if exp_type == OrderedDict:
            exp_type = dict

        # Allow int/float comparison (8 vs 8.0)
        if {orig_type, exp_type} <= {int, float}:
            if float(original) != float(exported):
                result.value_diffs.append(
                    ValueDiff(path=path, original=original, exported=exported, diff_type="value")
                )
            return

        # Type mismatch (except numeric)
        if orig_type != exp_type:
            # String vs number handling
            if (isinstance(original, str) and isinstance(exported, (int, float))) or \
               (isinstance(exported, str) and isinstance(original, (int, float))):
                # Compare as strings
                if str(original) != str(exported):
                    result.type_diffs.append(
                        ValueDiff(path=path, original=original, exported=exported, diff_type="type")
                    )
                return

            result.type_diffs.append(
                ValueDiff(path=path, original=original, exported=exported, diff_type="type")
            )
            return

        # Compare by type
        if isinstance(original, dict):
            self._compare_dicts(original, exported, path, result)
        elif isinstance(original, list):
            self._compare_lists(original, exported, path, result)
        elif isinstance(original, str):
            if self.ignore_whitespace:
                if original.strip() != exported.strip():
                    result.value_diffs.append(
                        ValueDiff(path=path, original=original, exported=exported, diff_type="value")
                    )
            else:
                if original != exported:
                    result.value_diffs.append(
                        ValueDiff(path=path, original=original, exported=exported, diff_type="value")
                    )
        elif isinstance(original, bool):
            if original != exported:
                result.value_diffs.append(
                    ValueDiff(path=path, original=original, exported=exported, diff_type="value")
                )
        else:
            if original != exported:
                result.value_diffs.append(
                    ValueDiff(path=path, original=original, exported=exported, diff_type="value")
                )

    def _compare_dicts(
        self,
        original: dict,
        exported: dict,
        path: str,
        result: VerificationResult,
    ) -> None:
        """Compare two dictionaries."""
        orig_keys = set(original.keys())
        exp_keys = set(exported.keys())

        # Missing keys
        for key in orig_keys - exp_keys:
            key_path = f"{path}.{key}" if path else key
            result.missing_keys.append(key_path)

        # Extra keys
        for key in exp_keys - orig_keys:
            key_path = f"{path}.{key}" if path else key
            result.extra_keys.append(key_path)

        # Compare common keys
        for key in orig_keys & exp_keys:
            key_path = f"{path}.{key}" if path else key
            self._compare_values(original[key], exported[key], key_path, result)

        # Check key order if not ignoring
        if not self.ignore_order:
            orig_order = list(original.keys())
            exp_order = list(exported.keys())
            if orig_order != exp_order:
                result.order_diffs.append(
                    f"{path}: key order differs - original: {orig_order[:5]}..., exported: {exp_order[:5]}..."
                )

    def _compare_lists(
        self,
        original: list,
        exported: list,
        path: str,
        result: VerificationResult,
    ) -> None:
        """Compare two lists."""
        # Special handling for type_key arrays - compare as sets if configured
        if self.ignore_type_key_order and path.endswith("type_key"):
            # Compare as sets - only check if same elements exist
            orig_set = set(str(x) for x in original if x is not None)
            exp_set = set(str(x) for x in exported if x is not None)
            if orig_set != exp_set:
                missing = orig_set - exp_set
                extra = exp_set - orig_set
                if missing or extra:
                    result.value_diffs.append(
                        ValueDiff(
                            path=path,
                            original=f"missing: {missing}" if missing else "",
                            exported=f"extra: {extra}" if extra else "",
                            diff_type="value",
                        )
                    )
            return

        if len(original) != len(exported):
            result.value_diffs.append(
                ValueDiff(
                    path=path,
                    original=f"length={len(original)}",
                    exported=f"length={len(exported)}",
                    diff_type="value",
                )
            )
            # Still compare up to the shorter length
            min_len = min(len(original), len(exported))
        else:
            min_len = len(original)

        for i in range(min_len):
            item_path = f"{path}[{i}]"
            self._compare_values(original[i], exported[i], item_path, result)


def compare_json_files(
    original_path: Path,
    exported_path: Path,
) -> VerificationResult:
    """
    Convenience function to compare two JSON files.

    Args:
        original_path: Path to original JSON file
        exported_path: Path to exported JSON file

    Returns:
        VerificationResult with comparison results
    """
    with open(exported_path, "r", encoding="utf-8") as f:
        exported_data = json.load(f)

    verifier = ExportVerifier()
    return verifier.verify_export(original_path, exported_data)
