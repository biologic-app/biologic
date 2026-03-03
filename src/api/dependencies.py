from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.database import get_db_session
from src.repositories.auth_repository import AuthRepository
from src.repositories.branches_repository import BranchRepository
from src.repositories.change_log_repository import ChangeLogRepository
from src.repositories.conclusions_repository import ConclusionRepository
from src.repositories.direction_statuses_repository import DirectionStatusRepository
from src.repositories.directions_repository import DirectionRepository
from src.repositories.doctors_repository import DoctorRepository
from src.repositories.indicators_repository import IndicatorRepository
from src.repositories.labs_repository import LabRepository
from src.repositories.objects_repository import ObjectRepository
from src.repositories.permissions_repository import PermissionRepository
from src.repositories.protocol_types_repository import ProtocolTypeRepository
from src.repositories.protocols_repository import ProtocolRepository
from src.repositories.research_goals_repository import ResearchGoalRepository
from src.repositories.research_repository import ResearchRepository
from src.repositories.research_statuses_repository import ResearchStatusRepository
from src.repositories.role_permissions_repository import RolePermissionRepository
from src.repositories.roles_repository import RoleRepository
from src.repositories.sample_statuses_repository import SampleStatusRepository
from src.repositories.sample_types_repository import SampleTypeRepository
from src.repositories.samples_repository import SampleRepository
from src.repositories.test_statuses_repository import TestStatusRepository
from src.repositories.tests_repository import TestRepository
from src.repositories.user_scopes_repository import UserScopeRepository
from src.repositories.users_repository import UserRepository
from src.services.auth_service import AuthService
from src.services.branches_service import BranchService
from src.services.change_log_service import ChangeLogService
from src.services.conclusions_service import ConclusionService
from src.services.dashboard_service import DashboardQuickActionsService
from src.services.direction_statuses_service import DirectionStatusService
from src.services.directions_service import DirectionService
from src.services.doctors_service import DoctorService
from src.services.indicators_service import IndicatorService
from src.services.labs_service import LabService
from src.services.objects_service import ObjectService
from src.services.permissions_service import PermissionService
from src.services.protocol_types_service import ProtocolTypeService
from src.services.protocols_service import ProtocolService
from src.services.research_goals_service import ResearchGoalService
from src.services.research_service import ResearchService
from src.services.research_statuses_service import ResearchStatusService
from src.services.role_permissions_service import RolePermissionService
from src.services.roles_service import RoleService
from src.services.sample_statuses_service import SampleStatusService
from src.services.sample_types_service import SampleTypeService
from src.services.samples_service import SampleService
from src.services.test_statuses_service import TestStatusService
from src.services.tests_service import TestService
from src.services.user_scopes_service import UserScopeService
from src.services.users_service import UserService

_dashboard_quick_actions_service = DashboardQuickActionsService()


def get_auth_service(
    db_session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    repository = AuthRepository(session=db_session)
    return AuthService(repository=repository, settings=settings)


def get_branches_service(db_session: AsyncSession = Depends(get_db_session)) -> BranchService:
    repository = BranchRepository(session=db_session)
    return BranchService(repository=repository)


def get_change_log_service(db_session: AsyncSession = Depends(get_db_session)) -> ChangeLogService:
    repository = ChangeLogRepository(session=db_session)
    return ChangeLogService(repository=repository)


def get_conclusions_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> ConclusionService:
    repository = ConclusionRepository(session=db_session)
    return ConclusionService(repository=repository)


def get_direction_statuses_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> DirectionStatusService:
    repository = DirectionStatusRepository(session=db_session)
    return DirectionStatusService(repository=repository)


def get_directions_service(db_session: AsyncSession = Depends(get_db_session)) -> DirectionService:
    repository = DirectionRepository(session=db_session)
    return DirectionService(repository=repository)


def get_doctors_service(db_session: AsyncSession = Depends(get_db_session)) -> DoctorService:
    repository = DoctorRepository(session=db_session)
    return DoctorService(repository=repository)


def get_indicators_service(db_session: AsyncSession = Depends(get_db_session)) -> IndicatorService:
    repository = IndicatorRepository(session=db_session)
    return IndicatorService(repository=repository)


def get_labs_service(db_session: AsyncSession = Depends(get_db_session)) -> LabService:
    repository = LabRepository(session=db_session)
    return LabService(repository=repository)


def get_objects_service(db_session: AsyncSession = Depends(get_db_session)) -> ObjectService:
    repository = ObjectRepository(session=db_session)
    return ObjectService(repository=repository)


def get_permissions_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> PermissionService:
    repository = PermissionRepository(session=db_session)
    return PermissionService(repository=repository)


def get_protocol_types_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> ProtocolTypeService:
    repository = ProtocolTypeRepository(session=db_session)
    return ProtocolTypeService(repository=repository)


def get_protocols_service(db_session: AsyncSession = Depends(get_db_session)) -> ProtocolService:
    repository = ProtocolRepository(session=db_session)
    return ProtocolService(repository=repository)


def get_research_goals_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> ResearchGoalService:
    repository = ResearchGoalRepository(session=db_session)
    return ResearchGoalService(repository=repository)


def get_research_service(db_session: AsyncSession = Depends(get_db_session)) -> ResearchService:
    repository = ResearchRepository(session=db_session)
    return ResearchService(repository=repository)


def get_research_statuses_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> ResearchStatusService:
    repository = ResearchStatusRepository(session=db_session)
    return ResearchStatusService(repository=repository)


def get_roles_service(db_session: AsyncSession = Depends(get_db_session)) -> RoleService:
    repository = RoleRepository(session=db_session)
    return RoleService(repository=repository)


def get_sample_statuses_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> SampleStatusService:
    repository = SampleStatusRepository(session=db_session)
    return SampleStatusService(repository=repository)


def get_sample_types_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> SampleTypeService:
    repository = SampleTypeRepository(session=db_session)
    return SampleTypeService(repository=repository)


def get_samples_service(db_session: AsyncSession = Depends(get_db_session)) -> SampleService:
    repository = SampleRepository(session=db_session)
    return SampleService(repository=repository)


def get_test_statuses_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> TestStatusService:
    repository = TestStatusRepository(session=db_session)
    return TestStatusService(repository=repository)


def get_tests_service(db_session: AsyncSession = Depends(get_db_session)) -> TestService:
    repository = TestRepository(session=db_session)
    return TestService(repository=repository)


def get_user_scopes_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> UserScopeService:
    repository = UserScopeRepository(session=db_session)
    return UserScopeService(repository=repository)


def get_users_service(db_session: AsyncSession = Depends(get_db_session)) -> UserService:
    repository = UserRepository(session=db_session)
    return UserService(repository=repository)


def get_role_permissions_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> RolePermissionService:
    repository = RolePermissionRepository(session=db_session)
    return RolePermissionService(repository=repository)


def get_dashboard_quick_actions_service() -> DashboardQuickActionsService:
    return _dashboard_quick_actions_service
