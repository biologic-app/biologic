"""Check frontend source file naming conventions."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _frontend_common import SRC, Violation, finish, source_files


def expected(path: Path) -> bool:
    """Return whether a source filename matches its directory convention."""
    name = path.name
    if name in {"main.ts", "sw.ts", "vite-env.d.ts", "registerServiceWorker.ts", "vue-router.d.ts"}:
        return True
    if path.suffix == ".css":
        return bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*\.css", name)) or name == "index.css"
    if name == "index.ts" or name.endswith(".gen.ts"):
        return True
    if path.suffix == ".vue":
        return bool(re.fullmatch(r"[A-Z][A-Za-z0-9]*\.vue", name))
    if path.parent.name == "composables":
        return bool(re.fullmatch(r"use[A-Z][A-Za-z0-9]*\.ts", name))
    if path.parent.name == "stores":
        return bool(re.fullmatch(r"use[A-Z][A-Za-z0-9]*(\.store)?\.ts", name))
    if path.name.endswith(".api.ts") or path.name.endswith(".service.ts"):
        return bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*\.(api|service)\.ts", name))
    return bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*(?:\.[a-z0-9-]+)?\.ts", name))


def main() -> int:
    """Check all source filenames, excluding generated and technical paths."""
    violations = [Violation("file-naming", path, "filename does not follow the normative convention") for path in source_files(SRC) if not expected(path)]
    return finish(violations)


if __name__ == "__main__":
    raise SystemExit(main())
