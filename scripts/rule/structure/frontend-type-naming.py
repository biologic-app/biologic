"""Check TypeScript declaration names using Tree-sitter syntax nodes."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _frontend_common import SRC, Violation, finish, node_position, node_text, trees, walk, source_files


def main() -> int:
    """Report non-PascalCase classes, interfaces, type aliases, and enums."""
    violations: list[Violation] = []
    for path in source_files(SRC):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx", ".vue"}:
            continue
        try:
            for root, source, offset in trees(path):
                for node in walk(root):
                    if node.type not in {"class_declaration", "interface_declaration", "type_alias_declaration", "enum_declaration"}:
                        continue
                    name = node.child_by_field_name("name")
                    value = node_text(source, name) if name else ""
                    if value and not re.fullmatch(r"[A-Z][A-Za-z0-9]*", value):
                        line, column = node_position(path, source, name or node, offset)
                        violations.append(Violation("type-naming", path, f"{node.type} {value!r} must use PascalCase", line, column))
        except Exception as exc:
            return 2 if not violations else finish(violations)
    return finish(violations)


if __name__ == "__main__":
    raise SystemExit(main())
