from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.laboratory_workflow.application.dto import CommandResult
from src.contexts.laboratory_workflow.domain.events import StatusChanged
from src.contexts.laboratory_workflow.domain.status_policy import (
    InvalidStatusTransition,
    SampleDeadlinePolicy,
    ensure_allowed_transition,
)
from src.core.errors import DomainConflictError, NotFoundError
from src.core.status_codes import DIRECTION_REGISTERED, SAMPLE_REGISTERED
from src.infrastructure.db.models import (
    ChangeLog,
    Direction,
    DirectionStatus,
    Research,
    Sample,
    SampleStatus,
)


class SqlAlchemyWorkflowRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session
        self.events: list[StatusChanged] = []

    async def register_direction(
        self,
        direction_id: UUID,
        actor_id: UUID,
        comment: str | None,
    ) -> CommandResult:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(Direction)
            .where(Direction.id == direction_id, Direction.deleted_at.is_(None))
            .with_for_update(),
        )
        direction = result.scalar_one_or_none()
        if direction is None:
            raise NotFoundError("Direction was not found.")

        current_status_code = await self._direction_status_code(direction.status_id)
        try:
            ensure_allowed_transition("directions", current_status_code, DIRECTION_REGISTERED)
        except InvalidStatusTransition as exc:
            raise DomainConflictError(
                code=exc.code,
                detail=(
                    "Direction can be registered only from draft status. "
                    f"Current status is {current_status_code}."
                ),
            ) from exc

        await self._ensure_direction_ready_for_registration(direction_id)
        target_status_id = await self._direction_status_id(DIRECTION_REGISTERED)
        direction.status_id = target_status_id
        direction.updated_by = actor_id
        direction.updated_at = now
        self.events.append(
            StatusChanged(
                entity_type="directions",
                entity_id=direction_id,
                event_type="DirectionRegistered",
                from_code=current_status_code,
                to_code=DIRECTION_REGISTERED,
                reason=comment or "",
            ),
        )
        self.session.add(
            ChangeLog(
                entity_type="directions",
                entity_id=direction_id,
                action="direction_registered",
                actor_id=actor_id,
                snapshot={"status_code": DIRECTION_REGISTERED},
                diff={
                    "status_code": {
                        "from": current_status_code,
                        "to": DIRECTION_REGISTERED,
                    },
                    "comment": comment,
                },
            ),
        )
        await self.session.commit()
        return CommandResult(id=direction_id, status_id=target_status_id, updated_at=now)

    async def _direction_status_code(self, status_id: UUID | None) -> str:
        if status_id is None:
            raise DomainConflictError(
                code="status_not_configured",
                detail="Direction has no configured status.",
            )
        result = await self.session.execute(
            select(DirectionStatus.code).where(
                DirectionStatus.id == status_id,
                DirectionStatus.deleted_at.is_(None),
            ),
        )
        code = result.scalar_one_or_none()
        if code is None:
            raise DomainConflictError(
                code="status_not_configured",
                detail="Direction status is not configured.",
            )
        return code

    async def _ensure_direction_ready_for_registration(self, direction_id: UUID) -> None:
        result = await self.session.execute(
            select(Sample.id, Sample.name, Sample.sample_type_id).where(
                Sample.direction_id == direction_id,
                Sample.deleted_at.is_(None),
            ),
        )
        samples = result.all()
        if not samples:
            raise DomainConflictError(
                code="direction_missing_samples",
                detail="Direction must contain at least one sample before registration.",
            )

        sample_ids = {sample_id for sample_id, _name, _sample_type_id in samples}
        missing_sample_data = [
            str(sample_id)
            for sample_id, name, sample_type_id in samples
            if not name or sample_type_id is None
        ]
        if missing_sample_data:
            raise DomainConflictError(
                code="direction_missing_sample_data",
                detail="Direction contains samples without required data.",
            )

        research_result = await self.session.execute(
            select(Research.sample_id).where(
                Research.sample_id.in_(sample_ids),
                Research.deleted_at.is_(None),
            ),
        )
        assigned_sample_ids = set(research_result.scalars().all())
        if sample_ids - assigned_sample_ids:
            raise DomainConflictError(
                code="direction_missing_research_assignments",
                detail="Direction contains samples without research assignments.",
            )

    async def _direction_status_id(self, code: str) -> UUID:
        result = await self.session.execute(
            select(DirectionStatus.id).where(
                DirectionStatus.code == code,
                DirectionStatus.deleted_at.is_(None),
            ),
        )
        status_id = result.scalar_one_or_none()
        if status_id is None:
            raise DomainConflictError(
                code="status_not_configured",
                detail=f"Direction status {code!r} is not configured.",
            )
        return status_id

    async def register_sample(
        self,
        sample_id: UUID,
        actor_id: UUID,
        received_at: datetime,
        deadline: datetime | None,
    ) -> CommandResult:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(Sample)
            .where(Sample.id == sample_id, Sample.deleted_at.is_(None))
            .with_for_update(),
        )
        sample = result.scalar_one_or_none()
        if sample is None:
            raise NotFoundError("Sample was not found.")

        current_status_code = await self._sample_status_code(sample.status_id)
        try:
            ensure_allowed_transition("samples", current_status_code, SAMPLE_REGISTERED)
        except InvalidStatusTransition as exc:
            raise DomainConflictError(
                code=exc.code,
                detail=(
                    "Sample can be registered only from pending status. "
                    f"Current status is {current_status_code}."
                ),
            ) from exc

        target_status_id = await self._sample_status_id(SAMPLE_REGISTERED)
        target_deadline = deadline or SampleDeadlinePolicy().calculate(received_at)
        previous_received_at = sample.received_at
        previous_deadline = sample.deadline

        sample.status_id = target_status_id
        sample.received_at = received_at
        sample.deadline = target_deadline
        sample.updated_by = actor_id
        sample.updated_at = now
        self.events.append(
            StatusChanged(
                entity_type="samples",
                entity_id=sample_id,
                event_type="SampleRegistered",
                from_code=current_status_code,
                to_code=SAMPLE_REGISTERED,
                reason="",
            ),
        )
        self.session.add(
            ChangeLog(
                entity_type="samples",
                entity_id=sample_id,
                action="sample_registered",
                actor_id=actor_id,
                snapshot={
                    "status_code": SAMPLE_REGISTERED,
                    "received_at": self._json_timestamp(received_at),
                    "deadline": self._json_timestamp(target_deadline),
                },
                diff={
                    "status_code": {
                        "from": current_status_code,
                        "to": SAMPLE_REGISTERED,
                    },
                    "received_at": {
                        "from": self._json_timestamp(previous_received_at),
                        "to": self._json_timestamp(received_at),
                    },
                    "deadline": {
                        "from": self._json_timestamp(previous_deadline),
                        "to": self._json_timestamp(target_deadline),
                    },
                },
            ),
        )
        await self.session.commit()
        return CommandResult(id=sample_id, status_id=target_status_id, updated_at=now)

    async def _sample_status_code(self, status_id: UUID | None) -> str:
        if status_id is None:
            raise DomainConflictError(
                code="status_not_configured",
                detail="Sample has no configured status.",
            )
        result = await self.session.execute(
            select(SampleStatus.code).where(
                SampleStatus.id == status_id,
                SampleStatus.deleted_at.is_(None),
            ),
        )
        code = result.scalar_one_or_none()
        if code is None:
            raise DomainConflictError(
                code="status_not_configured",
                detail="Sample status is not configured.",
            )
        return code

    async def _sample_status_id(self, code: str) -> UUID:
        result = await self.session.execute(
            select(SampleStatus.id).where(
                SampleStatus.code == code,
                SampleStatus.deleted_at.is_(None),
            ),
        )
        status_id = result.scalar_one_or_none()
        if status_id is None:
            raise DomainConflictError(
                code="status_not_configured",
                detail=f"Sample status {code!r} is not configured.",
            )
        return status_id

    def _json_timestamp(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()

    async def reject_sample(
        self,
        sample_id: UUID,
        actor_id: UUID,
        reason: str,
    ) -> CommandResult:
        raise DomainConflictError(
            code="workflow_command_not_implemented",
            detail="Reject sample persistence is not wired yet.",
        )

    async def assign_research(
        self,
        sample_id: UUID,
        actor_id: UUID,
        research_goal_id: UUID,
        comment: str | None,
    ) -> CommandResult:
        raise DomainConflictError(
            code="workflow_command_not_implemented",
            detail="Assign research persistence is not wired yet.",
        )

    async def complete_test(
        self,
        test_id: UUID,
        actor_id: UUID,
        value: str,
        norm: str | None,
        comment: str | None,
    ) -> CommandResult:
        raise DomainConflictError(
            code="workflow_command_not_implemented",
            detail="Complete test persistence is not wired yet.",
        )
