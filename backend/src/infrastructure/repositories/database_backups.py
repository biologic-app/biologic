"""SQLAlchemy access to the dump registry.

The registry is metadata only — one row per file under
``APP_DATABASE_BACKUP_DIR``. Nothing here touches the dump payload.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import NotFoundError
from src.infrastructure.db.models import DatabaseBackup


class DatabaseBackupRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, *, limit: int) -> tuple[list[DatabaseBackup], int]:
        total = await self.session.scalar(select(func.count()).select_from(DatabaseBackup))
        result = await self.session.execute(
            select(DatabaseBackup).order_by(DatabaseBackup.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def read(self, backup_id: UUID) -> DatabaseBackup:
        backup = await self.session.get(DatabaseBackup, backup_id)
        if backup is None:
            raise NotFoundError("Database backup not found.")
        return backup

    async def add(self, **values: Any) -> DatabaseBackup:
        backup = DatabaseBackup(**values)
        self.session.add(backup)
        await self.session.commit()
        await self.session.refresh(backup)
        return backup

    async def update(self, backup: DatabaseBackup, **values: Any) -> DatabaseBackup:
        for key, value in values.items():
            setattr(backup, key, value)
        await self.session.commit()
        await self.session.refresh(backup)
        return backup

    async def delete(self, backup_id: UUID) -> None:
        await self.session.execute(delete(DatabaseBackup).where(DatabaseBackup.id == backup_id))
        await self.session.commit()
