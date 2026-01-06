"""
Static analysis tool for finding unused code.

Uses multiple analysis methods:
1. AST parsing for function/class definitions
2. Import analysis for unused imports
3. Call graph analysis for unused functions
4. Coverage analysis for unreachable code

Usage:
    python -m scripts.code_audit [--project-root PATH] [--output-format json|text]
"""

import ast
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class UnusedCode:
    """Represents a piece of unused code."""

    file_path: str
    line_number: int
    code_type: str  # "function", "class", "import", "variable"
    name: str
    reason: str
    confidence: str  # "high", "medium", "low"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_type": self.code_type,
            "name": self.name,
            "reason": self.reason,
            "confidence": self.confidence,
        }


@dataclass
class AuditReport:
    """Complete audit report."""

    unused_functions: List[UnusedCode] = field(default_factory=list)
    unused_classes: List[UnusedCode] = field(default_factory=list)
    unused_imports: List[UnusedCode] = field(default_factory=list)
    unused_variables: List[UnusedCode] = field(default_factory=list)
    unreachable_code: List[UnusedCode] = field(default_factory=list)
    duplicate_code: List[Dict[str, Any]] = field(default_factory=list)
    total_lines: int = 0
    removable_lines: int = 0

    def get_summary(self) -> str:
        """Human-readable summary."""
        total_issues = (
            len(self.unused_functions)
            + len(self.unused_classes)
            + len(self.unused_imports)
            + len(self.unused_variables)
            + len(self.unreachable_code)
        )

        lines = [
            "=" * 60,
            "CODE AUDIT REPORT",
            "=" * 60,
            f"Total lines analyzed: {self.total_lines}",
            f"Estimated removable lines: {self.removable_lines}",
            f"Potential reduction: {self._calc_reduction():.1f}%",
            "",
            "FINDINGS:",
            f"  - Unused imports: {len(self.unused_imports)}",
            f"  - Unused functions: {len(self.unused_functions)}",
            f"  - Unused classes: {len(self.unused_classes)}",
            f"  - Unused variables: {len(self.unused_variables)}",
            f"  - Unreachable code: {len(self.unreachable_code)}",
            f"  - Duplicate code blocks: {len(self.duplicate_code)}",
            "",
            f"Total issues: {total_issues}",
            "=" * 60,
        ]
        return "\n".join(lines)

    def _calc_reduction(self) -> float:
        """Calculate percentage reduction."""
        if self.total_lines == 0:
            return 0.0
        return (self.removable_lines / self.total_lines) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "unused_functions": [u.to_dict() for u in self.unused_functions],
            "unused_classes": [u.to_dict() for u in self.unused_classes],
            "unused_imports": [u.to_dict() for u in self.unused_imports],
            "unused_variables": [u.to_dict() for u in self.unused_variables],
            "unreachable_code": [u.to_dict() for u in self.unreachable_code],
            "duplicate_code": self.duplicate_code,
            "total_lines": self.total_lines,
            "removable_lines": self.removable_lines,
            "summary": {
                "total_issues": (
                    len(self.unused_functions)
                    + len(self.unused_classes)
                    + len(self.unused_imports)
                    + len(self.unused_variables)
                    + len(self.unreachable_code)
                ),
                "potential_reduction_pct": self._calc_reduction(),
            },
        }


class DefinitionVisitor(ast.NodeVisitor):
    """AST visitor to collect definitions."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.functions: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.imports: List[Dict[str, Any]] = []
        self._class_stack: List[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        self.functions.append(
            {
                "name": node.name,
                "file_path": self.file_path,
                "line_number": node.lineno,
                "end_line": node.end_lineno or node.lineno,
                "is_method": len(self._class_stack) > 0,
                "is_private": node.name.startswith("_"),
                "decorators": decorators,
                "class_name": self._class_stack[-1] if self._class_stack else None,
            }
        )
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        # Treat same as regular function
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        self.functions.append(
            {
                "name": node.name,
                "file_path": self.file_path,
                "line_number": node.lineno,
                "end_line": node.end_lineno or node.lineno,
                "is_method": len(self._class_stack) > 0,
                "is_private": node.name.startswith("_"),
                "decorators": decorators,
                "class_name": self._class_stack[-1] if self._class_stack else None,
            }
        )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition."""
        self.classes.append(
            {
                "name": node.name,
                "file_path": self.file_path,
                "line_number": node.lineno,
                "end_line": node.end_lineno or node.lineno,
                "is_private": node.name.startswith("_"),
            }
        )
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statement."""
        for alias in node.names:
            self.imports.append(
                {
                    "name": alias.asname or alias.name,
                    "module": alias.name,
                    "file_path": self.file_path,
                    "line_number": node.lineno,
                    "is_from": False,
                }
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from...import statement."""
        module = node.module or ""
        for alias in node.names:
            self.imports.append(
                {
                    "name": alias.asname or alias.name,
                    "module": f"{module}.{alias.name}",
                    "file_path": self.file_path,
                    "line_number": node.lineno,
                    "is_from": True,
                }
            )
        self.generic_visit(node)

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Extract decorator name from AST node."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr
        elif isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return "unknown"


class UsageVisitor(ast.NodeVisitor):
    """AST visitor to collect usages of names."""

    def __init__(self):
        self.names_used: Set[str] = set()
        self.attributes_used: Set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        """Visit name reference."""
        if isinstance(node.ctx, ast.Load):
            self.names_used.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Visit attribute reference."""
        self.attributes_used.add(node.attr)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call."""
        if isinstance(node.func, ast.Name):
            self.names_used.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.attributes_used.add(node.func.attr)
        self.generic_visit(node)


class UnreachableCodeVisitor(ast.NodeVisitor):
    """Find code that is unreachable."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.unreachable: List[UnusedCode] = []

    def _check_statements(self, stmts: List[ast.stmt]) -> None:
        """Check a list of statements for unreachable code."""
        found_terminator = False
        for stmt in stmts:
            if found_terminator:
                self.unreachable.append(
                    UnusedCode(
                        file_path=self.file_path,
                        line_number=stmt.lineno,
                        code_type="unreachable",
                        name=f"Code at line {stmt.lineno}",
                        reason="Code appears after return/raise/break/continue",
                        confidence="high",
                    )
                )
            if isinstance(stmt, (ast.Return, ast.Raise)):
                found_terminator = True
            elif isinstance(stmt, (ast.Break, ast.Continue)):
                found_terminator = True
            else:
                self.visit(stmt)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function body."""
        self._check_statements(node.body)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function body."""
        self._check_statements(node.body)

    def visit_If(self, node: ast.If) -> None:
        """Check if statement bodies."""
        self._check_statements(node.body)
        self._check_statements(node.orelse)

    def visit_For(self, node: ast.For) -> None:
        """Check for loop body."""
        self._check_statements(node.body)
        self._check_statements(node.orelse)

    def visit_While(self, node: ast.While) -> None:
        """Check while loop body."""
        self._check_statements(node.body)
        self._check_statements(node.orelse)

    def visit_Try(self, node: ast.Try) -> None:
        """Check try block bodies."""
        self._check_statements(node.body)
        for handler in node.handlers:
            self._check_statements(handler.body)
        self._check_statements(node.orelse)
        self._check_statements(node.finalbody)


class CodeAuditor:
    """Main auditor class."""

    # Decorators that indicate an entry point
    ENTRY_POINT_DECORATORS = {
        "route",
        "get",
        "post",
        "put",
        "delete",
        "patch",
        "command",
        "group",
        "cli",
        "app_command",
        "fixture",
        "pytest_fixture",
        "property",
        "staticmethod",
        "classmethod",
        "abstractmethod",
    }

    # Magic methods that should not be flagged as unused
    MAGIC_METHODS = {
        "__init__",
        "__new__",
        "__del__",
        "__repr__",
        "__str__",
        "__bytes__",
        "__format__",
        "__hash__",
        "__bool__",
        "__eq__",
        "__ne__",
        "__lt__",
        "__le__",
        "__gt__",
        "__ge__",
        "__getattr__",
        "__setattr__",
        "__delattr__",
        "__getitem__",
        "__setitem__",
        "__delitem__",
        "__len__",
        "__iter__",
        "__next__",
        "__contains__",
        "__call__",
        "__enter__",
        "__exit__",
        "__add__",
        "__sub__",
        "__mul__",
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.all_definitions: Dict[str, List[Dict[str, Any]]] = {
            "functions": [],
            "classes": [],
            "imports": [],
        }
        self.all_usages: Dict[str, Set[str]] = {
            "names": set(),
            "attributes": set(),
        }
        self.total_lines = 0

    def audit(self) -> AuditReport:
        """Run complete audit and return report."""
        self._collect_definitions()
        self._collect_usages()
        return self._generate_report()

    def _collect_definitions(self) -> None:
        """Parse all Python files for definitions."""
        src_dir = self.project_root / "src" / "cv_generator"
        for py_file in src_dir.rglob("*.py"):
            self._parse_file_for_definitions(py_file)

    def _collect_usages(self) -> None:
        """Parse all Python files for usages."""
        # Collect from src directory
        src_dir = self.project_root / "src" / "cv_generator"
        for py_file in src_dir.rglob("*.py"):
            self._parse_file_for_usages(py_file)

        # Also collect from tests
        tests_dir = self.project_root / "tests"
        if tests_dir.exists():
            for py_file in tests_dir.rglob("*.py"):
                self._parse_file_for_usages(py_file)

    def _parse_file_for_definitions(self, file_path: Path) -> None:
        """Parse a single file for definitions."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.total_lines += content.count("\n") + 1

            tree = ast.parse(content, filename=str(file_path))
            rel_path = str(file_path.relative_to(self.project_root))
            visitor = DefinitionVisitor(rel_path)
            visitor.visit(tree)

            self.all_definitions["functions"].extend(visitor.functions)
            self.all_definitions["classes"].extend(visitor.classes)
            self.all_definitions["imports"].extend(visitor.imports)

        except SyntaxError as e:
            print(f"Warning: Syntax error in {file_path}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Error parsing {file_path}: {e}", file=sys.stderr)

    def _parse_file_for_usages(self, file_path: Path) -> None:
        """Parse a single file for usages."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            visitor = UsageVisitor()
            visitor.visit(tree)

            self.all_usages["names"].update(visitor.names_used)
            self.all_usages["attributes"].update(visitor.attributes_used)

        except Exception:
            pass  # Skip files that can't be parsed

    def _generate_report(self) -> AuditReport:
        """Generate the audit report."""
        report = AuditReport(total_lines=self.total_lines)

        report.unused_imports = self._find_unused_imports()
        report.unused_functions = self._find_unused_functions()
        report.unused_classes = self._find_unused_classes()
        report.unreachable_code = self._find_unreachable_code()

        # Estimate removable lines
        report.removable_lines = sum(
            1 for _ in report.unused_imports
        ) + sum(
            f.get("lines", 1) for f in self._estimate_function_lines(report.unused_functions)
        )

        return report

    def _find_unused_imports(self) -> List[UnusedCode]:
        """Find imports that are never used."""
        unused = []
        for imp in self.all_definitions["imports"]:
            name = imp["name"]
            # Check if the imported name is used anywhere
            if (
                name not in self.all_usages["names"]
                and name not in self.all_usages["attributes"]
            ):
                unused.append(
                    UnusedCode(
                        file_path=imp["file_path"],
                        line_number=imp["line_number"],
                        code_type="import",
                        name=name,
                        reason=f"Import '{name}' is never used in the codebase",
                        confidence="high",
                    )
                )
        return unused

    def _find_unused_functions(self) -> List[UnusedCode]:
        """Find functions that are never called."""
        unused = []
        for func in self.all_definitions["functions"]:
            name = func["name"]

            # Skip magic methods
            if name in self.MAGIC_METHODS:
                continue

            # Skip entry points (decorated functions)
            if any(d in self.ENTRY_POINT_DECORATORS for d in func.get("decorators", [])):
                continue

            # Skip test functions
            if name.startswith("test_"):
                continue

            # Check if the function is used
            if name not in self.all_usages["names"] and name not in self.all_usages["attributes"]:
                confidence = "medium" if func.get("is_private") else "low"
                unused.append(
                    UnusedCode(
                        file_path=func["file_path"],
                        line_number=func["line_number"],
                        code_type="function",
                        name=name,
                        reason=f"Function '{name}' appears to be unused",
                        confidence=confidence,
                    )
                )
        return unused

    def _find_unused_classes(self) -> List[UnusedCode]:
        """Find classes that are never instantiated or referenced."""
        unused = []
        for cls in self.all_definitions["classes"]:
            name = cls["name"]

            # Check if the class is used
            if name not in self.all_usages["names"] and name not in self.all_usages["attributes"]:
                confidence = "medium" if cls.get("is_private") else "low"
                unused.append(
                    UnusedCode(
                        file_path=cls["file_path"],
                        line_number=cls["line_number"],
                        code_type="class",
                        name=name,
                        reason=f"Class '{name}' appears to be unused",
                        confidence=confidence,
                    )
                )
        return unused

    def _find_unreachable_code(self) -> List[UnusedCode]:
        """Find code after return/raise statements."""
        unreachable = []
        src_dir = self.project_root / "src" / "cv_generator"
        for py_file in src_dir.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                tree = ast.parse(content, filename=str(py_file))
                rel_path = str(py_file.relative_to(self.project_root))
                visitor = UnreachableCodeVisitor(rel_path)
                visitor.visit(tree)
                unreachable.extend(visitor.unreachable)
            except Exception:
                pass
        return unreachable

    def _estimate_function_lines(
        self, unused_funcs: List[UnusedCode]
    ) -> List[Dict[str, Any]]:
        """Estimate lines for unused functions."""
        result = []
        func_map = {
            (f["file_path"], f["line_number"]): f for f in self.all_definitions["functions"]
        }
        for uc in unused_funcs:
            key = (uc.file_path, uc.line_number)
            if key in func_map:
                func = func_map[key]
                lines = func.get("end_line", func["line_number"]) - func["line_number"] + 1
                result.append({"name": uc.name, "lines": lines})
            else:
                result.append({"name": uc.name, "lines": 1})
        return result


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Code audit tool for CV Generator")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory",
    )
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        help="Output file (default: stdout)",
    )

    args = parser.parse_args()

    auditor = CodeAuditor(args.project_root)
    report = auditor.audit()

    if args.output_format == "json":
        output = json.dumps(report.to_dict(), indent=2)
    else:
        output = report.get_summary()

        # Add details
        if report.unused_imports:
            output += "\n\nUNUSED IMPORTS:\n"
            for item in report.unused_imports:
                output += f"  {item.file_path}:{item.line_number} - {item.name}\n"

        if report.unused_functions:
            output += "\n\nPOTENTIALLY UNUSED FUNCTIONS:\n"
            for item in report.unused_functions:
                output += f"  {item.file_path}:{item.line_number} - {item.name} ({item.confidence})\n"

        if report.unused_classes:
            output += "\n\nPOTENTIALLY UNUSED CLASSES:\n"
            for item in report.unused_classes:
                output += f"  {item.file_path}:{item.line_number} - {item.name} ({item.confidence})\n"

        if report.unreachable_code:
            output += "\n\nUNREACHABLE CODE:\n"
            for item in report.unreachable_code:
                output += f"  {item.file_path}:{item.line_number}\n"

    if args.output_file:
        args.output_file.write_text(output)
        print(f"Report written to {args.output_file}")
    else:
        print(output)


if __name__ == "__main__":
    main()
