"""Shared filesystem, diagnostic, and Tree-sitter helpers for frontend rules."""

from __future__ import annotations

import sys
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

try:
    from tree_sitter import Language, Node, Parser
    import tree_sitter_javascript
    import tree_sitter_typescript
except ImportError as exc:  # pragma: no cover - exercised when dependencies are absent
    Language = Node = Parser = None  # type: ignore[assignment,misc]
    tree_sitter_javascript = tree_sitter_typescript = None  # type: ignore[assignment]
    _TREE_SITTER_ERROR = exc
else:
    _TREE_SITTER_ERROR = None


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = Path(os.environ.get("FRONTEND_STRUCTURE_ROOT", str(ROOT / "frontend"))).resolve()
SRC = FRONTEND / "src"
TECHNICAL_PARTS = {
    "node_modules", ".git", "dist", "build", "dev-dist", "dist-ssr",
    "generated", "vendor", "coverage", "test-results", "playwright-report",
}
SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".vue", ".css"}


@dataclass(frozen=True)
class Violation:
    """One user-facing rule violation with an optional source position."""

    rule: str
    path: Path
    message: str
    line: int | None = None
    column: int | None = None

    def print(self) -> None:
        """Print the violation in the stable checker output format."""
        try:
            location = str(self.path.relative_to(ROOT))
        except ValueError:
            location = str(self.path)
        if self.line is not None:
            location += f":{self.line}:{(self.column or 0) + 1}"
        print(f"{location} [{self.rule}] {self.message}")


def finish(violations: list[Violation]) -> int:
    """Print violations and return the required checker exit code."""
    for violation in violations:
        violation.print()
    return 1 if violations else 0


def fail(message: str) -> int:
    """Print an internal checker error and return exit code 2."""
    print(f"[internal-error] {message}", file=sys.stderr)
    return 2


def is_technical(path: Path) -> bool:
    """Return whether a path belongs to an excluded technical directory."""
    return bool(TECHNICAL_PARTS.intersection(path.parts))


def source_files(root: Path = SRC) -> Iterator[Path]:
    """Yield non-technical frontend source files in deterministic order."""
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in SOURCE_SUFFIXES and not is_technical(path):
            yield path


def rel_line(source: str, offset: int) -> tuple[int, int]:
    """Convert a character offset to a one-based line and zero-based column."""
    line = source.count("\n", 0, offset) + 1
    previous = source.rfind("\n", 0, offset)
    return line, offset if previous < 0 else offset - previous - 1


def parser_for(path: Path) -> Parser:
    """Create a Tree-sitter parser for TypeScript or JavaScript source."""
    if _TREE_SITTER_ERROR is not None:
        raise RuntimeError(f"Tree-sitter dependencies are unavailable: {_TREE_SITTER_ERROR}")
    if path.suffix in {".js", ".jsx"}:
        language = Language(tree_sitter_javascript.language())
    elif path.suffix == ".tsx":
        language = Language(tree_sitter_typescript.language_tsx())
    else:
        language = Language(tree_sitter_typescript.language_typescript())
    return Parser(language)


def script_sources(path: Path) -> Iterable[tuple[str, int]]:
    """Yield Vue script blocks or complete TS/JS text with its source offset."""
    source = path.read_text(encoding="utf-8")
    if path.suffix != ".vue":
        yield source, 0
        return
    cursor = 0
    while True:
        start = source.find("<script", cursor)
        if start < 0:
            break
        open_end = source.find(">", start)
        close = source.find("</script>", open_end + 1)
        if open_end < 0 or close < 0:
            break
        yield source[open_end + 1:close], open_end + 1
        cursor = close + len("</script>")


def trees(path: Path) -> Iterator[tuple[Node, str, int]]:
    """Parse every TS/JS/Vue script block and yield tree, source, and offset."""
    if path.suffix not in {".ts", ".tsx", ".js", ".jsx", ".vue"}:
        return
    for source, offset in script_sources(path):
        tree = parser_for(path).parse(source.encode("utf-8"))
        yield tree.root_node, source, offset


def walk(node: Node) -> Iterator[Node]:
    """Yield a syntax-tree node and all descendants without recursion limits."""
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def node_position(path: Path, source: str, node: Node, offset: int = 0) -> tuple[int, int]:
    """Return a source position for a Tree-sitter node, including Vue offset."""
    line, column = rel_line(path.read_text(encoding="utf-8"), offset + node.start_byte)
    return line, column


def node_text(source: str, node: Node) -> str:
    """Return the exact UTF-8 text represented by a Tree-sitter node."""
    return source.encode("utf-8")[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
