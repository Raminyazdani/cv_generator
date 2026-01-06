"""
Tests for cv_generator.config module.

Tests configuration loading, profile management, and variant filtering.
"""

import json
import sys
from pathlib import Path

import pytest

from cv_generator.config import (
    BuildConfig,
    Config,
    ConfigError,
    LoggingConfig,
    PathsConfig,
    ProjectConfig,
    clear_current_profile,
    find_config_file,
    get_current_profile,
    get_state_dir,
    list_profiles,
    load_config,
    load_state,
    save_state,
    set_current_profile,
)


class TestConfigDataclasses:
    """Tests for config dataclass structures."""

    def test_default_config(self):
        """Test that default config has sensible values."""
        config = Config()

        assert config.project.name == ""
        assert config.project.default_lang == "en"
        assert config.project.variants == []

        assert config.paths.cvs is None
        assert config.paths.templates is None
        assert config.paths.output is None

        assert config.build.latex_engine == "xelatex"
        assert config.build.keep_latex is False
        assert config.build.dry_run is False

        assert config.logging.level == "WARNING"
        assert config.logging.log_file is None

    def test_config_from_dict(self):
        """Test creating config from a dictionary."""
        data = {
            "project": {
                "name": "Test Project",
                "default_lang": "de",
                "variants": ["academic", "industry"],
            },
            "paths": {
                "cvs": "data/cvs",
                "output": "output",
            },
            "build": {
                "keep_latex": True,
            },
            "logging": {
                "level": "DEBUG",
            },
        }

        config = Config.from_dict(data)

        assert config.project.name == "Test Project"
        assert config.project.default_lang == "de"
        assert config.project.variants == ["academic", "industry"]
        assert config.paths.cvs == "data/cvs"
        assert config.paths.output == "output"
        assert config.paths.templates is None  # Not specified
        assert config.build.keep_latex is True
        assert config.logging.level == "DEBUG"

    def test_config_from_empty_dict(self):
        """Test creating config from empty dict uses defaults."""
        config = Config.from_dict({})

        assert config.project.default_lang == "en"
        assert config.build.latex_engine == "xelatex"


class TestFindConfigFile:
    """Tests for config file discovery."""

    def test_find_nonexistent_config_returns_none(self, tmp_path, monkeypatch):
        """Test that missing config file returns None."""
        monkeypatch.chdir(tmp_path)

        result = find_config_file()
        assert result is None

    def test_find_config_in_cwd(self, tmp_path, monkeypatch):
        """Test finding config in current directory."""
        config_file = tmp_path / "cv_generator.toml"
        config_file.write_text("[project]\nname = 'test'\n")

        monkeypatch.chdir(tmp_path)

        result = find_config_file()
        assert result == config_file

    def test_explicit_path_not_found_raises(self, tmp_path):
        """Test that explicit nonexistent path raises error."""
        missing_path = tmp_path / "missing.toml"

        with pytest.raises(ConfigError) as exc_info:
            find_config_file(missing_path)

        assert "not found" in str(exc_info.value)


class TestLoadConfig:
    """Tests for config loading."""

    def test_load_missing_config_returns_defaults(self, tmp_path, monkeypatch):
        """Test that missing config file returns default config."""
        monkeypatch.chdir(tmp_path)

        config = load_config()

        assert isinstance(config, Config)
        assert config.project.default_lang == "en"

    def test_load_valid_config(self, tmp_path, monkeypatch):
        """Test loading a valid TOML config file."""
        # Skip if TOML parsing is not available
        if sys.version_info < (3, 11):
            try:
                import tomli  # noqa: F401
            except ImportError:
                pytest.skip("tomli not installed for Python < 3.11")

        config_content = """
[project]
name = "Test CV"
default_lang = "de"

[build]
keep_latex = true
"""
        config_file = tmp_path / "cv_generator.toml"
        config_file.write_text(config_content)

        monkeypatch.chdir(tmp_path)

        config = load_config()

        assert config.project.name == "Test CV"
        assert config.project.default_lang == "de"
        assert config.build.keep_latex is True


class TestProfileState:
    """Tests for profile state management."""

    def test_load_empty_state(self, tmp_path, monkeypatch):
        """Test loading state when no state file exists."""
        # Mock the state directory to use tmp_path
        state_dir = tmp_path / ".cvgen"

        monkeypatch.setattr("cv_generator.config.get_state_dir", lambda: state_dir)

        state = load_state()
        assert state == {}

    def test_save_and_load_state(self, tmp_path, monkeypatch):
        """Test saving and loading state."""
        state_dir = tmp_path / ".cvgen"

        monkeypatch.setattr("cv_generator.config.get_state_dir", lambda: state_dir)
        monkeypatch.setattr("cv_generator.config.get_state_file", lambda: state_dir / "state.json")

        # Save state
        save_state({"current_profile": "ramin", "other": "data"})

        # Load it back
        state = load_state()

        assert state["current_profile"] == "ramin"
        assert state["other"] == "data"

    def test_get_current_profile_when_not_set(self, tmp_path, monkeypatch):
        """Test getting current profile when none is set."""
        state_dir = tmp_path / ".cvgen"

        monkeypatch.setattr("cv_generator.config.get_state_dir", lambda: state_dir)
        monkeypatch.setattr("cv_generator.config.get_state_file", lambda: state_dir / "state.json")

        result = get_current_profile()
        assert result is None

    def test_set_and_get_current_profile(self, tmp_path, monkeypatch):
        """Test setting and getting current profile."""
        state_dir = tmp_path / ".cvgen"

        monkeypatch.setattr("cv_generator.config.get_state_dir", lambda: state_dir)
        monkeypatch.setattr("cv_generator.config.get_state_file", lambda: state_dir / "state.json")

        set_current_profile("ramin")

        result = get_current_profile()
        assert result == "ramin"

    def test_clear_current_profile(self, tmp_path, monkeypatch):
        """Test clearing the current profile."""
        state_dir = tmp_path / ".cvgen"

        monkeypatch.setattr("cv_generator.config.get_state_dir", lambda: state_dir)
        monkeypatch.setattr("cv_generator.config.get_state_file", lambda: state_dir / "state.json")

        set_current_profile("ramin")
        assert get_current_profile() == "ramin"

        clear_current_profile()
        assert get_current_profile() is None


class TestListProfiles:
    """Tests for profile discovery."""

    def test_list_profiles_empty_dir(self, tmp_path):
        """Test listing profiles in empty directory."""
        profiles = list_profiles(tmp_path)
        assert profiles == []

    def test_list_profiles_finds_json_files(self, tmp_path):
        """Test that profiles are found from JSON files."""
        (tmp_path / "ramin.json").write_text('{"basics": []}')
        (tmp_path / "mahsa.json").write_text('{"basics": []}')
        (tmp_path / "ramin_de.json").write_text('{"basics": []}')

        profiles = list_profiles(tmp_path)

        assert "ramin" in profiles
        assert "mahsa" in profiles
        # ramin_de should be parsed as profile=ramin, lang=de
        assert len(profiles) == 2


class TestVariantFiltering:
    """Tests for variant filtering in generator."""

    def test_filter_by_variant_filters_experiences(self):
        """Test that variant filtering works on experiences."""
        from cv_generator.generator import filter_by_variant

        data = {
            "basics": [{"fname": "Test"}],
            "experiences": [
                {"role": "Job A", "type_key": "academic"},
                {"role": "Job B", "type_key": "industry"},
                {"role": "Job C"},  # No type_key - should always include
            ],
        }

        filtered = filter_by_variant(data, "academic")

        assert len(filtered["experiences"]) == 2
        assert filtered["experiences"][0]["role"] == "Job A"
        assert filtered["experiences"][1]["role"] == "Job C"

    def test_filter_by_variant_with_list_type_key(self):
        """Test variant filtering with list type_key."""
        from cv_generator.generator import filter_by_variant

        data = {
            "basics": [{"fname": "Test"}],
            "experiences": [
                {"role": "Job A", "type_key": ["academic", "full"]},
                {"role": "Job B", "type_key": ["industry"]},
            ],
        }

        filtered = filter_by_variant(data, "academic")

        assert len(filtered["experiences"]) == 1
        assert filtered["experiences"][0]["role"] == "Job A"

    def test_filter_by_variant_preserves_other_sections(self):
        """Test that variant filtering preserves non-list sections."""
        from cv_generator.generator import filter_by_variant

        data = {
            "basics": [{"fname": "Test"}],
            "skills": {"Technical": {"Python": []}},
        }

        filtered = filter_by_variant(data, "academic")

        assert filtered["basics"] == [{"fname": "Test"}]
        assert filtered["skills"] == {"Technical": {"Python": []}}

    def test_filter_by_variant_nested_skills(self):
        """Test variant filtering works on nested skills with type_key (F-010)."""
        from cv_generator.generator import filter_by_variant

        data = {
            "basics": [{"fname": "Test"}],
            "skills": {
                "Programming & Scripting": {
                    "Programming Languages": [
                        {"long_name": "Python", "type_key": ["Full CV", "Programming"]},
                        {"long_name": "JavaScript", "type_key": ["Full CV"]},
                        {"long_name": "Rust", "type_key": ["Programming"]},
                    ]
                },
                "Soft Skills": {
                    "Core Soft Skills": [
                        {"long_name": "Team Collaboration", "type_key": ["Full CV"]},
                        {"long_name": "Leadership"},  # No type_key - universal
                    ]
                }
            },
        }

        # Filter for "Programming" variant
        filtered = filter_by_variant(data, "Programming")

        # Should include Python and Rust (both have "Programming")
        prog_langs = filtered["skills"]["Programming & Scripting"]["Programming Languages"]
        assert len(prog_langs) == 2
        assert prog_langs[0]["long_name"] == "Python"
        assert prog_langs[1]["long_name"] == "Rust"

        # Should include Leadership (no type_key) but not Team Collaboration
        soft_skills = filtered["skills"]["Soft Skills"]["Core Soft Skills"]
        assert len(soft_skills) == 1
        assert soft_skills[0]["long_name"] == "Leadership"

    def test_filter_by_variant_nested_skills_empty_result(self):
        """Test variant filtering with no matching skills (F-010)."""
        from cv_generator.generator import filter_by_variant

        data = {
            "basics": [{"fname": "Test"}],
            "skills": {
                "Technical": {
                    "Languages": [
                        {"long_name": "Python", "type_key": ["Academic"]},
                    ]
                }
            },
        }

        # Filter for "Industry" variant - no skills match
        filtered = filter_by_variant(data, "Industry")

        # Structure should be preserved but list should be empty
        assert "skills" in filtered
        assert "Technical" in filtered["skills"]
        assert "Languages" in filtered["skills"]["Technical"]
        assert filtered["skills"]["Technical"]["Languages"] == []

    def test_filter_by_variant_skills_universal_items(self):
        """Test that skills without type_key are always included (F-010)."""
        from cv_generator.generator import filter_by_variant

        data = {
            "basics": [{"fname": "Test"}],
            "skills": {
                "Technical": {
                    "Languages": [
                        {"long_name": "Python"},  # No type_key - universal
                        {"long_name": "Java", "type_key": ["Enterprise"]},
                    ]
                }
            },
        }

        # Filter for "Academic" variant
        filtered = filter_by_variant(data, "Academic")

        # Python should be included (no type_key), Java should be excluded
        langs = filtered["skills"]["Technical"]["Languages"]
        assert len(langs) == 1
        assert langs[0]["long_name"] == "Python"


class TestProfileCLI:
    """Tests for profile CLI commands."""

    def test_profile_list_help(self, capsys):
        """Test that profile list --help works."""
        from cv_generator.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["profile", "list", "--help"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "List available profiles" in captured.out or "--input-dir" in captured.out

    def test_profile_use_help(self, capsys):
        """Test that profile use --help works."""
        from cv_generator.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["profile", "use", "--help"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "profile_name" in captured.out or "Set" in captured.out

    def test_profile_clear_help(self, capsys):
        """Test that profile clear --help works."""
        from cv_generator.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["profile", "clear", "--help"])

        assert exc_info.value.code == 0
