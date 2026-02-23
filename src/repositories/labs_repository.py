from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Lab
from src.repositories.crud_repository import CRUDRepository


class LabRepository(CRUDRepository[Lab]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Lab)
