from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import RolePermission
from src.repositories.crud_repository import CRUDRepository


class RolePermissionRepository(CRUDRepository[RolePermission]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=RolePermission)
