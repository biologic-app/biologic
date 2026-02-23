from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import ProtocolType
from src.repositories.crud_repository import CRUDRepository


class ProtocolTypeRepository(CRUDRepository[ProtocolType]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=ProtocolType)
