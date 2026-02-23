from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Indicator
from src.repositories.crud_repository import CRUDRepository


class IndicatorRepository(CRUDRepository[Indicator]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Indicator)
