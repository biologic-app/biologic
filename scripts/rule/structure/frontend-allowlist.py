"""Validate documented technical exclusions and required frontend directories."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _frontend_common import FRONTEND, Violation, finish


def main() -> int:
    """Check that mandatory frontend roots exist and generated code is isolated."""
    violations: list[Violation] = []
    for relative in ("src", "src/app", "src/modules", "src/shared", "tests"):
        path = FRONTEND / relative
        if not path.is_dir():
            violations.append(Violation("allowlist", path, "required frontend directory is missing"))
    generated = FRONTEND / "src/shared/api/generated"
    if generated.exists():
        for path in generated.rglob("*.ts"):
            if not path.name.endswith(".gen.ts") and path.name != "index.ts":
                violations.append(Violation("allowlist", path, "generated API source must use .gen.ts or index.ts"))
    return finish(violations)


if __name__ == "__main__":
    raise SystemExit(main())
