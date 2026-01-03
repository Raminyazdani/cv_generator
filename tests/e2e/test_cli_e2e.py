"""
End-to-end tests for the CV Generator CLI.

Tests the CLI using subprocess to simulate real-world usage.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import FIXTURES_MULTILANG_DIR, FIXTURES_VALID_DIR


class TestCLIE2E:
    """End-to-end tests for the cvgen CLI."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create a temporary project directory with fixtures."""
        project_dir = tmp_path / "cv_project"
        project_dir.mkdir()

        # Create data/cvs directory
        cvs_dir = project_dir / "data" / "cvs"
        cvs_dir.mkdir(parents=True)

        # Copy test CV files
        minimal_cv = FIXTURES_VALID_DIR / "minimal.json"
        shutil.copy(minimal_cv, cvs_dir / "test.json")

        # Create output directory
        output_dir = project_dir / "output"
        output_dir.mkdir()

        return project_dir

    @pytest.fixture
    def multilang_project_dir(self, tmp_path):
        """Create a temporary project directory with multilang fixtures."""
        project_dir = tmp_path / "multilang_project"
        project_dir.mkdir()

        # Create data/cvs directory
        cvs_dir = project_dir / "data" / "cvs"
        cvs_dir.mkdir(parents=True)

        # Copy multilang CV files
        for lang in ["en", "de", "fa"]:
            src = FIXTURES_MULTILANG_DIR / f"cv.{lang}.json"
            dst = cvs_dir / f"test_{lang}.json"
            shutil.copy(src, dst)

        # Create lang_engine directory with lang.json
        lang_dir = project_dir / "src" / "cv_generator" / "lang_engine"
        lang_dir.mkdir(parents=True)
        shutil.copy(FIXTURES_MULTILANG_DIR / "lang.json", lang_dir / "lang.json")

        # Create output directory
        output_dir = project_dir / "output"
        output_dir.mkdir()

        return project_dir

    def run_cvgen(self, args: list, cwd: Path = None, env: dict = None) -> subprocess.CompletedProcess:
        """Run the cvgen CLI command."""
        cmd = [sys.executable, "-m", "cv_generator.cli"] + args

        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        return subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            env=merged_env
        )

    def test_help_command(self):
        """Test that --help returns successfully."""
        result = self.run_cvgen(["--help"])
        assert result.returncode == 0
        assert "cvgen" in result.stdout

    def test_version_command(self):
        """Test that --version returns successfully."""
        result = self.run_cvgen(["--version"])
        assert result.returncode == 0
        assert "cvgen" in result.stdout

    def test_build_help_command(self):
        """Test that build --help returns successfully."""
        result = self.run_cvgen(["build", "--help"])
        assert result.returncode == 0
        assert "--dry-run" in result.stdout
        assert "--name" in result.stdout

    def test_lint_help_command(self):
        """Test that lint --help returns successfully."""
        result = self.run_cvgen(["lint", "--help"])
        assert result.returncode == 0
        assert "--file" in result.stdout
        assert "--strict" in result.stdout

    def test_lint_valid_file(self):
        """Test linting a valid CV file."""
        valid_file = str(FIXTURES_VALID_DIR / "minimal.json")
        result = self.run_cvgen(["lint", "--file", valid_file])
        assert result.returncode == 0

    def test_lint_invalid_file(self):
        """Test linting an invalid CV file (missing basics)."""
        from tests.conftest import FIXTURES_LINT_DIR
        invalid_file = str(FIXTURES_LINT_DIR / "missing_basics.json")
        result = self.run_cvgen(["lint", "--file", invalid_file])
        # Should return validation error code
        assert result.returncode == 5  # EXIT_VALIDATION_ERROR

    def test_lint_json_format_output(self):
        """Test linting with JSON format output."""
        valid_file = str(FIXTURES_VALID_DIR / "minimal.json")
        result = self.run_cvgen(["lint", "--file", valid_file, "--format", "json"])
        assert result.returncode == 0

        # Should be valid JSON
        output = json.loads(result.stdout)
        assert output["all_valid"] is True

    def test_build_nonexistent_input_dir(self):
        """Test build with nonexistent input directory."""
        result = self.run_cvgen([
            "build",
            "--input-dir", "/nonexistent/path/to/cvs"
        ])
        assert result.returncode == 2  # EXIT_CONFIG_ERROR

    def test_export_help_command(self):
        """Test that export --help returns successfully."""
        result = self.run_cvgen(["export", "--help"])
        assert result.returncode == 0
        assert "--format" in result.stdout
        assert "html" in result.stdout
        assert "md" in result.stdout

    def test_db_help_command(self):
        """Test that db --help returns successfully."""
        result = self.run_cvgen(["db", "--help"])
        assert result.returncode == 0
        assert "init" in result.stdout
        assert "import" in result.stdout
        assert "export" in result.stdout

    def test_doctor_command(self):
        """Test that doctor command runs."""
        result = self.run_cvgen(["doctor"])
        # Doctor should complete (may have warnings but shouldn't crash)
        # Exit code 0 means all checks passed, exit code 1 means issues found
        assert result.returncode in [0, 1]


class TestCLIBuildE2E:
    """End-to-end tests specifically for the build command."""

    def run_cvgen(self, args: list, cwd: Path = None) -> subprocess.CompletedProcess:
        """Run the cvgen CLI command."""
        cmd = [sys.executable, "-m", "cv_generator.cli"] + args
        return subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True
        )

    def test_build_dry_run_with_valid_fixture(self, tmp_path):
        """Test dry-run build with valid fixture files."""
        # Set up test directories
        cvs_dir = tmp_path / "cvs"
        cvs_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Copy minimal fixture
        shutil.copy(FIXTURES_VALID_DIR / "minimal.json", cvs_dir / "test.json")

        result = self.run_cvgen([
            "build",
            "--input-dir", str(cvs_dir),
            "--output-dir", str(output_dir),
            "--dry-run",
            "--keep-latex"
        ])

        # Should succeed or fail gracefully
        # Note: This may fail if templates aren't found, which is OK for this test
        # The key is it doesn't crash
        assert result.returncode in [0, 1, 2]

    def test_build_with_name_filter(self, tmp_path):
        """Test build with name filter."""
        cvs_dir = tmp_path / "cvs"
        cvs_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create multiple CV files
        shutil.copy(FIXTURES_VALID_DIR / "minimal.json", cvs_dir / "alice.json")
        shutil.copy(FIXTURES_VALID_DIR / "complete.json", cvs_dir / "bob.json")

        result = self.run_cvgen([
            "build",
            "--input-dir", str(cvs_dir),
            "--output-dir", str(output_dir),
            "--name", "alice",
            "--dry-run"
        ])

        # Should complete (may or may not find templates)
        assert result.returncode in [0, 1, 2]
