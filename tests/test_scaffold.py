"""
Tests for cv_generator.scaffold module and cvgen init command.

Tests project scaffolding functionality.
"""

import json
from pathlib import Path

import pytest

from cv_generator.cli import create_parser, main
from cv_generator.scaffold import (
    get_cv_template,
    get_next_steps,
    scaffold_project,
)


class TestScaffoldProject:
    """Tests for scaffold_project function."""

    def test_scaffold_creates_directory(self, tmp_path: Path):
        """Test that scaffold creates the destination directory."""
        dest = tmp_path / "newproject"
        result = scaffold_project(dest, profile_name="test", lang="en")

        assert result.success
        assert dest.exists()
        assert dest.is_dir()

    def test_scaffold_creates_cv_json(self, tmp_path: Path):
        """Test that scaffold creates CV JSON file."""
        dest = tmp_path / "newproject"
        result = scaffold_project(dest, profile_name="jane", lang="en")

        assert result.success
        cv_file = dest / "cvs" / "jane.en.json"
        assert cv_file.exists()

        # Verify it's valid JSON
        with open(cv_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "basics" in data
        assert "education" in data
        assert "experiences" in data

    def test_scaffold_creates_config(self, tmp_path: Path):
        """Test that scaffold creates config file."""
        dest = tmp_path / "newproject"
        result = scaffold_project(dest, profile_name="test", lang="en")

        assert result.success
        config_file = dest / "cv_generator.toml"
        assert config_file.exists()

        content = config_file.read_text(encoding="utf-8")
        assert "[project]" in content
        assert "[paths]" in content
        assert "[build]" in content

    def test_scaffold_creates_readme(self, tmp_path: Path):
        """Test that scaffold creates README file."""
        dest = tmp_path / "newproject"
        result = scaffold_project(dest, profile_name="test", lang="en")

        assert result.success
        readme_file = dest / "README.md"
        assert readme_file.exists()

        content = readme_file.read_text(encoding="utf-8")
        assert "CV Project" in content
        assert "cvgen build" in content

    def test_scaffold_creates_gitignore(self, tmp_path: Path):
        """Test that scaffold creates .gitignore file."""
        dest = tmp_path / "newproject"
        result = scaffold_project(dest, profile_name="test", lang="en")

        assert result.success
        gitignore = dest / ".gitignore"
        assert gitignore.exists()

        content = gitignore.read_text(encoding="utf-8")
        assert "output/" in content

    def test_scaffold_creates_output_dir(self, tmp_path: Path):
        """Test that scaffold creates output directory."""
        dest = tmp_path / "newproject"
        result = scaffold_project(dest, profile_name="test", lang="en")

        assert result.success
        output_dir = dest / "output"
        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_scaffold_fails_on_nonempty_dir(self, tmp_path: Path):
        """Test that scaffold fails on non-empty directory without force."""
        dest = tmp_path / "existing"
        dest.mkdir()
        (dest / "existing_file.txt").write_text("content")

        result = scaffold_project(dest, profile_name="test", lang="en", force=False)

        assert not result.success
        assert result.error is not None
        assert "not empty" in result.error

    def test_scaffold_force_overwrites(self, tmp_path: Path):
        """Test that scaffold with force works on non-empty directory."""
        dest = tmp_path / "existing"
        dest.mkdir()
        (dest / "existing_file.txt").write_text("content")

        result = scaffold_project(dest, profile_name="test", lang="en", force=True)

        assert result.success
        assert (dest / "cvs" / "test.en.json").exists()

    def test_scaffold_different_languages(self, tmp_path: Path):
        """Test scaffolding with different languages."""
        for lang in ["en", "de", "fa"]:
            dest = tmp_path / f"project_{lang}"
            result = scaffold_project(dest, profile_name="test", lang=lang)

            assert result.success
            cv_file = dest / "cvs" / f"test.{lang}.json"
            assert cv_file.exists()

    def test_scaffold_tracks_created_files(self, tmp_path: Path):
        """Test that scaffold tracks all created files."""
        dest = tmp_path / "newproject"
        result = scaffold_project(dest, profile_name="test", lang="en")

        assert result.success
        # Should create: cv json, config, readme, gitignore
        expected_files = [
            dest / "cvs" / "test.en.json",
            dest / "cv_generator.toml",
            dest / "README.md",
            dest / ".gitignore",
        ]
        assert len(result.files_created) == len(expected_files)

        # Check all files exist and are tracked
        for file_path in result.files_created:
            assert file_path.is_relative_to(dest)
            assert file_path.exists()


class TestCVTemplate:
    """Tests for CV template generation."""

    def test_cv_template_has_basics(self):
        """Test that CV template includes basics section."""
        template = get_cv_template("test", "en")
        assert "basics" in template
        assert len(template["basics"]) > 0
        assert "fname" in template["basics"][0]
        assert "lname" in template["basics"][0]

    def test_cv_template_uses_profile_name(self):
        """Test that CV template uses the profile name."""
        template = get_cv_template("jane", "en")
        assert template["basics"][0]["fname"] == "Jane"

    def test_cv_template_has_education(self):
        """Test that CV template includes education section."""
        template = get_cv_template("test", "en")
        assert "education" in template
        assert len(template["education"]) > 0

    def test_cv_template_has_experiences(self):
        """Test that CV template includes experiences section."""
        template = get_cv_template("test", "en")
        assert "experiences" in template
        assert len(template["experiences"]) > 0


class TestGetNextSteps:
    """Tests for next steps generation."""

    def test_next_steps_includes_cd(self, tmp_path: Path):
        """Test that next steps includes cd command."""
        steps = get_next_steps(tmp_path, "test", "en")
        assert any("cd" in step for step in steps)

    def test_next_steps_includes_build(self, tmp_path: Path):
        """Test that next steps includes build command."""
        steps = get_next_steps(tmp_path, "test", "en")
        assert any("build" in step for step in steps)


class TestInitCLI:
    """Tests for init CLI command."""

    def test_init_help(self, capsys):
        """Test that init --help works."""
        with pytest.raises(SystemExit) as exc_info:
            main(["init", "--help"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "path" in captured.out
        assert "--profile" in captured.out
        assert "--lang" in captured.out

    def test_parser_init_command(self):
        """Test parsing init command arguments."""
        parser = create_parser()
        args = parser.parse_args(["init", "/tmp/test", "--profile", "jane", "--lang", "de"])

        assert args.command == "init"
        assert args.path == "/tmp/test"
        assert args.profile == "jane"
        assert args.lang == "de"

    def test_parser_init_with_force(self):
        """Test parsing init command with --force."""
        parser = create_parser()
        args = parser.parse_args(["init", "/tmp/test", "--force"])

        assert args.command == "init"
        assert args.force is True

    def test_init_creates_project(self, tmp_path: Path, capsys):
        """Test that init command creates a project."""
        dest = str(tmp_path / "newproject")
        result = main(["init", dest, "--profile", "jane"])

        assert result == 0
        assert (tmp_path / "newproject" / "cvs" / "jane.en.json").exists()

        captured = capsys.readouterr()
        assert "Created new CV project" in captured.out

    def test_init_fails_on_nonempty_without_force(self, tmp_path: Path, capsys):
        """Test that init fails on non-empty directory without force."""
        dest = tmp_path / "existing"
        dest.mkdir()
        (dest / "file.txt").write_text("content")

        result = main(["init", str(dest)])

        assert result == 2  # EXIT_CONFIG_ERROR
        captured = capsys.readouterr()
        assert "not empty" in captured.out

    def test_init_succeeds_with_force(self, tmp_path: Path, capsys):
        """Test that init succeeds with force flag on non-empty directory."""
        dest = tmp_path / "existing"
        dest.mkdir()
        (dest / "file.txt").write_text("content")

        result = main(["init", str(dest), "--force"])

        assert result == 0
        captured = capsys.readouterr()
        assert "Created new CV project" in captured.out


class TestGeneratedCVValidation:
    """Tests that generated CV passes linting."""

    def test_generated_cv_passes_lint(self, tmp_path: Path):
        """Test that generated CV JSON passes schema validation."""
        dest = tmp_path / "newproject"
        scaffold_project(dest, profile_name="test", lang="en")

        cv_file = dest / "cvs" / "test.en.json"

        # Run lint on the generated file
        result = main(["lint", "--file", str(cv_file)])

        assert result == 0  # EXIT_SUCCESS

    def test_generated_cv_is_valid_json(self, tmp_path: Path):
        """Test that generated CV is valid JSON."""
        dest = tmp_path / "newproject"
        scaffold_project(dest, profile_name="test", lang="en")

        cv_file = dest / "cvs" / "test.en.json"

        # Should not raise
        with open(cv_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, dict)
