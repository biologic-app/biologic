from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Result
from src.repositories.crud_repository import CRUDRepository


class ResultRepository(CRUDRepository[Result]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Result)
