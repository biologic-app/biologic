from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Permission
from src.repositories.crud_repository import CRUDRepository


class PermissionRepository(CRUDRepository[Permission]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Permission)
