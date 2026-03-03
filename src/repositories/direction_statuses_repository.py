from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import DirectionStatus
from src.repositories.crud_repository import CRUDRepository


class DirectionStatusRepository(CRUDRepository[DirectionStatus]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=DirectionStatus)
