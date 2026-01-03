"""
Tests for cv_generator.logging_config module.

Tests the logging configuration with various verbosity flags.
"""

import logging

import pytest

from cv_generator.logging_config import (
    configure_logging,
    get_log_level_from_flags,
    setup_logging,
)


class TestGetLogLevelFromFlags:
    """Tests for get_log_level_from_flags function."""

    def test_default_level(self):
        """Test default level is WARNING."""
        level = get_log_level_from_flags()
        assert level == logging.WARNING

    def test_verbose_flag(self):
        """Test verbose flag sets INFO level."""
        level = get_log_level_from_flags(verbose=True)
        assert level == logging.INFO

    def test_quiet_flag(self):
        """Test quiet flag sets ERROR level."""
        level = get_log_level_from_flags(quiet=True)
        assert level == logging.ERROR

    def test_debug_flag(self):
        """Test debug flag sets DEBUG level."""
        level = get_log_level_from_flags(debug=True)
        assert level == logging.DEBUG

    def test_debug_overrides_verbose(self):
        """Test debug flag overrides verbose flag."""
        level = get_log_level_from_flags(verbose=True, debug=True)
        assert level == logging.DEBUG

    def test_debug_overrides_quiet(self):
        """Test debug flag overrides quiet flag."""
        level = get_log_level_from_flags(quiet=True, debug=True)
        assert level == logging.DEBUG

    def test_quiet_overrides_verbose(self):
        """Test quiet flag overrides verbose flag."""
        level = get_log_level_from_flags(verbose=True, quiet=True)
        assert level == logging.ERROR


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configure_sets_debug_level(self):
        """Test that configure_logging sets the correct level."""
        configure_logging(level=logging.DEBUG)

        # Check the cv_generator logger has correct level
        cv_logger = logging.getLogger("cv_generator")
        assert cv_logger.level == logging.DEBUG

    def test_configure_sets_warning_level(self):
        """Test that configure_logging sets WARNING level."""
        configure_logging(level=logging.WARNING)

        cv_logger = logging.getLogger("cv_generator")
        assert cv_logger.level == logging.WARNING

    def test_configure_sets_error_level(self):
        """Test that configure_logging sets ERROR level."""
        configure_logging(level=logging.ERROR)

        cv_logger = logging.getLogger("cv_generator")
        assert cv_logger.level == logging.ERROR

    def test_configure_sets_info_level(self):
        """Test that configure_logging sets INFO level."""
        configure_logging(level=logging.INFO)

        cv_logger = logging.getLogger("cv_generator")
        assert cv_logger.level == logging.INFO


class TestSetupLogging:
    """Tests for setup_logging wrapper function."""

    def test_setup_with_verbose(self):
        """Test setup_logging with verbose flag sets INFO level."""
        setup_logging(verbose=True)

        cv_logger = logging.getLogger("cv_generator")
        assert cv_logger.level == logging.INFO

    def test_setup_with_debug(self):
        """Test setup_logging with debug flag sets DEBUG level."""
        setup_logging(debug=True)

        cv_logger = logging.getLogger("cv_generator")
        assert cv_logger.level == logging.DEBUG

    def test_setup_with_quiet(self):
        """Test setup_logging with quiet flag sets ERROR level."""
        setup_logging(quiet=True)

        cv_logger = logging.getLogger("cv_generator")
        assert cv_logger.level == logging.ERROR

    def test_setup_default(self):
        """Test setup_logging with default flags sets WARNING level."""
        setup_logging()

        cv_logger = logging.getLogger("cv_generator")
        assert cv_logger.level == logging.WARNING


class TestCLILoggingIntegration:
    """Integration tests for CLI logging behavior."""

    def test_cli_verbose_flag_is_parsed(self):
        """Test that CLI --verbose flag is parsed correctly."""
        from cv_generator.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["-v", "build"])
        assert args.verbose is True
        assert args.debug is False
        assert args.quiet is False

    def test_cli_debug_flag_is_parsed(self):
        """Test that CLI --debug flag is parsed correctly."""
        from cv_generator.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["--debug", "build"])
        assert args.debug is True
        assert args.verbose is False
        assert args.quiet is False

    def test_cli_quiet_flag_is_parsed(self):
        """Test that CLI --quiet flag is parsed correctly."""
        from cv_generator.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["--quiet", "build"])
        assert args.quiet is True
        assert args.verbose is False
        assert args.debug is False

    def test_cli_short_quiet_flag_is_parsed(self):
        """Test that CLI -q flag is parsed correctly."""
        from cv_generator.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["-q", "build"])
        assert args.quiet is True
