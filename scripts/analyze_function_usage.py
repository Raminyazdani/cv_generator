"""
Analyze function call graphs to find unused functions.

Builds a call graph and identifies functions that are never called
from any entry point.

Usage:
    python -m scripts.analyze_function_usage [--project-root PATH]
"""

import ast
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class FunctionDef:
    """Represents a function definition."""

    name: str
    file_path: str
    line_number: int
    end_line: int
    is_method: bool
    is_private: bool  # starts with _
    decorators: List[str]
    class_name: Optional[str]
    docstring: Optional[str] = None

    @property
    def qualified_name(self) -> str:
        """Get fully qualified name."""
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name


@dataclass
class UsageReport:
    """Report of function usage analysis."""

    total_functions: int = 0
    entry_points: int = 0
    reachable: int = 0
    unreachable_functions: List[FunctionDef] = field(default_factory=list)

    def get_summary(self) -> str:
        """Get human-readable summary."""
        lines = [
            "=" * 60,
            "FUNCTION USAGE ANALYSIS",
            "=" * 60,
            f"Total functions: {self.total_functions}",
            f"Entry points: {self.entry_points}",
            f"Reachable functions: {self.reachable}",
            f"Potentially unreachable: {len(self.unreachable_functions)}",
            "=" * 60,
        ]
        return "\n".join(lines)


class FunctionCallVisitor(ast.NodeVisitor):
    """Collect function calls from AST."""

    def __init__(self):
        self.calls: Set[str] = set()
        self._class_stack: List[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call."""
        if isinstance(node.func, ast.Name):
            self.calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.add(node.func.attr)
            # Also add self.method calls
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "self":
                self.calls.add(node.func.attr)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Visit attribute access (could be method reference)."""
        self.calls.add(node.attr)
        self.generic_visit(node)


class FunctionUsageAnalyzer:
    """Build call graph and identify unused functions."""

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
        "option",
        "argument",
        "app_command",
        "fixture",
        "pytest_fixture",
        "property",
        "staticmethod",
        "classmethod",
        "abstractmethod",
        "contextmanager",
    }

    # Functions that are always entry points
    ENTRY_POINT_NAMES = {
        "main",
        "setup",
        "teardown",
        "run",
        "__init__",
        "__new__",
        "__del__",
        "__repr__",
        "__str__",
        "__eq__",
        "__hash__",
        "__len__",
        "__iter__",
        "__next__",
        "__getitem__",
        "__setitem__",
        "__contains__",
        "__call__",
        "__enter__",
        "__exit__",
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.definitions: Dict[str, FunctionDef] = {}
        self.calls: Dict[str, Set[str]] = defaultdict(set)
        self.entry_points: Set[str] = set()
        self.all_calls: Set[str] = set()

    def analyze(self) -> UsageReport:
        """Run analysis and return report."""
        self._parse_all_files()
        self._identify_entry_points()
        self._build_call_graph()
        return self._find_unreachable()

    def _parse_all_files(self) -> None:
        """Parse all Python files for function definitions and calls."""
        src_dir = self.project_root / "src" / "cv_generator"
        tests_dir = self.project_root / "tests"

        # Parse source files
        for py_file in src_dir.rglob("*.py"):
            self._parse_file(py_file)

        # Parse test files for calls (but not definitions to flag)
        if tests_dir.exists():
            for py_file in tests_dir.rglob("*.py"):
                self._parse_file_for_calls(py_file)

    def _parse_file(self, file_path: Path) -> None:
        """Parse a file for definitions and calls."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            rel_path = str(file_path.relative_to(self.project_root))

            # Collect definitions
            class_stack: List[str] = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_stack.append(node.name)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    decorators = []
                    for d in node.decorator_list:
                        if isinstance(d, ast.Name):
                            decorators.append(d.id)
                        elif isinstance(d, ast.Attribute):
                            decorators.append(d.attr)
                        elif isinstance(d, ast.Call):
                            if isinstance(d.func, ast.Name):
                                decorators.append(d.func.id)
                            elif isinstance(d.func, ast.Attribute):
                                decorators.append(d.func.attr)

                    # Get class context
                    class_name = None
                    for parent in ast.walk(tree):
                        if isinstance(parent, ast.ClassDef):
                            for child in ast.walk(parent):
                                if child is node:
                                    class_name = parent.name
                                    break

                    func_def = FunctionDef(
                        name=node.name,
                        file_path=rel_path,
                        line_number=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        is_method=class_name is not None,
                        is_private=node.name.startswith("_") and not node.name.startswith("__"),
                        decorators=decorators,
                        class_name=class_name,
                        docstring=ast.get_docstring(node),
                    )

                    key = f"{rel_path}:{node.name}"
                    if class_name:
                        key = f"{rel_path}:{class_name}.{node.name}"
                    self.definitions[key] = func_def

            # Collect calls
            visitor = FunctionCallVisitor()
            visitor.visit(tree)
            self.all_calls.update(visitor.calls)

        except Exception as e:
            print(f"Warning: Error parsing {file_path}: {e}", file=sys.stderr)

    def _parse_file_for_calls(self, file_path: Path) -> None:
        """Parse a file just for call information."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content, filename=str(file_path))
            visitor = FunctionCallVisitor()
            visitor.visit(tree)
            self.all_calls.update(visitor.calls)
        except Exception:
            pass

    def _identify_entry_points(self) -> None:
        """Identify entry points that must be kept."""
        for key, func_def in self.definitions.items():
            # Check for entry point decorators
            if any(d in self.ENTRY_POINT_DECORATORS for d in func_def.decorators):
                self.entry_points.add(key)
                continue

            # Check for entry point names
            if func_def.name in self.ENTRY_POINT_NAMES:
                self.entry_points.add(key)
                continue

            # Check for test functions
            if func_def.name.startswith("test_"):
                self.entry_points.add(key)
                continue

            # Check for magic methods
            if func_def.name.startswith("__") and func_def.name.endswith("__"):
                self.entry_points.add(key)
                continue

    def _build_call_graph(self) -> None:
        """Build graph of function calls."""
        # This is already done during parsing - all_calls contains all calls

    def _find_unreachable(self) -> UsageReport:
        """Find functions not reachable from any entry point."""
        unreachable = []

        for key, func_def in self.definitions.items():
            # Skip entry points
            if key in self.entry_points:
                continue

            # Check if function name is called anywhere
            if func_def.name not in self.all_calls:
                # Also check qualified name for methods
                if func_def.qualified_name not in self.all_calls:
                    unreachable.append(func_def)

        report = UsageReport(
            total_functions=len(self.definitions),
            entry_points=len(self.entry_points),
            reachable=len(self.definitions) - len(unreachable),
            unreachable_functions=unreachable,
        )

        return report


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze function usage")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory",
    )
    parser.add_argument(
        "--show-entry-points",
        action="store_true",
        help="Show identified entry points",
    )

    args = parser.parse_args()

    analyzer = FunctionUsageAnalyzer(args.project_root)
    report = analyzer.analyze()

    print(report.get_summary())

    if args.show_entry_points:
        print("\nENTRY POINTS:")
        for key in sorted(analyzer.entry_points):
            print(f"  {key}")

    if report.unreachable_functions:
        print("\nPOTENTIALLY UNREACHABLE FUNCTIONS:")
        for func in sorted(report.unreachable_functions, key=lambda f: f.file_path):
            confidence = "medium" if func.is_private else "low"
            print(f"  {func.file_path}:{func.line_number}")
            print(f"    Function: {func.qualified_name}")
            print(f"    Private: {func.is_private}")
            print(f"    Confidence: {confidence}")
            print()


if __name__ == "__main__":
    main()
