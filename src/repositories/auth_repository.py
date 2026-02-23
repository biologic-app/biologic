from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Role, RolePermission, User


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_with_role_by_username(
        self, username: str
    ) -> tuple[User, Role | None] | None:
        stmt = (
            select(User, Role)
            .join(Role, Role.id == User.role_id, isouter=True)
            .where(User.username == username, User.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        return row[0], row[1]

    async def get_user_with_role_by_id(self, user_id: UUID) -> tuple[User, Role | None] | None:
        stmt = (
            select(User, Role)
            .join(Role, Role.id == User.role_id, isouter=True)
            .where(User.id == user_id, User.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        return row[0], row[1]

    async def bump_refresh_token_version(self, user_id: UUID) -> int | None:
        stmt = (
            update(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .values(
                refresh_token_version=User.refresh_token_version + 1,
                updated_at=datetime.now(UTC),
            )
            .returning(User.refresh_token_version)
        )
        result = await self._session.execute(stmt)
        new_version = result.scalar_one_or_none()
        await self._session.commit()
        return new_version

    async def list_permissions_by_role_id(self, role_id: UUID) -> list[tuple[str, str]]:
        stmt = select(RolePermission.resource, RolePermission.action).where(RolePermission.role_id == role_id)
        result = await self._session.execute(stmt)
        rows = result.all()
        return [(resource, action) for resource, action in rows]
