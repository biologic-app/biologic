from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Role
from src.repositories.crud_repository import CRUDRepository


class RoleRepository(CRUDRepository[Role]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Role)
