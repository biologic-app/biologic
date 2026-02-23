from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import ResearchGoal
from src.repositories.crud_repository import CRUDRepository


class ResearchGoalRepository(CRUDRepository[ResearchGoal]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=ResearchGoal)
