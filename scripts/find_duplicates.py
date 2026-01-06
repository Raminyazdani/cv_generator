"""
Find duplicate or near-duplicate code blocks.

Uses hash comparison and sequence matching to find similar code.

Usage:
    python -m scripts.find_duplicates [--project-root PATH]
"""

import ast
import hashlib
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class CodeLocation:
    """Location of a code block."""

    file_path: str
    start_line: int
    end_line: int

    @property
    def line_count(self) -> int:
        return self.end_line - self.start_line + 1


@dataclass
class DuplicateGroup:
    """A group of duplicate code blocks."""

    code_hash: str
    occurrences: List[CodeLocation] = field(default_factory=list)
    line_count: int = 0
    sample_code: str = ""

    @property
    def potential_savings(self) -> int:
        """Calculate lines that could be saved by consolidation."""
        if len(self.occurrences) <= 1:
            return 0
        # Can save all but one occurrence, minus overhead for abstraction
        return (len(self.occurrences) - 1) * self.line_count - 3  # -3 for function overhead


@dataclass
class SimilarGroup:
    """A group of similar (but not identical) code blocks."""

    locations: List[CodeLocation] = field(default_factory=list)
    similarity: float = 0.0
    sample_code_a: str = ""
    sample_code_b: str = ""


@dataclass
class ConsolidationSuggestion:
    """Suggestion for consolidating duplicate code."""

    duplicates: DuplicateGroup
    suggested_location: str
    suggested_name: str
    estimated_savings: int


class DuplicateFinder:
    """Find duplicate code for consolidation."""

    def __init__(self, project_root: Path, min_lines: int = 5):
        self.project_root = project_root
        self.min_lines = min_lines
        self._blocks: List[Dict[str, Any]] = []

    def find_exact_duplicates(self) -> List[DuplicateGroup]:
        """Find exactly identical code blocks."""
        self._collect_blocks()

        # Group by hash
        hash_groups: Dict[str, List[Dict[str, Any]]] = {}
        for block in self._blocks:
            h = block["hash"]
            if h not in hash_groups:
                hash_groups[h] = []
            hash_groups[h].append(block)

        # Convert to DuplicateGroup objects
        duplicates = []
        for h, blocks in hash_groups.items():
            if len(blocks) > 1:
                group = DuplicateGroup(
                    code_hash=h,
                    occurrences=[
                        CodeLocation(
                            file_path=b["file_path"],
                            start_line=b["start_line"],
                            end_line=b["end_line"],
                        )
                        for b in blocks
                    ],
                    line_count=blocks[0]["line_count"],
                    sample_code=blocks[0]["code"][:500],  # First 500 chars as sample
                )
                duplicates.append(group)

        return sorted(duplicates, key=lambda d: d.line_count * len(d.occurrences), reverse=True)

    def find_similar_blocks(
        self, similarity_threshold: float = 0.85
    ) -> List[SimilarGroup]:
        """Find near-duplicate blocks (>threshold similar)."""
        self._collect_blocks()

        similar_groups = []
        checked: Set[Tuple[str, str]] = set()

        for i, block_a in enumerate(self._blocks):
            for j, block_b in enumerate(self._blocks[i + 1 :], start=i + 1):
                # Skip if same file and overlapping
                if block_a["file_path"] == block_b["file_path"]:
                    if (
                        block_a["start_line"] <= block_b["end_line"]
                        and block_a["end_line"] >= block_b["start_line"]
                    ):
                        continue

                # Skip if already checked
                key = (block_a["hash"], block_b["hash"])
                if key in checked:
                    continue
                checked.add(key)

                # Compare
                similarity = SequenceMatcher(
                    None, block_a["code"], block_b["code"]
                ).ratio()

                if similarity >= similarity_threshold and similarity < 1.0:
                    similar_groups.append(
                        SimilarGroup(
                            locations=[
                                CodeLocation(
                                    file_path=block_a["file_path"],
                                    start_line=block_a["start_line"],
                                    end_line=block_a["end_line"],
                                ),
                                CodeLocation(
                                    file_path=block_b["file_path"],
                                    start_line=block_b["start_line"],
                                    end_line=block_b["end_line"],
                                ),
                            ],
                            similarity=similarity,
                            sample_code_a=block_a["code"][:200],
                            sample_code_b=block_b["code"][:200],
                        )
                    )

        return sorted(similar_groups, key=lambda s: s.similarity, reverse=True)

    def find_similar_functions(self) -> List[SimilarGroup]:
        """Find functions with similar logic."""
        src_dir = self.project_root / "src" / "cv_generator"
        functions: List[Dict[str, Any]] = []

        for py_file in src_dir.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content, filename=str(py_file))
                lines = content.split("\n")
                rel_path = str(py_file.relative_to(self.project_root))

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        start = node.lineno
                        end = node.end_lineno or start
                        if end - start + 1 >= self.min_lines:
                            code = "\n".join(lines[start - 1 : end])
                            functions.append(
                                {
                                    "name": node.name,
                                    "file_path": rel_path,
                                    "start_line": start,
                                    "end_line": end,
                                    "code": code,
                                }
                            )
            except Exception:
                continue

        # Compare functions
        similar = []
        checked: Set[Tuple[str, str]] = set()

        for i, func_a in enumerate(functions):
            for j, func_b in enumerate(functions[i + 1 :], start=i + 1):
                # Skip same function
                if func_a["name"] == func_b["name"] and func_a["file_path"] == func_b["file_path"]:
                    continue

                key = tuple(sorted([func_a["name"], func_b["name"]]))
                if key in checked:
                    continue
                checked.add(key)

                similarity = SequenceMatcher(
                    None, func_a["code"], func_b["code"]
                ).ratio()

                if similarity >= 0.8:
                    similar.append(
                        SimilarGroup(
                            locations=[
                                CodeLocation(
                                    file_path=func_a["file_path"],
                                    start_line=func_a["start_line"],
                                    end_line=func_a["end_line"],
                                ),
                                CodeLocation(
                                    file_path=func_b["file_path"],
                                    start_line=func_b["start_line"],
                                    end_line=func_b["end_line"],
                                ),
                            ],
                            similarity=similarity,
                            sample_code_a=f"{func_a['name']} in {func_a['file_path']}",
                            sample_code_b=f"{func_b['name']} in {func_b['file_path']}",
                        )
                    )

        return sorted(similar, key=lambda s: s.similarity, reverse=True)

    def suggest_consolidation(
        self, duplicates: List[DuplicateGroup]
    ) -> List[ConsolidationSuggestion]:
        """Suggest how to consolidate duplicates."""
        suggestions = []

        for dup in duplicates:
            if dup.potential_savings <= 0:
                continue

            # Suggest location based on most common directory
            dirs = [Path(loc.file_path).parent for loc in dup.occurrences]
            common_dir = max(set(dirs), key=dirs.count)

            # Generate a name
            suggested_name = f"_shared_block_{dup.code_hash[:8]}"

            suggestions.append(
                ConsolidationSuggestion(
                    duplicates=dup,
                    suggested_location=str(common_dir / "_shared.py"),
                    suggested_name=suggested_name,
                    estimated_savings=dup.potential_savings,
                )
            )

        return sorted(suggestions, key=lambda s: s.estimated_savings, reverse=True)

    def _collect_blocks(self) -> None:
        """Collect code blocks from all files."""
        if self._blocks:
            return  # Already collected

        src_dir = self.project_root / "src" / "cv_generator"

        for py_file in src_dir.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                rel_path = str(py_file.relative_to(self.project_root))

                # Collect function-sized blocks
                i = 0
                while i < len(lines):
                    # Look for blocks of min_lines or more
                    block_lines = []
                    start_line = i + 1

                    while i < len(lines) and len(block_lines) < self.min_lines * 2:
                        block_lines.append(lines[i])
                        i += 1

                    if len(block_lines) >= self.min_lines:
                        code = "".join(block_lines).strip()
                        if code:  # Non-empty
                            code_hash = hashlib.md5(code.encode()).hexdigest()
                            self._blocks.append(
                                {
                                    "file_path": rel_path,
                                    "start_line": start_line,
                                    "end_line": start_line + len(block_lines) - 1,
                                    "line_count": len(block_lines),
                                    "code": code,
                                    "hash": code_hash,
                                }
                            )

                    # Slide window
                    if i < len(lines):
                        i -= len(block_lines) - 1

            except Exception:
                continue


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Find duplicate code")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory",
    )
    parser.add_argument(
        "--min-lines",
        type=int,
        default=5,
        help="Minimum lines for a block (default: 5)",
    )
    parser.add_argument(
        "--functions-only",
        action="store_true",
        help="Only compare functions",
    )

    args = parser.parse_args()

    finder = DuplicateFinder(args.project_root, min_lines=args.min_lines)

    if args.functions_only:
        similar = finder.find_similar_functions()
        print(f"Found {len(similar)} similar function pairs:")
        for group in similar[:20]:  # Top 20
            print(f"\n  Similarity: {group.similarity:.1%}")
            print(f"    {group.sample_code_a}")
            print(f"    {group.sample_code_b}")
    else:
        duplicates = finder.find_exact_duplicates()
        print(f"Found {len(duplicates)} duplicate code groups:")
        for dup in duplicates[:10]:  # Top 10
            print(f"\n  Hash: {dup.code_hash[:8]}...")
            print(f"  Lines: {dup.line_count}")
            print(f"  Occurrences: {len(dup.occurrences)}")
            for loc in dup.occurrences:
                print(f"    - {loc.file_path}:{loc.start_line}-{loc.end_line}")

        # Suggestions
        suggestions = finder.suggest_consolidation(duplicates)
        if suggestions:
            print("\n\nCONSOLIDATION SUGGESTIONS:")
            for sug in suggestions[:5]:
                print(f"\n  Function: {sug.suggested_name}")
                print(f"  Location: {sug.suggested_location}")
                print(f"  Savings: ~{sug.estimated_savings} lines")


if __name__ == "__main__":
    main()
