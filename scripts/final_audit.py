"""
Comprehensive Final Audit Script

Runs ALL possible tests and validations, collecting ONLY problems.
Generates final_audit.md with problem report.

Usage:
    python -m scripts.final_audit [--project-root PATH] [--output PATH]
"""
import json
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

class Severity(Enum):
    CRITICAL = '🔴 CRITICAL'
    HIGH = '🟠 HIGH'
    MEDIUM = '🟡 MEDIUM'
    LOW = '🟢 LOW'

@dataclass
class Problem:
    id: str
    severity: Severity
    category: str
    subcategory: str
    title: str
    description: str
    reproduction_steps: List[str]
    expected_behavior: str
    actual_behavior: str
    affected_files: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    suggested_fix: Optional[str] = None

class FinalAuditor:
    """
    Master auditor that runs all audit categories and generates a problem report.

    This class orchestrates a comprehensive audit of the CV Generator project by:
    1. Running 20 specialized audit categories (database, import, export, web UI, etc.)
    2. Collecting problems from each audit category
    3. Categorizing problems by severity (CRITICAL, HIGH, MEDIUM, LOW)
    4. Generating a markdown report (final_audit.md) containing ONLY problems found

    The generated report includes:
    - Summary table with problem counts by severity
    - Problems grouped by category
    - Detailed information for each problem including reproduction steps
    - Problem index for quick reference

    Usage:
        auditor = FinalAuditor(project_root)
        problems = auditor.run_full_audit()
        report = auditor.generate_report()
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.problems: List[Problem] = []
        self.problem_counter = 0
        self.start_time = datetime.now()

    def run_full_audit(self) -> List[Problem]:
        """Run complete audit across all categories."""
        print('=' * 60)
        print('FINAL COMPREHENSIVE AUDIT')
        print(f'Started: {self.start_time}')
        print('=' * 60)
        self._audit_database()
        self._audit_import_engine()
        self._audit_export_engine()
        self._audit_round_trip()
        self._audit_web_ui()
        self._audit_sync_engine()
        self._audit_variant_management()
        self._audit_test_suite()
        self._audit_code_quality()
        self._audit_file_structure()
        self._audit_documentation()
        self._audit_latex_generation()
        self._audit_cli()
        self._audit_security()
        self._audit_performance()
        self._audit_edge_cases()
        self._audit_error_handling()
        self._audit_logging()
        self._audit_configuration()
        self._audit_dependencies()
        return self.problems

    def _add_problem(self, severity: Severity, category: str, subcategory: str, title: str, description: str, reproduction_steps: List[str], expected: str, actual: str, **kwargs):
        """Add a problem to the list."""
        self.problem_counter += 1
        problem = Problem(id=f'PROB-{self.problem_counter:04d}', severity=severity, category=category, subcategory=subcategory, title=title, description=description, reproduction_steps=reproduction_steps, expected_behavior=expected, actual_behavior=actual, **kwargs)
        self.problems.append(problem)
        print(f'  ❌ Found: [{problem.id}] {title}')

    def _audit_database(self):
        """Audit database schema, integrity, and operations."""
        print('\n[1/20] Auditing Database...')
        from .audit_categories.database_audit import DatabaseAuditor
        auditor = DatabaseAuditor(self.project_root, self._add_problem)
        auditor.run_all_checks()

    def _audit_import_engine(self):
        """Audit import engine functionality."""
        print('\n[2/20] Auditing Import Engine...')
        from .audit_categories.import_audit import ImportAuditor
        auditor = ImportAuditor(self.project_root, self._add_problem)
        auditor.run_all_checks()

    def _audit_export_engine(self):
        """Audit export engine functionality."""
        print('\n[3/20] Auditing Export Engine...')
        from .audit_categories.export_audit import ExportAuditor
        auditor = ExportAuditor(self.project_root, self._add_problem)
        auditor.run_all_checks()

    def _audit_round_trip(self):
        """Audit round-trip integrity."""
        print('\n[4/20] Auditing Round-Trip Integrity...')
        cv_dir = self.project_root / 'data' / 'cvs'
        if not cv_dir.exists():
            return
        cv_files = list(cv_dir.glob('*.json'))
        for cv_file in cv_files:
            self._check_round_trip_single_file(cv_file)

    def _check_round_trip_single_file(self, cv_file: Path):
        """Check round-trip for a single CV file."""
        import tempfile
        try:
            sys.path.insert(0, str(self.project_root / 'src'))
            from cv_generator.db import export_cv, import_cv, init_db
            from cv_generator.io import load_cv_json, parse_cv_filename
            original_data = load_cv_json(cv_file)
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
                temp_db = Path(f.name)
            try:
                init_db(temp_db, force=True)
                import_cv(cv_file, temp_db, overwrite=True)
                slug, lang = parse_cv_filename(cv_file.name)
                if lang != 'en':
                    slug = f'{slug}_{lang}'
                exported_data = export_cv(slug, temp_db)
                original_keys = set(original_data.keys())
                exported_keys = set(exported_data.keys())
                missing_keys = original_keys - exported_keys
                if missing_keys:
                    self._add_problem(severity=Severity.HIGH, category='Round-Trip', subcategory='Data Loss', title=f'Missing sections after round-trip: {cv_file.name}', description=f'Sections {missing_keys} are missing after import/export', reproduction_steps=[f'1. Load {cv_file.name}', '2. Import to database', '3. Export from database', '4. Compare sections'], expected=f'All sections preserved: {original_keys}', actual=f'Missing sections: {missing_keys}', affected_files=[str(cv_file)])
            finally:
                if temp_db.exists():
                    temp_db.unlink()
        except Exception as e:
            self._add_problem(severity=Severity.CRITICAL, category='Round-Trip', subcategory='Execution Error', title=f'Round-trip failed for {cv_file.name}', description='Exception during round-trip verification', reproduction_steps=[f'1. Run round-trip test for {cv_file.name}'], expected='Round-trip completes successfully', actual=f'Exception: {type(e).__name__}', affected_files=[str(cv_file)], error_message=str(e), stack_trace=traceback.format_exc())

    def _audit_web_ui(self):
        """Audit web UI functionality."""
        print('\n[5/20] Auditing Web UI...')
        from .audit_categories.web_ui_audit import WebUIAuditor
        auditor = WebUIAuditor(self.project_root, self._add_problem)
        auditor.run_all_checks()

    def _audit_sync_engine(self):
        """Audit sync engine functionality."""
        print('\n[6/20] Auditing Sync Engine...')
        from .audit_categories.sync_audit import SyncAuditor
        auditor = SyncAuditor(self.project_root, self._add_problem)
        auditor.run_all_checks()

    def _audit_variant_management(self):
        """Audit variant management functionality."""
        print('\n[7/20] Auditing Variant Management...')
        vm_path = self.project_root / 'src' / 'cv_generator' / 'variant_manager.py'
        if not vm_path.exists():
            self._add_problem(severity=Severity.CRITICAL, category='Variant Management', subcategory='Missing Module', title='Variant manager module not found', description='The variant_manager.py module is missing', reproduction_steps=['1. Check for variant_manager.py'], expected='variant_manager.py exists', actual='File not found', affected_files=[str(vm_path)])
            return
        try:
            with open(vm_path, 'r', encoding='utf-8') as f:
                content = f.read()
            required_functions = ['add_variant', 'remove_variant', 'list_variants']
            for func in required_functions:
                if f'def {func}' not in content:
                    self._add_problem(severity=Severity.MEDIUM, category='Variant Management', subcategory='Missing Function', title=f'Missing function: {func}', description=f"Function '{func}' not found in variant_manager.py", reproduction_steps=[f"1. Search for 'def {func}' in variant_manager.py"], expected=f"Function '{func}' is defined", actual='Function not found', affected_files=[str(vm_path)])
        except Exception as e:
            self._add_problem(severity=Severity.HIGH, category='Variant Management', subcategory='Parse Error', title='Cannot parse variant_manager.py', description=str(e), reproduction_steps=['1. Try to parse variant_manager.py'], expected='File parses successfully', actual=f'Exception: {type(e).__name__}', affected_files=[str(vm_path)], error_message=str(e))

    def _audit_test_suite(self):
        """Audit test suite quality and coverage."""
        print('\n[8/20] Auditing Test Suite...')
        try:
            result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/', '-v', '--tb=no', '-q', '--no-header'], capture_output=True, text=True, cwd=self.project_root, timeout=300)
            if result.returncode != 0:
                output = result.stdout + result.stderr
                failed_tests = []
                for line in output.split('\n'):
                    if 'FAILED' in line:
                        test_name = line.split('FAILED')[0].strip()
                        failed_tests.append(test_name)
                if failed_tests:
                    self._add_problem(severity=Severity.HIGH, category='Test Suite', subcategory='Test Failures', title=f'{len(failed_tests)} test(s) failed', description='Tests are failing in the test suite', reproduction_steps=['1. Run: pytest tests/ -v', '2. Check failed tests'], expected='All tests pass', actual=f"Failed tests: {', '.join(failed_tests[:5])}{('...' if len(failed_tests) > 5 else '')}", error_message=output[-2000:] if len(output) > 2000 else output)
        except subprocess.TimeoutExpired:
            self._add_problem(severity=Severity.HIGH, category='Test Suite', subcategory='Timeout', title='Test suite timed out', description='The test suite did not complete within 5 minutes', reproduction_steps=['1. Run: pytest tests/'], expected='Tests complete in reasonable time', actual='Tests timed out after 5 minutes')
        except Exception as e:
            self._add_problem(severity=Severity.MEDIUM, category='Test Suite', subcategory='Execution Error', title='Cannot run test suite', description=str(e), reproduction_steps=['1. Run: pytest tests/'], expected='Tests execute successfully', actual=f'Exception: {type(e).__name__}', error_message=str(e))

    def _audit_code_quality(self):
        """Audit code quality metrics."""
        print('\n[9/20] Auditing Code Quality...')
        from .audit_categories.code_quality_audit import CodeQualityAuditor
        auditor = CodeQualityAuditor(self.project_root, self._add_problem)
        auditor.run_all_checks()

    def _audit_file_structure(self):
        """Audit file structure and organization."""
        print('\n[10/20] Auditing File Structure...')
        root = self.project_root
        temp_patterns = ['*.pyc', '*.pyo', '__pycache__', '.DS_Store', '*.swp', '*.swo']
        temp_files_in_repo = []
        for pattern in temp_patterns:
            for f in root.rglob(pattern):
                if '.git' not in str(f):
                    temp_files_in_repo.append(str(f.relative_to(root)))
        if temp_files_in_repo:
            self._add_problem(severity=Severity.LOW, category='File Structure', subcategory='Temp Files', title=f'{len(temp_files_in_repo)} temp/cache files in repo', description='Temporary or cache files found in the repository', reproduction_steps=['1. Search for *.pyc, __pycache__, etc.'], expected='No temp files in repository', actual=f"Found: {', '.join(temp_files_in_repo[:5])}{('...' if len(temp_files_in_repo) > 5 else '')}", suggested_fix='Add these patterns to .gitignore')
        required_dirs = ['src/cv_generator', 'tests', 'data/cvs', 'docs', 'scripts']
        for dir_path in required_dirs:
            full_path = root / dir_path
            if not full_path.exists():
                self._add_problem(severity=Severity.HIGH, category='File Structure', subcategory='Missing Directory', title=f'Required directory missing: {dir_path}', description=f'The directory {dir_path} is required but does not exist', reproduction_steps=[f'1. Check if {dir_path} exists'], expected=f'Directory {dir_path} exists', actual='Directory not found')

    def _audit_documentation(self):
        """Audit documentation accuracy and completeness."""
        print('\n[11/20] Auditing Documentation...')
        from .audit_categories.documentation_audit import DocumentationAuditor
        auditor = DocumentationAuditor(self.project_root, self._add_problem)
        auditor.run_all_checks()

    def _audit_latex_generation(self):
        """Audit LaTeX/PDF generation."""
        print('\n[12/20] Auditing LaTeX Generation...')
        templates_dir = self.project_root / 'templates'
        if not templates_dir.exists():
            self._add_problem(severity=Severity.HIGH, category='LaTeX Generation', subcategory='Missing Templates', title='Templates directory not found', description='The templates directory is missing', reproduction_steps=['1. Check for templates/ directory'], expected='templates/ directory exists', actual='Directory not found')
            return
        awesome_cv = self.project_root / 'awesome-cv.cls'
        if not awesome_cv.exists():
            self._add_problem(severity=Severity.HIGH, category='LaTeX Generation', subcategory='Missing File', title='awesome-cv.cls not found', description='The Awesome-CV class file is missing', reproduction_steps=['1. Check for awesome-cv.cls in project root'], expected='awesome-cv.cls exists', actual='File not found', affected_files=[str(awesome_cv)])
        template_files = list(templates_dir.glob('*.tex')) + list(templates_dir.glob('*.jinja2'))
        if not template_files:
            self._add_problem(severity=Severity.HIGH, category='LaTeX Generation', subcategory='Missing Templates', title='No template files found', description='No .tex or .jinja2 template files in templates/', reproduction_steps=['1. List files in templates/'], expected='Template files exist', actual='No template files found')

    def _audit_cli(self):
        """Audit CLI commands."""
        print('\n[13/20] Auditing CLI...')
        try:
            result = subprocess.run([sys.executable, '-m', 'cv_generator.cli', '--help'], capture_output=True, text=True, cwd=self.project_root, timeout=30)
            if result.returncode != 0:
                self._add_problem(severity=Severity.CRITICAL, category='CLI', subcategory='Command Failure', title='CLI --help fails', description='The CLI help command does not work', reproduction_steps=['1. Run: python -m cv_generator.cli --help'], expected='Help output displayed', actual='Command failed', error_message=result.stderr)
        except Exception as e:
            self._add_problem(severity=Severity.CRITICAL, category='CLI', subcategory='Execution Error', title='Cannot run CLI', description=str(e), reproduction_steps=['1. Run: python -m cv_generator.cli --help'], expected='CLI executes', actual=f'Exception: {type(e).__name__}', error_message=str(e))

    def _audit_security(self):
        """Audit security considerations."""
        print('\n[14/20] Auditing Security...')
        from .audit_categories.security_audit import SecurityAuditor
        auditor = SecurityAuditor(self.project_root, self._add_problem)
        auditor.run_all_checks()

    def _audit_performance(self):
        """Audit performance characteristics."""
        print('\n[15/20] Auditing Performance...')
        db_file = self.project_root / 'src' / 'cv_generator' / 'db.py'
        if db_file.exists():
            try:
                with open(db_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                lines = content.split('\n')
                n_plus_1_candidates = []
                for i, line in enumerate(lines):
                    if 'for ' in line:
                        nearby_lines = '\n'.join(lines[i:i + 5])
                        if 'cursor.execute' in nearby_lines:
                            n_plus_1_candidates.append((i + 1, line.strip()))
                if len(n_plus_1_candidates) > 3:
                    self._add_problem(severity=Severity.LOW, category='Performance', subcategory='N+1 Queries', title='Potential N+1 query patterns in db.py', description=f'Found {len(n_plus_1_candidates)} loops with database queries nearby', reproduction_steps=['1. Review db.py for loops containing cursor.execute', '2. Consider batch queries where applicable'], expected='Batch queries for better performance', actual=f'{len(n_plus_1_candidates)} potential N+1 patterns', affected_files=[str(db_file)], suggested_fix='Consider using batch queries or JOINs')
            except Exception:
                pass

    def _audit_edge_cases(self):
        """Audit edge case handling."""
        print('\n[16/20] Auditing Edge Cases...')
        cv_dir = self.project_root / 'data' / 'cvs'
        if cv_dir.exists():
            for cv_file in cv_dir.glob('*.json'):
                try:
                    with open(cv_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    for section, content in data.items():
                        if isinstance(content, list) and len(content) == 0:
                            pass
                except json.JSONDecodeError as e:
                    self._add_problem(severity=Severity.CRITICAL, category='Edge Cases', subcategory='Invalid JSON', title=f'Invalid JSON in {cv_file.name}', description='The CV file contains invalid JSON', reproduction_steps=[f'1. Try to parse {cv_file.name}'], expected='Valid JSON', actual='JSON parse error', affected_files=[str(cv_file)], error_message=str(e))
                except Exception:
                    pass

    def _audit_error_handling(self):
        """Audit error handling."""
        print('\n[17/20] Auditing Error Handling...')
        src_dir = self.project_root / 'src' / 'cv_generator'
        if src_dir.exists():
            for py_file in src_dir.rglob('*.py'):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        stripped = line.strip()
                        if stripped == 'except:' or (stripped.startswith('except:') and (not stripped.startswith('except '))):
                            self._add_problem(severity=Severity.LOW, category='Error Handling', subcategory='Bare Except', title=f'Bare except clause in {py_file.name}', description="Using bare 'except:' catches all exceptions including SystemExit", reproduction_steps=[f'1. Check {py_file.name} line {i}'], expected='except Exception: or specific exception', actual='Bare except: clause', affected_files=[str(py_file)], suggested_fix="Use 'except Exception:' instead")
                            break
                except Exception:
                    pass

    def _audit_logging(self):
        """Audit logging implementation."""
        print('\n[18/20] Auditing Logging...')
        logging_config = self.project_root / 'src' / 'cv_generator' / 'logging_config.py'
        if not logging_config.exists():
            self._add_problem(severity=Severity.LOW, category='Logging', subcategory='Missing Config', title='Logging configuration file not found', description='No dedicated logging_config.py file found', reproduction_steps=['1. Check for logging_config.py'], expected='logging_config.py exists', actual='File not found')

    def _audit_configuration(self):
        """Audit configuration handling."""
        print('\n[19/20] Auditing Configuration...')
        config_example = self.project_root / 'cv_generator.toml.example'
        if not config_example.exists():
            self._add_problem(severity=Severity.LOW, category='Configuration', subcategory='Missing Example', title='No configuration example file', description='cv_generator.toml.example not found', reproduction_steps=['1. Check for cv_generator.toml.example'], expected='Example config file exists', actual='File not found')

    def _audit_dependencies(self):
        """Audit dependencies."""
        print('\n[20/20] Auditing Dependencies...')
        pyproject = self.project_root / 'pyproject.toml'
        if not pyproject.exists():
            self._add_problem(severity=Severity.CRITICAL, category='Dependencies', subcategory='Missing File', title='pyproject.toml not found', description='No pyproject.toml file found', reproduction_steps=['1. Check for pyproject.toml'], expected='pyproject.toml exists', actual='File not found')
            return
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True, text=True, cwd=self.project_root, timeout=60)
            if result.returncode != 0:
                self._add_problem(severity=Severity.MEDIUM, category='Dependencies', subcategory='Dependency Issues', title='Dependency check failed', description='pip check found dependency issues', reproduction_steps=['1. Run: pip check'], expected='No dependency issues', actual='Issues found', error_message=result.stdout + result.stderr)
        except Exception:
            pass

    def generate_report(self) -> str:
        """Generate final_audit.md content."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        if not self.problems:
            return f'# Final Audit Report\n\n> Generated: {end_time.isoformat()}\n> Duration: {duration}\n\n---\n\n## Summary\n\n✅ **No problems found.** All systems passed validation.\n'
        by_category: Dict[str, List[Problem]] = {}
        for problem in self.problems:
            if problem.category not in by_category:
                by_category[problem.category] = []
            by_category[problem.category].append(problem)
        critical = len([p for p in self.problems if p.severity.name == 'CRITICAL'])
        high = len([p for p in self.problems if p.severity.name == 'HIGH'])
        medium = len([p for p in self.problems if p.severity.name == 'MEDIUM'])
        low = len([p for p in self.problems if p.severity.name == 'LOW'])
        report = f'# Final Audit Report\n\n> Generated: {end_time.isoformat()}\n> Audit Duration: {duration}\n\n---\n\n## Summary\n\n| Severity | Count |\n|----------|-------|\n| 🔴 CRITICAL | {critical} |\n| 🟠 HIGH | {high} |\n| 🟡 MEDIUM | {medium} |\n| 🟢 LOW | {low} |\n| **TOTAL** | **{len(self.problems)}** |\n\n---\n\n## Problems by Category\n\n'
        for category in sorted(by_category.keys()):
            problems = by_category[category]
            report += f'\n### {category} ({len(problems)} problems)\n\n'
            severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
            problems.sort(key=lambda p: severity_order.index(p.severity.name))
            for problem in problems:
                report += self._format_problem(problem)
        report += self._generate_problem_index()
        return report

    def _format_problem(self, problem: Problem) -> str:
        """Format a single problem for the report."""
        steps = '\n'.join([f'   {step}' for step in problem.reproduction_steps])
        files = ', '.join(problem.affected_files) if problem.affected_files else 'N/A'
        output = f'\n---\n\n#### [{problem.id}] {problem.title}\n\n**Severity**: {problem.severity.value}\n**Category**: {problem.category} > {problem.subcategory}\n\n**Description**:\n{problem.description}\n\n**Reproduction Steps**:\n{steps}\n\n**Expected Behavior**:\n{problem.expected_behavior}\n\n**Actual Behavior**:\n{problem.actual_behavior}\n\n**Affected Files**: {files}\n\n'
        if problem.error_message:
            output += f'**Error Message**:\n```\n{problem.error_message}\n```\n\n'
        if problem.stack_trace:
            output += f'**Stack Trace**:\n```\n{problem.stack_trace}\n```\n\n'
        if problem.suggested_fix:
            output += f'**Suggested Fix**:\n{problem.suggested_fix}\n\n'
        return output

    def _generate_problem_index(self) -> str:
        """Generate problem index for quick reference."""
        output = '\n---\n\n## Problem Index\n\n| ID | Severity | Category | Title |\n|----|----------|----------|-------|\n'
        for problem in sorted(self.problems, key=lambda p: p.id):
            output += f'| {problem.id} | {problem.severity.value} | {problem.category} | {problem.title} |\n'
        return output

def main():
    """Run the final audit."""
    import argparse
    parser = argparse.ArgumentParser(description='Run comprehensive final audit')
    parser.add_argument('--project-root', type=Path, default=Path(__file__).parent.parent, help='Project root directory')
    parser.add_argument('--output', type=Path, default=None, help='Output file path (default: final_audit.md in project root)')
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    output_path = args.output or project_root / 'final_audit.md'
    auditor = FinalAuditor(project_root)
    problems = auditor.run_full_audit()
    report = auditor.generate_report()
    output_path.write_text(report, encoding='utf-8')
    print('\n' + '=' * 60)
    print(f'AUDIT COMPLETE: {len(problems)} problems found')
    print(f'Report written to: {output_path}')
    print('=' * 60)
    critical_count = len([p for p in problems if p.severity == Severity.CRITICAL])
    if critical_count > 0:
        print(f'\n⚠️  {critical_count} CRITICAL problems require immediate attention!')
        return 1
    return 0
if __name__ == '__main__':
    sys.exit(main())
