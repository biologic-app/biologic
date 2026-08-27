"""Database operations API: dump registry, export, upload, restore.

Storage split, deliberately: the dump *file* lives on the server filesystem
under ``APP_DATABASE_BACKUP_DIR``, and PostgreSQL keeps only the record that
points at it. That keeps multi-gigabyte payloads out of the database it is
supposed to back up, and lets an operator copy a dump off the box with `scp`.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.data_transfer import (
    DatabaseTransferError,
    backup_dir,
    build_filename,
    create_dump,
    database_overview,
    detect_format,
    pg_tools_available,
    preferred_format,
    restore_dump,
)
from src.core.config import get_settings
from src.core.cursor_pagination import json_value
from src.core.database import get_db_session
from src.core.errors import BadRequestError, NotFoundError
from src.core.pagination import PageMeta
from src.core.responses import ListResponse, ResponseMeta, SingleResponse
from src.infrastructure.db.models import DatabaseBackup
from src.infrastructure.repositories.database_backups import DatabaseBackupRepository
from src.presentation.http.access_control.dependencies import get_current_user_id

router = APIRouter(prefix="/database", tags=["database"])

# A restore replaces every application table, so the client has to say so in
# full words rather than by clicking through a default-valued flag.
RESTORE_CONFIRMATION = "RESTORE_DATABASE"

# Bytes read per chunk while streaming an upload to disk.
_UPLOAD_CHUNK = 1024 * 1024


async def get_backup_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DatabaseBackupRepository:
    return DatabaseBackupRepository(session=session)


def _serialize(backup: DatabaseBackup) -> dict[str, Any]:
    return {
        "id": json_value(backup.id),
        "filename": backup.filename,
        "file_path": backup.file_path,
        "format": backup.format,
        "origin": backup.origin,
        "status": backup.status,
        "size_bytes": backup.size_bytes,
        "duration_ms": backup.duration_ms,
        "error": backup.error,
        "created_by": json_value(backup.created_by),
        "created_at": json_value(backup.created_at),
        "completed_at": json_value(backup.completed_at),
        "restored_at": json_value(backup.restored_at),
        # The file can vanish underneath us (manual cleanup, a moved volume);
        # the UI must not offer download/restore for a record without bytes.
        "file_exists": Path(backup.file_path).exists(),
    }


@router.get("/status")
async def read_status(
    repository: Annotated[DatabaseBackupRepository, Depends(get_backup_repository)],
    _actor_id: Annotated[UUID, Depends(get_current_user_id)],
) -> SingleResponse[dict[str, Any]]:
    """Live facts about the target database and the dump storage behind it."""
    settings = get_settings()
    backups, total = await repository.list(limit=1)
    try:
        overview: dict[str, Any] = await database_overview()
        reachable = True
        error: str | None = None
    except DatabaseTransferError as exc:
        overview = {}
        reachable = False
        error = str(exc)
    return SingleResponse(
        data={
            **overview,
            "reachable": reachable,
            "error": error,
            "engine": preferred_format(),
            "pg_tools_available": pg_tools_available(),
            "backup_dir": str(backup_dir()),
            "backup_count": total,
            "last_backup_at": json_value(backups[0].created_at) if backups else None,
            "max_upload_mb": settings.database_backup_max_mb,
        },
        meta=ResponseMeta(),
    )


@router.get("/backups")
async def list_backups(
    repository: Annotated[DatabaseBackupRepository, Depends(get_backup_repository)],
    _actor_id: Annotated[UUID, Depends(get_current_user_id)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ListResponse[dict[str, Any]]:
    items, total = await repository.list(limit=limit)
    return ListResponse(
        items=[_serialize(item) for item in items],
        meta=PageMeta(
            total=total,
            limit=limit,
            next_cursor=None,
            has_more=total > len(items),
            includes_requested=[],
            includes_applied=[],
            includes_allowed=[],
        ),
    )


@router.post("/backups", status_code=status.HTTP_201_CREATED)
async def create_backup(
    repository: Annotated[DatabaseBackupRepository, Depends(get_backup_repository)],
    actor_id: Annotated[UUID, Depends(get_current_user_id)],
) -> SingleResponse[dict[str, Any]]:
    """Dump the database to a new file and register it."""
    fmt = preferred_format()
    filename = build_filename(fmt)
    path = backup_dir() / filename
    # The row is written *before* the dump so a crash mid-export leaves an
    # honest `in_progress` record instead of an invisible half-written file.
    backup = await repository.add(
        filename=filename,
        file_path=str(path),
        format=fmt,
        origin="export",
        status="in_progress",
        created_by=actor_id,
    )
    started = time.monotonic()
    try:
        await create_dump(path)
    except DatabaseTransferError as exc:
        path.unlink(missing_ok=True)
        await repository.update(
            backup,
            status="failed",
            error=str(exc),
            completed_at=datetime.now(UTC),
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        raise BadRequestError(str(exc)) from exc
    backup = await repository.update(
        backup,
        status="completed",
        size_bytes=path.stat().st_size,
        completed_at=datetime.now(UTC),
        duration_ms=int((time.monotonic() - started) * 1000),
    )
    return SingleResponse(data=_serialize(backup), meta=ResponseMeta(operation="create_backup"))


@router.post("/backups/upload", status_code=status.HTTP_201_CREATED)
async def upload_backup(
    file: Annotated[UploadFile, File()],
    repository: Annotated[DatabaseBackupRepository, Depends(get_backup_repository)],
    actor_id: Annotated[UUID, Depends(get_current_user_id)],
) -> SingleResponse[dict[str, Any]]:
    """Store an externally produced dump; restoring it is a separate command."""
    settings = get_settings()
    max_bytes = settings.database_backup_max_mb * 1024 * 1024
    head = await file.read(len(b"PGDMP"))
    if not head:
        raise BadRequestError("Database dump is empty.")
    fmt = detect_format(head)
    filename = build_filename(fmt, prefix="uploaded")
    path = backup_dir() / filename
    size = 0
    try:
        with path.open("wb") as target:
            target.write(head)
            size += len(head)
            while chunk := await file.read(_UPLOAD_CHUNK):
                size += len(chunk)
                if size > max_bytes:
                    raise BadRequestError(
                        f"Database dump exceeds {settings.database_backup_max_mb} MB."
                    )
                target.write(chunk)
    except BadRequestError:
        path.unlink(missing_ok=True)
        raise
    backup = await repository.add(
        filename=filename,
        file_path=str(path),
        format=fmt,
        origin="upload",
        status="completed",
        size_bytes=size,
        created_by=actor_id,
        completed_at=datetime.now(UTC),
    )
    return SingleResponse(data=_serialize(backup), meta=ResponseMeta(operation="upload_backup"))


@router.get("/backups/{backup_id}/download")
async def download_backup(
    backup_id: UUID,
    repository: Annotated[DatabaseBackupRepository, Depends(get_backup_repository)],
    _actor_id: Annotated[UUID, Depends(get_current_user_id)],
) -> FileResponse:
    backup = await repository.read(backup_id)
    path = Path(backup.file_path)
    if not path.exists():
        raise NotFoundError("Dump file is missing on the server filesystem.")
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=backup.filename,
    )


@router.post("/backups/{backup_id}/restore")
async def restore_backup(
    backup_id: UUID,
    repository: Annotated[DatabaseBackupRepository, Depends(get_backup_repository)],
    _actor_id: Annotated[UUID, Depends(get_current_user_id)],
    confirmation: Annotated[str, Query()] = "",
) -> SingleResponse[dict[str, Any]]:
    """Replace the contents of the application database with a stored dump."""
    if confirmation != RESTORE_CONFIRMATION:
        raise BadRequestError(f"Confirmation must be {RESTORE_CONFIRMATION}.")
    backup = await repository.read(backup_id)
    if backup.status != "completed":
        raise BadRequestError("Only a completed dump can be restored.")
    started = time.monotonic()
    try:
        await restore_dump(Path(backup.file_path), backup.format)
    except DatabaseTransferError as exc:
        raise BadRequestError(str(exc)) from exc
    # The registry survives its own restore (both engines exclude the table),
    # so stamping the row afterwards is safe.
    backup = await repository.update(backup, restored_at=datetime.now(UTC))
    return SingleResponse(
        data={
            "id": json_value(backup.id),
            "restored_at": json_value(backup.restored_at),
            "duration_ms": int((time.monotonic() - started) * 1000),
        },
        meta=ResponseMeta(operation="restore_backup"),
    )


@router.delete("/backups/{backup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup(
    backup_id: UUID,
    repository: Annotated[DatabaseBackupRepository, Depends(get_backup_repository)],
    _actor_id: Annotated[UUID, Depends(get_current_user_id)],
) -> Response:
    backup = await repository.read(backup_id)
    # File first: a row without bytes is recoverable noise, bytes without a row
    # are an orphan nobody will ever find.
    Path(backup.file_path).unlink(missing_ok=True)
    await repository.delete(backup_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
