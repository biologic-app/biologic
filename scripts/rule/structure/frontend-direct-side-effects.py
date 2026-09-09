"""Find direct network and browser-storage side effects in Vue components."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _frontend_common import SRC, Violation, finish, node_position, source_files, trees, walk


def main() -> int:
    """Reject fetch/localStorage calls in Vue files, except explicit infrastructure paths."""
    violations: list[Violation] = []
    for path in source_files(SRC):
        if path.suffix != ".vue":
            continue
        try:
            for root, source, offset in trees(path):
                for node in walk(root):
                    if node.type != "call_expression":
                        continue
                    function = node.child_by_field_name("function")
                    text = function.text.decode() if function else ""
                    if text in {"fetch", "localStorage.getItem", "localStorage.setItem"}:
                        line, column = node_position(path, source, node, offset)
                        violations.append(Violation("direct-side-effects", path, f"direct {text} is not allowed in Vue components", line, column))
        except Exception:
            return 2
    return finish(violations)


if __name__ == "__main__":
    raise SystemExit(main())
