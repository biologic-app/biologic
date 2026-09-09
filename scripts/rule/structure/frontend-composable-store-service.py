"""Check semantic placement of composables, stores, and services."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _frontend_common import SRC, Violation, finish, source_files, trees, walk


def main() -> int:
    """Use paths plus AST calls to keep stores and composables distinct."""
    violations: list[Violation] = []
    for path in source_files(SRC):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx", ".vue"}:
            continue
        try:
            has_store = any(n.type == "call_expression" and n.child_by_field_name("function") and "defineStore" in n.child_by_field_name("function").text.decode() for root, _, _ in trees(path) for n in walk(root))
        except Exception:
            return 2
        if has_store and "stores" not in path.parts and path.name != "index.ts":
            violations.append(Violation("composable-store-service", path, "defineStore must be declared in a stores directory"))
        if path.parent.name == "services" and not path.name.endswith(".service.ts"):
            violations.append(Violation("composable-store-service", path, "service file must end with .service.ts"))
        if path.parent.name == "composables" and not path.name.startswith("use"):
            violations.append(Violation("composable-store-service", path, "composable file must start with use"))
    return finish(violations)


if __name__ == "__main__":
    raise SystemExit(main())
