"""Check function and method names through the TypeScript syntax tree."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _frontend_common import SRC, Violation, finish, node_position, node_text, source_files, trees, walk


def main() -> int:
    """Report named functions and methods that are not camelCase or PascalCase constructors."""
    violations: list[Violation] = []
    for path in source_files(SRC):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx", ".vue"}:
            continue
        try:
            for root, source, offset in trees(path):
                for node in walk(root):
                    if node.type not in {"function_declaration", "method_definition", "method_signature"}:
                        continue
                    name = node.child_by_field_name("name")
                    value = node_text(source, name) if name else ""
                    if value and not re.fullmatch(r"[a-z][A-Za-z0-9]*", value) and value not in {"constructor"}:
                        line, column = node_position(path, source, name or node, offset)
                        violations.append(Violation("symbol-naming", path, f"function {value!r} must use camelCase", line, column))
        except Exception:
            return 2
    return finish(violations)


if __name__ == "__main__":
    raise SystemExit(main())
