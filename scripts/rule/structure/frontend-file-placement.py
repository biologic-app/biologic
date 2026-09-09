"""Check that frontend source files live in recognized architectural areas."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _frontend_common import SRC, Violation, finish, source_files


TOP = {"app", "pages", "modules", "shared"}
ALLOWED = {"api", "components", "composables", "data", "domain", "pages", "services", "stores", "types", "engine", "nodes", "ui", "config", "constants", "i18n", "icons", "tour", "utils", "generated", "core", "client", "layouts", "router", "store", "styles"}


def main() -> int:
    """Report source files under unknown top-level or semantic directories."""
    violations: list[Violation] = []
    for path in source_files(SRC):
        parts = path.relative_to(SRC).parts
        if parts[0] not in TOP and parts[0] not in {"main.ts", "sw.ts", "vite-env.d.ts"}:
            violations.append(Violation("file-placement", path, f"top-level directory {parts[0]!r} is not allowed"))
        for index, part in enumerate(parts[1:-1], start=1):
            # The first component below modules is the feature name, not a
            # semantic layer (for example modules/workflows/components).
            if parts[0] == "modules" and index == 1:
                continue
            if part.startswith(".") or part not in ALLOWED:
                violations.append(Violation("file-placement", path, f"directory {part!r} is not an approved semantic directory"))
                break
    return finish(violations)


if __name__ == "__main__":
    raise SystemExit(main())
