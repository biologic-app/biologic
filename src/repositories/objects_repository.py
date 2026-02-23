from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Object
from src.repositories.crud_repository import CRUDRepository


class ObjectRepository(CRUDRepository[Object]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Object)
