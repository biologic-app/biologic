from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import ResearchStatus
from src.repositories.crud_repository import CRUDRepository


class ResearchStatusRepository(CRUDRepository[ResearchStatus]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=ResearchStatus)
