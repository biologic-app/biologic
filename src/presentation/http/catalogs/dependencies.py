from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.catalogs.application.use_cases.branch_crud import BranchCrudUseCase
from src.contexts.catalogs.application.use_cases.conclusion_crud import ConclusionCrudUseCase
from src.contexts.catalogs.application.use_cases.direction_status_crud import (
    DirectionStatusCrudUseCase,
)
from src.contexts.catalogs.application.use_cases.doctor_crud import DoctorCrudUseCase
from src.contexts.catalogs.application.use_cases.indicator_crud import IndicatorCrudUseCase
from src.contexts.catalogs.application.use_cases.lab_crud import LabCrudUseCase
from src.contexts.catalogs.application.use_cases.object_crud import ObjectCrudUseCase
from src.contexts.catalogs.application.use_cases.protocol_type_crud import ProtocolTypeCrudUseCase
from src.contexts.catalogs.application.use_cases.research_goal_crud import ResearchGoalCrudUseCase
from src.contexts.catalogs.application.use_cases.research_status_crud import (
    ResearchStatusCrudUseCase,
)
from src.contexts.catalogs.application.use_cases.sample_status_crud import SampleStatusCrudUseCase
from src.contexts.catalogs.application.use_cases.sample_type_crud import SampleTypeCrudUseCase
from src.contexts.catalogs.application.use_cases.test_status_crud import TestStatusCrudUseCase
from src.contexts.catalogs.infrastructure.repositories import (
    BranchRepository,
    ConclusionRepository,
    DirectionStatusRepository,
    DoctorRepository,
    IndicatorRepository,
    LabRepository,
    ObjectRepository,
    ProtocolTypeRepository,
    ResearchGoalRepository,
    ResearchStatusRepository,
    SampleStatusRepository,
    SampleTypeRepository,
    TestStatusRepository,
)
from src.core.database import get_db_session


async def get_branch_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BranchCrudUseCase:
    return BranchCrudUseCase(repository=BranchRepository(session=session))


async def get_lab_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LabCrudUseCase:
    return LabCrudUseCase(repository=LabRepository(session=session))


async def get_object_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ObjectCrudUseCase:
    return ObjectCrudUseCase(repository=ObjectRepository(session=session))


async def get_doctor_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DoctorCrudUseCase:
    return DoctorCrudUseCase(repository=DoctorRepository(session=session))


async def get_sample_type_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SampleTypeCrudUseCase:
    return SampleTypeCrudUseCase(repository=SampleTypeRepository(session=session))


async def get_research_goal_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResearchGoalCrudUseCase:
    return ResearchGoalCrudUseCase(repository=ResearchGoalRepository(session=session))


async def get_indicator_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IndicatorCrudUseCase:
    return IndicatorCrudUseCase(repository=IndicatorRepository(session=session))


async def get_conclusion_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ConclusionCrudUseCase:
    return ConclusionCrudUseCase(repository=ConclusionRepository(session=session))


async def get_protocol_type_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProtocolTypeCrudUseCase:
    return ProtocolTypeCrudUseCase(repository=ProtocolTypeRepository(session=session))


async def get_direction_status_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DirectionStatusCrudUseCase:
    return DirectionStatusCrudUseCase(repository=DirectionStatusRepository(session=session))


async def get_sample_status_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SampleStatusCrudUseCase:
    return SampleStatusCrudUseCase(repository=SampleStatusRepository(session=session))


async def get_research_status_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResearchStatusCrudUseCase:
    return ResearchStatusCrudUseCase(repository=ResearchStatusRepository(session=session))


async def get_test_status_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TestStatusCrudUseCase:
    return TestStatusCrudUseCase(repository=TestStatusRepository(session=session))
