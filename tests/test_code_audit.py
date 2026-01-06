"""
Unit tests for code audit tools.

Tests the static analysis tools in scripts/:
- code_audit.py
- find_unused_imports.py
- analyze_function_usage.py
- find_duplicates.py
- generate_audit_report.py
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


# Add scripts directory to path
@pytest.fixture(autouse=True)
def add_scripts_to_path():
    """Add scripts directory to sys.path."""
    scripts_dir = Path(__file__).parent.parent / "scripts"
    sys.path.insert(0, str(scripts_dir))
    yield
    sys.path.remove(str(scripts_dir))


class TestCodeAudit:
    """Tests for code_audit.py"""

    def test_unused_code_dataclass(self):
        """Test UnusedCode dataclass."""
        from code_audit import UnusedCode

        item = UnusedCode(
            file_path="test.py",
            line_number=10,
            code_type="import",
            name="os",
            reason="Not used",
            confidence="high",
        )
        assert item.file_path == "test.py"
        assert item.line_number == 10
        assert item.to_dict()["name"] == "os"

    def test_audit_report_summary(self):
        """Test AuditReport summary generation."""
        from code_audit import AuditReport, UnusedCode

        report = AuditReport(
            total_lines=1000,
            removable_lines=100,
        )
        report.unused_imports.append(
            UnusedCode(
                file_path="test.py",
                line_number=1,
                code_type="import",
                name="os",
                reason="Unused",
                confidence="high",
            )
        )

        summary = report.get_summary()
        assert "CODE AUDIT REPORT" in summary
        assert "1000" in summary
        assert "100" in summary

    def test_audit_report_to_dict(self):
        """Test AuditReport to_dict conversion."""
        from code_audit import AuditReport

        report = AuditReport(total_lines=500, removable_lines=50)
        d = report.to_dict()

        assert d["total_lines"] == 500
        assert d["removable_lines"] == 50
        assert "summary" in d

    def test_definition_visitor_functions(self):
        """Test DefinitionVisitor finds functions."""
        import ast

        from code_audit import DefinitionVisitor

        code = """
def foo():
    pass

def bar(x):
    return x
"""
        tree = ast.parse(code)
        visitor = DefinitionVisitor("test.py")
        visitor.visit(tree)

        assert len(visitor.functions) == 2
        names = [f["name"] for f in visitor.functions]
        assert "foo" in names
        assert "bar" in names

    def test_definition_visitor_classes(self):
        """Test DefinitionVisitor finds classes."""
        import ast

        from code_audit import DefinitionVisitor

        code = """
class Foo:
    pass

class Bar:
    def method(self):
        pass
"""
        tree = ast.parse(code)
        visitor = DefinitionVisitor("test.py")
        visitor.visit(tree)

        assert len(visitor.classes) == 2
        names = [c["name"] for c in visitor.classes]
        assert "Foo" in names
        assert "Bar" in names

    def test_definition_visitor_imports(self):
        """Test DefinitionVisitor finds imports."""
        import ast

        from code_audit import DefinitionVisitor

        code = """
import os
from pathlib import Path
from typing import List, Dict
"""
        tree = ast.parse(code)
        visitor = DefinitionVisitor("test.py")
        visitor.visit(tree)

        assert len(visitor.imports) == 4  # os, Path, List, Dict
        names = [i["name"] for i in visitor.imports]
        assert "os" in names
        assert "Path" in names

    def test_usage_visitor(self):
        """Test UsageVisitor collects usages."""
        import ast

        from code_audit import UsageVisitor

        code = """
x = os.path.join("a", "b")
y = foo()
z = obj.method()
"""
        tree = ast.parse(code)
        visitor = UsageVisitor()
        visitor.visit(tree)

        assert "os" in visitor.names_used
        assert "foo" in visitor.names_used
        assert "join" in visitor.attributes_used
        assert "method" in visitor.attributes_used

    def test_unreachable_code_visitor(self):
        """Test UnreachableCodeVisitor finds unreachable code."""
        import ast

        from code_audit import UnreachableCodeVisitor

        code = """
def foo():
    return 1
    x = 2  # unreachable
"""
        tree = ast.parse(code)
        visitor = UnreachableCodeVisitor("test.py")
        visitor.visit(tree)

        assert len(visitor.unreachable) == 1
        assert visitor.unreachable[0].line_number == 4


class TestFindUnusedImports:
    """Tests for find_unused_imports.py"""

    def test_unused_import_dataclass(self):
        """Test UnusedImport dataclass."""
        from find_unused_imports import UnusedImport

        item = UnusedImport(
            file_path="test.py",
            line_number=1,
            import_name="os",
            full_import="import os",
            tool="ruff",
        )
        assert item.file_path == "test.py"
        d = item.to_dict()
        assert d["tool"] == "ruff"

    def test_cross_reference_results(self):
        """Test cross_reference_results combines results."""
        from find_unused_imports import UnusedImport, cross_reference_results

        ruff_results = [
            UnusedImport("a.py", 1, "os", "import os", "ruff"),
            UnusedImport("b.py", 2, "sys", "import sys", "ruff"),
        ]
        vulture_results = [
            UnusedImport("a.py", 1, "os", "import os", "vulture"),
        ]

        combined = cross_reference_results(ruff_results, vulture_results)

        # os should be found by both tools
        os_item = next(i for i in combined if i.import_name == "os")
        assert "multiple" in os_item.tool


class TestAnalyzeFunctionUsage:
    """Tests for analyze_function_usage.py"""

    def test_function_def_dataclass(self):
        """Test FunctionDef dataclass."""
        from analyze_function_usage import FunctionDef

        func = FunctionDef(
            name="foo",
            file_path="test.py",
            line_number=10,
            end_line=20,
            is_method=False,
            is_private=False,
            decorators=[],
            class_name=None,
        )
        assert func.qualified_name == "foo"

        method = FunctionDef(
            name="bar",
            file_path="test.py",
            line_number=30,
            end_line=40,
            is_method=True,
            is_private=True,
            decorators=["staticmethod"],
            class_name="MyClass",
        )
        assert method.qualified_name == "MyClass.bar"

    def test_usage_report_summary(self):
        """Test UsageReport summary generation."""
        from analyze_function_usage import UsageReport

        report = UsageReport(
            total_functions=100,
            entry_points=20,
            reachable=80,
        )

        summary = report.get_summary()
        assert "FUNCTION USAGE ANALYSIS" in summary
        assert "100" in summary


class TestFindDuplicates:
    """Tests for find_duplicates.py"""

    def test_code_location_line_count(self):
        """Test CodeLocation line count calculation."""
        from find_duplicates import CodeLocation

        loc = CodeLocation(file_path="test.py", start_line=10, end_line=20)
        assert loc.line_count == 11

    def test_duplicate_group_savings(self):
        """Test DuplicateGroup potential_savings calculation."""
        from find_duplicates import CodeLocation, DuplicateGroup

        # Single occurrence - no savings
        group1 = DuplicateGroup(
            code_hash="abc123",
            occurrences=[CodeLocation("a.py", 1, 10)],
            line_count=10,
        )
        assert group1.potential_savings <= 0

        # Multiple occurrences - savings possible
        group2 = DuplicateGroup(
            code_hash="abc123",
            occurrences=[
                CodeLocation("a.py", 1, 10),
                CodeLocation("b.py", 1, 10),
                CodeLocation("c.py", 1, 10),
            ],
            line_count=10,
        )
        # 2 copies can be removed (3-1) * 10 lines - 3 overhead = 17
        assert group2.potential_savings > 0


class TestRemoveDeadCode:
    """Tests for remove_dead_code.py"""

    def test_removal_result_dataclass(self):
        """Test RemovalResult dataclass."""
        from remove_dead_code import RemovalResult

        result = RemovalResult(
            success=True,
            file_path="test.py",
            name="unused_import",
            code_type="import",
            lines_removed=1,
            tests_passed=True,
        )
        assert result.success
        assert result.lines_removed == 1

    def test_batch_removal_result_summary(self):
        """Test BatchRemovalResult summary."""
        from remove_dead_code import BatchRemovalResult, RemovalResult

        batch = BatchRemovalResult(
            total_attempted=10,
            successful=8,
            failed=2,
            test_failures=1,
            total_lines_removed=8,
        )
        batch.results.append(
            RemovalResult(
                success=True,
                file_path="a.py",
                name="x",
                code_type="import",
                lines_removed=1,
                tests_passed=True,
            )
        )

        summary = batch.get_summary()
        assert "DEAD CODE REMOVAL" in summary
        assert "8" in summary  # successful


class TestGenerateAuditReport:
    """Tests for generate_audit_report.py"""

    def test_count_lines(self):
        """Test count_lines function."""
        from generate_audit_report import count_lines

        # Create a temporary project structure
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            src_dir = project_root / "src" / "cv_generator"
            src_dir.mkdir(parents=True)

            # Create a test file
            test_file = src_dir / "test.py"
            test_file.write_text("# line 1\n# line 2\n# line 3\n")

            result = count_lines(project_root)
            assert result["file_count"] == 1
            assert result["total_lines"] == 3

    def test_format_text_report(self):
        """Test format_text_report function."""
        from generate_audit_report import format_text_report

        report = {
            "generated_at": "2024-01-01T00:00:00",
            "project_root": "/tmp/test",
            "code_stats": {"file_count": 10, "total_lines": 1000},
            "ruff_analysis": {
                "total_issues": 5,
                "unused_imports": 2,
                "unused_variables": 1,
                "import_order": 2,
            },
            "vulture_analysis": {"total_issues": 3},
            "function_analysis": {
                "total_functions": 50,
                "entry_points": 10,
                "reachable": 45,
                "potentially_unreachable": 5,
            },
            "duplicate_analysis": {
                "exact_duplicates": 2,
                "similar_functions": 3,
            },
            "summary": {
                "estimated_removable_lines": 10,
                "potential_reduction_pct": 1.0,
                "action_items": ["Remove unused imports"],
            },
        }

        output = format_text_report(report)
        assert "CV GENERATOR CODE AUDIT REPORT" in output
        assert "1000" in output
        assert "Remove unused imports" in output
