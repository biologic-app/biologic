from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Sample
from src.repositories.crud_repository import CRUDRepository


class SampleRepository(CRUDRepository[Sample]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Sample)
