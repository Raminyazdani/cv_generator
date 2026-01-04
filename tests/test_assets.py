"""
Tests for cv_generator.assets module.

Tests the asset validation and optimization functionality:
- Asset reference discovery from CV JSON
- Asset validation (existence, extensions)
- Logo resolver with mapping file
- Image optimization with safety checks
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cv_generator.assets import (
    ALLOWED_IMAGE_EXTENSIONS,
    AssetReference,
    AssetType,
    AssetValidationReport,
    AssetValidationResult,
    LogoResolver,
    check_assets,
    discover_asset_references,
    optimize_assets,
    validate_asset,
)


class TestAssetReference:
    """Tests for AssetReference dataclass."""

    def test_url_detection(self):
        """Test that URLs are correctly detected."""
        ref = AssetReference(
            path="https://example.com/image.jpg",
            asset_type=AssetType.PHOTO,
            source_section="basics",
            source_key="Pictures[0].URL",
        )
        assert ref.is_url is True
        assert ref.is_local is False

    def test_local_path_detection(self):
        """Test that local paths are correctly detected."""
        ref = AssetReference(
            path="pics/photo.jpg",
            asset_type=AssetType.PHOTO,
            source_section="basics",
            source_key="Pictures[0].URL",
        )
        assert ref.is_url is False
        assert ref.is_local is True

    def test_empty_path(self):
        """Test handling of empty path."""
        ref = AssetReference(
            path="",
            asset_type=AssetType.PHOTO,
            source_section="basics",
            source_key="Pictures[0].URL",
        )
        assert ref.is_url is False
        assert ref.is_local is False


class TestDiscoverAssetReferences:
    """Tests for discover_asset_references function."""

    def test_discover_profile_pictures(self):
        """Test discovery of profile pictures."""
        cv_data = {
            "basics": [
                {
                    "Pictures": [
                        {"type_of": "profile", "URL": "https://example.com/profile.jpg"},
                        {"type_of": "cover", "URL": "https://example.com/cover.jpg"},
                    ]
                }
            ]
        }
        assets = discover_asset_references(cv_data)
        assert len(assets) == 2
        assert all(a.asset_type == AssetType.PHOTO for a in assets)
        assert all(a.source_section == "basics" for a in assets)

    def test_discover_education_logos(self):
        """Test discovery of education logos."""
        cv_data = {
            "education": [
                {"institution": "MIT", "logo_url": "logos/mit.png"},
                {"institution": "Stanford", "logo_url": ""},  # Empty - should be skipped
            ]
        }
        assets = discover_asset_references(cv_data)
        assert len(assets) == 1
        assert assets[0].asset_type == AssetType.LOGO
        assert "MIT" in assets[0].source_key

    def test_discover_certificates(self):
        """Test discovery of certificate URLs."""
        cv_data = {
            "workshop_and_certifications": [
                {
                    "issuer": "Academy",
                    "certifications": [
                        {"name": "Course 1", "URL": "https://example.com/cert1.pdf"},
                        {"name": "Course 2", "URL": None},  # None - should be skipped
                    ],
                }
            ]
        }
        assets = discover_asset_references(cv_data)
        assert len(assets) == 1
        assert assets[0].asset_type == AssetType.CERTIFICATE

    def test_discover_reference_letters(self):
        """Test discovery of reference letter URLs."""
        cv_data = {
            "references": [
                {"name": "Prof. Smith", "URL": "https://example.com/ref.pdf"},
            ]
        }
        assets = discover_asset_references(cv_data)
        assert len(assets) == 1
        assert assets[0].asset_type == AssetType.REFERENCE

    def test_discover_language_certifications(self):
        """Test discovery of language certification URLs."""
        cv_data = {
            "languages": [
                {
                    "language": "English",
                    "certifications": [
                        {"test": "IELTS", "URL": "https://example.com/ielts.pdf"},
                    ],
                }
            ]
        }
        assets = discover_asset_references(cv_data)
        assert len(assets) == 1
        assert assets[0].asset_type == AssetType.CERTIFICATE
        assert "English" in assets[0].source_key

    def test_empty_cv_data(self):
        """Test with empty CV data."""
        assets = discover_asset_references({})
        assert len(assets) == 0


class TestValidateAsset:
    """Tests for validate_asset function."""

    def test_url_always_valid(self):
        """Test that URLs are always considered valid."""
        asset = AssetReference(
            path="https://example.com/image.jpg",
            asset_type=AssetType.PHOTO,
            source_section="basics",
            source_key="Pictures[0].URL",
        )
        result = validate_asset(asset)
        assert result.is_valid is True

    def test_missing_local_file(self, tmp_path):
        """Test detection of missing local file."""
        asset = AssetReference(
            path="nonexistent.jpg",
            asset_type=AssetType.PHOTO,
            source_section="basics",
            source_key="Pictures[0].URL",
        )
        result = validate_asset(asset, base_dirs=[tmp_path])
        assert result.is_valid is False
        assert result.exists is False
        assert result.error is not None

    def test_existing_local_file(self, tmp_path):
        """Test validation of existing local file."""
        # Create a test file
        test_file = tmp_path / "photo.jpg"
        test_file.write_text("fake image data")

        asset = AssetReference(
            path="photo.jpg",
            asset_type=AssetType.PHOTO,
            source_section="basics",
            source_key="Pictures[0].URL",
        )
        result = validate_asset(asset, base_dirs=[tmp_path])
        assert result.is_valid is True
        assert result.exists is True

    def test_invalid_extension(self, tmp_path):
        """Test detection of invalid file extension."""
        # Create a file with invalid extension
        test_file = tmp_path / "photo.exe"
        test_file.write_text("fake data")

        asset = AssetReference(
            path="photo.exe",
            asset_type=AssetType.PHOTO,
            source_section="basics",
            source_key="Pictures[0].URL",
        )
        result = validate_asset(asset, base_dirs=[tmp_path])
        assert result.valid_extension is False

    def test_empty_path(self):
        """Test validation of empty path."""
        asset = AssetReference(
            path="",
            asset_type=AssetType.PHOTO,
            source_section="basics",
            source_key="Pictures[0].URL",
        )
        result = validate_asset(asset)
        assert result.is_valid is False
        assert "Empty" in result.error


class TestCheckAssets:
    """Tests for check_assets function."""

    def test_check_assets_with_missing_files(self, tmp_path):
        """Test that check_assets reports missing files."""
        cv_data = {
            "basics": [
                {
                    "Pictures": [
                        {"type_of": "profile", "URL": "missing_photo.jpg"},
                    ]
                }
            ]
        }
        report = check_assets(cv_data, profile="test", lang="en", base_dirs=[tmp_path])
        assert report.is_valid is False
        assert report.missing_count == 1

    def test_check_assets_with_urls_only(self):
        """Test that check_assets handles URLs correctly."""
        cv_data = {
            "basics": [
                {
                    "Pictures": [
                        {"type_of": "profile", "URL": "https://example.com/photo.jpg"},
                    ]
                }
            ]
        }
        report = check_assets(cv_data, profile="test", lang="en")
        assert report.is_valid is True
        assert report.total_assets == 1


class TestAssetValidationReport:
    """Tests for AssetValidationReport dataclass."""

    def test_empty_report(self):
        """Test empty report is valid."""
        report = AssetValidationReport()
        assert report.is_valid is True
        assert report.total_assets == 0

    def test_report_counts(self):
        """Test report counting methods."""
        asset1 = AssetReference("a.jpg", AssetType.PHOTO, "basics", "key1")
        asset2 = AssetReference("b.jpg", AssetType.PHOTO, "basics", "key2")

        report = AssetValidationReport(
            profile="test",
            lang="en",
            results=[
                AssetValidationResult(asset=asset1, exists=True),
                AssetValidationResult(asset=asset2, exists=False, error="Not found"),
            ],
        )
        assert report.total_assets == 2
        assert report.valid_count == 1
        assert report.invalid_count == 1

    def test_to_dict(self):
        """Test to_dict conversion."""
        report = AssetValidationReport(profile="test", lang="en")
        d = report.to_dict()
        assert d["profile"] == "test"
        assert d["lang"] == "en"
        assert d["valid"] is True
        assert "summary" in d
        assert "assets" in d

    def test_format_text(self):
        """Test text formatting."""
        report = AssetValidationReport(profile="test", lang="en")
        text = report.format_text()
        assert "Asset Validation" in text
        assert "test" in text


class TestLogoResolver:
    """Tests for LogoResolver class."""

    def test_exact_match(self, tmp_path):
        """Test exact match resolution."""
        # Create logo map
        logo_map = {
            "mapping": {
                "University of Berlin": "logos/berlin.png",
            },
            "default": None,
        }
        map_file = tmp_path / "logo_map.json"
        map_file.write_text(json.dumps(logo_map))

        resolver = LogoResolver(map_file)
        result = resolver.resolve("University of Berlin")
        assert result == "logos/berlin.png"

    def test_case_insensitive_match(self, tmp_path):
        """Test case-insensitive matching."""
        logo_map = {
            "mapping": {
                "MIT": "logos/mit.png",
            },
            "default": None,
        }
        map_file = tmp_path / "logo_map.json"
        map_file.write_text(json.dumps(logo_map))

        resolver = LogoResolver(map_file)
        result = resolver.resolve("mit")  # lowercase
        assert result == "logos/mit.png"

    def test_partial_match(self, tmp_path):
        """Test partial match resolution."""
        logo_map = {
            "mapping": {
                "Berlin": "logos/berlin.png",
            },
            "default": None,
        }
        map_file = tmp_path / "logo_map.json"
        map_file.write_text(json.dumps(logo_map))

        resolver = LogoResolver(map_file)
        result = resolver.resolve("University of Berlin")
        assert result == "logos/berlin.png"

    def test_default_fallback(self, tmp_path):
        """Test default logo fallback."""
        logo_map = {
            "mapping": {},
            "default": "logos/default.png",
        }
        map_file = tmp_path / "logo_map.json"
        map_file.write_text(json.dumps(logo_map))

        resolver = LogoResolver(map_file)
        result = resolver.resolve("Unknown University")
        assert result == "logos/default.png"

    def test_no_match_no_default(self, tmp_path):
        """Test no match and no default returns None."""
        logo_map = {
            "mapping": {},
            "default": None,
        }
        map_file = tmp_path / "logo_map.json"
        map_file.write_text(json.dumps(logo_map))

        resolver = LogoResolver(map_file)
        result = resolver.resolve("Unknown University")
        assert result is None

    def test_missing_map_file(self, tmp_path):
        """Test handling of missing map file."""
        resolver = LogoResolver(tmp_path / "nonexistent.json")
        result = resolver.resolve("Any University")
        assert result is None

    def test_list_mappings(self, tmp_path):
        """Test listing available mappings."""
        logo_map = {
            "mapping": {
                "MIT": "logos/mit.png",
                "Stanford": "logos/stanford.png",
            },
            "default": None,
        }
        map_file = tmp_path / "logo_map.json"
        map_file.write_text(json.dumps(logo_map))

        resolver = LogoResolver(map_file)
        mappings = resolver.list_mappings()
        assert len(mappings) == 2
        assert "MIT" in mappings


class TestOptimizeAssets:
    """Tests for optimize_assets function."""

    def test_refuses_data_directory(self, tmp_path):
        """Test that optimize refuses to write to data/."""
        cv_data = {"basics": []}

        with patch("cv_generator.assets.get_repo_root") as mock_root:
            mock_root.return_value = tmp_path
            data_dir = tmp_path / "data"
            data_dir.mkdir()

            with pytest.raises(ValueError) as exc_info:
                optimize_assets(cv_data, output_dir=data_dir / "output")

            assert "data/" in str(exc_info.value)

    def test_creates_output_directory(self, tmp_path):
        """Test that output directory is created."""
        cv_data = {"basics": []}
        output_dir = tmp_path / "output" / "optimized"

        with patch("cv_generator.assets.get_repo_root") as mock_root:
            mock_root.return_value = tmp_path
            results = optimize_assets(cv_data, output_dir=output_dir)

        assert output_dir.exists()
        assert results["processed"] == 0

    def test_copies_local_file(self, tmp_path):
        """Test that local files are copied."""
        # Create source structure
        pics_dir = tmp_path / "data" / "pics"
        pics_dir.mkdir(parents=True)
        source_file = pics_dir / "photo.jpg"
        source_file.write_bytes(b"fake jpeg data")

        cv_data = {
            "basics": [
                {
                    "Pictures": [
                        {"type_of": "profile", "URL": "photo.jpg"},
                    ]
                }
            ]
        }

        output_dir = tmp_path / "output" / "optimized"

        with patch("cv_generator.assets.get_repo_root") as mock_root:
            mock_root.return_value = tmp_path
            results = optimize_assets(cv_data, output_dir=output_dir)

        assert results["processed"] == 1
        assert (output_dir / "photo.jpg").exists()

    def test_skip_pillow_optimization_when_missing(self, tmp_path):
        """Test graceful handling when Pillow is not installed."""
        # This test ensures the code handles import errors gracefully
        # The actual behavior depends on whether Pillow is installed
        pics_dir = tmp_path / "data" / "pics"
        pics_dir.mkdir(parents=True)
        source_file = pics_dir / "photo.png"
        source_file.write_bytes(b"fake png data")

        cv_data = {
            "basics": [
                {
                    "Pictures": [
                        {"type_of": "profile", "URL": "photo.png"},
                    ]
                }
            ]
        }

        output_dir = tmp_path / "output" / "optimized"

        with patch("cv_generator.assets.get_repo_root") as mock_root:
            mock_root.return_value = tmp_path
            results = optimize_assets(cv_data, output_dir=output_dir)

        # Should either optimize or copy, but not fail
        assert results["processed"] >= 0

    def test_handles_missing_source(self, tmp_path):
        """Test handling of missing source files."""
        cv_data = {
            "basics": [
                {
                    "Pictures": [
                        {"type_of": "profile", "URL": "nonexistent.jpg"},
                    ]
                }
            ]
        }

        output_dir = tmp_path / "output" / "optimized"

        with patch("cv_generator.assets.get_repo_root") as mock_root:
            mock_root.return_value = tmp_path
            results = optimize_assets(cv_data, output_dir=output_dir)

        assert results["skipped"] == 1
        assert len(results["errors"]) == 1


class TestCLIIntegration:
    """Tests for CLI integration of assets command."""

    def test_assets_help(self, capsys):
        """Test that assets --help works."""
        from cv_generator.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["assets", "--help"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "check" in captured.out
        assert "optimize" in captured.out

    def test_assets_check_help(self, capsys):
        """Test that assets check --help works."""
        from cv_generator.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["assets", "check", "--help"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--name" in captured.out
        assert "--format" in captured.out

    def test_assets_optimize_help(self, capsys):
        """Test that assets optimize --help works."""
        from cv_generator.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["assets", "optimize", "--help"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--out" in captured.out
        assert "--max-width" in captured.out
