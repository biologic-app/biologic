from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Branch
from src.repositories.crud_repository import CRUDRepository


class BranchRepository(CRUDRepository[Branch]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Branch)
