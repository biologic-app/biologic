from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import SampleTarget
from src.repositories.crud_repository import CRUDRepository


class SampleTargetRepository(CRUDRepository[SampleTarget]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=SampleTarget)
