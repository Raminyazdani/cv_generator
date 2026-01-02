"""
Command-line interface for CV Generator.

Provides the `cvgen` command with the following subcommands:
- build: Generate PDF CVs from JSON files
- ensure: Validate multilingual CV JSON consistency
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional, List, Dict

from . import __version__
from .generator import generate_all_cvs
from .paths import (
    get_default_cvs_path,
    get_default_templates_path,
    get_default_output_path
)
from .errors import (
    CVGeneratorError,
    EXIT_SUCCESS,
    EXIT_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_TEMPLATE_ERROR
)
from .ensure import (
    run_ensure,
    EXIT_ENSURE_ERROR,
)

# Set up module logger
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False, debug: bool = False) -> None:
    """
    Configure logging based on verbosity level.
    
    Args:
        verbose: Enable INFO level logging.
        debug: Enable DEBUG level logging (overrides verbose).
    """
    if debug:
        level = logging.DEBUG
        format_str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    elif verbose:
        level = logging.INFO
        format_str = "%(message)s"
    else:
        level = logging.WARNING
        format_str = "%(message)s"
    
    logging.basicConfig(
        level=level,
        format=format_str,
        stream=sys.stderr
    )
    
    # Also configure the cv_generator logger
    cv_logger = logging.getLogger("cv_generator")
    cv_logger.setLevel(level)


def build_command(args: argparse.Namespace) -> int:
    """
    Execute the build command.
    
    Args:
        args: Parsed command-line arguments.
        
    Returns:
        Exit code.
    """
    # Resolve paths
    cvs_dir = Path(args.input_dir) if args.input_dir else None
    templates_dir = Path(args.templates_dir) if args.templates_dir else None
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    # Log configuration
    if cvs_dir:
        logger.info(f"Input directory: {cvs_dir}")
    if templates_dir:
        logger.info(f"Templates directory: {templates_dir}")
    if output_dir:
        logger.info(f"Output directory: {output_dir}")
    if args.name:
        logger.info(f"Building CV for: {args.name}")
    if args.dry_run:
        logger.info("Dry run mode: LaTeX will not be compiled")
    if args.keep_intermediate:
        logger.info("Keeping intermediate files")
    
    try:
        results = generate_all_cvs(
            cvs_dir=cvs_dir,
            templates_dir=templates_dir,
            output_dir=output_dir,
            name_filter=args.name,
            dry_run=args.dry_run,
            keep_intermediate=args.keep_intermediate
        )
    except CVGeneratorError as e:
        logger.error(str(e))
        return e.exit_code
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return EXIT_ERROR
    
    # Check results
    if not results:
        if args.name:
            logger.error(f"No CV files found matching '{args.name}'")
        else:
            logger.error("No CV files found")
        return EXIT_CONFIG_ERROR
    
    # Report results
    failed = [r for r in results if not r.success]
    if failed:
        for result in failed:
            logger.error(f"Failed: {result.name}_{result.lang}: {result.error}")
        return EXIT_ERROR
    
    return EXIT_SUCCESS


def ensure_command(args: argparse.Namespace) -> int:
    """
    Execute the ensure command.
    
    Args:
        args: Parsed command-line arguments.
        
    Returns:
        Exit code (0 if OK, 2 if mismatches found).
    """
    # Parse languages
    langs = [lang.strip() for lang in args.langs.split(",")]
    
    # Build explicit paths if provided
    paths: Optional[Dict[str, Path]] = None
    if args.path_en or args.path_de or args.path_fa:
        paths = {}
        if args.path_en:
            paths["en"] = Path(args.path_en)
        if args.path_de:
            paths["de"] = Path(args.path_de)
        if args.path_fa:
            paths["fa"] = Path(args.path_fa)
    
    # Determine CVs directory
    cvs_dir = None
    if args.dir:
        cvs_dir = Path(args.dir)
    elif args.input_dir:
        cvs_dir = Path(args.input_dir)
    
    # Load language mapping if specified
    lang_map = None
    if args.lang_map:
        lang_map_path = Path(args.lang_map)
        if lang_map_path.exists():
            with open(lang_map_path, "r", encoding="utf-8") as f:
                lang_map = json.load(f)
    
    # Log configuration
    logger.info(f"Checking CV consistency for: {args.name}")
    logger.info(f"Languages: {', '.join(langs)}")
    if cvs_dir:
        logger.info(f"Input directory: {cvs_dir}")
    
    try:
        report = run_ensure(
            name=args.name,
            langs=langs,
            cvs_dir=cvs_dir,
            paths=paths,
            lang_map=lang_map,
            max_errors=args.max_errors,
            fail_fast=args.fail_fast,
        )
    except Exception as e:
        logger.exception(f"Error during ensure check: {e}")
        return EXIT_ERROR
    
    # Output the report
    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(report.format_text())
    
    # Return appropriate exit code
    if report.is_valid:
        return EXIT_SUCCESS
    else:
        return EXIT_ENSURE_ERROR


def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser for the CLI.
    
    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        prog="cvgen",
        description="Generate beautiful PDF CVs from JSON data using Jinja2 templates and Awesome-CV.",
        epilog="Example: cvgen build --name ramin"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"cvgen {__version__}"
    )
    
    # Global options
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output (INFO level logging)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output (DEBUG level logging)"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        description="Available commands"
    )
    
    # Build command
    build_parser = subparsers.add_parser(
        "build",
        help="Build PDF CVs from JSON files",
        description="Generate PDF CVs from JSON files in the input directory."
    )
    
    build_parser.add_argument(
        "--name", "-n",
        type=str,
        help="Build only the CV with this base name (e.g., 'ramin')"
    )
    build_parser.add_argument(
        "--input-dir", "-i",
        type=str,
        help=f"Input directory containing CV JSON files (default: data/cvs)"
    )
    build_parser.add_argument(
        "--output-dir", "-o",
        type=str,
        help=f"Output directory for generated PDFs (default: output)"
    )
    build_parser.add_argument(
        "--templates-dir", "-t",
        type=str,
        help=f"Templates directory (default: templates)"
    )
    build_parser.add_argument(
        "--keep-intermediate", "-k",
        action="store_true",
        help="Keep intermediate result files (don't clean up result/ directory)"
    )
    build_parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Render LaTeX but skip xelatex compilation"
    )
    
    build_parser.set_defaults(func=build_command)
    
    # Ensure command
    ensure_parser = subparsers.add_parser(
        "ensure",
        help="Validate multilingual CV JSON consistency",
        description="Check that multilingual CV JSON files have consistent structure."
    )
    
    ensure_parser.add_argument(
        "--name", "-n",
        type=str,
        required=True,
        help="Name of the person (e.g., 'ramin')"
    )
    ensure_parser.add_argument(
        "--langs", "-l",
        type=str,
        default="en,de,fa",
        help="Comma-separated language codes to check (default: en,de,fa)"
    )
    ensure_parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    ensure_parser.add_argument(
        "--input-dir", "-i",
        type=str,
        help="Input directory containing CV JSON files (default: data/cvs)"
    )
    ensure_parser.add_argument(
        "--dir", "-D",
        type=str,
        help="Directory containing CV files (e.g., data/cvs/i18n/ramin)"
    )
    ensure_parser.add_argument(
        "--path-en",
        type=str,
        help="Explicit path to English CV file"
    )
    ensure_parser.add_argument(
        "--path-de",
        type=str,
        help="Explicit path to German CV file"
    )
    ensure_parser.add_argument(
        "--path-fa",
        type=str,
        help="Explicit path to Persian CV file"
    )
    ensure_parser.add_argument(
        "--lang-map",
        type=str,
        help="Path to language mapping file (lang.json)"
    )
    ensure_parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop at first batch of errors"
    )
    ensure_parser.add_argument(
        "--max-errors",
        type=int,
        default=None,
        help="Maximum number of errors before stopping"
    )
    
    ensure_parser.set_defaults(func=ensure_command)
    
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI.
    
    Args:
        argv: Command-line arguments (defaults to sys.argv).
        
    Returns:
        Exit code.
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Set up logging
    setup_logging(verbose=args.verbose, debug=args.debug)
    
    # If no command specified, default to 'build'
    if not args.command:
        # Re-parse with 'build' as default
        args = parser.parse_args(['build'] + (argv if argv else sys.argv[1:]))
    
    # Execute the command
    if hasattr(args, 'func'):
        return args.func(args)
    else:
        parser.print_help()
        return EXIT_SUCCESS


def main_cli() -> None:
    """
    CLI entry point for setuptools console_scripts.
    
    Calls main() and exits with the returned code.
    """
    sys.exit(main())


if __name__ == "__main__":
    main_cli()
