from src.application.catalogs.use_cases.branch_crud import BranchCrudUseCase
from src.application.catalogs.use_cases.conclusion_crud import ConclusionCrudUseCase
from src.application.catalogs.use_cases.direction_status_crud import (
    DirectionStatusCrudUseCase,
)
from src.application.catalogs.use_cases.doctor_crud import DoctorCrudUseCase
from src.application.catalogs.use_cases.indicator_crud import IndicatorCrudUseCase
from src.application.catalogs.use_cases.lab_crud import LabCrudUseCase
from src.application.catalogs.use_cases.object_crud import ObjectCrudUseCase
from src.application.catalogs.use_cases.protocol_type_crud import ProtocolTypeCrudUseCase
from src.application.catalogs.use_cases.research_goal_crud import ResearchGoalCrudUseCase
from src.application.catalogs.use_cases.research_status_crud import (
    ResearchStatusCrudUseCase,
)
from src.application.catalogs.use_cases.sample_status_crud import SampleStatusCrudUseCase
from src.application.catalogs.use_cases.sample_type_crud import SampleTypeCrudUseCase
from src.application.catalogs.use_cases.test_status_crud import TestStatusCrudUseCase
from src.infrastructure.uow import build_uow_factory


async def get_branch_use_case() -> BranchCrudUseCase:
    return BranchCrudUseCase(uow_factory=build_uow_factory())


async def get_lab_use_case() -> LabCrudUseCase:
    return LabCrudUseCase(uow_factory=build_uow_factory())


async def get_object_use_case() -> ObjectCrudUseCase:
    return ObjectCrudUseCase(uow_factory=build_uow_factory())


async def get_doctor_use_case() -> DoctorCrudUseCase:
    return DoctorCrudUseCase(uow_factory=build_uow_factory())


async def get_sample_type_use_case() -> SampleTypeCrudUseCase:
    return SampleTypeCrudUseCase(uow_factory=build_uow_factory())


async def get_research_goal_use_case() -> ResearchGoalCrudUseCase:
    return ResearchGoalCrudUseCase(uow_factory=build_uow_factory())


async def get_indicator_use_case() -> IndicatorCrudUseCase:
    return IndicatorCrudUseCase(uow_factory=build_uow_factory())


async def get_conclusion_use_case() -> ConclusionCrudUseCase:
    return ConclusionCrudUseCase(uow_factory=build_uow_factory())


async def get_protocol_type_use_case() -> ProtocolTypeCrudUseCase:
    return ProtocolTypeCrudUseCase(uow_factory=build_uow_factory())


async def get_direction_status_use_case() -> DirectionStatusCrudUseCase:
    return DirectionStatusCrudUseCase(uow_factory=build_uow_factory())


async def get_sample_status_use_case() -> SampleStatusCrudUseCase:
    return SampleStatusCrudUseCase(uow_factory=build_uow_factory())


async def get_research_status_use_case() -> ResearchStatusCrudUseCase:
    return ResearchStatusCrudUseCase(uow_factory=build_uow_factory())


async def get_test_status_use_case() -> TestStatusCrudUseCase:
    return TestStatusCrudUseCase(uow_factory=build_uow_factory())
