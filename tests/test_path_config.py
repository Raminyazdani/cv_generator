"""
Tests for flexible path configuration (paths_config.py).

Tests the precedence chain:
1. Explicit CLI flags
2. Environment variables
3. Configuration file
4. Legacy data/ directory
5. User home directory
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from cv_generator.paths_config import PathConfig, create_path_config_from_cli


class TestPathConfigPrecedence:
    """Test precedence chain for path resolution."""

    def test_explicit_paths_take_precedence(self, tmp_path):
        """Test that explicit parameters override everything."""
        explicit_cvs = tmp_path / "explicit_cvs"
        explicit_cvs.mkdir()

        config = PathConfig(cvs_dir=explicit_cvs)

        assert config.cvs_dir == explicit_cvs

    def test_environment_variables(self, tmp_path, monkeypatch):
        """Test environment variable path resolution."""
        env_cvs = tmp_path / "env_cvs"
        env_cvs.mkdir()

        monkeypatch.setenv("CVGEN_CVS_DIR", str(env_cvs))

        config = PathConfig()
        assert config.cvs_dir == env_cvs

    def test_env_data_dir_fallback(self, tmp_path, monkeypatch):
        """Test CVGEN_DATA_DIR environment variable with cvs subdirectory."""
        data_dir = tmp_path / "data"
        cvs_dir = data_dir / "cvs"
        cvs_dir.mkdir(parents=True)

        monkeypatch.setenv("CVGEN_DATA_DIR", str(data_dir))

        config = PathConfig()
        assert config.cvs_dir == cvs_dir

    def test_legacy_data_directory(self, tmp_path):
        """Test backward compatibility with data/ directory."""
        repo_root = tmp_path
        legacy_cvs = repo_root / "data" / "cvs"
        legacy_cvs.mkdir(parents=True)

        config = PathConfig(repo_root=repo_root)
        assert config.cvs_dir == legacy_cvs

    def test_user_home_directory(self, tmp_path, monkeypatch):
        """Test fallback to ~/.cvgen/ directory."""
        # Mock home directory
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        cvgen_cvs = fake_home / ".cvgen" / "cvs"
        cvgen_cvs.mkdir(parents=True)

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        config = PathConfig()
        assert config.cvs_dir == cvgen_cvs

    def test_cwd_fallback(self, tmp_path, monkeypatch):
        """Test fallback to current working directory."""
        cwd = tmp_path / "cwd"
        cwd.mkdir()
        cvs_dir = cwd / "cvs"
        cvs_dir.mkdir()

        monkeypatch.setattr(Path, "cwd", lambda: cwd)
        # Mock empty home to skip that fallback
        fake_home = tmp_path / "empty_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        config = PathConfig()
        assert config.cvs_dir == cvs_dir

    def test_error_when_no_cvs_found(self, tmp_path, monkeypatch):
        """Test that helpful error is raised when CVs directory cannot be found."""
        # Mock empty directories
        fake_home = tmp_path / "empty_home"
        fake_home.mkdir()
        fake_cwd = tmp_path / "empty_cwd"
        fake_cwd.mkdir()

        monkeypatch.setattr(Path, "home", lambda: fake_home)
        monkeypatch.setattr(Path, "cwd", lambda: fake_cwd)

        config = PathConfig()

        with pytest.raises(FileNotFoundError) as exc_info:
            _ = config.cvs_dir

        error_msg = str(exc_info.value)
        assert "Cannot find CVs directory" in error_msg
        assert "--cvs-dir" in error_msg
        assert "CVGEN_CVS_DIR" in error_msg


class TestPathConfigAllPaths:
    """Test all path types (cvs, pics, db, templates, output, assets)."""

    def test_pics_dir_with_warning(self, tmp_path, monkeypatch, caplog):
        """Test that pics_dir returns default with warning when not found."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        config = PathConfig()
        pics_dir = config.pics_dir

        assert pics_dir == fake_home / ".cvgen" / "pics"
        assert "Pictures directory not found" in caplog.text

    def test_db_path_default(self, tmp_path, monkeypatch):
        """Test db_path defaults to ~/.cvgen/db/cv.db."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        config = PathConfig()
        assert config.db_path == fake_home / ".cvgen" / "db" / "cv.db"

    def test_output_dir_default(self, tmp_path, monkeypatch):
        """Test output_dir defaults to ./output."""
        fake_cwd = tmp_path / "cwd"
        fake_cwd.mkdir()

        monkeypatch.setattr(Path, "cwd", lambda: fake_cwd)

        config = PathConfig()
        assert config.output_dir == fake_cwd / "output"

    def test_templates_dir_error(self, tmp_path, monkeypatch):
        """Test that templates_dir raises error when not found."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        monkeypatch.setattr(Path, "home", lambda: fake_home)
        # Ensure we don't find the repo templates
        monkeypatch.setenv("PWD", str(tmp_path))

        config = PathConfig(repo_root=tmp_path)  # Pass empty repo root

        with pytest.raises(FileNotFoundError) as exc_info:
            _ = config.templates_dir

        error_msg = str(exc_info.value)
        assert "Cannot find LaTeX templates directory" in error_msg
        assert "CVGEN_TEMPLATES_DIR" in error_msg


class TestPathConfigValidation:
    """Test validation methods."""

    def test_validate_success(self, tmp_path):
        """Test validation passes when required paths exist."""
        cvs_dir = tmp_path / "cvs"
        cvs_dir.mkdir()
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        config = PathConfig(cvs_dir=cvs_dir, templates_dir=templates_dir)
        config.validate(require_cvs=True, require_templates=True)  # Should not raise

    def test_validate_missing_cvs(self, tmp_path):
        """Test validation fails when CVs directory is missing."""
        cvs_dir = tmp_path / "nonexistent_cvs"
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        config = PathConfig(cvs_dir=cvs_dir, templates_dir=templates_dir)

        with pytest.raises(FileNotFoundError) as exc_info:
            config.validate(require_cvs=True, require_templates=True)

        assert "CVs directory does not exist" in str(exc_info.value)


class TestPathConfigUtilities:
    """Test utility methods."""

    def test_create_user_directories(self, tmp_path, monkeypatch):
        """Test creating default user directories."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        config = PathConfig()
        config.create_user_directories()

        # Check all directories were created
        assert (fake_home / ".cvgen" / "cvs").exists()
        assert (fake_home / ".cvgen" / "pics").exists()
        assert (fake_home / ".cvgen" / "db").exists()
        assert (fake_home / ".cvgen" / "assets").exists()
        assert (fake_home / ".cvgen" / "templates").exists()

    def test_repr(self, tmp_path):
        """Test string representation."""
        cvs_dir = tmp_path / "cvs"
        cvs_dir.mkdir()
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        config = PathConfig(cvs_dir=cvs_dir, templates_dir=templates_dir)
        repr_str = repr(config)

        assert "PathConfig" in repr_str
        assert "cvs_dir" in repr_str


class TestCreatePathConfigFromCLI:
    """Test CLI integration helper."""

    def test_create_from_cli_args(self, tmp_path):
        """Test creating PathConfig from argparse Namespace."""

        class Args:
            cvs_dir = str(tmp_path / "cvs")
            pics_dir = None
            db_path = None
            templates_dir = str(tmp_path / "templates")
            output_dir = None
            assets_dir = None
            config_file = None
            repo_root = None

        config = create_path_config_from_cli(Args())

        assert config._cvs_dir == Path(tmp_path / "cvs")
        assert config._templates_dir == Path(tmp_path / "templates")

    def test_create_from_cli_with_config_file(self, tmp_path):
        """Test config file loading from CLI args."""
        config_file_path = tmp_path / "test_config.toml"
        config_file_path.write_text('[paths]\ncvs_dir = "/custom/path"\n')

        class Args:
            cvs_dir = None
            pics_dir = None
            db_path = None
            templates_dir = None
            output_dir = None
            assets_dir = None
            config_file = str(config_file_path)
            repo_root = None

        config = create_path_config_from_cli(Args())

        assert config._config_file == config_file_path
        # Config should be loaded
        assert "paths" in config._config_data


class TestConfigFileParsing:
    """Test TOML configuration file parsing."""

    def test_config_file_loading(self, tmp_path):
        """Test loading paths from TOML config file."""
        config_file = tmp_path / "cv_generator.toml"
        config_content = """
[paths]
cvs_dir = "/custom/cvs"
pics_dir = "/custom/pics"
db_path = "/custom/db/cv.db"
templates_dir = "/custom/templates"
output_dir = "/custom/output"
assets_dir = "/custom/assets"
"""
        config_file.write_text(config_content)

        config = PathConfig(config_file=config_file)

        assert config._config_data["paths"]["cvs_dir"] == "/custom/cvs"
        assert config._config_data["paths"]["pics_dir"] == "/custom/pics"

    def test_config_file_with_expanduser(self, tmp_path, monkeypatch):
        """Test that ~ is expanded in config file paths."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        cvs_dir = fake_home / "my_cvs"
        cvs_dir.mkdir()

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        config_file = tmp_path / "cv_generator.toml"
        config_file.write_text('[paths]\ncvs_dir = "~/my_cvs"\n')

        config = PathConfig(config_file=config_file)
        assert config.cvs_dir == cvs_dir
