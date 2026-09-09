"""Check Vue component filenames and script declarations."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _frontend_common import SRC, Violation, finish, source_files


def main() -> int:
    """Check that Vue component filenames use PascalCase and route pages use Page suffix."""
    violations: list[Violation] = []
    for path in source_files(SRC):
        if path.suffix != ".vue":
            continue
        stem = path.stem
        if not re.fullmatch(r"[A-Z][A-Za-z0-9]*", stem):
            violations.append(Violation("component-naming", path, f"component {stem!r} must use PascalCase"))
        if path.parent.name == "pages" and path.parent.parent.name == "modules" and not stem.endswith("Page"):
            violations.append(Violation("component-naming", path, "module route component must end with Page"))
    return finish(violations)


if __name__ == "__main__":
    raise SystemExit(main())
