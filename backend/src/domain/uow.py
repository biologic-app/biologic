"""Single Unit of Work for the whole bounded context.

The backend is one DDD bounded context. Every aggregate is mutated through a
single Unit of Work so that a command and its side effects (e.g. notifications,
audit history) commit atomically on one database session.

The Protocol lives in the domain layer and references repository *ports*
(Protocols) only — no web framework, no ORM — mirroring the staraudio
``identity`` domain UoW. The concrete implementation lives in
``src.infrastructure.uow``.
"""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from typing import Protocol, Self

from src.application.access_control.ports import (
    AccessControlCrudRepository,
    RolePermissionRepositoryPort,
    UserAuthRepository,
    UserPermissionOverrideRepositoryPort,
)
from src.application.catalogs.ports import CatalogCrudRepository, CatalogStatusRepository
from src.contexts.laboratory_workflow.application.ports import WorkflowRepository
from src.contexts.notifications.application.service import NotificationRepository


class UnitOfWork(Protocol):
    """Single Unit of Work spanning every aggregate of the bounded context.

    New aggregate repositories are added here as additional attributes as the
    remaining modules are migrated onto the single UoW.
    """

    workflow: WorkflowRepository
    notifications: NotificationRepository

    # Catalogs (reference data) repositories.
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

    # Access control repositories.
    users: UserAuthRepository
    roles: AccessControlCrudRepository
    permissions: AccessControlCrudRepository
    role_permissions: RolePermissionRepositoryPort
    user_permission_overrides: UserPermissionOverrideRepositoryPort
    user_scopes: AccessControlCrudRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None:
        """Commit every change accumulated on the shared session."""
        ...

    async def rollback(self) -> None:
        """Roll back every change accumulated on the shared session."""
        ...


UnitOfWorkFactory = Callable[[], UnitOfWork]
