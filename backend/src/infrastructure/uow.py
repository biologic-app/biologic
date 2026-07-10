"""SQLAlchemy implementation of the single Unit of Work.

One session, one transaction, every aggregate repository bound to it. The
repositories themselves only ``flush`` — the transaction boundary is owned here,
so a workflow command and the notifications/audit rows it produces commit
atomically.
"""

from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.access_control.ports import (
    AccessControlCrudRepository,
    RolePermissionRepositoryPort,
    UserAuthRepository,
    UserPermissionOverrideRepositoryPort,
)
from src.application.catalogs.ports import (
    CatalogCrudRepository,
    CatalogStatusRepository,
)
from src.contexts.laboratory_workflow.application.ports import WorkflowRepository
from src.contexts.laboratory_workflow.infrastructure.repositories import (
    SqlAlchemyWorkflowRepository,
)
from src.contexts.notifications.application.service import NotificationRepository
from src.contexts.notifications.infrastructure.repositories import (
    SqlAlchemyNotificationRepository,
)
from src.core.database import get_session_factory
from src.domain.uow import UnitOfWork, UnitOfWorkFactory
from src.infrastructure.repositories.access_control import (
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    RoleSubscriptionRuleRepository,
    UserPermissionOverrideRepository,
    UserRepository,
    UserScopeRepository,
)
from src.infrastructure.repositories.catalogs import (
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


class SqlAlchemyUnitOfWork:
    """Concrete single Unit of Work bound to one async session."""

    workflow: WorkflowRepository
    notifications: NotificationRepository
    branches: CatalogCrudRepository
    labs: CatalogCrudRepository
    objects: CatalogCrudRepository
    doctors: CatalogCrudRepository
    sample_types: CatalogCrudRepository
    research_goals: CatalogCrudRepository
    indicators: CatalogCrudRepository
    conclusions: CatalogCrudRepository
    protocol_types: CatalogCrudRepository
    direction_statuses: CatalogStatusRepository
    sample_statuses: CatalogStatusRepository
    research_statuses: CatalogStatusRepository
    test_statuses: CatalogStatusRepository
    users: UserAuthRepository
    roles: AccessControlCrudRepository
    permissions: AccessControlCrudRepository
    role_permissions: RolePermissionRepositoryPort
    role_subscription_rules: AccessControlCrudRepository
    user_permission_overrides: UserPermissionOverrideRepositoryPort
    user_scopes: AccessControlCrudRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self.session = self._session_factory()
        await self.session.begin()
        self.workflow = SqlAlchemyWorkflowRepository(session=self.session)
        self.notifications = SqlAlchemyNotificationRepository(session=self.session)
        self.branches = BranchRepository(session=self.session)
        self.labs = LabRepository(session=self.session)
        self.objects = ObjectRepository(session=self.session)
        self.doctors = DoctorRepository(session=self.session)
        self.sample_types = SampleTypeRepository(session=self.session)
        self.research_goals = ResearchGoalRepository(session=self.session)
        self.indicators = IndicatorRepository(session=self.session)
        self.conclusions = ConclusionRepository(session=self.session)
        self.protocol_types = ProtocolTypeRepository(session=self.session)
        self.direction_statuses = DirectionStatusRepository(session=self.session)
        self.sample_statuses = SampleStatusRepository(session=self.session)
        self.research_statuses = ResearchStatusRepository(session=self.session)
        self.test_statuses = TestStatusRepository(session=self.session)
        self.users = UserRepository(session=self.session)
        self.roles = RoleRepository(session=self.session)
        self.permissions = PermissionRepository(session=self.session)
        self.role_permissions = RolePermissionRepository(session=self.session)
        self.role_subscription_rules = RoleSubscriptionRuleRepository(session=self.session)
        self.user_permission_overrides = UserPermissionOverrideRepository(session=self.session)
        self.user_scopes = UserScopeRepository(session=self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.session is None:
            return
        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            await self.session.close()
            self.session = None

    async def commit(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of work session is not initialized")
        await self.session.commit()

    async def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of work session is not initialized")
        await self.session.rollback()


def build_uow_factory() -> UnitOfWorkFactory:
    """Return a factory that opens a fresh single Unit of Work per call."""
    session_factory = get_session_factory()

    def _factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    return _factory
