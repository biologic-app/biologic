from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import ConclusionStatus
from src.repositories.crud_repository import CRUDRepository


class ConclusionStatusRepository(CRUDRepository[ConclusionStatus]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=ConclusionStatus)
