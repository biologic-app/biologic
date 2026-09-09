"""Check forbidden import directions with Tree-sitter import declarations."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _frontend_common import SRC, Violation, finish, node_text, source_files, trees, walk


def main() -> int:
    """Reject shared-to-feature and feature-to-feature-internal imports."""
    violations: list[Violation] = []
    for path in source_files(SRC):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx", ".vue"}:
            continue
        try:
            for root, source, offset in trees(path):
                for node in walk(root):
                    if node.type != "import_statement":
                        continue
                    text = node_text(source, node)
                    if path.parts and "shared" in path.parts and "@/modules/" in text:
                        line, column = node.start_point
                        violations.append(Violation("dependency-layers", path, "shared code must not import feature modules", line + 1, column))
                    if "modules" in path.parts:
                        feature_index = path.parts.index("modules") + 1
                        feature = path.parts[feature_index]
                        if f"@/modules/{feature}/" not in text and "@/modules/" in text:
                            line, column = node.start_point
                            violations.append(Violation("dependency-layers", path, "a module must not import another module's internals", line + 1, column))
        except Exception:
            return 2
    return finish(violations)


if __name__ == "__main__":
    raise SystemExit(main())
