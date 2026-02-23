from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Doctor
from src.repositories.crud_repository import CRUDRepository


class DoctorRepository(CRUDRepository[Doctor]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Doctor)
