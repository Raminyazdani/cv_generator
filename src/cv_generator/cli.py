"""
Command-line interface for CV Generator Web UI.

Provides the `cvgen` command with the following subcommands:
- web: Start the web UI server for managing CV data and tags
- db: SQLite database operations (init, import, export)
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .errors import (
    EXIT_CONFIG_ERROR,
    EXIT_ERROR,
    EXIT_SUCCESS,
)
from .logging_config import setup_logging

logger = logging.getLogger(__name__)


def web_command(args: argparse.Namespace) -> int:
    """
    Start the web server for managing CV data.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .web import run_server

    db_path = Path(args.db) if args.db else None
    allow_unsafe_bind = getattr(args, "i_know_what_im_doing", False)

    try:
        run_server(
            host=args.host,
            port=args.port,
            debug=args.debug if hasattr(args, 'debug') else False,
            db_path=db_path,
            allow_unsafe_bind=allow_unsafe_bind
        )
        return EXIT_SUCCESS
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else EXIT_ERROR
    except Exception as e:
        logger.error(f"Error starting web server: {e}")
        print(f"❌ Error: {e}")
        return EXIT_ERROR


def db_init_command(args: argparse.Namespace) -> int:
    """
    Initialize the database.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .db import init_db

    db_path = Path(args.db) if args.db else None

    try:
        result_path = init_db(db_path, force=args.force)
        logger.info(f"Database initialized: {result_path}")
        print(f"✅ Database initialized: {result_path}")
        return EXIT_SUCCESS
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        print(f"❌ Error: {e}")
        return EXIT_ERROR


def db_import_command(args: argparse.Namespace) -> int:
    """
    Import CV JSON files into the database.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .db import import_all_cvs

    db_path = Path(args.db) if args.db else None
    input_dir = Path(args.input_dir) if args.input_dir else None

    try:
        results = import_all_cvs(
            input_dir=input_dir,
            db_path=db_path,
            name_filter=args.name,
            overwrite=args.overwrite,
            backup=not args.no_backup
        )

        print("\n📥 Import Results:")
        print(f"   Files processed: {results['files_processed']}")
        print(f"   Total entries: {results['total_entries']}")

        for file_result in results.get("files", []):
            if file_result.get("success"):
                print(f"   ✅ {file_result['file']}: {file_result.get('entries_imported', 0)} entries")
            else:
                print(f"   ❌ {file_result['file']}: {file_result.get('error', 'Unknown error')}")

        return EXIT_SUCCESS
    except Exception as e:
        logger.error(f"Error importing CVs: {e}")
        print(f"❌ Error: {e}")
        return EXIT_ERROR


def db_export_command(args: argparse.Namespace) -> int:
    """
    Export CV data from database to JSON files.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .db import export_all_cvs

    db_path = Path(args.db) if args.db else None
    output_dir = Path(args.output_dir) if args.output_dir else None
    pretty = args.format != "min"

    try:
        results = export_all_cvs(
            output_dir=output_dir,
            db_path=db_path,
            name_filter=args.name,
            pretty=pretty,
            force=args.force
        )

        print("\n📤 Export Results:")
        print(f"   Files exported: {results['files_exported']}")

        for file_result in results.get("files", []):
            if file_result.get("success"):
                print(f"   ✅ {file_result['file']}")
            else:
                print(f"   ❌ {file_result['slug']}: {file_result.get('error', 'Unknown error')}")

        return EXIT_SUCCESS
    except Exception as e:
        logger.error(f"Error exporting CVs: {e}")
        print(f"❌ Error: {e}")
        return EXIT_ERROR


def db_list_command(args: argparse.Namespace) -> int:
    """
    List database contents (persons or tags).

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .db import list_persons, list_tags

    db_path = Path(args.db) if args.db else None

    try:
        if args.what == "persons":
            items = list_persons(db_path)
            if args.format == "json":
                print(json.dumps(items, indent=2, ensure_ascii=False))
            else:
                print(f"\n👥 Persons in database: {len(items)}")
                for item in items:
                    print(f"   • {item['slug']}: {item['entry_count']} entries")
                    if item.get('display_name'):
                        print(f"     Name: {item['display_name']}")
        else:
            items = list_tags(db_path)
            if args.format == "json":
                print(json.dumps(items, indent=2, ensure_ascii=False))
            else:
                print(f"\n🏷️  Tags in database: {len(items)}")
                for item in items:
                    print(f"   • {item['name']}: used {item['usage_count']} times")

        return EXIT_SUCCESS
    except Exception as e:
        logger.error(f"Error listing database contents: {e}")
        print(f"❌ Error: {e}")
        return EXIT_ERROR


def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser for the CLI.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        prog="cvgen",
        description="CV Generator Web UI - A lightweight web interface for managing CV data.",
        epilog="Example: cvgen web"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"cvgen {__version__}"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress output except errors"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        description="Available commands"
    )

    # Web command
    web_parser = subparsers.add_parser(
        "web",
        help="Start the web UI server",
        description="Start the local web server for managing CV data and tags."
    )
    web_parser.add_argument(
        "--db",
        type=str,
        help="Path to database file (default: data/db/cv.db)"
    )
    web_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    web_parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to listen on (default: 5000)"
    )
    web_parser.add_argument(
        "--debug",
        action="store_true",
        dest="debug",
        help="Enable Flask debug mode"
    )
    web_parser.add_argument(
        "--i-know-what-im-doing",
        action="store_true",
        dest="i_know_what_im_doing",
        help="Required when binding to non-localhost address"
    )
    web_parser.set_defaults(func=web_command)

    # DB command group
    db_parser = subparsers.add_parser(
        "db",
        help="Database operations",
        description="Manage the SQLite database for CV data."
    )

    db_subparsers = db_parser.add_subparsers(
        dest="db_command",
        title="db commands",
        description="Available database commands"
    )

    # DB init
    db_init_parser = db_subparsers.add_parser(
        "init",
        help="Initialize the database",
        description="Create the database and apply schema."
    )
    db_init_parser.add_argument(
        "--db",
        type=str,
        help="Path to database file"
    )
    db_init_parser.add_argument(
        "--force",
        action="store_true",
        help="Recreate the database even if it exists"
    )
    db_init_parser.set_defaults(func=db_init_command)

    # DB import
    db_import_parser = db_subparsers.add_parser(
        "import",
        help="Import CV JSON files into database",
        description="Import CV JSON files from a directory."
    )
    db_import_parser.add_argument(
        "--db",
        type=str,
        help="Path to database file"
    )
    db_import_parser.add_argument(
        "--input-dir", "-i",
        type=str,
        help="Input directory containing CV JSON files"
    )
    db_import_parser.add_argument(
        "--name", "-n",
        type=str,
        help="Import only CVs matching this name"
    )
    db_import_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing entries"
    )
    db_import_parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't backup database before overwrite"
    )
    db_import_parser.set_defaults(func=db_import_command)

    # DB export
    db_export_parser = db_subparsers.add_parser(
        "export",
        help="Export database to JSON files",
        description="Export CV data from database to JSON files."
    )
    db_export_parser.add_argument(
        "--db",
        type=str,
        help="Path to database file"
    )
    db_export_parser.add_argument(
        "--output-dir", "-o",
        type=str,
        help="Output directory for JSON files"
    )
    db_export_parser.add_argument(
        "--name", "-n",
        type=str,
        help="Export only CVs matching this slug"
    )
    db_export_parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["pretty", "min"],
        default="pretty",
        help="Output format (default: pretty)"
    )
    db_export_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files"
    )
    db_export_parser.set_defaults(func=db_export_command)

    # DB list
    db_list_parser = db_subparsers.add_parser(
        "list",
        help="List database contents",
        description="List persons or tags in the database."
    )
    db_list_parser.add_argument(
        "--db",
        type=str,
        help="Path to database file"
    )
    db_list_parser.add_argument(
        "--what",
        type=str,
        choices=["persons", "tags"],
        default="persons",
        help="What to list (default: persons)"
    )
    db_list_parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    db_list_parser.set_defaults(func=db_list_command)

    db_parser.set_defaults(func=lambda args: db_parser.print_help() or EXIT_SUCCESS)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI.

    Args:
        argv: Command-line arguments.

    Returns:
        Exit code.
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    setup_logging(verbose=args.verbose, debug=args.debug, quiet=args.quiet)

    if not args.command:
        parser.print_help()
        return EXIT_SUCCESS

    if hasattr(args, 'func'):
        return args.func(args)
    else:
        parser.print_help()
        return EXIT_SUCCESS


def main_cli() -> None:
    """CLI entry point for setuptools console_scripts."""
    sys.exit(main())


if __name__ == "__main__":
    main_cli()
