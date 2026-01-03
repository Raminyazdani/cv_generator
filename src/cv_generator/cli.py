"""
Command-line interface for CV Generator.

Provides the `cvgen` command with the following subcommands:
- build: Generate PDF CVs from JSON files
- ensure: Validate multilingual CV JSON consistency
- lint: Validate CV JSON files against the schema
- db: SQLite database operations (init, import, export, diff)
- doctor: System health checks
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

from . import __version__
from .ensure import (
    EXIT_ENSURE_ERROR,
    run_ensure,
)
from .errors import (
    EXIT_CONFIG_ERROR,
    EXIT_ERROR,
    EXIT_SUCCESS,
    EXIT_VALIDATION_ERROR,
    CVGeneratorError,
)
from .generator import generate_all_cvs
from .io import discover_cv_files
from .logging_config import setup_logging
from .validate_schema import validate_cv_file

# Set up module logger
logger = logging.getLogger(__name__)


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

    # Validate input directory if specified
    if cvs_dir and not cvs_dir.exists():
        logger.error(f"Input directory not found: {cvs_dir}")
        return EXIT_CONFIG_ERROR

    # Validate templates directory if specified
    if templates_dir and not templates_dir.exists():
        logger.error(f"Templates directory not found: {templates_dir}")
        return EXIT_CONFIG_ERROR

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
    if args.keep_latex:
        logger.info("Keeping LaTeX source files")

    try:
        results = generate_all_cvs(
            cvs_dir=cvs_dir,
            templates_dir=templates_dir,
            output_dir=output_dir,
            name_filter=args.name,
            dry_run=args.dry_run,
            keep_latex=args.keep_latex
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


def lint_command(args: argparse.Namespace) -> int:
    """
    Execute the lint command to validate CV JSON against schema.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 if OK, 5 if validation errors found in strict mode).
    """
    # Determine CVs directory
    cvs_dir = Path(args.input_dir) if args.input_dir else None

    # Collect files to validate
    files_to_validate = []

    if args.file:
        # Validate a specific file
        file_path = Path(args.file)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return EXIT_CONFIG_ERROR
        files_to_validate.append(file_path)
    else:
        # Discover CV files
        try:
            files_to_validate = discover_cv_files(
                cvs_path=cvs_dir,
                name_filter=args.name
            )
        except Exception as e:
            logger.error(f"Error discovering CV files: {e}")
            return EXIT_CONFIG_ERROR

    if not files_to_validate:
        if args.name:
            logger.error(f"No CV files found matching '{args.name}'")
        else:
            logger.error("No CV files found")
        return EXIT_CONFIG_ERROR

    # Log configuration
    logger.info(f"Validating {len(files_to_validate)} file(s)")
    if args.strict:
        logger.info("Running in strict mode")

    # Validate each file
    all_valid = True
    reports = []

    for file_path in files_to_validate:
        logger.debug(f"Validating: {file_path}")
        report = validate_cv_file(file_path, strict=args.strict)
        reports.append(report)

        if not report.is_valid:
            all_valid = False

    # Output results
    if args.format == "json":
        results = {
            "files_validated": len(files_to_validate),
            "all_valid": all_valid,
            "reports": [r.to_dict() for r in reports],
        }
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("\n🔍 Schema Validation Results:")
        print(f"   Files validated: {len(files_to_validate)}")
        print(f"   Mode: {'strict' if args.strict else 'default (warnings allowed)'}")
        print()

        for report in reports:
            if report.file_path:
                print(f"📄 {report.file_path.name}")
            if report.is_valid and not report.issues:
                print("   ✅ Valid")
            else:
                status = "❌ Invalid" if not report.is_valid else "⚠️ Warnings"
                print(f"   {status} ({report.error_count} errors, {report.warning_count} warnings)")
                for issue in report.issues:
                    print(f"      {issue}")
            print()

    # Return appropriate exit code
    if all_valid:
        return EXIT_SUCCESS
    else:
        return EXIT_VALIDATION_ERROR


def db_init_command(args: argparse.Namespace) -> int:
    """
    Execute the db init command.

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
    Execute the db import command.

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
    Execute the db export command.

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
            apply_tags=args.apply_tags,
            apply_tags_to_all=args.apply_tags_to_all,
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


def db_diff_command(args: argparse.Namespace) -> int:
    """
    Execute the db diff command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .db import diff_all_cvs

    db_path = Path(args.db) if args.db else None
    input_dir = Path(args.input_dir) if args.input_dir else None

    try:
        results = diff_all_cvs(
            input_dir=input_dir,
            db_path=db_path,
            name_filter=args.name
        )

        if args.format == "json":
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print("\n🔍 Diff Results:")
            print(f"   Files compared: {results['files_compared']}")
            print(f"   Matches: {results['matches']}")
            print(f"   Mismatches: {results['mismatches']}")

            for file_result in results.get("files", []):
                if file_result.get("match"):
                    print(f"   ✅ {file_result['file']}: Match")
                elif file_result.get("error"):
                    print(f"   ⚠️  {file_result['file']}: {file_result['error']}")
                else:
                    print(f"   ❌ {file_result['file']}: {file_result['difference_count']} differences")
                    for diff in file_result.get("differences", [])[:5]:
                        print(f"      - {diff['path']}: {diff['type']}")
                    if len(file_result.get("differences", [])) > 5:
                        print(f"      ... and {len(file_result['differences']) - 5} more")

        # Return non-zero if there are mismatches
        if results['mismatches'] > 0:
            return EXIT_ENSURE_ERROR
        return EXIT_SUCCESS
    except Exception as e:
        logger.error(f"Error comparing CVs: {e}")
        print(f"❌ Error: {e}")
        return EXIT_ERROR


def db_list_command(args: argparse.Namespace) -> int:
    """
    Execute the db list command.

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


def db_doctor_command(args: argparse.Namespace) -> int:
    """
    Execute the db doctor command (health check).

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .db import doctor

    db_path = Path(args.db) if args.db else None

    try:
        results = doctor(db_path)

        if args.format == "json":
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print(f"\n🏥 Database Health Check: {results['database']}")
            print(f"   Status: {'✅ Healthy' if results['healthy'] else '❌ Issues Found'}")
            print()
            print("📊 Statistics:")
            print(f"   Persons: {results['stats'].get('persons', 0)}")
            print(f"   Entries: {results['stats'].get('entries', 0)}")
            print(f"   Tags: {results['stats'].get('tags', 0)}")
            print(f"   Tag Assignments: {results['stats'].get('tag_assignments', 0)}")

            if results['issues']:
                print()
                print(f"⚠️  Issues ({len(results['issues'])}):")
                for issue in results['issues']:
                    print(f"   • {issue}")

            print()
            print("🔍 Checks:")
            checks = results.get('checks', {})
            if 'schema_version' in checks:
                sv = checks['schema_version']
                status = "✅" if sv.get('ok') else "❌"
                print(f"   {status} Schema version: v{sv.get('current', '?')} (expected v{sv.get('expected', '?')})")
            if 'orphaned_entries' in checks:
                oe = checks['orphaned_entries']
                status = "✅" if oe.get('ok') else "❌"
                print(f"   {status} Orphaned entries: {oe.get('count', 0)}")
            if 'orphaned_tags' in checks:
                ot = checks['orphaned_tags']
                print(f"   ℹ️  Unused tags: {ot.get('count', 0)}")
            if 'duplicate_tags' in checks:
                dt = checks['duplicate_tags']
                status = "✅" if dt.get('ok') else "❌"
                print(f"   {status} Duplicate tags: {dt.get('count', 0)}")
            if 'missing_identity_keys' in checks:
                mi = checks['missing_identity_keys']
                print(f"   ℹ️  Missing identity keys: {mi.get('count', 0)}")
            if 'invalid_json' in checks:
                ij = checks['invalid_json']
                status = "✅" if ij.get('ok') else "❌"
                print(f"   {status} Invalid JSON: {ij.get('count', 0)}")

        return EXIT_SUCCESS if results['healthy'] else EXIT_ENSURE_ERROR
    except Exception as e:
        logger.error(f"Error running health check: {e}")
        print(f"❌ Error: {e}")
        return EXIT_ERROR


def doctor_command(args: argparse.Namespace) -> int:
    """
    Execute the doctor command for system health checks.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .doctor import run_checks

    template_dir = Path(args.templates_dir) if args.templates_dir else None
    output_dir = Path(args.output_dir) if args.output_dir else None

    try:
        report = run_checks(
            template_dir=template_dir,
            output_dir=output_dir,
            check_db=True,
        )

        if args.format == "json":
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            # args.verbose is always available (global option)
            print(report.format_text(verbose=args.verbose))

        return EXIT_SUCCESS if report.is_healthy else EXIT_ENSURE_ERROR
    except Exception as e:
        logger.error(f"Error running doctor: {e}")
        print(f"❌ Error: {e}")
        return EXIT_ERROR


def web_tags_command(args: argparse.Namespace) -> int:
    """
    Execute the web tags command (start web server).

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .web import run_server

    db_path = Path(args.db) if args.db else None

    try:
        run_server(
            host=args.host,
            port=args.port,
            debug=args.debug if hasattr(args, 'debug') else False,
            db_path=db_path
        )
        return EXIT_SUCCESS
    except Exception as e:
        logger.error(f"Error starting web server: {e}")
        print(f"❌ Error: {e}")
        return EXIT_ERROR


# Extended help topics for 'cvgen help <topic>'
HELP_TOPICS = {
    "build": """
cvgen build — Generate PDF CVs from JSON files

SYNOPSIS
    cvgen build [OPTIONS]

DESCRIPTION
    The build command renders CV JSON files to LaTeX using Jinja2 templates,
    then compiles them to PDF using XeLaTeX.

    By default, all CV files in data/cvs/ are processed. Use --name to filter
    to a specific person.

OPTIONS
    --name, -n NAME     Build only CVs matching this base name (e.g., 'ramin')
    --input-dir, -i     Directory containing CV JSON files (default: data/cvs)
    --output-dir, -o    Output directory root (default: output)
    --templates-dir, -t Templates directory (default: templates)
    --keep-latex, -k    Keep LaTeX sources in output/latex/ for debugging
    --dry-run, -d       Render LaTeX but skip PDF compilation

EXAMPLES
    # Generate all CVs
    cvgen build

    # Generate only ramin's CV
    cvgen build --name ramin

    # Dry run with verbose output
    cvgen -v build --dry-run

    # Keep LaTeX files for debugging
    cvgen build --keep-latex

OUTPUT STRUCTURE
    output/
      pdf/<name>/<lang>/<name>_<lang>.pdf
      latex/<name>/<lang>/main.tex        (with --keep-latex)
      latex/<name>/<lang>/sections/*.tex  (with --keep-latex)
""",

    "ensure": """
cvgen ensure — Validate multilingual CV JSON consistency

SYNOPSIS
    cvgen ensure --name NAME [OPTIONS]

DESCRIPTION
    The ensure command checks that multilingual CV JSON files have consistent
    structure across languages. It compares the English version (canonical)
    with German and Persian versions.

    Use this to verify that:
    - All languages have the same sections and fields
    - No keys are missing or extra in any language
    - Skill headings are properly translated

OPTIONS
    --name, -n NAME     Name of the person (required)
    --langs, -l LANGS   Comma-separated language codes (default: en,de,fa)
    --format, -f FMT    Output format: text or json (default: text)
    --input-dir, -i     Directory containing CV JSON files
    --dir, -D           Directory containing CV files directly
    --lang-map          Path to language mapping file (lang.json)
    --fail-fast         Stop at first batch of errors
    --max-errors N      Maximum errors before stopping

EXAMPLES
    # Check ramin's CV consistency across all languages
    cvgen ensure --name ramin

    # Check only English and German
    cvgen ensure --name ramin --langs en,de

    # Output as JSON for programmatic use
    cvgen ensure --name ramin --format json

EXIT CODES
    0  All languages are consistent
    2  Mismatches found
""",

    "lint": """
cvgen lint — Validate CV JSON files against schema

SYNOPSIS
    cvgen lint [OPTIONS]

DESCRIPTION
    The lint command validates CV JSON files against the schema to detect
    structural issues before rendering. This helps catch errors like:

    - Missing required fields (e.g., 'basics')
    - Wrong types (e.g., string instead of array)
    - Invalid field values

OPTIONS
    --name, -n NAME     Validate only CVs matching this base name
    --file, -f FILE     Path to a specific CV JSON file to validate
    --input-dir, -i     Directory containing CV JSON files (default: data/cvs)
    --strict            Treat all issues as errors (fail on any issue)
    --format            Output format: text or json (default: text)

EXAMPLES
    # Validate all CV files
    cvgen lint

    # Validate only ramin's CVs
    cvgen lint --name ramin

    # Validate a specific file
    cvgen lint --file data/cvs/ramin.json

    # Strict mode - fail on any schema issue
    cvgen lint --strict

EXIT CODES
    0  All files are valid
    5  Validation errors found (in strict mode or for critical errors)
""",

    "languages": """
cvgen languages — Language support and translation

DESCRIPTION
    CV Generator supports multilingual CVs with the following languages:

    - en: English (canonical/reference)
    - de: German
    - fa: Persian (with RTL support)

FILE NAMING
    Multilingual CV files follow these naming patterns:

    1. Preferred (i18n directory):
       data/cvs/i18n/<name>/cv.en.json
       data/cvs/i18n/<name>/cv.de.json
       data/cvs/i18n/<name>/cv.fa.json

    2. Alternative (flat structure):
       data/cvs/<name>.en.json
       data/cvs/<name>.de.json
       data/cvs/<name>_en.json
       data/cvs/<name>_de.json

TRANSLATION MAPPING
    Skill headings and categories can be translated using a lang.json file:

    {
      "Technical Skills": {
        "de": "Technische Fähigkeiten",
        "fa": "مهارت‌های فنی"
      },
      "Soft Skills": {
        "de": "Soft Skills",
        "fa": "مهارت‌های نرم"
      }
    }

RTL SUPPORT
    Persian (fa) CVs are automatically rendered with RTL (right-to-left)
    text direction. The IS_RTL template variable is set to True for RTL
    languages.

VALIDATING TRANSLATIONS
    Use 'cvgen ensure' to verify consistency across language versions.
""",

    "templates": """
cvgen templates — Template customization

DESCRIPTION
    CV Generator uses Jinja2 templates with LaTeX to render CVs.
    Templates are stored in the templates/ directory.

TEMPLATE FILES
    layout.tex       Main document structure (document class, header, footer)
    header.tex       Personal info and social links
    education.tex    Education history
    experience.tex   Work experience
    skills.tex       Technical and soft skills
    language.tex     Language proficiencies
    projects.tex     Projects and contributions
    certificates.tex Certifications and awards
    publications.tex Academic publications
    references.tex   Professional references

JINJA2 SYNTAX
    Templates use custom delimiters to avoid LaTeX conflicts:

    Blocks:    <BLOCK> ... </BLOCK>
    Variables: <VAR> ... </VAR>
    Comments:  /*/*/* ... */*/*/

    Example:
        <VAR> basics[0]["fname"] | latex_escape </VAR>
        <BLOCK> if education|length > 0 </BLOCK>
          ... education section ...
        <BLOCK> endif </BLOCK>

AVAILABLE FILTERS
    latex_escape    Escape LaTeX special characters (#, %, _, etc.)
    file_exists     Check if a file path exists
    debug           Print value to console during rendering
    find_pic        Check if profile picture exists
    get_pic         Get profile picture path

ADDING A NEW SECTION
    1. Create templates/newsection.tex
    2. Add to layout.tex: <VAR> newsection_section | default('') </VAR>
    3. Add corresponding data to your CV JSON
""",

    "json-schema": """
cvgen json-schema — CV JSON data format

DESCRIPTION
    CV data is stored as JSON files loosely based on JSON Resume format.
    See data/cvs/*.json for examples.

TOP-LEVEL SECTIONS
    basics      Personal info (name, email, phone, location)
    profiles    Social links (GitHub, LinkedIn, Google Scholar)
    education   Education history
    experiences Work experience
    skills      Technical and soft skills
    languages   Language proficiencies
    projects    Projects and contributions
    publications Academic publications
    workshop_and_certifications  Certifications and training
    references  Professional references

BASICS EXAMPLE
    {
      "basics": [{
        "fname": "Jane",
        "lname": "Doe",
        "label": ["Software Engineer", "ML Researcher"],
        "email": "jane@example.com",
        "phone": {"formatted": "+1 555-0100"},
        "location": [{
          "city": "San Francisco",
          "region": "CA",
          "country": "USA"
        }]
      }]
    }

SKILLS STRUCTURE
    {
      "skills": {
        "Technical Skills": {
          "Programming": [
            {"short_name": "Python", "long_name": "Python 3.x"},
            {"short_name": "JavaScript"}
          ],
          "Frameworks": [
            {"short_name": "React"},
            {"short_name": "Django"}
          ]
        },
        "Soft Skills": {
          "Communication": [
            {"short_name": "Technical Writing"}
          ]
        }
      }
    }

VALIDATION
    Use 'cvgen ensure' to validate consistency across language versions.
""",

    "troubleshooting": """
cvgen troubleshooting — Common issues and solutions

XELATEX NOT FOUND
    Symptom: 'xelatex' is not recognized as a command

    Solution:
    1. Install TeX Live or MiKTeX
    2. Add xelatex to your PATH
    3. Verify: xelatex --version

LATEX COMPILATION ERRORS
    Symptom: PDF not produced, LaTeX log shows errors

    Common causes:
    - Unescaped special characters in JSON (#, %, _, &, $)
    - Missing fields referenced in templates

    Solutions:
    - Use | latex_escape filter in templates
    - Ensure all required keys exist in JSON
    - Run with --keep-latex to inspect generated .tex files

MISSING FONTS
    Symptom: Font warnings or substitutions in PDF

    Solution:
    - Install fonts used by Awesome-CV (Roboto, Source Sans Pro)
    - Or modify templates to use available fonts

WINDOWS FILE LOCKS
    Symptom: "Access is denied" when cleaning up

    Solution:
    - Close files in editors that lock them
    - Pause OneDrive/antivirus sync temporarily
    - The generator has retry logic for file locks

TEMPLATE ERRORS
    Symptom: Jinja TemplateError with file name

    Solution:
    - Check the referenced template file
    - Verify JSON data matches template expectations
    - Use | debug filter to inspect values

PROFILE PICTURE NOT SHOWING
    Symptom: CV generates without photo

    Solution:
    - Place photo at data/pics/<name>.jpg
    - Name must match CV file base name
    - Supported format: JPG
""",

    "doctor": """
cvgen doctor — System health checks

SYNOPSIS
    cvgen doctor [OPTIONS]

DESCRIPTION
    The doctor command validates the environment and repo configuration
    before users attempt builds. It performs read-only checks to identify
    potential issues.

    Use this to verify that:
    - Python version meets requirements
    - Required dependencies are installed
    - LaTeX engine (xelatex) is available
    - Templates are valid
    - Output directory is writable
    - Database is healthy (if exists)

OPTIONS
    --templates-dir, -t Templates directory to check (default: templates)
    --output-dir, -o    Output directory to check (default: output)
    --format, -f        Output format: text or json (default: text)

EXAMPLES
    # Run all health checks
    cvgen doctor

    # Output as JSON for CI integration
    cvgen doctor --format json

    # Verbose output with fix hints for all checks
    cvgen -v doctor

EXIT CODES
    0  All checks passed (healthy)
    2  One or more checks failed (unhealthy)
""",
}


def help_command(args: argparse.Namespace) -> int:
    """
    Execute the help command to show extended help topics.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    topic = args.topic.lower() if args.topic else None

    if not topic:
        # List available topics
        print("Available help topics:\n")
        print("  build           Generate PDF CVs from JSON files")
        print("  ensure          Validate multilingual CV consistency")
        print("  lint            Validate CV JSON files against schema")
        print("  doctor          System health checks")
        print("  languages       Language support and translation")
        print("  templates       Template customization")
        print("  json-schema     CV JSON data format")
        print("  troubleshooting Common issues and solutions")
        print("\nUse 'cvgen help <topic>' for detailed information.")
        return EXIT_SUCCESS

    # Normalize topic names
    topic_aliases = {
        "generate": "build",
        "validate": "ensure",
        "langs": "languages",
        "template": "templates",
        "schema": "json-schema",
        "json": "json-schema",
    }
    topic = topic_aliases.get(topic, topic)

    if topic in HELP_TOPICS:
        print(HELP_TOPICS[topic].strip())
        return EXIT_SUCCESS
    else:
        print(f"Unknown help topic: '{topic}'")
        print("\nAvailable topics: build, ensure, lint, doctor, languages, templates, json-schema, troubleshooting")
        return EXIT_ERROR


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
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress output except errors"
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
        help="Input directory containing CV JSON files (default: data/cvs)"
    )
    build_parser.add_argument(
        "--output-dir", "-o",
        type=str,
        help="Output directory root (default: output). PDFs go to output/pdf/<name>/<lang>/"
    )
    build_parser.add_argument(
        "--templates-dir", "-t",
        type=str,
        help="Templates directory (default: templates)"
    )
    build_parser.add_argument(
        "--keep-latex", "-k",
        action="store_true",
        dest="keep_latex",
        help="Keep LaTeX source files in output/latex/ (default: clean up after compilation)"
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

    # Lint command
    lint_parser = subparsers.add_parser(
        "lint",
        help="Validate CV JSON files against schema",
        description="Check CV JSON files for structural issues before rendering."
    )

    lint_parser.add_argument(
        "--name", "-n",
        type=str,
        help="Validate only CVs matching this base name (e.g., 'ramin')"
    )
    lint_parser.add_argument(
        "--file", "-f",
        type=str,
        help="Path to a specific CV JSON file to validate"
    )
    lint_parser.add_argument(
        "--input-dir", "-i",
        type=str,
        help="Input directory containing CV JSON files (default: data/cvs)"
    )
    lint_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat all schema issues as errors (fail on any issue)"
    )
    lint_parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )

    lint_parser.set_defaults(func=lint_command)

    # DB command
    db_parser = subparsers.add_parser(
        "db",
        help="SQLite database operations",
        description="Manage CV data in SQLite database for querying and editing."
    )

    db_subparsers = db_parser.add_subparsers(
        dest="db_command",
        title="db commands",
        description="Available database commands"
    )

    # DB init command
    db_init_parser = db_subparsers.add_parser(
        "init",
        help="Initialize the database",
        description="Create the database and apply schema."
    )
    db_init_parser.add_argument(
        "--db",
        type=str,
        help="Path to database file (default: data/db/cv.db)"
    )
    db_init_parser.add_argument(
        "--force",
        action="store_true",
        help="Recreate the database even if it exists"
    )
    db_init_parser.set_defaults(func=db_init_command)

    # DB import command
    db_import_parser = db_subparsers.add_parser(
        "import",
        help="Import CV JSON files into database",
        description="Import CV JSON files from a directory into the database."
    )
    db_import_parser.add_argument(
        "--db",
        type=str,
        help="Path to database file (default: data/db/cv.db)"
    )
    db_import_parser.add_argument(
        "--input-dir", "-i",
        type=str,
        help="Input directory containing CV JSON files (default: data/cvs)"
    )
    db_import_parser.add_argument(
        "--name", "-n",
        type=str,
        help="Import only CVs matching this base name"
    )
    db_import_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing entries for each person"
    )
    db_import_parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't backup database before overwrite"
    )
    db_import_parser.set_defaults(func=db_import_command)

    # DB export command
    db_export_parser = db_subparsers.add_parser(
        "export",
        help="Export database to JSON files",
        description="Export CV data from database to JSON files."
    )
    db_export_parser.add_argument(
        "--db",
        type=str,
        help="Path to database file (default: data/db/cv.db)"
    )
    db_export_parser.add_argument(
        "--output-dir", "-o",
        type=str,
        help="Output directory for JSON files (default: data/cvs)"
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
        "--apply-tags",
        action="store_true",
        help="Rebuild type_key from database tags for entries that originally had it"
    )
    db_export_parser.add_argument(
        "--apply-tags-to-all",
        action="store_true",
        help="Add type_key to ALL entries from database tags (not just those that had it)"
    )
    db_export_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files without asking"
    )
    db_export_parser.set_defaults(func=db_export_command)

    # DB diff command
    db_diff_parser = db_subparsers.add_parser(
        "diff",
        help="Compare JSON files with database",
        description="Compare CV JSON files with their database exports."
    )
    db_diff_parser.add_argument(
        "--db",
        type=str,
        help="Path to database file (default: data/db/cv.db)"
    )
    db_diff_parser.add_argument(
        "--input-dir", "-i",
        type=str,
        help="Input directory containing CV JSON files (default: data/cvs)"
    )
    db_diff_parser.add_argument(
        "--name", "-n",
        type=str,
        help="Compare only CVs matching this base name"
    )
    db_diff_parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    db_diff_parser.set_defaults(func=db_diff_command)

    # DB list command
    db_list_parser = db_subparsers.add_parser(
        "list",
        help="List database contents",
        description="List persons or tags in the database."
    )
    db_list_parser.add_argument(
        "--db",
        type=str,
        help="Path to database file (default: data/db/cv.db)"
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

    # DB doctor command
    db_doctor_parser = db_subparsers.add_parser(
        "doctor",
        help="Check database health",
        description="Run health checks on the database and report issues."
    )
    db_doctor_parser.add_argument(
        "--db",
        type=str,
        help="Path to database file (default: data/db/cv.db)"
    )
    db_doctor_parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    db_doctor_parser.set_defaults(func=db_doctor_command)

    db_parser.set_defaults(func=lambda args: db_parser.print_help() or EXIT_SUCCESS)

    # Web command
    web_parser = subparsers.add_parser(
        "web",
        help="Web UI for tag management",
        description="Start web server for managing tags and CV entries."
    )

    web_subparsers = web_parser.add_subparsers(
        dest="web_command",
        title="web commands",
        description="Available web commands"
    )

    # Web tags command
    web_tags_parser = web_subparsers.add_parser(
        "tags",
        help="Start the Tag Manager web UI",
        description="Start local web server for managing tags on CV entries."
    )
    web_tags_parser.add_argument(
        "--db",
        type=str,
        help="Path to database file (default: data/db/cv.db)"
    )
    web_tags_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1, use 0.0.0.0 for LAN access)"
    )
    web_tags_parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to listen on (default: 5000)"
    )
    web_tags_parser.set_defaults(func=web_tags_command)

    web_parser.set_defaults(func=lambda args: web_parser.print_help() or EXIT_SUCCESS)

    # Doctor command for system health checks
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Run system health checks",
        description="Validate environment and repo configuration before builds."
    )
    doctor_parser.add_argument(
        "--templates-dir", "-t",
        type=str,
        help="Templates directory to check (default: templates)"
    )
    doctor_parser.add_argument(
        "--output-dir", "-o",
        type=str,
        help="Output directory to check (default: output)"
    )
    doctor_parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    doctor_parser.set_defaults(func=doctor_command)

    # Help command for extended help topics
    help_parser = subparsers.add_parser(
        "help",
        help="Show extended help for a topic",
        description="Display detailed help for specific topics."
    )
    help_parser.add_argument(
        "topic",
        nargs="?",
        type=str,
        help="Topic to get help on (build, ensure, languages, templates, json-schema, troubleshooting)"
    )
    help_parser.set_defaults(func=help_command)

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

    # Set up logging with quiet support
    setup_logging(verbose=args.verbose, debug=args.debug, quiet=args.quiet)

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
