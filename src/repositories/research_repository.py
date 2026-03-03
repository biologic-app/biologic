from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Research
from src.repositories.crud_repository import CRUDRepository


class ResearchRepository(CRUDRepository[Research]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Research)
