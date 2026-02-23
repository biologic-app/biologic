from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Conclusion
from src.repositories.crud_repository import CRUDRepository


class ConclusionRepository(CRUDRepository[Conclusion]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Conclusion)
