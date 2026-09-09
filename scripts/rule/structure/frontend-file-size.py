"""Check source file size limits while honoring technical-directory exclusions."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _frontend_common import SRC, TECHNICAL_PARTS, Violation, finish, source_files


def main() -> int:
    """Report non-technical source files over 500 lines or 30 KiB."""
    violations: list[Violation] = []
    for path in source_files(SRC):
        if TECHNICAL_PARTS.intersection(path.parts):
            continue
        lines = path.read_text(encoding="utf-8").count("\n") + 1
        size = path.stat().st_size
        if lines > 500 or size > 30 * 1024:
            violations.append(Violation("file-size", path, f"source file has {lines} lines and {size} bytes; limits are 500 lines and 30720 bytes"))
    return finish(violations)


if __name__ == "__main__":
    raise SystemExit(main())
