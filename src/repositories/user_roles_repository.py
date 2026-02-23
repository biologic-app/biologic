from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import UserRole
from src.repositories.crud_repository import CRUDRepository


class UserRoleRepository(CRUDRepository[UserRole]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=UserRole)
