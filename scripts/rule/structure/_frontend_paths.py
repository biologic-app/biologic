"""Small shared path and import-graph helpers for filesystem rules."""

from __future__ import annotations

from pathlib import Path

from _frontend_common import FRONTEND, SRC, TECHNICAL_PARTS, SOURCE_SUFFIXES, source_files


def frontend_path(path: Path) -> str:
    """Return a stable repository-relative path for a frontend file."""
    return str(path.relative_to(FRONTEND.parent))


def meaningful_files(directory: Path) -> list[Path]:
    """Return direct source files that count toward the seven-file threshold."""
    return sorted(
        path for path in directory.iterdir()
        if path.is_file() and path.suffix in SOURCE_SUFFIXES and not (TECHNICAL_PARTS & set(path.parts))
    )


def allowed_layer(path: Path) -> str:
    """Classify an src path into the normative architecture layer."""
    relative = path.relative_to(SRC)
    return relative.parts[0] if relative.parts else "src"
