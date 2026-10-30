"""
Command-line interface for CV Generator.

Provides the `cvgen` command with the following subcommands:
- build: Generate PDF CVs from JSON files
- ensure: Validate multilingual CV JSON consistency
- lint: Validate CV JSON files against the schema
- db: SQLite database operations (init, import, export, diff)
- doctor: System health checks
- profile: Manage CV profile selection
- init: Create a new CV project scaffold
- diff: Compare current vs previous TeX artifacts
- clean: Clean output directories with backup support
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
from . import __version__
from .config import Config, ConfigError, clear_current_profile, get_current_profile, list_profiles, load_config, set_current_profile
from .ensure import EXIT_ENSURE_ERROR, run_ensure
from .errors import EXIT_CONFIG_ERROR, EXIT_ERROR, EXIT_SUCCESS, EXIT_VALIDATION_ERROR, CVGeneratorError
from .generator import generate_all_cvs
from .io import discover_cv_files
from .logging_config import setup_logging
from .validate_schema import validate_cv_file
logger = logging.getLogger(__name__)

def build_command(args: argparse.Namespace) -> int:
    """
    Execute the build command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .report import BuildArtifact, BuildReport
    config = getattr(args, '_config', None)
    if config is None:
        config = Config()
    cvs_dir = Path(args.input_dir) if args.input_dir else None
    if cvs_dir is None and config.paths.cvs:
        cvs_dir = Path(config.paths.cvs)
    templates_dir = Path(args.templates_dir) if args.templates_dir else None
    if templates_dir is None and config.paths.templates:
        templates_dir = Path(config.paths.templates)
    output_dir = Path(args.output_dir) if args.output_dir else None
    if output_dir is None and config.paths.output:
        output_dir = Path(config.paths.output)
    pics_dir = Path(args.pics_dir) if hasattr(args, 'pics_dir') and args.pics_dir else None
    name_filter = args.name
    if name_filter is None:
        current = get_current_profile()
        if current:
            name_filter = current
            logger.info(f'Using current profile: {current}')
    if cvs_dir and (not cvs_dir.exists()):
        logger.error(f'Input directory not found: {cvs_dir}')
        return EXIT_CONFIG_ERROR
    if templates_dir and (not templates_dir.exists()):
        logger.error(f'Templates directory not found: {templates_dir}')
        return EXIT_CONFIG_ERROR
    if cvs_dir:
        logger.info(f'Input directory: {cvs_dir}')
    if templates_dir:
        logger.info(f'Templates directory: {templates_dir}')
    if output_dir:
        logger.info(f'Output directory: {output_dir}')
    if name_filter:
        logger.info(f'Building CV for: {name_filter}')
    if args.dry_run:
        logger.info('Dry run mode: LaTeX will not be compiled')
    if args.keep_latex:
        logger.info('Keeping LaTeX source files')
    variant = getattr(args, 'variant', None)
    if variant:
        logger.info(f'Using variant filter: {variant}')
    incremental = getattr(args, 'incremental', False)
    no_incremental = getattr(args, 'no_incremental', False)
    if no_incremental:
        incremental = False
    if incremental:
        logger.info('Incremental build enabled')
    generate_report = getattr(args, 'report', False)
    watch_mode = getattr(args, 'watch', False)
    if watch_mode:
        return _run_watch_mode(cvs_dir=cvs_dir, templates_dir=templates_dir, output_dir=output_dir, pics_dir=pics_dir, name_filter=name_filter, dry_run=args.dry_run, keep_latex=args.keep_latex, variant=variant)
    report = None
    if generate_report:
        report = BuildReport(dry_run=args.dry_run, incremental=incremental, variant=variant)
        report.start()
    try:
        results = generate_all_cvs(cvs_dir=cvs_dir, templates_dir=templates_dir, output_dir=output_dir, pics_dir=pics_dir, name_filter=name_filter, dry_run=args.dry_run, keep_latex=args.keep_latex, variant=variant, incremental=incremental, latex_timeout=getattr(args, 'latex_timeout', None))
    except CVGeneratorError as e:
        logger.error(str(e))
        if report:
            report.add_error(str(e))
            report.finish()
            _write_report(report, output_dir)
        return e.exit_code
    except Exception as e:
        logger.exception(f'Unexpected error: {e}')
        if report:
            report.add_error(f'Unexpected error: {e}')
            report.finish()
            _write_report(report, output_dir)
        return EXIT_ERROR
    if not results:
        if name_filter:
            logger.error(f"No CV files found matching '{name_filter}'")
        else:
            logger.error('No CV files found')
        return EXIT_CONFIG_ERROR
    if report:
        for result in results:
            artifact = BuildArtifact(profile=result.name, lang=result.lang, pdf_path=str(result.pdf_path) if result.pdf_path else None, tex_path=str(result.tex_path) if getattr(result, 'tex_path', None) else None, success=result.success, error=result.error, skipped=getattr(result, 'skipped', False))
            report.add_artifact(artifact)
            if result.error:
                report.add_error(f'{result.name}_{result.lang}: {result.error}')
        report.finish()
        report_paths = _write_report(report, output_dir)
        if report_paths:
            print(f"📊 Build report written to: {report_paths.get('json')}")
    failed = [r for r in results if not r.success]
    if failed:
        for result in failed:
            logger.error(f'Failed: {result.name}_{result.lang}: {result.error}')
        return EXIT_ERROR
    return EXIT_SUCCESS

def _write_report(report, output_dir: Optional[Path]) -> Optional[dict]:
    """Helper to write build report."""
    from .report import write_build_report
    try:
        return write_build_report(report, output_dir)
    except Exception as e:
        logger.error(f'Failed to write build report: {e}')
        return None

def _run_watch_mode(*, cvs_dir: Optional[Path], templates_dir: Optional[Path], output_dir: Optional[Path], pics_dir: Optional[Path], name_filter: Optional[str], dry_run: bool, keep_latex: bool, variant: Optional[str]) -> int:
    """
    Run build in watch mode, rebuilding on file changes.

    Args:
        cvs_dir: Directory containing CV JSON files.
        templates_dir: Templates directory.
        output_dir: Output directory.
        pics_dir: Profile pictures directory.
        name_filter: Name filter for CVs.
        dry_run: Dry run mode.
        keep_latex: Keep LaTeX files.
        variant: Variant filter.

    Returns:
        Exit code.
    """
    from .paths import get_default_cvs_path, get_default_templates_path
    from .watch import FileWatcher, format_change_reason
    watch_cvs_dir = cvs_dir or get_default_cvs_path()
    watch_templates_dir = templates_dir or get_default_templates_path()
    watch_paths = [watch_cvs_dir, watch_templates_dir]
    watcher = FileWatcher(watch_paths, patterns=['*.json', '*.tex'])

    def do_build() -> None:
        """Execute a build."""
        try:
            results = generate_all_cvs(cvs_dir=cvs_dir, templates_dir=templates_dir, output_dir=output_dir, pics_dir=pics_dir, name_filter=name_filter, dry_run=dry_run, keep_latex=keep_latex, variant=variant, incremental=True)
            successful = sum((1 for r in results if r.success))
            skipped = sum((1 for r in results if r.skipped))
            if skipped > 0:
                print(f'✅ Built {successful}/{len(results)} CVs ({skipped} skipped)')
            else:
                print(f'✅ Built {successful}/{len(results)} CVs')
        except Exception as e:
            logger.error(f'Build failed: {e}')
            print(f'❌ Build failed: {e}')

    def on_change(events) -> None:
        """Handle file change events."""
        reason = format_change_reason(events)
        print(f'\n🔄 Rebuilding: {reason}')
        do_build()

    def on_start() -> None:
        """Initial build when watch mode starts."""
        print('🔍 Watch mode: performing initial build...')
        do_build()
        print('\n👀 Watching for changes in:')
        print(f'   - {watch_cvs_dir}')
        print(f'   - {watch_templates_dir}')
    try:
        watcher.watch(callback=on_change, on_start=on_start)
    except KeyboardInterrupt:
        print('\n👋 Watch mode stopped')
    return EXIT_SUCCESS

def ensure_command(args: argparse.Namespace) -> int:
    """
    Execute the ensure command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 if OK, 2 if mismatches found, non-zero in strict mode).
    """
    from .ensure import write_fixed_cvs
    langs = [lang.strip() for lang in args.langs.split(',')]
    paths: Optional[Dict[str, Path]] = None
    if args.path_en or args.path_de or args.path_fa:
        paths = {}
        if args.path_en:
            paths['en'] = Path(args.path_en)
        if args.path_de:
            paths['de'] = Path(args.path_de)
        if args.path_fa:
            paths['fa'] = Path(args.path_fa)
    cvs_dir = None
    if args.dir:
        cvs_dir = Path(args.dir)
    elif args.input_dir:
        cvs_dir = Path(args.input_dir)
    lang_map = None
    if args.lang_map:
        lang_map_path = Path(args.lang_map)
        if lang_map_path.exists():
            with open(lang_map_path, 'r', encoding='utf-8') as f:
                lang_map = json.load(f)
    logger.info(f'Checking CV consistency for: {args.name}')
    logger.info(f"Languages: {', '.join(langs)}")
    if cvs_dir:
        logger.info(f'Input directory: {cvs_dir}')
    if args.strict:
        logger.info('Running in strict mode (any issue = failure)')
    if args.fix:
        fix_out = Path(args.fix_out) if args.fix_out else Path('output/fixed')
        logger.info(f'Fix mode enabled, output to: {fix_out}')
    if args.fix:
        fix_out = Path(args.fix_out) if args.fix_out else Path('output/fixed')
        try:
            report, written_files = write_fixed_cvs(name=args.name, langs=langs, fix_out=fix_out, cvs_dir=cvs_dir, paths=paths, lang_map=lang_map)
            if written_files:
                print(f'\n✅ Fixed {len(written_files)} file(s):')
                for lang, path in written_files.items():
                    print(f'   {lang}: {path}')
            elif report.is_valid:
                print('✓ No fixes needed - all files are consistent!')
            else:
                print('⚠️  No files written (possibly no fixable issues)')
        except ValueError as e:
            logger.error(str(e))
            print(f'❌ Error: {e}')
            return EXIT_ERROR
        except Exception as e:
            logger.exception(f'Error during fix operation: {e}')
            return EXIT_ERROR
    else:
        try:
            report = run_ensure(name=args.name, langs=langs, cvs_dir=cvs_dir, paths=paths, lang_map=lang_map, max_errors=args.max_errors, fail_fast=args.fail_fast)
        except Exception as e:
            logger.exception(f'Error during ensure check: {e}')
            return EXIT_ERROR
    report_format = getattr(args, 'report', None) or args.format
    if report_format == 'json':
        report_content = json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
        if args.report_out:
            report_out_path = Path(args.report_out)
            report_out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_out_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
                f.write('\n')
            logger.info(f'Report written to: {report_out_path}')
            print(f'📄 Report written to: {report_out_path}')
        else:
            print(report_content)
    else:
        verbose = getattr(args, 'verbose', False)
        print(report.format_text(verbose=verbose))
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
    cvs_dir = Path(args.input_dir) if args.input_dir else None
    files_to_validate = []
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            logger.error(f'File not found: {file_path}')
            return EXIT_CONFIG_ERROR
        files_to_validate.append(file_path)
    else:
        try:
            files_to_validate = discover_cv_files(cvs_path=cvs_dir, name_filter=args.name)
        except Exception as e:
            logger.error(f'Error discovering CV files: {e}')
            return EXIT_CONFIG_ERROR
    if not files_to_validate:
        if args.name:
            logger.error(f"No CV files found matching '{args.name}'")
        else:
            logger.error('No CV files found')
        return EXIT_CONFIG_ERROR
    logger.info(f'Validating {len(files_to_validate)} file(s)')
    if args.strict:
        logger.info('Running in strict mode')
    all_valid = True
    reports = []
    for file_path in files_to_validate:
        logger.debug(f'Validating: {file_path}')
        report = validate_cv_file(file_path, strict=args.strict)
        reports.append(report)
        if not report.is_valid:
            all_valid = False
    if args.format == 'json':
        results = {'files_validated': len(files_to_validate), 'all_valid': all_valid, 'reports': [r.to_dict() for r in reports]}
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print('\n🔍 Schema Validation Results:')
        print(f'   Files validated: {len(files_to_validate)}')
        print(f"   Mode: {('strict' if args.strict else 'default (warnings allowed)')}")
        print()
        for report in reports:
            if report.file_path:
                print(f'📄 {report.file_path.name}')
            if report.is_valid and (not report.issues):
                print('   ✅ Valid')
            else:
                status = '❌ Invalid' if not report.is_valid else '⚠️ Warnings'
                print(f'   {status} ({report.error_count} errors, {report.warning_count} warnings)')
                for issue in report.issues:
                    print(f'      {issue}')
            print()
    if all_valid:
        return EXIT_SUCCESS
    else:
        return EXIT_VALIDATION_ERROR

def assets_check_command(args: argparse.Namespace) -> int:
    """
    Execute the assets check command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .assets import check_assets
    from .io import discover_cv_files, load_cv_json, parse_cv_filename
    cvs_dir = Path(args.input_dir) if args.input_dir else None
    try:
        cv_files = discover_cv_files(cvs_path=cvs_dir, name_filter=args.name)
    except Exception as e:
        logger.error(f'Error discovering CV files: {e}')
        print(f'❌ Error: {e}')
        return EXIT_CONFIG_ERROR
    if not cv_files:
        if args.name:
            print(f"❌ No CV files found matching '{args.name}'")
        else:
            print('❌ No CV files found')
        return EXIT_CONFIG_ERROR
    logger.info(f'Checking assets in {len(cv_files)} CV file(s)')
    all_valid = True
    reports = []
    for cv_file in cv_files:
        profile_name, lang = parse_cv_filename(cv_file.name)
        try:
            cv_data = load_cv_json(cv_file)
        except Exception as e:
            logger.error(f'Error loading {cv_file.name}: {e}')
            print(f'❌ Error loading {cv_file.name}: {e}')
            continue
        report = check_assets(cv_data, profile=profile_name, lang=lang)
        reports.append(report)
        if not report.is_valid:
            all_valid = False
    if args.format == 'json':
        results = {'files_checked': len(cv_files), 'all_valid': all_valid, 'reports': [r.to_dict() for r in reports]}
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print('\n🔍 Asset Validation Results:')
        print(f'   Files checked: {len(cv_files)}')
        print()
        for report in reports:
            print(report.format_text(verbose=args.verbose))
            print()
    if all_valid:
        return EXIT_SUCCESS
    else:
        return EXIT_VALIDATION_ERROR

def assets_optimize_command(args: argparse.Namespace) -> int:
    """
    Execute the assets optimize command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .assets import optimize_assets
    from .io import discover_cv_files, load_cv_json
    output_dir = Path(args.out)
    cvs_dir = Path(args.input_dir) if args.input_dir else None
    try:
        cv_files = discover_cv_files(cvs_path=cvs_dir, name_filter=args.name)
    except Exception as e:
        logger.error(f'Error discovering CV files: {e}')
        print(f'❌ Error: {e}')
        return EXIT_CONFIG_ERROR
    if not cv_files:
        if args.name:
            print(f"❌ No CV files found matching '{args.name}'")
        else:
            print('❌ No CV files found')
        return EXIT_CONFIG_ERROR
    logger.info(f'Optimizing assets from {len(cv_files)} CV file(s)')
    total_results = {'processed': 0, 'optimized': 0, 'copied': 0, 'skipped': 0, 'errors': []}
    for cv_file in cv_files:
        try:
            cv_data = load_cv_json(cv_file)
        except Exception as e:
            logger.error(f'Error loading {cv_file.name}: {e}')
            continue
        try:
            results = optimize_assets(cv_data=cv_data, output_dir=output_dir, max_width=args.max_width, max_height=args.max_height, quality=args.quality)
            total_results['processed'] += results['processed']
            total_results['optimized'] += results['optimized']
            total_results['copied'] += results['copied']
            total_results['skipped'] += results['skipped']
            total_results['errors'].extend(results['errors'])
        except ValueError as e:
            print(f'❌ Error: {e}')
            return EXIT_CONFIG_ERROR
        except Exception as e:
            logger.error(f'Error optimizing assets: {e}')
            total_results['errors'].append(str(e))
    if args.format == 'json':
        print(json.dumps(total_results, indent=2, ensure_ascii=False))
    else:
        print('\n📦 Asset Optimization Results:')
        print(f'   Output directory: {output_dir}')
        print(f"   Total processed: {total_results['processed']}")
        print(f"   Optimized: {total_results['optimized']}")
        print(f"   Copied (unchanged): {total_results['copied']}")
        print(f"   Skipped: {total_results['skipped']}")
        if total_results['errors']:
            print(f"\n⚠️  Errors ({len(total_results['errors'])}):")
            for error in total_results['errors'][:5]:
                print(f'   • {error}')
            if len(total_results['errors']) > 5:
                print(f"   ... and {len(total_results['errors']) - 5} more")
    if total_results['errors']:
        return EXIT_ERROR
    return EXIT_SUCCESS

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
        logger.info(f'Database initialized: {result_path}')
        print(f'✅ Database initialized: {result_path}')
        return EXIT_SUCCESS
    except Exception as e:
        logger.error(f'Error initializing database: {e}')
        print(f'❌ Error: {e}')
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
        results = import_all_cvs(input_dir=input_dir, db_path=db_path, name_filter=args.name, overwrite=args.overwrite, backup=not args.no_backup)
        print('\n📥 Import Results:')
        print(f"   Files processed: {results['files_processed']}")
        print(f"   Total entries: {results['total_entries']}")
        for file_result in results.get('files', []):
            if file_result.get('success'):
                print(f"   ✅ {file_result['file']}: {file_result.get('entries_imported', 0)} entries")
            else:
                print(f"   ❌ {file_result['file']}: {file_result.get('error', 'Unknown error')}")
        return EXIT_SUCCESS
    except Exception as e:
        logger.error(f'Error importing CVs: {e}')
        print(f'❌ Error: {e}')
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
    pretty = args.format != 'min'
    try:
        results = export_all_cvs(output_dir=output_dir, db_path=db_path, name_filter=args.name, pretty=pretty, apply_tags=args.apply_tags, apply_tags_to_all=args.apply_tags_to_all, force=args.force)
        print('\n📤 Export Results:')
        print(f"   Files exported: {results['files_exported']}")
        for file_result in results.get('files', []):
            if file_result.get('success'):
                print(f"   ✅ {file_result['file']}")
            else:
                print(f"   ❌ {file_result['slug']}: {file_result.get('error', 'Unknown error')}")
        return EXIT_SUCCESS
    except Exception as e:
        logger.error(f'Error exporting CVs: {e}')
        print(f'❌ Error: {e}')
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
        results = diff_all_cvs(input_dir=input_dir, db_path=db_path, name_filter=args.name)
        if args.format == 'json':
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print('\n🔍 Diff Results:')
            print(f"   Files compared: {results['files_compared']}")
            print(f"   Matches: {results['matches']}")
            print(f"   Mismatches: {results['mismatches']}")
            for file_result in results.get('files', []):
                if file_result.get('match'):
                    print(f"   ✅ {file_result['file']}: Match")
                elif file_result.get('error'):
                    print(f"   ⚠️  {file_result['file']}: {file_result['error']}")
                else:
                    print(f"   ❌ {file_result['file']}: {file_result['difference_count']} differences")
                    for diff in file_result.get('differences', [])[:5]:
                        print(f"      - {diff['path']}: {diff['type']}")
                    if len(file_result.get('differences', [])) > 5:
                        print(f"      ... and {len(file_result['differences']) - 5} more")
        if results['mismatches'] > 0:
            return EXIT_ENSURE_ERROR
        return EXIT_SUCCESS
    except Exception as e:
        logger.error(f'Error comparing CVs: {e}')
        print(f'❌ Error: {e}')
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
        if args.what == 'persons':
            items = list_persons(db_path)
            if args.format == 'json':
                print(json.dumps(items, indent=2, ensure_ascii=False))
            else:
                print(f'\n👥 Persons in database: {len(items)}')
                for item in items:
                    print(f"   • {item['slug']}: {item['entry_count']} entries")
                    if item.get('display_name'):
                        print(f"     Name: {item['display_name']}")
        else:
            items = list_tags(db_path)
            if args.format == 'json':
                print(json.dumps(items, indent=2, ensure_ascii=False))
            else:
                print(f'\n🏷️  Tags in database: {len(items)}')
                for item in items:
                    print(f"   • {item['name']}: used {item['usage_count']} times")
        return EXIT_SUCCESS
    except Exception as e:
        logger.error(f'Error listing database contents: {e}')
        print(f'❌ Error: {e}')
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
        if args.format == 'json':
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print(f"\n🏥 Database Health Check: {results['database']}")
            print(f"   Status: {('✅ Healthy' if results['healthy'] else '❌ Issues Found')}")
            print()
            print('📊 Statistics:')
            print(f"   Persons: {results['stats'].get('persons', 0)}")
            print(f"   Entries: {results['stats'].get('entries', 0)}")
            print(f"   Tags: {results['stats'].get('tags', 0)}")
            print(f"   Tag Assignments: {results['stats'].get('tag_assignments', 0)}")
            if results['issues']:
                print()
                print(f"⚠️  Issues ({len(results['issues'])}):")
                for issue in results['issues']:
                    print(f'   • {issue}')
            print()
            print('🔍 Checks:')
            checks = results.get('checks', {})
            if 'schema_version' in checks:
                sv = checks['schema_version']
                status = '✅' if sv.get('ok') else '❌'
                print(f"   {status} Schema version: v{sv.get('current', '?')} (expected v{sv.get('expected', '?')})")
            if 'orphaned_entries' in checks:
                oe = checks['orphaned_entries']
                status = '✅' if oe.get('ok') else '❌'
                print(f"   {status} Orphaned entries: {oe.get('count', 0)}")
            if 'orphaned_tags' in checks:
                ot = checks['orphaned_tags']
                print(f"   ℹ️  Unused tags: {ot.get('count', 0)}")
            if 'duplicate_tags' in checks:
                dt = checks['duplicate_tags']
                status = '✅' if dt.get('ok') else '❌'
                print(f"   {status} Duplicate tags: {dt.get('count', 0)}")
            if 'missing_identity_keys' in checks:
                mi = checks['missing_identity_keys']
                print(f"   ℹ️  Missing identity keys: {mi.get('count', 0)}")
            if 'invalid_json' in checks:
                ij = checks['invalid_json']
                status = '✅' if ij.get('ok') else '❌'
                print(f"   {status} Invalid JSON: {ij.get('count', 0)}")
        return EXIT_SUCCESS if results['healthy'] else EXIT_ENSURE_ERROR
    except Exception as e:
        logger.error(f'Error running health check: {e}')
        print(f'❌ Error: {e}')
        return EXIT_ERROR

def db_integrity_command(args: argparse.Namespace) -> int:
    """
    Execute the db integrity command (reference integrity check).

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .integrity import run_integrity_check
    db_path = Path(args.db) if args.db else None
    try:
        report = run_integrity_check(db_path)
        if args.format == 'json':
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            verbose = getattr(args, 'verbose', False)
            print(report.format_text(verbose=verbose))
        return EXIT_SUCCESS if report.is_healthy else EXIT_ENSURE_ERROR
    except Exception as e:
        logger.error(f'Error running integrity check: {e}')
        print(f'❌ Error: {e}')
        return EXIT_ERROR

def db_verify_erd_command(args: argparse.Namespace) -> int:
    """
    Execute the db verify-erd command (ERD schema verification).

    Verifies that the database schema matches the ERD specification in docs/erd.txt.
    Reports table-by-table status and any mismatches.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .db import get_db_path
    from .erd_parser import verify_schema_against_erd
    db_path = Path(args.db) if args.db else get_db_path()
    erd_path = Path(args.erd) if args.erd else None
    try:
        results = verify_schema_against_erd(db_path, erd_path)
        if args.format == 'json':
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            _print_erd_verification_report(results)
        return EXIT_SUCCESS if results['valid'] else EXIT_ENSURE_ERROR
    except Exception as e:
        logger.error(f'Error verifying ERD schema: {e}')
        print(f'❌ Error: {e}')
        return EXIT_ERROR

def _print_erd_verification_report(results: Dict) -> None:
    """Print ERD verification report in text format."""
    lines = ['=' * 80, 'ERD Schema Verification Report', '=' * 80, f"ERD File: {results['erd_path']}", f"Database: {results['db_path']}", '', f"Overall Status: {('✓ VALID' if results['valid'] else '✗ INVALID')}", f"Tables Checked: {results['tables_checked']}", f"Tables Matched: {results['tables_matched']}", f"Tables Mismatched: {results['tables_mismatched']}", f"Tables Missing: {len(results['tables_missing'])}", '', '-' * 80, 'Table-by-Table Results:', '-' * 80]
    for table_name, detail in sorted(results.get('table_details', {}).items()):
        status = detail['status']
        status_icon = '✓' if status == 'match' else '✗'
        lines.append(f'\n{status_icon} {table_name}: {status.upper()}')
        if detail['columns']['expected']:
            lines.append(f"   Columns: {len(detail['columns']['found'])}/{len(detail['columns']['expected'])}")
        if detail['columns']['missing']:
            lines.append(f"   Missing columns: {', '.join(detail['columns']['missing'])}")
        if detail['foreign_keys']['missing']:
            for fk in detail['foreign_keys']['missing']:
                lines.append(f"   Missing FK: {fk['from']} -> {fk['table']}.{fk['to']}")
        if detail['unique_constraints']['missing']:
            for uc in detail['unique_constraints']['missing']:
                lines.append(f"   Missing unique: ({', '.join(uc)})")
    if results['tables_missing']:
        lines.append('\n' + '-' * 80)
        lines.append('Missing Tables:')
        lines.append('-' * 80)
        for table in results['tables_missing']:
            lines.append(f'  ✗ {table}')
    if results['issues']:
        lines.append('\n' + '-' * 80)
        lines.append('All Issues:')
        lines.append('-' * 80)
        for issue in results['issues']:
            lines.append(f'  • {issue}')
    lines.append('\n' + '=' * 80)
    print('\n'.join(lines))
    if results['valid']:
        print()
        print('✅ Database schema matches ERD specification 100%')
    else:
        print()
        print('❌ Database schema does NOT match ERD specification')
        print(f"   Tables missing: {len(results['tables_missing'])}")
        print(f"   Tables with issues: {results['tables_mismatched']}")

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
        report = run_checks(template_dir=template_dir, output_dir=output_dir, check_db=True)
        if args.format == 'json':
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(report.format_text(verbose=args.verbose))
        return EXIT_SUCCESS if report.is_healthy else EXIT_ENSURE_ERROR
    except Exception as e:
        logger.error(f'Error running doctor: {e}')
        print(f'❌ Error: {e}')
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
    allow_unsafe_bind = getattr(args, 'i_know_what_im_doing', False)
    try:
        run_server(host=args.host, port=args.port, debug=args.debug if hasattr(args, 'debug') else False, db_path=db_path, allow_unsafe_bind=allow_unsafe_bind)
        return EXIT_SUCCESS
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else EXIT_ERROR
    except Exception as e:
        logger.error(f'Error starting web server: {e}')
        print(f'❌ Error: {e}')
        return EXIT_ERROR

def profile_list_command(args: argparse.Namespace) -> int:
    """
    Execute the profile list command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    cvs_dir = Path(args.input_dir) if args.input_dir else None
    try:
        profiles = list_profiles(cvs_dir)
        current = get_current_profile()
        if args.format == 'json':
            result = {'profiles': profiles, 'current': current}
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            if not profiles:
                print('No profiles found.')
                return EXIT_SUCCESS
            print('\n📋 Available Profiles:')
            for profile in profiles:
                if profile == current:
                    print(f'   • {profile} (current)')
                else:
                    print(f'   • {profile}')
            print()
            if current:
                print(f'Current profile: {current}')
                print("Use 'cvgen profile use <name>' to switch profiles.")
            else:
                print('No profile selected.')
                print("Use 'cvgen profile use <name>' to select a profile.")
        return EXIT_SUCCESS
    except Exception as e:
        logger.error(f'Error listing profiles: {e}')
        print(f'❌ Error: {e}')
        return EXIT_ERROR

def profile_use_command(args: argparse.Namespace) -> int:
    """
    Execute the profile use command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    profile_name = args.profile_name
    cvs_dir = Path(args.input_dir) if args.input_dir else None
    try:
        profiles = list_profiles(cvs_dir)
        if profile_name not in profiles:
            print(f"❌ Profile '{profile_name}' not found.")
            print(f"Available profiles: {', '.join(profiles)}")
            return EXIT_CONFIG_ERROR
        set_current_profile(profile_name)
        print(f'✅ Set current profile to: {profile_name}')
        print("Now 'cvgen build' will use this profile by default.")
        return EXIT_SUCCESS
    except Exception as e:
        logger.error(f'Error setting profile: {e}')
        print(f'❌ Error: {e}')
        return EXIT_ERROR

def profile_clear_command(args: argparse.Namespace) -> int:
    """
    Execute the profile clear command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    try:
        current = get_current_profile()
        if current:
            clear_current_profile()
            print(f'✅ Cleared current profile (was: {current})')
        else:
            print('No profile was set.')
        return EXIT_SUCCESS
    except Exception as e:
        logger.error(f'Error clearing profile: {e}')
        print(f'❌ Error: {e}')
        return EXIT_ERROR

def export_command(args: argparse.Namespace) -> int:
    """
    Execute the export command to generate CV in HTML/Markdown format.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .exporters import get_exporter, list_exporters
    from .io import discover_cv_files, load_cv_json, parse_cv_filename
    exporter = get_exporter(args.format)
    if exporter is None:
        available = ', '.join(list_exporters())
        logger.error(f'Unknown export format: {args.format}')
        print(f"❌ Unknown export format: '{args.format}'")
        print(f'Available formats: {available}')
        return EXIT_CONFIG_ERROR
    cvs_dir = Path(args.input_dir) if args.input_dir else None
    output_dir = Path(args.output_dir) if args.output_dir else None
    if output_dir is None:
        from .paths import get_default_output_path
        output_dir = get_default_output_path()
    try:
        cv_files = discover_cv_files(cvs_path=cvs_dir, name_filter=args.name)
    except Exception as e:
        logger.error(f'Error discovering CV files: {e}')
        print(f'❌ Error: {e}')
        return EXIT_CONFIG_ERROR
    if not cv_files:
        if args.name:
            logger.error(f"No CV files found matching '{args.name}'")
            print(f"❌ No CV files found matching '{args.name}'")
        else:
            logger.error('No CV files found')
            print('❌ No CV files found')
        return EXIT_CONFIG_ERROR
    if args.lang:
        filtered_files = []
        for cv_file in cv_files:
            _, file_lang = parse_cv_filename(cv_file.name)
            if file_lang == args.lang:
                filtered_files.append(cv_file)
        cv_files = filtered_files
        if not cv_files:
            print(f"❌ No CV files found for language '{args.lang}'")
            return EXIT_CONFIG_ERROR
    logger.info(f'Exporting {len(cv_files)} CV file(s) to {args.format.upper()}')
    results = []
    for cv_file in cv_files:
        profile_name, lang = parse_cv_filename(cv_file.name)
        try:
            cv_data = load_cv_json(cv_file)
        except Exception as e:
            logger.error(f'Error loading {cv_file.name}: {e}')
            print(f'❌ Error loading {cv_file.name}: {e}')
            continue
        result = exporter.export(cv_data=cv_data, output_dir=output_dir, profile_name=profile_name, lang=lang)
        results.append(result)
        if result.success:
            print(f'✅ Exported: {result.output_path}')
        else:
            print(f'❌ Failed: {profile_name}_{lang}: {result.error}')
    successful = sum((1 for r in results if r.success))
    print(f'\n📊 Exported {successful}/{len(results)} CV(s) successfully')
    if successful == len(results):
        return EXIT_SUCCESS
    elif successful > 0:
        return EXIT_ERROR
    else:
        return EXIT_ERROR

def init_command(args: argparse.Namespace) -> int:
    """
    Execute the init command to create a new CV project.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .scaffold import get_next_steps, scaffold_project
    dest_path = Path(args.path).resolve()
    profile_name = args.profile or 'mycv'
    lang = args.lang or 'en'
    force = getattr(args, 'force', False)
    logger.info(f'Creating new CV project at: {dest_path}')
    logger.info(f'Profile: {profile_name}, Language: {lang}')
    result = scaffold_project(dest_path=dest_path, profile_name=profile_name, lang=lang, force=force)
    if not result.success:
        print(f'❌ Error: {result.error}')
        return EXIT_CONFIG_ERROR
    print(f'\n✅ Created new CV project at: {dest_path}')
    print('\n📁 Files created:')
    for file_path in result.files_created:
        rel_path = file_path.relative_to(dest_path)
        print(f'   • {rel_path}')
    print('\n🚀 Next steps:')
    steps = get_next_steps(dest_path, profile_name, lang)
    for i, step in enumerate(steps, 1):
        print(f'   {i}. {step}')
    print()
    return EXIT_SUCCESS

def diff_command(args: argparse.Namespace) -> int:
    """
    Execute the diff command to compare current vs previous TeX artifacts.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .tex_diff import diff_command_handler
    output_dir = Path(args.output_dir) if args.output_dir else None
    report, output = diff_command_handler(profile=args.name, lang=args.lang, output_root=output_dir, format=args.format)
    print(output)
    if report.has_previous_build and (report.files_changed > 0 or report.files_added > 0 or report.files_removed > 0):
        return EXIT_ENSURE_ERROR
    return EXIT_SUCCESS

def clean_command(args: argparse.Namespace) -> int:
    """
    Execute the clean command to remove output directories.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    from .cleanup import clean_output_directory, list_backups
    output_dir = Path(args.output_dir) if args.output_dir else None
    backup = getattr(args, 'backup', True)
    yes = getattr(args, 'yes', False)
    verbose = getattr(args, 'verbose', False)
    output_types = None
    if args.type:
        output_types = [t.strip() for t in args.type.split(',')]
    if getattr(args, 'list_backups', False):
        backups = list_backups(output_dir)
        if not backups:
            print('No backups found.')
        else:
            print(f'\n📦 Backups ({len(backups)}):')
            for backup_path in backups:
                size_mb = backup_path.stat().st_size / (1024 * 1024)
                print(f'   • {backup_path.name} ({size_mb:.2f} MB)')
        return EXIT_SUCCESS
    results = clean_output_directory(output_types=output_types, output_root=output_dir, backup=backup, yes=yes, verbose=verbose)
    if results['cleaned']:
        print(f"\n🗑️ Cleaned {len(results['cleaned'])} directory(ies)")
        for path in results['cleaned']:
            print(f'   • {path}')
    if results['backups']:
        print(f"\n📦 Created {len(results['backups'])} backup(s)")
        for path in results['backups']:
            print(f'   • {path}')
    if results['skipped']:
        print(f"\nℹ️ Skipped {len(results['skipped'])} directory(ies)")
    if results['failed']:
        print(f"\n❌ Failed to clean {len(results['failed'])} directory(ies)")
        for item in results['failed']:
            print(f"   • {item['path']}: {item['error']}")
        return EXIT_ERROR
    return EXIT_SUCCESS
HELP_TOPICS = {'build': "\ncvgen build — Generate PDF CVs from JSON files\n\nSYNOPSIS\n    cvgen build [OPTIONS]\n\nDESCRIPTION\n    The build command renders CV JSON files to LaTeX using Jinja2 templates,\n    then compiles them to PDF using XeLaTeX.\n\n    By default, all CV files in data/cvs/ are processed. Use --name to filter\n    to a specific person.\n\nOPTIONS\n    --name, -n NAME     Build only CVs matching this base name (e.g., 'example')\n    --input-dir, -i     Directory containing CV JSON files (default: data/cvs)\n    --output-dir, -o    Output directory root (default: output)\n    --templates-dir, -t Templates directory (default: templates)\n    --keep-latex, -k    Keep LaTeX sources in output/latex/ for debugging\n    --dry-run, -d       Render LaTeX but skip PDF compilation\n    --incremental       Skip rebuilding CVs whose inputs haven't changed\n    --no-incremental    Force full rebuild, ignoring cache\n    --watch, -w         Watch for file changes and rebuild automatically\n\nCLEANUP OPTIONS (Windows)\n    --no-cleanup        Skip cleanup of intermediate files\n    --force-cleanup     Force cleanup even if files are locked (may fail)\n    --cleanup-timeout N Maximum time to wait for file locks (default: 120s)\n\nINCREMENTAL BUILDS\n    Use --incremental to enable incremental builds. This hashes the CV JSON,\n    template files, and assets. If nothing has changed, the build is skipped.\n\n    Cache is stored in output/.cache/ and is never written to data/.\n\nWATCH MODE\n    Use --watch to continuously watch for changes and rebuild automatically.\n    This is useful during development when iterating on templates or CV data.\n\n    Watch mode uses incremental builds by default for efficiency.\n\nEXAMPLES\n    # Generate all CVs\n    cvgen build\n\n    # Generate only example's CV\n    cvgen build --name example\n\n    # Dry run with verbose output\n    cvgen -v build --dry-run\n\n    # Keep LaTeX files for debugging\n    cvgen build --keep-latex\n\n    # Incremental build (skip unchanged)\n    cvgen build --incremental\n\n    # Watch mode for development\n    cvgen build --watch\n\n    # Skip cleanup (Windows file lock issues)\n    cvgen build --no-cleanup\n\n    # Force cleanup with extended timeout\n    cvgen build --force-cleanup --cleanup-timeout 300\n\nOUTPUT STRUCTURE\n    output/\n      pdf/<name>/<lang>/<name>_<lang>.pdf\n      latex/<name>/<lang>/main.tex        (with --keep-latex)\n      latex/<name>/<lang>/sections/*.tex  (with --keep-latex)\n      .cache/<name>_<lang>.json           (incremental build cache)\n", 'export': "\ncvgen export — Export CVs to HTML or Markdown format\n\nSYNOPSIS\n    cvgen export [OPTIONS]\n\nDESCRIPTION\n    The export command generates CV output in alternative formats such as\n    HTML (for web preview) or Markdown (for documentation or plain text).\n\n    This is a read-only operation that does not modify source CV files.\n\nOPTIONS\n    --name, -n NAME     Export only CVs matching this base name (e.g., 'example')\n    --lang, -l LANG     Export only CVs with this language code (e.g., 'en')\n    --format, -f FMT    Output format: html or md (default: html)\n    --input-dir, -i     Directory containing CV JSON files (default: data/cvs)\n    --output-dir, -o    Output directory root (default: output)\n\nEXAMPLES\n    # Export all CVs to HTML\n    cvgen export\n\n    # Export example's English CV to Markdown\n    cvgen export --name example --lang en --format md\n\n    # Export to a specific output directory\n    cvgen export --output-dir ./exports\n\nOUTPUT STRUCTURE\n    output/\n      html/<name>/<lang>/cv.html\n      md/<name>/<lang>/cv.md\n", 'ensure': "\ncvgen ensure — Validate multilingual CV JSON consistency\n\nSYNOPSIS\n    cvgen ensure --name NAME [OPTIONS]\n\nDESCRIPTION\n    The ensure command checks that multilingual CV JSON files have consistent\n    structure across languages. It compares the English version (canonical)\n    with German and Persian versions.\n\n    Use this to verify that:\n    - All languages have the same sections and fields\n    - No keys are missing or extra in any language\n    - Skill headings are properly translated\n\nMODES\n    --strict            Fail with non-zero exit code on any mismatch (CI mode)\n    --fix               Generate corrected copies with missing keys filled in\n    --report json       Output machine-readable JSON report\n\nOPTIONS\n    --name, -n NAME     Name of the person (required)\n    --langs, -l LANGS   Comma-separated language codes (default: en,de,fa)\n    --format, -f FMT    Output format: text or json (default: text)\n    --input-dir, -i     Directory containing CV JSON files\n    --dir, -D           Directory containing CV files directly\n    --lang-map          Path to language mapping file (lang.json)\n    --fail-fast         Stop at first batch of errors\n    --max-errors N      Maximum errors before stopping\n    --strict            Fail on ANY mismatch (for CI pipelines)\n    --fix               Generate corrected copies in --fix-out directory\n    --fix-out DIR       Output directory for fixed files (default: output/fixed)\n    --report FMT        Report format: text or json\n    --report-out FILE   Write JSON report to FILE (e.g., output/reports/ensure.json)\n\nSAFETY\n    The data/ directory is LOCKED. The --fix option can ONLY write to output/\n    or other non-data directories. Attempting to use --fix-out with a path\n    under data/ will result in an error.\n\nEXAMPLES\n    # Check example's CV consistency across all languages\n    cvgen ensure --name example\n\n    # Check only English and German\n    cvgen ensure --name example --langs en,de\n\n    # Output as JSON for programmatic use\n    cvgen ensure --name example --format json\n\n    # Strict mode for CI (exit non-zero on any issue)\n    cvgen ensure --name example --strict\n\n    # Generate fixed copies (writes to output/fixed/)\n    cvgen ensure --name example --fix\n\n    # Generate fixed copies to a custom directory\n    cvgen ensure --name example --fix --fix-out output/my-fixes/\n\n    # Generate JSON report to file for CI\n    cvgen ensure --name example --report json --report-out output/reports/ensure.json\n\nEXIT CODES\n    0  All languages are consistent\n    2  Mismatches found (always in --strict mode, also in normal mode)\n", 'lint': "\ncvgen lint — Validate CV JSON files against schema\n\nSYNOPSIS\n    cvgen lint [OPTIONS]\n\nDESCRIPTION\n    The lint command validates CV JSON files against the schema to detect\n    structural issues before rendering. This helps catch errors like:\n\n    - Missing required fields (e.g., 'basics')\n    - Wrong types (e.g., string instead of array)\n    - Invalid field values\n\nOPTIONS\n    --name, -n NAME     Validate only CVs matching this base name\n    --file, -f FILE     Path to a specific CV JSON file to validate\n    --input-dir, -i     Directory containing CV JSON files (default: data/cvs)\n    --strict            Treat all issues as errors (fail on any issue)\n    --format            Output format: text or json (default: text)\n\nEXAMPLES\n    # Validate all CV files\n    cvgen lint\n\n    # Validate only example's CVs\n    cvgen lint --name example\n\n    # Validate a specific file\n    cvgen lint --file data/cvs/example.json\n\n    # Strict mode - fail on any schema issue\n    cvgen lint --strict\n\nEXIT CODES\n    0  All files are valid\n    5  Validation errors found (in strict mode or for critical errors)\n", 'languages': '\ncvgen languages — Language support and translation\n\nDESCRIPTION\n    CV Generator supports multilingual CVs with the following languages:\n\n    - en: English (canonical/reference)\n    - de: German\n    - fa: Persian (with RTL support)\n\nFILE NAMING\n    Multilingual CV files follow these naming patterns:\n\n    1. Preferred (i18n directory):\n       data/cvs/i18n/<name>/cv.en.json\n       data/cvs/i18n/<name>/cv.de.json\n       data/cvs/i18n/<name>/cv.fa.json\n\n    2. Alternative (flat structure):\n       data/cvs/<name>.en.json\n       data/cvs/<name>.de.json\n       data/cvs/<name>_en.json\n       data/cvs/<name>_de.json\n\nTRANSLATION MAPPING\n    Skill headings and categories can be translated using a lang.json file:\n\n    {\n      "Technical Skills": {\n        "de": "Technische Fähigkeiten",\n        "fa": "مهارت\u200cهای فنی"\n      },\n      "Soft Skills": {\n        "de": "Soft Skills",\n        "fa": "مهارت\u200cهای نرم"\n      }\n    }\n\nRTL SUPPORT\n    Persian (fa) CVs are automatically rendered with RTL (right-to-left)\n    text direction. The IS_RTL template variable is set to True for RTL\n    languages.\n\nVALIDATING TRANSLATIONS\n    Use \'cvgen ensure\' to verify consistency across language versions.\n', 'templates': '\ncvgen templates — Template customization\n\nDESCRIPTION\n    CV Generator uses Jinja2 templates with LaTeX to render CVs.\n    Templates are stored in the templates/ directory.\n\nTEMPLATE FILES\n    layout.tex       Main document structure (document class, header, footer)\n    header.tex       Personal info and social links\n    education.tex    Education history\n    experience.tex   Work experience\n    skills.tex       Technical and soft skills\n    language.tex     Language proficiencies\n    projects.tex     Projects and contributions\n    certificates.tex Certifications and awards\n    publications.tex Academic publications\n    references.tex   Professional references\n\nJINJA2 SYNTAX\n    Templates use custom delimiters to avoid LaTeX conflicts:\n\n    Blocks:    <BLOCK> ... </BLOCK>\n    Variables: <VAR> ... </VAR>\n    Comments:  /*/*/* ... */*/*/\n\n    Example:\n        <VAR> basics[0]["fname"] | latex_escape </VAR>\n        <BLOCK> if education|length > 0 </BLOCK>\n          ... education section ...\n        <BLOCK> endif </BLOCK>\n\nAVAILABLE FILTERS\n    latex_escape    Escape LaTeX special characters (#, %, _, etc.)\n    file_exists     Check if a file path exists\n    debug           Print value to console during rendering\n    find_pic        Check if profile picture exists\n    get_pic         Get profile picture path\n\nADDING A NEW SECTION\n    1. Create templates/newsection.tex\n    2. Add to layout.tex: <VAR> newsection_section | default(\'\') </VAR>\n    3. Add corresponding data to your CV JSON\n', 'json-schema': '\ncvgen json-schema — CV JSON data format\n\nDESCRIPTION\n    CV data is stored as JSON files loosely based on JSON Resume format.\n    See data/cvs/*.json for examples.\n\nTOP-LEVEL SECTIONS\n    basics      Personal info (name, email, phone, location)\n    profiles    Social links (GitHub, LinkedIn, Google Scholar)\n    education   Education history\n    experiences Work experience\n    skills      Technical and soft skills\n    languages   Language proficiencies\n    projects    Projects and contributions\n    publications Academic publications\n    workshop_and_certifications  Certifications and training\n    references  Professional references\n\nBASICS EXAMPLE\n    {\n      "basics": [{\n        "fname": "Jane",\n        "lname": "Doe",\n        "label": ["Software Engineer", "ML Researcher"],\n        "email": "jane@example.com",\n        "phone": {"formatted": "+1 555-0100"},\n        "location": [{\n          "city": "San Francisco",\n          "region": "CA",\n          "country": "USA"\n        }]\n      }]\n    }\n\nSKILLS STRUCTURE\n    {\n      "skills": {\n        "Technical Skills": {\n          "Programming": [\n            {"short_name": "Python", "long_name": "Python 3.x"},\n            {"short_name": "JavaScript"}\n          ],\n          "Frameworks": [\n            {"short_name": "React"},\n            {"short_name": "Django"}\n          ]\n        },\n        "Soft Skills": {\n          "Communication": [\n            {"short_name": "Technical Writing"}\n          ]\n        }\n      }\n    }\n\nVALIDATION\n    Use \'cvgen ensure\' to validate consistency across language versions.\n', 'troubleshooting': '\ncvgen troubleshooting — Common issues and solutions\n\nXELATEX NOT FOUND\n    Symptom: \'xelatex\' is not recognized as a command\n\n    Solution:\n    1. Install TeX Live or MiKTeX\n    2. Add xelatex to your PATH\n    3. Verify: xelatex --version\n\nLATEX COMPILATION ERRORS\n    Symptom: PDF not produced, LaTeX log shows errors\n\n    Common causes:\n    - Unescaped special characters in JSON (#, %, _, &, $)\n    - Missing fields referenced in templates\n\n    Solutions:\n    - Use | latex_escape filter in templates\n    - Ensure all required keys exist in JSON\n    - Run with --keep-latex to inspect generated .tex files\n\nMISSING FONTS\n    Symptom: Font warnings or substitutions in PDF\n\n    Solution:\n    - Install fonts used by Awesome-CV (Roboto, Source Sans Pro)\n    - Or modify templates to use available fonts\n\nWINDOWS FILE LOCKS\n    Symptom: "Access is denied" when cleaning up\n\n    Solution:\n    - Close files in editors that lock them\n    - Pause OneDrive/antivirus sync temporarily\n    - The generator has retry logic for file locks\n\nTEMPLATE ERRORS\n    Symptom: Jinja TemplateError with file name\n\n    Solution:\n    - Check the referenced template file\n    - Verify JSON data matches template expectations\n    - Use | debug filter to inspect values\n\nPROFILE PICTURE NOT SHOWING\n    Symptom: CV generates without photo\n\n    Solution:\n    - Place photo at data/pics/<name>.jpg\n    - Name must match CV file base name\n    - Supported format: JPG\n', 'doctor': '\ncvgen doctor — System health checks\n\nSYNOPSIS\n    cvgen doctor [OPTIONS]\n\nDESCRIPTION\n    The doctor command validates the environment and repo configuration\n    before users attempt builds. It performs read-only checks to identify\n    potential issues.\n\n    Use this to verify that:\n    - Python version meets requirements\n    - Required dependencies are installed\n    - LaTeX engine (xelatex) is available\n    - Templates are valid\n    - Output directory is writable\n    - Database is healthy (if exists)\n\nOPTIONS\n    --templates-dir, -t Templates directory to check (default: templates)\n    --output-dir, -o    Output directory to check (default: output)\n    --format, -f        Output format: text or json (default: text)\n\nEXAMPLES\n    # Run all health checks\n    cvgen doctor\n\n    # Output as JSON for CI integration\n    cvgen doctor --format json\n\n    # Verbose output with fix hints for all checks\n    cvgen -v doctor\n\nEXIT CODES\n    0  All checks passed (healthy)\n    2  One or more checks failed (unhealthy)\n', 'assets': '\ncvgen assets — Asset validation and optimization\n\nSYNOPSIS\n    cvgen assets check [OPTIONS]\n    cvgen assets optimize --out <dir> [OPTIONS]\n\nDESCRIPTION\n    The assets command validates asset references (images, logos, certificates)\n    in CV JSON files and optionally optimizes images for faster LaTeX compilation.\n\n    This command is read-only for data/ and only writes to output/ or\n    user-specified directories.\n\nSUBCOMMANDS\n    check             Validate that all referenced assets exist\n    optimize          Copy and resize images to output directory\n\nCHECK OPTIONS\n    --name, -n NAME     Check only CVs matching this base name\n    --input-dir, -i     Directory containing CV JSON files (default: data/cvs)\n    --format, -f        Output format: text or json (default: text)\n\nOPTIMIZE OPTIONS\n    --out, -o DIR       Output directory for optimized assets\n                        (default: output/assets_optimized)\n    --name, -n NAME     Optimize only assets from CVs matching this name\n    --max-width N       Maximum width for resized images (default: 800)\n    --max-height N      Maximum height for resized images (default: 800)\n    --quality N         JPEG quality 1-100 (default: 85)\n    --format, -f        Output format: text or json (default: text)\n\nASSET TYPES DETECTED\n    - Profile photos (basics[].Pictures[].URL)\n    - Institution logos (education[].logo_url)\n    - Certificates (workshop_and_certifications[].certifications[].URL)\n    - Reference letters (references[].URL)\n    - Language certifications (languages[].certifications[].URL)\n\nEXAMPLES\n    # Check all asset references\n    cvgen assets check\n\n    # Check assets for a specific profile\n    cvgen assets check --name example\n\n    # Optimize images for faster LaTeX compilation\n    cvgen assets optimize --out output/assets_optimized/\n\n    # Optimize with custom settings\n    cvgen assets optimize --max-width 600 --quality 90\n\nLOGO LIBRARY\n    A logo library can be configured at assets/logo_map.json with structure:\n\n    {\n      "mapping": {\n        "University of Berlin": "logos/berlin.png",\n        "MIT": "logos/mit.png"\n      },\n      "default": "logos/default.png"\n    }\n\nSAFETY\n    The optimize command NEVER writes to data/. If you try to specify an\n    output directory under data/, the command will refuse with an error.\n\nEXIT CODES\n    0  All assets valid / optimization successful\n    5  Asset validation errors found\n', 'profile': "\ncvgen profile — Manage CV profile selection\n\nSYNOPSIS\n    cvgen profile list [OPTIONS]\n    cvgen profile use NAME [OPTIONS]\n    cvgen profile clear\n\nDESCRIPTION\n    The profile command manages the currently selected CV profile. When a\n    profile is set, 'cvgen build' will use it as the default without needing\n    the --name flag.\n\nSUBCOMMANDS\n    list              List available profiles\n    use NAME          Set the current profile to NAME\n    clear             Clear the current profile selection\n\nOPTIONS\n    --input-dir, -i   Directory containing CV JSON files (default: data/cvs)\n    --format, -f      Output format for 'list': text or json (default: text)\n\nEXAMPLES\n    # List all available profiles\n    cvgen profile list\n\n    # Set example as the current profile\n    cvgen profile use example\n\n    # Now build will use example by default\n    cvgen build\n\n    # Clear the current profile\n    cvgen profile clear\n\nSTATE FILE\n    The current profile is stored in .cvgen/state.json (excluded from git).\n    This file is created automatically when you use 'cvgen profile use'.\n", 'config': '\ncvgen configuration — Config file support\n\nDESCRIPTION\n    CV Generator supports an optional TOML configuration file to reduce\n    repetitive CLI flags.\n\nCONFIG FILE\n    The default config file name is \'cv_generator.toml\'. It is searched for in:\n    1. Current directory\n    2. Repository root\n\n    You can also specify a custom path with --config:\n        cvgen --config path/to/config.toml build\n\nCONFIG SECTIONS\n    [project]\n    name = "My CV Project"\n    default_lang = "en"\n    variants = ["academic", "industry"]\n\n    [paths]\n    cvs = "data/cvs"\n    templates = "templates"\n    output = "output"\n    db = "data/db/cv.db"\n\n    [build]\n    latex_engine = "xelatex"\n    keep_latex = false\n    dry_run = false\n\n    [logging]\n    level = "WARNING"\n    log_file = "output/logs/cvgen.log"\n\nPRECEDENCE\n    CLI flags override config file values, which override internal defaults:\n    1. CLI flags (highest priority)\n    2. Config file values\n    3. Internal defaults (lowest priority)\n\nEXAMPLE CONFIG\n    # cv_generator.toml\n    [project]\n    name = "My CVs"\n    default_lang = "en"\n\n    [paths]\n    cvs = "data/cvs"\n    output = "output"\n\n    [build]\n    keep_latex = true\n', 'init': '\ncvgen init — Create a new CV project\n\nSYNOPSIS\n    cvgen init <path> [OPTIONS]\n\nDESCRIPTION\n    The init command creates a new CV project with a minimal working\n    structure. This is the fastest way to get started with CV Generator.\n\n    The generated project includes:\n    - A minimal valid CV JSON file ready to edit\n    - A config file (cv_generator.toml) with project settings\n    - A README with next steps and documentation links\n    - A .gitignore file for version control\n\nARGUMENTS\n    <path>              Directory where the project will be created.\n                        Can be an absolute or relative path.\n\nOPTIONS\n    --profile, -p NAME  Name for your CV profile (default: mycv).\n                        This determines the JSON filename.\n    --lang, -l LANG     Language code: en, de, or fa (default: en).\n    --force, -f         Overwrite existing files if directory is not empty.\n\nEXAMPLES\n    # Create a new project in the current directory\n    cvgen init .\n\n    # Create a project with a specific profile name\n    cvgen init ~/Documents/my-cv --profile jane\n\n    # Create a German CV project\n    cvgen init ./german-cv --profile hans --lang de\n\n    # Overwrite an existing project\n    cvgen init ./my-cv --force\n\nGENERATED STRUCTURE\n    <path>/\n      cvs/\n        <profile>.<lang>.json   # Your CV data (edit this!)\n      output/                    # Build output directory\n      cv_generator.toml          # Configuration file\n      README.md                  # Next steps documentation\n      .gitignore                 # Git ignore rules\n\nNEXT STEPS AFTER INIT\n    After running cvgen init, follow these steps:\n\n    1. cd <path>\n    2. Edit cvs/<profile>.<lang>.json with your information\n    3. cvgen build --input-dir cvs\n\n    The generated PDF will be at:\n    output/pdf/<profile>/<lang>/<profile>_<lang>.pdf\n\nREQUIREMENTS\n    To generate PDFs, you need XeLaTeX installed:\n    - Ubuntu/Debian: sudo apt-get install texlive-xetex texlive-fonts-extra\n    - macOS: brew install --cask mactex\n    - Windows: Install MiKTeX or TeX Live\n\n    Without LaTeX, you can still:\n    - Edit and validate your CV JSON\n    - Use --dry-run --keep-latex to generate LaTeX source files\n'}

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
        print('Available help topics:\n')
        print('  init            Create a new CV project')
        print('  build           Generate PDF CVs from JSON files')
        print('  export          Export CVs to HTML/Markdown')
        print('  ensure          Validate multilingual CV consistency')
        print('  lint            Validate CV JSON files against schema')
        print('  assets          Asset validation and optimization')
        print('  doctor          System health checks')
        print('  profile         Manage CV profile selection')
        print('  config          Configuration file support')
        print('  languages       Language support and translation')
        print('  templates       Template customization')
        print('  json-schema     CV JSON data format')
        print('  troubleshooting Common issues and solutions')
        print("\nUse 'cvgen help <topic>' for detailed information.")
        return EXIT_SUCCESS
    topic_aliases = {'generate': 'build', 'validate': 'ensure', 'langs': 'languages', 'template': 'templates', 'schema': 'json-schema', 'profiles': 'profile', 'configuration': 'config', 'json': 'json-schema', 'scaffold': 'init', 'new': 'init', 'asset': 'assets', 'images': 'assets', 'logos': 'assets'}
    topic = topic_aliases.get(topic, topic)
    if topic in HELP_TOPICS:
        print(HELP_TOPICS[topic].strip())
        return EXIT_SUCCESS
    else:
        print(f"Unknown help topic: '{topic}'")
        print('\nAvailable topics: build, ensure, lint, assets, doctor, languages, templates, json-schema, troubleshooting')
        return EXIT_ERROR

def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser for the CLI.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(prog='cvgen', description='Generate beautiful PDF CVs from JSON data using Jinja2 templates and Awesome-CV.', epilog='Example: cvgen build --name example')
    parser.add_argument('--version', action='version', version=f'cvgen {__version__}')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output (INFO level logging)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output (DEBUG level logging)')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress output except errors')
    parser.add_argument('--config', '-c', type=str, dest='config_file', help='Path to config file (default: cv_generator.toml)')
    subparsers = parser.add_subparsers(dest='command', title='commands', description='Available commands')
    init_parser = subparsers.add_parser('init', help='Create a new CV project scaffold', description='Create a new CV project with a minimal working structure.')
    init_parser.add_argument('path', type=str, help='Directory where the project will be created')
    init_parser.add_argument('--profile', '-p', type=str, default='mycv', help='Name for your CV profile (default: mycv)')
    init_parser.add_argument('--lang', '-l', type=str, choices=['en', 'de', 'fa'], default='en', help='Language code: en, de, or fa (default: en)')
    init_parser.add_argument('--force', '-f', action='store_true', help='Overwrite existing files if directory is not empty')
    init_parser.set_defaults(func=init_command)
    build_parser = subparsers.add_parser('build', help='Build PDF CVs from JSON files', description='Generate PDF CVs from JSON files in the input directory.')
    build_parser.add_argument('--name', '-n', type=str, help="Build only the CV with this base name (e.g., 'example')")
    build_parser.add_argument('--input-dir', '-i', type=str, help='Input directory containing CV JSON files (default: data/cvs)')
    build_parser.add_argument('--output-dir', '-o', type=str, help='Output directory root (default: output). PDFs go to output/pdf/<name>/<lang>/')
    build_parser.add_argument('--templates-dir', '-t', type=str, help='Templates directory (default: templates)')
    build_parser.add_argument('--pics-dir', type=str, help='Profile pictures directory (default: data/pics or ~/.cvgen/pics)')
    build_parser.add_argument('--keep-latex', '-k', action='store_true', dest='keep_latex', help='Keep LaTeX source files in output/latex/ (default: clean up after compilation)')
    build_parser.add_argument('--dry-run', '-d', action='store_true', help='Render LaTeX but skip xelatex compilation')
    build_parser.add_argument('--variant', '-V', type=str, help="Filter entries by variant/type_key (e.g., 'academic', 'industry')")
    build_parser.add_argument('--incremental', action='store_true', dest='incremental', help='Enable incremental builds (skip unchanged CVs based on input hashing)')
    build_parser.add_argument('--no-incremental', action='store_true', dest='no_incremental', help='Force full rebuild, ignoring cache')
    build_parser.add_argument('--watch', '-w', action='store_true', dest='watch', help='Watch for file changes and rebuild automatically')
    build_parser.add_argument('--report', action='store_true', dest='report', help='Generate a build report in output/reports/')
    latex_group = build_parser.add_argument_group('LaTeX Options')
    latex_group.add_argument('--latex-timeout', type=int, default=120, metavar='SECONDS', dest='latex_timeout', help='LaTeX compilation timeout in seconds (default: 120)')
    cleanup_group = build_parser.add_argument_group('Cleanup Options')
    cleanup_group.add_argument('--no-cleanup', action='store_true', dest='no_cleanup', help='Skip cleanup of intermediate files')
    cleanup_group.add_argument('--force-cleanup', action='store_true', dest='force_cleanup', help='Force cleanup even if files are locked (may fail)')
    cleanup_group.add_argument('--cleanup-timeout', type=int, default=120, metavar='SECONDS', dest='cleanup_timeout', help='Maximum time to wait for file locks (default: 120s)')
    build_parser.set_defaults(func=build_command)
    ensure_parser = subparsers.add_parser('ensure', help='Validate multilingual CV JSON consistency', description='Check that multilingual CV JSON files have consistent structure.')
    ensure_parser.add_argument('--name', '-n', type=str, required=True, help="Name of the person (e.g., 'example')")
    ensure_parser.add_argument('--langs', '-l', type=str, default='en,de,fa', help='Comma-separated language codes to check (default: en,de,fa)')
    ensure_parser.add_argument('--format', '-f', type=str, choices=['text', 'json'], default='text', help='Output format (default: text)')
    ensure_parser.add_argument('--input-dir', '-i', type=str, help='Input directory containing CV JSON files (default: data/cvs)')
    ensure_parser.add_argument('--dir', '-D', type=str, help='Directory containing CV files (e.g., data/cvs/i18n/example)')
    ensure_parser.add_argument('--path-en', type=str, help='Explicit path to English CV file')
    ensure_parser.add_argument('--path-de', type=str, help='Explicit path to German CV file')
    ensure_parser.add_argument('--path-fa', type=str, help='Explicit path to Persian CV file')
    ensure_parser.add_argument('--lang-map', type=str, help='Path to language mapping file (lang.json)')
    ensure_parser.add_argument('--fail-fast', action='store_true', help='Stop at first batch of errors')
    ensure_parser.add_argument('--max-errors', type=int, default=None, help='Maximum number of errors before stopping')
    ensure_parser.add_argument('--strict', action='store_true', help='Fail with non-zero exit code on any mismatch (for CI use)')
    ensure_parser.add_argument('--fix', action='store_true', help='Generate corrected copies of language variants (writes to --fix-out, never to data/)')
    ensure_parser.add_argument('--fix-out', type=str, default='output/fixed', help='Output directory for fixed files (default: output/fixed). Cannot be under data/.')
    ensure_parser.add_argument('--report', type=str, choices=['text', 'json'], help='Report format (overrides --format for report output)')
    ensure_parser.add_argument('--report-out', type=str, help='Path to write JSON report file (e.g., output/reports/ensure.json)')
    ensure_parser.set_defaults(func=ensure_command)
    lint_parser = subparsers.add_parser('lint', help='Validate CV JSON files against schema', description='Check CV JSON files for structural issues before rendering.')
    lint_parser.add_argument('--name', '-n', type=str, help="Validate only CVs matching this base name (e.g., 'example')")
    lint_parser.add_argument('--file', '-f', type=str, help='Path to a specific CV JSON file to validate')
    lint_parser.add_argument('--input-dir', '-i', type=str, help='Input directory containing CV JSON files (default: data/cvs)')
    lint_parser.add_argument('--strict', action='store_true', help='Treat all schema issues as errors (fail on any issue)')
    lint_parser.add_argument('--format', type=str, choices=['text', 'json'], default='text', help='Output format (default: text)')
    lint_parser.set_defaults(func=lint_command)
    assets_parser = subparsers.add_parser('assets', help='Asset validation and optimization', description='Validate asset references (images/logos) and optionally optimize images.')
    assets_subparsers = assets_parser.add_subparsers(dest='assets_command', title='assets commands', description='Available asset commands')
    assets_check_parser = assets_subparsers.add_parser('check', help='Validate asset references in CV files', description='Check that all referenced images, logos, and files exist.')
    assets_check_parser.add_argument('--name', '-n', type=str, help="Check only CVs matching this base name (e.g., 'example')")
    assets_check_parser.add_argument('--input-dir', '-i', type=str, help='Input directory containing CV JSON files (default: data/cvs)')
    assets_check_parser.add_argument('--format', '-f', type=str, choices=['text', 'json'], default='text', help='Output format (default: text)')
    assets_check_parser.set_defaults(func=assets_check_command)
    assets_optimize_parser = assets_subparsers.add_parser('optimize', help='Optimize images for faster LaTeX compilation', description='Copy and resize images to an output directory. Never modifies data/.')
    assets_optimize_parser.add_argument('--out', '-o', type=str, default='output/assets_optimized', help='Output directory for optimized assets (default: output/assets_optimized)')
    assets_optimize_parser.add_argument('--name', '-n', type=str, help='Optimize only assets from CVs matching this base name')
    assets_optimize_parser.add_argument('--input-dir', '-i', type=str, help='Input directory containing CV JSON files (default: data/cvs)')
    assets_optimize_parser.add_argument('--max-width', type=int, default=800, help='Maximum width for resized images (default: 800)')
    assets_optimize_parser.add_argument('--max-height', type=int, default=800, help='Maximum height for resized images (default: 800)')
    assets_optimize_parser.add_argument('--quality', type=int, default=85, help='JPEG quality 1-100 (default: 85)')
    assets_optimize_parser.add_argument('--format', '-f', type=str, choices=['text', 'json'], default='text', help='Output format (default: text)')
    assets_optimize_parser.set_defaults(func=assets_optimize_command)
    assets_parser.set_defaults(func=lambda args: assets_parser.print_help() or EXIT_SUCCESS)
    db_parser = subparsers.add_parser('db', help='SQLite database operations', description='Manage CV data in SQLite database for querying and editing.')
    db_subparsers = db_parser.add_subparsers(dest='db_command', title='db commands', description='Available database commands')
    db_init_parser = db_subparsers.add_parser('init', help='Initialize the database', description='Create the database and apply schema.')
    db_init_parser.add_argument('--db', type=str, help='Path to database file (default: data/db/cv.db)')
    db_init_parser.add_argument('--force', action='store_true', help='Recreate the database even if it exists')
    db_init_parser.set_defaults(func=db_init_command)
    db_import_parser = db_subparsers.add_parser('import', help='Import CV JSON files into database', description='Import CV JSON files from a directory into the database.')
    db_import_parser.add_argument('--db', type=str, help='Path to database file (default: data/db/cv.db)')
    db_import_parser.add_argument('--input-dir', '-i', type=str, help='Input directory containing CV JSON files (default: data/cvs)')
    db_import_parser.add_argument('--name', '-n', type=str, help='Import only CVs matching this base name')
    db_import_parser.add_argument('--overwrite', action='store_true', help='Replace existing entries for each person')
    db_import_parser.add_argument('--no-backup', action='store_true', help="Don't backup database before overwrite")
    db_import_parser.set_defaults(func=db_import_command)
    db_export_parser = db_subparsers.add_parser('export', help='Export database to JSON files', description='Export CV data from database to JSON files.')
    db_export_parser.add_argument('--db', type=str, help='Path to database file (default: data/db/cv.db)')
    db_export_parser.add_argument('--output-dir', '-o', type=str, help='Output directory for JSON files (default: data/cvs)')
    db_export_parser.add_argument('--name', '-n', type=str, help='Export only CVs matching this slug')
    db_export_parser.add_argument('--format', '-f', type=str, choices=['pretty', 'min'], default='pretty', help='Output format (default: pretty)')
    db_export_parser.add_argument('--apply-tags', action='store_true', help='Rebuild type_key from database tags for entries that originally had it')
    db_export_parser.add_argument('--apply-tags-to-all', action='store_true', help='Add type_key to ALL entries from database tags (not just those that had it)')
    db_export_parser.add_argument('--force', action='store_true', help='Overwrite existing files without asking')
    db_export_parser.set_defaults(func=db_export_command)
    db_diff_parser = db_subparsers.add_parser('diff', help='Compare JSON files with database', description='Compare CV JSON files with their database exports.')
    db_diff_parser.add_argument('--db', type=str, help='Path to database file (default: data/db/cv.db)')
    db_diff_parser.add_argument('--input-dir', '-i', type=str, help='Input directory containing CV JSON files (default: data/cvs)')
    db_diff_parser.add_argument('--name', '-n', type=str, help='Compare only CVs matching this base name')
    db_diff_parser.add_argument('--format', '-f', type=str, choices=['text', 'json'], default='text', help='Output format (default: text)')
    db_diff_parser.set_defaults(func=db_diff_command)
    db_list_parser = db_subparsers.add_parser('list', help='List database contents', description='List persons or tags in the database.')
    db_list_parser.add_argument('--db', type=str, help='Path to database file (default: data/db/cv.db)')
    db_list_parser.add_argument('--what', type=str, choices=['persons', 'tags'], default='persons', help='What to list (default: persons)')
    db_list_parser.add_argument('--format', '-f', type=str, choices=['text', 'json'], default='text', help='Output format (default: text)')
    db_list_parser.set_defaults(func=db_list_command)
    db_doctor_parser = db_subparsers.add_parser('doctor', help='Check database health', description='Run health checks on the database and report issues.')
    db_doctor_parser.add_argument('--db', type=str, help='Path to database file (default: data/db/cv.db)')
    db_doctor_parser.add_argument('--format', '-f', type=str, choices=['text', 'json'], default='text', help='Output format (default: text)')
    db_doctor_parser.set_defaults(func=db_doctor_command)
    db_integrity_parser = db_subparsers.add_parser('integrity', help='Check reference integrity (stable IDs, tags, links)', description='Run comprehensive reference integrity checks on stable IDs, person entities, tag references, and cross-language links.')
    db_integrity_parser.add_argument('--db', type=str, help='Path to database file (default: data/db/cv.db)')
    db_integrity_parser.add_argument('--format', '-f', type=str, choices=['text', 'json'], default='text', help='Output format (default: text)')
    db_integrity_parser.set_defaults(func=db_integrity_command)
    db_verify_erd_parser = db_subparsers.add_parser('verify-erd', help='Verify database schema matches ERD specification', description='Compare the database schema against docs/erd.txt and report table-by-table match status. Reports missing tables, columns, foreign keys, and unique constraints.')
    db_verify_erd_parser.add_argument('--db', type=str, help='Path to database file (default: data/db/cv.db)')
    db_verify_erd_parser.add_argument('--erd', type=str, help='Path to ERD file (default: docs/erd.txt)')
    db_verify_erd_parser.add_argument('--format', '-f', type=str, choices=['text', 'json'], default='text', help='Output format (default: text)')
    db_verify_erd_parser.set_defaults(func=db_verify_erd_command)
    db_parser.set_defaults(func=lambda args: db_parser.print_help() or EXIT_SUCCESS)
    web_parser = subparsers.add_parser('web', help='Web UI for tag management', description='Start web server for managing tags and CV entries.')
    web_subparsers = web_parser.add_subparsers(dest='web_command', title='web commands', description='Available web commands')
    web_tags_parser = web_subparsers.add_parser('tags', help='Start the Tag Manager web UI', description='Start local web server for managing tags on CV entries.')
    web_tags_parser.add_argument('--db', type=str, help='Path to database file (default: data/db/cv.db)')
    web_tags_parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to bind to (default: 127.0.0.1, use 0.0.0.0 for LAN access)')
    web_tags_parser.add_argument('--port', type=int, default=5000, help='Port to listen on (default: 5000)')
    web_tags_parser.add_argument('--i-know-what-im-doing', action='store_true', dest='i_know_what_im_doing', help='Required flag when binding to non-localhost address to acknowledge security risks')
    web_tags_parser.set_defaults(func=web_tags_command)
    web_parser.set_defaults(func=lambda args: web_parser.print_help() or EXIT_SUCCESS)
    profile_parser = subparsers.add_parser('profile', help='Manage CV profile selection', description='List, select, and manage CV profiles.')
    profile_subparsers = profile_parser.add_subparsers(dest='profile_command', title='profile commands', description='Available profile commands')
    profile_list_parser = profile_subparsers.add_parser('list', help='List available profiles', description='List all CV profiles found in the data directory.')
    profile_list_parser.add_argument('--input-dir', '-i', type=str, help='Input directory containing CV JSON files (default: data/cvs)')
    profile_list_parser.add_argument('--format', '-f', type=str, choices=['text', 'json'], default='text', help='Output format (default: text)')
    profile_list_parser.set_defaults(func=profile_list_command)
    profile_use_parser = profile_subparsers.add_parser('use', help='Set the current profile', description='Set a profile as the default for build commands.')
    profile_use_parser.add_argument('profile_name', type=str, help='Name of the profile to use')
    profile_use_parser.add_argument('--input-dir', '-i', type=str, help='Input directory containing CV JSON files (default: data/cvs)')
    profile_use_parser.set_defaults(func=profile_use_command)
    profile_clear_parser = profile_subparsers.add_parser('clear', help='Clear the current profile', description='Remove the current profile selection.')
    profile_clear_parser.set_defaults(func=profile_clear_command)
    profile_parser.set_defaults(func=lambda args: profile_parser.print_help() or EXIT_SUCCESS)
    export_parser = subparsers.add_parser('export', help='Export CVs to HTML or Markdown format', description='Export CV data to alternative formats (HTML, Markdown).')
    export_parser.add_argument('--name', '-n', type=str, help="Export only CVs matching this base name (e.g., 'example')")
    export_parser.add_argument('--lang', '-l', type=str, help="Export only CVs with this language code (e.g., 'en', 'de')")
    export_parser.add_argument('--format', '-f', type=str, choices=['html', 'md'], default='html', help='Export format: html or md (default: html)')
    export_parser.add_argument('--input-dir', '-i', type=str, help='Input directory containing CV JSON files (default: data/cvs)')
    export_parser.add_argument('--output-dir', '-o', type=str, help='Output directory root (default: output)')
    export_parser.set_defaults(func=export_command)
    doctor_parser = subparsers.add_parser('doctor', help='Run system health checks', description='Validate environment and repo configuration before builds.')
    doctor_parser.add_argument('--templates-dir', '-t', type=str, help='Templates directory to check (default: templates)')
    doctor_parser.add_argument('--output-dir', '-o', type=str, help='Output directory to check (default: output)')
    doctor_parser.add_argument('--format', '-f', type=str, choices=['text', 'json'], default='text', help='Output format (default: text)')
    doctor_parser.set_defaults(func=doctor_command)
    diff_parser = subparsers.add_parser('diff', help='Compare current vs previous TeX artifacts', description='Show differences between current and previous build outputs.')
    diff_parser.add_argument('--name', '-n', type=str, required=True, help="Profile name (e.g., 'example')")
    diff_parser.add_argument('--lang', '-l', type=str, required=True, help="Language code (e.g., 'en', 'de')")
    diff_parser.add_argument('--output-dir', '-o', type=str, help='Output directory root (default: output)')
    diff_parser.add_argument('--format', '-f', type=str, choices=['text', 'json'], default='text', help='Output format (default: text)')
    diff_parser.set_defaults(func=diff_command)
    clean_parser = subparsers.add_parser('clean', help='Clean output directories with optional backup', description='Remove generated output files with safety features.')
    clean_parser.add_argument('--type', '-t', type=str, help='Comma-separated output types to clean (pdf,latex,html,md). Default: all')
    clean_parser.add_argument('--output-dir', '-o', type=str, help='Output directory root (default: output)')
    clean_parser.add_argument('--backup', action='store_true', default=True, dest='backup', help='Create backup before cleaning (default: True)')
    clean_parser.add_argument('--no-backup', action='store_false', dest='backup', help='Skip backup creation')
    clean_parser.add_argument('--yes', '-y', action='store_true', dest='yes', help='Skip confirmation prompts (for CI use)')
    clean_parser.add_argument('--list-backups', action='store_true', dest='list_backups', help='List existing backups instead of cleaning')
    clean_parser.set_defaults(func=clean_command)
    help_parser = subparsers.add_parser('help', help='Show extended help for a topic', description='Display detailed help for specific topics.')
    help_parser.add_argument('topic', nargs='?', type=str, help='Topic to get help on (build, ensure, languages, templates, json-schema, troubleshooting)')
    help_parser.set_defaults(func=help_command)
    return parser

def main(argv: Optional[List[str]]=None) -> int:
    """
    Main entry point for the CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv).

    Returns:
        Exit code.
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    setup_logging(verbose=args.verbose, debug=args.debug, quiet=args.quiet)
    config_path = Path(args.config_file) if args.config_file else None
    try:
        config = load_config(config_path)
        args._config = config
    except ConfigError as e:
        logger.error(f'Config error: {e}')
        print(f'❌ Config error: {e}')
        return EXIT_CONFIG_ERROR
    if not args.command:
        args = parser.parse_args(['build'] + (argv if argv else sys.argv[1:]))
        args._config = config
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
if __name__ == '__main__':
    main_cli()
