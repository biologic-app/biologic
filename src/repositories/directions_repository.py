from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Direction
from src.repositories.crud_repository import CRUDRepository


class DirectionRepository(CRUDRepository[Direction]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Direction)
