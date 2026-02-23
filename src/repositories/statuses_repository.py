from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Status
from src.repositories.crud_repository import CRUDRepository


class StatusRepository(CRUDRepository[Status]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Status)
