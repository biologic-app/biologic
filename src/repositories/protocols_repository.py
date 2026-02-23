from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Protocol
from src.repositories.crud_repository import CRUDRepository


class ProtocolRepository(CRUDRepository[Protocol]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Protocol)
