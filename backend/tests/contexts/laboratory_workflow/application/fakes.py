from __future__ import annotations

from datetime import datetime
from types import TracebackType
from typing import Self, cast
from uuid import UUID

from src.application.access_control.ports import (
    AccessControlCrudRepository,
    RolePermissionRepositoryPort,
    UserAuthRepository,
    UserPermissionOverrideRepositoryPort,
)
from src.application.catalogs.ports import CatalogCrudRepository, CatalogStatusRepository
from src.application.workflows.ports import WorkflowsRepository
from src.contexts.laboratory_workflow.application.dto import CommandResult
from src.contexts.laboratory_workflow.application.ports import WorkflowRepository
from src.contexts.notifications.application.service import NotificationRepository
from src.domain.uow import UnitOfWork, UnitOfWorkFactory


class WorkflowRepositoryFake(WorkflowRepository):
    async def register_direction(
        self,
        direction_id: UUID,
        actor_id: UUID,
        comment: str | None,
    ) -> CommandResult:
        raise AssertionError("register_direction should not be called")

    async def register_sample(
        self,
        sample_id: UUID,
        actor_id: UUID,
        received_at: datetime,
        deadline: datetime | None,
    ) -> CommandResult:
        raise AssertionError("register_sample should not be called")

    async def reject_sample(
        self,
        sample_id: UUID,
        actor_id: UUID,
        reason: str,
    ) -> CommandResult:
        raise AssertionError("reject_sample should not be called")

    async def assign_research(
        self,
        sample_id: UUID,
        actor_id: UUID,
        research_goal_id: UUID,
        comment: str | None,
    ) -> CommandResult:
        raise AssertionError("assign_research should not be called")

    async def complete_test(
        self,
        test_id: UUID,
        actor_id: UUID,
        value: str,
        norm: str | None,
        comment: str | None,
        verdict: bool | None,
        workflow_run_id: UUID | None = None,
    ) -> CommandResult:
        raise AssertionError("complete_test should not be called")

    async def reject_research(
        self,
        research_id: UUID,
        actor_id: UUID,
        reason: str,
    ) -> CommandResult:
        raise AssertionError("reject_research should not be called")

    async def reject_test(
        self,
        test_id: UUID,
        actor_id: UUID,
        reason: str,
        workflow_run_id: UUID | None = None,
    ) -> CommandResult:
        raise AssertionError("reject_test should not be called")

    async def close_sample(
        self,
        sample_id: UUID,
        actor_id: UUID,
        verdict: str,
        comment: str | None,
    ) -> CommandResult:
        raise AssertionError("close_sample should not be called")

    async def create_protocol(
        self,
        actor_id: UUID,
        sample_ids: list[UUID],
        protocol_type_id: UUID | None,
        conclusion_id: UUID | None,
        copies: int | None,
    ) -> CommandResult:
        raise AssertionError("create_protocol should not be called")

    async def update_protocol(
        self,
        protocol_id: UUID,
        actor_id: UUID,
        protocol_type_id: UUID | None,
        conclusion_id: UUID | None,
        copies: int | None,
    ) -> CommandResult:
        raise AssertionError("update_protocol should not be called")

    async def issue_protocol(
        self,
        protocol_id: UUID,
        actor_id: UUID,
        issued_at: datetime | None,
    ) -> CommandResult:
        raise AssertionError("issue_protocol should not be called")

    async def resolve_notification_targets(
        self, entity_type: str, entity_id: UUID
    ) -> set[UUID]:
        raise AssertionError("resolve_notification_targets should not be called")


class FakeUnitOfWork:
    """Single Unit of Work test double wrapping a fake workflow repository.

    Mirrors the real ``SqlAlchemyUnitOfWork`` surface: aggregate repositories as
    attributes plus the async-context-manager / commit / rollback protocol.
    """

    def __init__(self, workflow: WorkflowRepository) -> None:
        self.workflow = workflow
        # Never exercised by these fakes (no domain events are emitted), but the
        # attribute must satisfy the UnitOfWork protocol for the type checker.
        self.workflows = cast(WorkflowsRepository, None)
        self.notifications = cast(NotificationRepository, None)
        self.branches = cast(CatalogCrudRepository, None)
        self.labs = cast(CatalogCrudRepository, None)
        self.objects = cast(CatalogCrudRepository, None)
        self.doctors = cast(CatalogCrudRepository, None)
        self.sample_types = cast(CatalogCrudRepository, None)
        self.research_goals = cast(CatalogCrudRepository, None)
        self.indicators = cast(CatalogCrudRepository, None)
        self.conclusions = cast(CatalogCrudRepository, None)
        self.protocol_types = cast(CatalogCrudRepository, None)
        self.direction_statuses = cast(CatalogStatusRepository, None)
        self.sample_statuses = cast(CatalogStatusRepository, None)
        self.research_statuses = cast(CatalogStatusRepository, None)
        self.test_statuses = cast(CatalogStatusRepository, None)
        self.users = cast(UserAuthRepository, None)
        self.roles = cast(AccessControlCrudRepository, None)
        self.permissions = cast(AccessControlCrudRepository, None)
        self.role_permissions = cast(RolePermissionRepositoryPort, None)
        self.role_subscription_rules = cast(AccessControlCrudRepository, None)
        self.user_permission_overrides = cast(UserPermissionOverrideRepositoryPort, None)
        self.user_scopes = cast(AccessControlCrudRepository, None)
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def fake_uow_factory(uow: UnitOfWork) -> UnitOfWorkFactory:
    """Return a factory that always yields the given UoW double."""
    return lambda: uow
