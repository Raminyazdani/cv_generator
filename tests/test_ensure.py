"""
Tests for cv_generator.ensure module.

Tests the multilingual CV JSON consistency checker.
"""

import json
from pathlib import Path

import pytest

from cv_generator.ensure import (
    EnsureIssue,
    EnsureReport,
    compare_cv_structure,
    find_cv_files,
    get_item_identity,
    match_list_items,
    run_ensure,
)

# Get fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestEnsureIssue:
    """Tests for EnsureIssue class."""

    def test_to_dict_basic(self):
        """Test basic conversion to dict."""
        issue = EnsureIssue(
            lang="de",
            path="skills.Programming",
            issue_type="missing",
            expected="Programming Languages",
            hint="Key missing"
        )
        result = issue.to_dict()

        assert result["lang"] == "de"
        assert result["path"] == "skills.Programming"
        assert result["issue_type"] == "missing"
        assert result["expected"] == "Programming Languages"
        assert result["hint"] == "Key missing"

    def test_to_dict_minimal(self):
        """Test minimal conversion to dict."""
        issue = EnsureIssue(
            lang="de",
            path="basics",
            issue_type="extra",
        )
        result = issue.to_dict()

        assert result["lang"] == "de"
        assert result["path"] == "basics"
        assert "expected" not in result
        assert "hint" not in result


class TestEnsureReport:
    """Tests for EnsureReport class."""

    def test_empty_report_is_valid(self):
        """Test that empty report is valid."""
        report = EnsureReport()
        assert report.is_valid
        assert report.total_issues == 0

    def test_report_with_issues_not_valid(self):
        """Test that report with issues is not valid."""
        report = EnsureReport()
        report.missing.append(EnsureIssue(
            lang="de",
            path="basics",
            issue_type="missing"
        ))

        assert not report.is_valid
        assert report.total_issues == 1

    def test_to_dict(self):
        """Test conversion to dict."""
        report = EnsureReport()
        report.missing.append(EnsureIssue(
            lang="de",
            path="basics",
            issue_type="missing"
        ))
        report.extra.append(EnsureIssue(
            lang="de",
            path="extra_key",
            issue_type="extra"
        ))

        result = report.to_dict()

        assert len(result["missing"]) == 1
        assert len(result["extra"]) == 1
        assert result["summary"]["total_issues"] == 2

    def test_format_text_valid(self):
        """Test text formatting for valid report."""
        report = EnsureReport()
        text = report.format_text()

        assert "consistent" in text.lower() or "✓" in text

    def test_format_text_with_issues(self):
        """Test text formatting with issues."""
        report = EnsureReport()
        report.missing.append(EnsureIssue(
            lang="de",
            path="basics",
            issue_type="missing",
            hint="Key missing"
        ))

        text = report.format_text()

        assert "Missing" in text
        assert "[de]" in text
        assert "basics" in text


class TestGetItemIdentity:
    """Tests for get_item_identity function."""

    def test_identity_by_url(self):
        """Test identity by URL."""
        item = {"url": "https://example.com", "title": "Test"}
        identity = get_item_identity(item, "projects")

        assert identity == "url:https://example.com"

    def test_identity_by_title(self):
        """Test identity by title when no URL."""
        item = {"title": "Test Project", "url": None}
        identity = get_item_identity(item, "projects")

        assert identity == "title:Test Project"

    def test_identity_by_experience(self):
        """Test identity for experience items."""
        item = {
            "role": "Developer",
            "institution": "Company",
            "duration": "2020-2022"
        }
        identity = get_item_identity(item, "experiences")

        assert identity == "exp:Developer|Company|2020-2022"

    def test_identity_by_email(self):
        """Test identity by email for references."""
        item = {"name": "John", "email": ["john@example.com"]}
        identity = get_item_identity(item, "references")

        assert identity == "email:john@example.com"

    def test_identity_none_for_non_dict(self):
        """Test that non-dict returns None."""
        identity = get_item_identity("string", "context")
        assert identity is None


class TestMatchListItems:
    """Tests for match_list_items function."""

    def test_match_by_identity(self):
        """Test matching by identity."""
        en_list = [
            {"url": "https://a.com"},
            {"url": "https://b.com"},
        ]
        other_list = [
            {"url": "https://b.com"},  # Swapped order
            {"url": "https://a.com"},
        ]

        matches = match_list_items(en_list, other_list, "projects")

        # First item should match index 1 in other list
        assert matches[0][1] == 1
        assert matches[0][2] == "identity"
        # Second item should match index 0 in other list
        assert matches[1][1] == 0

    def test_match_by_index_fallback(self):
        """Test fallback to index matching."""
        en_list = [{"x": 1}, {"x": 2}]
        other_list = [{"y": 1}, {"y": 2}]

        matches = match_list_items(en_list, other_list, "context")

        assert matches[0][1] == 0
        assert matches[0][2] == "index"
        assert matches[1][1] == 1


class TestCompareStructure:
    """Tests for compare_cv_structure function."""

    def test_identical_structures(self):
        """Test that identical structures produce no issues."""
        en_data = {"a": 1, "b": {"c": 2}}
        other_data = {"a": 1, "b": {"c": 2}}

        report = compare_cv_structure(en_data, other_data, "de")

        assert report.is_valid

    def test_missing_key(self):
        """Test detection of missing key."""
        en_data = {"a": 1, "b": 2}
        other_data = {"a": 1}

        report = compare_cv_structure(en_data, other_data, "de")

        assert len(report.missing) == 1
        assert report.missing[0].path == "b"

    def test_extra_key(self):
        """Test detection of extra key."""
        en_data = {"a": 1}
        other_data = {"a": 1, "b": 2}

        report = compare_cv_structure(en_data, other_data, "de")

        assert len(report.extra) == 1
        assert report.extra[0].path == "b"

    def test_missing_list_item(self):
        """Test detection of missing list item."""
        en_data = {"items": [{"id": 1}, {"id": 2}]}
        other_data = {"items": [{"id": 1}]}

        report = compare_cv_structure(en_data, other_data, "de")

        assert len(report.missing) == 1
        assert "items[1]" in report.missing[0].path

    def test_extra_list_item(self):
        """Test detection of extra list item."""
        en_data = {"items": [{"id": 1}]}
        other_data = {"items": [{"id": 1}, {"id": 2}]}

        report = compare_cv_structure(en_data, other_data, "de")

        assert len(report.extra) == 1


class TestFindCVFiles:
    """Tests for find_cv_files function."""

    def test_find_with_explicit_paths(self):
        """Test finding with explicit paths."""
        paths = {
            "en": Path("/path/to/en.json"),
            "de": Path("/path/to/de.json"),
        }

        result = find_cv_files("test", ["en", "de"], paths=paths)

        assert result == paths

    def test_find_in_directory(self):
        """Test finding files in fixture directory."""
        fixture_dir = FIXTURES_DIR / "ramin"

        if fixture_dir.exists():
            result = find_cv_files("ramin", ["en", "de", "fa"], cvs_dir=fixture_dir)

            assert "en" in result
            assert "de" in result
            assert "fa" in result


class TestRunEnsure:
    """Tests for run_ensure function."""

    def test_run_ensure_valid(self):
        """Test running ensure on valid fixture."""
        fixture_dir = FIXTURES_DIR / "ramin"
        lang_map_path = fixture_dir / "lang.json"

        if fixture_dir.exists():
            with open(lang_map_path, "r", encoding="utf-8") as f:
                lang_map = json.load(f)

            report = run_ensure(
                name="ramin",
                langs=["en", "de", "fa"],
                cvs_dir=fixture_dir,
                lang_map=lang_map,
            )

            assert report.is_valid

    def test_run_ensure_mismatch(self):
        """Test running ensure on mismatch fixture."""
        fixture_dir = FIXTURES_DIR / "mismatch"
        lang_map_path = fixture_dir / "lang.json"

        if fixture_dir.exists():
            with open(lang_map_path, "r", encoding="utf-8") as f:
                lang_map = json.load(f)

            report = run_ensure(
                name="mismatch",
                langs=["en", "de"],
                cvs_dir=fixture_dir,
                lang_map=lang_map,
            )

            assert not report.is_valid
            assert report.total_issues > 0

    def test_run_ensure_missing_file(self):
        """Test running ensure when file is missing."""
        report = run_ensure(
            name="nonexistent",
            langs=["en", "de"],
            cvs_dir=Path("/nonexistent"),
        )

        assert not report.is_valid
        assert len(report.missing) > 0


class TestEnsureCommand:
    """Integration tests for the ensure CLI command."""

    def test_ensure_help(self, capsys):
        """Test that ensure --help works."""
        from cv_generator.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["ensure", "--help"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--name" in captured.out
        assert "--langs" in captured.out

    def test_ensure_valid_fixture(self):
        """Test ensure command on valid fixture."""
        from cv_generator.cli import main

        fixture_dir = FIXTURES_DIR / "ramin"
        lang_map_path = fixture_dir / "lang.json"

        if fixture_dir.exists():
            result = main([
                "ensure",
                "--name", "ramin",
                "--dir", str(fixture_dir),
                "--lang-map", str(lang_map_path),
            ])

            assert result == 0

    def test_ensure_mismatch_fixture(self):
        """Test ensure command on mismatch fixture."""
        from cv_generator.cli import main

        fixture_dir = FIXTURES_DIR / "mismatch"
        lang_map_path = fixture_dir / "lang.json"

        if fixture_dir.exists():
            result = main([
                "ensure",
                "--name", "mismatch",
                "--langs", "en,de",
                "--dir", str(fixture_dir),
                "--lang-map", str(lang_map_path),
            ])

            assert result == 2  # EXIT_ENSURE_ERROR

    def test_ensure_json_output(self, capsys):
        """Test ensure command with JSON output."""
        from cv_generator.cli import main

        fixture_dir = FIXTURES_DIR / "mismatch"
        lang_map_path = fixture_dir / "lang.json"

        if fixture_dir.exists():
            main([
                "ensure",
                "--name", "mismatch",
                "--langs", "en,de",
                "--dir", str(fixture_dir),
                "--lang-map", str(lang_map_path),
                "--format", "json",
            ])

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            assert "missing" in output
            assert "extra" in output
            assert "summary" in output


class TestEnsureStrictMode:
    """Tests for strict mode functionality."""

    def test_strict_mode_returns_nonzero_on_mismatch(self):
        """Test that --strict returns non-zero exit code on any mismatch."""
        from cv_generator.cli import main

        fixture_dir = FIXTURES_DIR / "mismatch"
        lang_map_path = fixture_dir / "lang.json"

        if fixture_dir.exists():
            result = main([
                "ensure",
                "--name", "mismatch",
                "--langs", "en,de",
                "--dir", str(fixture_dir),
                "--lang-map", str(lang_map_path),
                "--strict",
            ])

            assert result == 2  # EXIT_ENSURE_ERROR

    def test_strict_mode_returns_zero_on_valid(self):
        """Test that --strict returns zero exit code when valid."""
        from cv_generator.cli import main

        fixture_dir = FIXTURES_DIR / "ramin"
        lang_map_path = fixture_dir / "lang.json"

        if fixture_dir.exists():
            result = main([
                "ensure",
                "--name", "ramin",
                "--dir", str(fixture_dir),
                "--lang-map", str(lang_map_path),
                "--strict",
            ])

            assert result == 0


class TestEnsureFixMode:
    """Tests for fix mode functionality."""

    def test_fix_creates_output_files(self, tmp_path):
        """Test that --fix creates fixed output files."""
        from cv_generator.cli import main

        fixture_dir = FIXTURES_DIR / "mismatch"
        lang_map_path = fixture_dir / "lang.json"
        fix_out = tmp_path / "fixed"

        if fixture_dir.exists():
            main([
                "ensure",
                "--name", "mismatch",
                "--langs", "en,de",
                "--dir", str(fixture_dir),
                "--lang-map", str(lang_map_path),
                "--fix",
                "--fix-out", str(fix_out),
            ])

            # Check fixed file was created
            fixed_file = fix_out / "cv.de.json"
            assert fixed_file.exists()

            # Check fixed file is valid JSON
            with open(fixed_file) as f:
                fixed_data = json.load(f)

            # Check that missing keys were added
            assert "phone" in fixed_data["basics"][0]

    def test_fix_refuses_data_path(self, tmp_path):
        """Test that --fix refuses to write to data/ directory."""
        from cv_generator.ensure import write_fixed_cvs, is_path_under_data

        # Test the path detection
        assert is_path_under_data(Path("data/cvs/fixed"))
        assert is_path_under_data(Path("/path/to/data/cvs/"))
        assert not is_path_under_data(Path("output/fixed"))
        assert not is_path_under_data(Path(tmp_path))

    def test_fix_preserves_existing_data(self, tmp_path):
        """Test that --fix preserves existing data in target file."""
        from cv_generator.cli import main

        fixture_dir = FIXTURES_DIR / "mismatch"
        lang_map_path = fixture_dir / "lang.json"
        fix_out = tmp_path / "fixed"

        if fixture_dir.exists():
            main([
                "ensure",
                "--name", "mismatch",
                "--langs", "en,de",
                "--dir", str(fixture_dir),
                "--lang-map", str(lang_map_path),
                "--fix",
                "--fix-out", str(fix_out),
            ])

            fixed_file = fix_out / "cv.de.json"
            with open(fixed_file) as f:
                fixed_data = json.load(f)

            # Existing data should be preserved
            assert fixed_data["basics"][0]["fname"] == "Test"
            assert fixed_data["basics"][0]["email"] == "test@example.com"


class TestEnsureReportOutput:
    """Tests for report output functionality."""

    def test_report_json_to_file(self, tmp_path):
        """Test that --report-out writes report to file."""
        from cv_generator.cli import main

        fixture_dir = FIXTURES_DIR / "mismatch"
        lang_map_path = fixture_dir / "lang.json"
        report_out = tmp_path / "reports" / "ensure.json"

        if fixture_dir.exists():
            main([
                "ensure",
                "--name", "mismatch",
                "--langs", "en,de",
                "--dir", str(fixture_dir),
                "--lang-map", str(lang_map_path),
                "--report", "json",
                "--report-out", str(report_out),
            ])

            # Check report file was created
            assert report_out.exists()

            # Check report is valid JSON
            with open(report_out) as f:
                report_data = json.load(f)

            assert "summary" in report_data
            assert "profile_name" in report_data
            assert report_data["profile_name"] == "mismatch"

    def test_report_includes_fixability(self, capsys):
        """Test that report includes fixability information."""
        from cv_generator.cli import main

        fixture_dir = FIXTURES_DIR / "mismatch"
        lang_map_path = fixture_dir / "lang.json"

        if fixture_dir.exists():
            main([
                "ensure",
                "--name", "mismatch",
                "--langs", "en,de",
                "--dir", str(fixture_dir),
                "--lang-map", str(lang_map_path),
                "--format", "json",
            ])

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            assert "fixable_count" in output["summary"]
            assert "non_fixable_count" in output["summary"]
            assert output["summary"]["fixable_count"] >= 0


class TestEnsureReportMetadata:
    """Tests for report metadata fields."""

    def test_report_includes_profile_name(self):
        """Test that report includes profile name."""
        report = run_ensure(
            name="test_profile",
            langs=["en", "de"],
            cvs_dir=Path("/nonexistent"),
        )

        assert report.profile_name == "test_profile"

    def test_report_includes_langs(self):
        """Test that report includes languages."""
        report = run_ensure(
            name="test",
            langs=["en", "de", "fa"],
            cvs_dir=Path("/nonexistent"),
        )

        assert report.langs == ["en", "de", "fa"]

    def test_report_includes_anchor_lang(self):
        """Test that report includes anchor language."""
        report = run_ensure(
            name="test",
            langs=["de", "en"],
            cvs_dir=Path("/nonexistent"),
        )

        # Should use 'en' as anchor if present
        assert report.anchor_lang == "en"

    def test_report_dict_includes_metadata(self):
        """Test that to_dict includes metadata."""
        report = EnsureReport()
        report.profile_name = "test"
        report.langs = ["en", "de"]
        report.anchor_lang = "en"

        result = report.to_dict()

        assert result["profile_name"] == "test"
        assert result["langs"] == ["en", "de"]
        assert result["anchor_lang"] == "en"
