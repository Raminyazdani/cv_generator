"""
Tests for cv_generator.cli module.

Tests the command-line interface.
"""

import sys
from pathlib import Path

import pytest

from cv_generator.cli import main, create_parser


class TestCLI:
    """Tests for the CLI."""
    
    def test_help_flag(self, capsys):
        """Test that --help flag works."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "cvgen" in captured.out
    
    def test_version_flag(self, capsys):
        """Test that --version flag works."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "cvgen" in captured.out
    
    def test_build_help(self, capsys):
        """Test that build --help works."""
        with pytest.raises(SystemExit) as exc_info:
            main(["build", "--help"])
        
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--name" in captured.out
        assert "--dry-run" in captured.out


class TestCreateParser:
    """Tests for argument parser creation."""
    
    def test_parser_created(self):
        """Test that parser is created successfully."""
        parser = create_parser()
        assert parser is not None
    
    def test_parser_build_command(self):
        """Test parsing build command arguments."""
        parser = create_parser()
        args = parser.parse_args(["build", "--name", "test", "--dry-run"])
        
        assert args.command == "build"
        assert args.name == "test"
        assert args.dry_run is True
    
    def test_parser_verbose_flag(self):
        """Test parsing verbose flag."""
        parser = create_parser()
        args = parser.parse_args(["-v", "build"])
        
        assert args.verbose is True
    
    def test_parser_debug_flag(self):
        """Test parsing debug flag."""
        parser = create_parser()
        args = parser.parse_args(["--debug", "build"])
        
        assert args.debug is True
    
    def test_parser_directory_options(self):
        """Test parsing directory options."""
        parser = create_parser()
        args = parser.parse_args([
            "build",
            "--input-dir", "/path/to/cvs",
            "--output-dir", "/path/to/output",
            "--templates-dir", "/path/to/templates"
        ])
        
        assert args.input_dir == "/path/to/cvs"
        assert args.output_dir == "/path/to/output"
        assert args.templates_dir == "/path/to/templates"


class TestDBCommands:
    """Tests for db CLI commands."""
    
    def test_db_help(self, capsys):
        """Test that db --help works."""
        with pytest.raises(SystemExit) as exc_info:
            main(["db", "--help"])
        
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "init" in captured.out
        assert "import" in captured.out
        assert "export" in captured.out
        assert "diff" in captured.out
    
    def test_db_init_help(self, capsys):
        """Test that db init --help works."""
        with pytest.raises(SystemExit) as exc_info:
            main(["db", "init", "--help"])
        
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--db" in captured.out
        assert "--force" in captured.out
    
    def test_db_import_help(self, capsys):
        """Test that db import --help works."""
        with pytest.raises(SystemExit) as exc_info:
            main(["db", "import", "--help"])
        
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--input-dir" in captured.out
        assert "--name" in captured.out
        assert "--overwrite" in captured.out
    
    def test_db_export_help(self, capsys):
        """Test that db export --help works."""
        with pytest.raises(SystemExit) as exc_info:
            main(["db", "export", "--help"])
        
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--output-dir" in captured.out
        assert "--name" in captured.out
        assert "--format" in captured.out
    
    def test_db_diff_help(self, capsys):
        """Test that db diff --help works."""
        with pytest.raises(SystemExit) as exc_info:
            main(["db", "diff", "--help"])
        
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--input-dir" in captured.out
        assert "--name" in captured.out
        assert "--format" in captured.out
    
    def test_parser_db_init_command(self):
        """Test parsing db init command."""
        parser = create_parser()
        args = parser.parse_args(["db", "init", "--db", "/tmp/test.db", "--force"])
        
        assert args.command == "db"
        assert args.db_command == "init"
        assert args.db == "/tmp/test.db"
        assert args.force is True
    
    def test_parser_db_import_command(self):
        """Test parsing db import command."""
        parser = create_parser()
        args = parser.parse_args([
            "db", "import",
            "--input-dir", "/path/to/cvs",
            "--name", "ramin",
            "--overwrite"
        ])
        
        assert args.command == "db"
        assert args.db_command == "import"
        assert args.input_dir == "/path/to/cvs"
        assert args.name == "ramin"
        assert args.overwrite is True
    
    def test_parser_db_export_command(self):
        """Test parsing db export command."""
        parser = create_parser()
        args = parser.parse_args([
            "db", "export",
            "--output-dir", "/path/to/output",
            "--name", "ramin",
            "--format", "min"
        ])
        
        assert args.command == "db"
        assert args.db_command == "export"
        assert args.output_dir == "/path/to/output"
        assert args.name == "ramin"
        assert args.format == "min"
