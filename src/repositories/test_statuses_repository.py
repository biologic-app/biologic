from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import TestStatus
from src.repositories.crud_repository import CRUDRepository


class TestStatusRepository(CRUDRepository[TestStatus]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=TestStatus)
