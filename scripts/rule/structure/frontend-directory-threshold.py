"""Check the normative maximum of seven meaningful direct source files."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _frontend_common import FRONTEND, Violation, finish
from _frontend_paths import meaningful_files


def main() -> int:
    """Check every non-technical frontend directory and report overfull ones."""
    violations: list[Violation] = []
    for directory in sorted(p for p in (FRONTEND / "src").rglob("*") if p.is_dir()):
        files = meaningful_files(directory)
        if len(files) > 7:
            violations.append(Violation("directory-threshold", directory, f"contains {len(files)} meaningful source files; maximum is 7"))
    return finish(violations)


if __name__ == "__main__":
    raise SystemExit(main())
