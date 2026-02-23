from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import ChangeLog, RolePermission
from src.repositories.crud_repository import CRUDRepository


class RolePermissionRepository(CRUDRepository[RolePermission]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=RolePermission)

    async def get_by_pk(self, role_id: UUID, resource: str, action: str) -> RolePermission | None:
        stmt = (
            select(RolePermission)
            .where(RolePermission.role_id == role_id)
            .where(RolePermission.resource == resource)
            .where(RolePermission.action == action)
            .where(RolePermission.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_by_pk(
        self, role_id: UUID, resource: str, action: str, values: dict[str, object]
    ) -> RolePermission | None:
        entity = await self.get_by_pk(role_id, resource, action)
        if entity is None:
            return None
        for key, value in values.items():
            setattr(entity, key, value)
        entity.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(entity)
        return entity

    async def delete_by_pk(
        self, role_id: UUID, resource: str, action: str, reason: str | None = None
    ) -> bool:
        entity = await self.get_by_pk(role_id, resource, action)
        if entity is None:
            return False
        now = datetime.now(UTC)
        entity.deleted_at = now
        entity.updated_at = now

        diff_payload: dict[str, object] | None = None
        if reason:
            diff_payload = {"reason": reason}

        self._session.add(
            ChangeLog(
                entity_type="role_permissions",
                entity_id=role_id,
                action="soft_delete",
                diff=diff_payload,
            )
        )
        await self._session.commit()
        return True
