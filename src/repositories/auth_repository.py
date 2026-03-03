from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Permission, Role, RolePermission, User


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
        stmt = (
            select(Permission.resource, Permission.action)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        return [(resource, action) for resource, action in rows]

    async def is_allowed(
        self,
        *,
        user_id: UUID,
        resource: str,
        action: str,
        target_scope_id: UUID | None,
    ) -> bool:
        stmt = text("""
            WITH user_role AS (
              SELECT u.role_id, r.scope_type
              FROM users u
              JOIN roles r ON r.id = u.role_id
              WHERE u.id = :user_id
                AND u.deleted_at IS NULL
            ),
            has_permission AS (
              SELECT 1
              FROM role_permissions rp
              JOIN permissions p ON p.id = rp.permission_id
              JOIN user_role ur ON ur.role_id = rp.role_id
              WHERE p.resource = :resource
                AND p.action = :action
            ),
            has_scope AS (
              SELECT 1
              FROM user_role ur
              WHERE ur.scope_type = 'global'
              UNION ALL
              SELECT 1
              FROM user_scopes us
              JOIN user_role ur ON ur.scope_type != 'global'
              WHERE us.user_id = :user_id
                AND (us.scope_id IS NULL OR us.scope_id = :target_scope_id)
            )
            SELECT
              EXISTS(SELECT 1 FROM has_permission) AND
              EXISTS(SELECT 1 FROM has_scope) AS is_allowed
            """)
        result = await self._session.execute(
            stmt,
            {
                "user_id": user_id,
                "resource": resource,
                "action": action,
                "target_scope_id": target_scope_id,
            },
        )
        return bool(result.scalar_one())
