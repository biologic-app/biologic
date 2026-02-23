from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import ChangeLog
from src.repositories.crud_repository import CRUDRepository


class ChangeLogRepository(CRUDRepository[ChangeLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=ChangeLog)
