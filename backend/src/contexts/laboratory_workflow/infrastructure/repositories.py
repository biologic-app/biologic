from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.laboratory_workflow.application.dto import CommandResult
from src.contexts.laboratory_workflow.domain.events import StatusChanged
from src.contexts.laboratory_workflow.domain.status_policy import (
    InvalidStatusTransition,
    SampleDeadlinePolicy,
    ensure_allowed_transition,
)
from src.contexts.laboratory_workflow.infrastructure.crud_repositories import (
    SubscriptionCrudRepository,
)
from src.core.errors import DomainConflictError, NotFoundError
from src.core.status_codes import (
    DIRECTION_COMPLETED,
    DIRECTION_DRAFT,
    DIRECTION_IN_PROGRESS,
    DIRECTION_PARTIALLY_COMPLETED,
    DIRECTION_REGISTERED,
    RESEARCH_COMPLETED,
    RESEARCH_IN_PROGRESS,
    RESEARCH_REJECTED,
    SAMPLE_ANALYZED,
    SAMPLE_COMPLETED,
    SAMPLE_IN_PROGRESS,
    SAMPLE_REGISTERED,
    SAMPLE_REJECTED,
    TEST_COMPLETED,
    TEST_IN_PROGRESS,
    TEST_REJECTED,
)
from src.infrastructure.db.models import (
    ChangeLog,
    Direction,
    DirectionStatus,
    Indicator,
    Protocol,
    Research,
    ResearchGoal,
    ResearchStatus,
    Sample,
    SampleStatus,
    Test,
    TestStatus,
)


class SqlAlchemyWorkflowRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session
        self.events: list[StatusChanged] = []

    async def resolve_notification_targets(
        self, entity_type: str, entity_id: UUID
    ) -> set[UUID]:
        """Every user that should be notified about an event on this entity.

        Delegates to SubscriptionCrudRepository, which merges the mandatory
        role-based rules, the direction owner, the linked sanitary doctor and
        manual subscriptions. Used by the notifications context's subscriber to
        fan a notification out to a specific set of users instead of
        broadcasting to everyone.
        """
        return await SubscriptionCrudRepository(
            session=self.session
        ).resolve_notification_targets(entity_type, entity_id)

    # NOTE: this repository only flushes. The transaction boundary is owned by
    # the single Unit of Work (src.infrastructure.uow.SqlAlchemyUnitOfWork), so a
    # workflow command and the notification/audit rows it emits commit atomically.

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

        await self._ensure_direction_ready_for_registration(direction)
        target_status_id = await self._direction_status_id(DIRECTION_REGISTERED)
        direction.status_id = target_status_id
        direction.updated_by = actor_id
        direction.updated_at = now

        # Регистрация направления каскадно регистрирует его образцы: они
        # переходят pending → registered вместе с направлением.
        await self._register_direction_samples(
            direction_id=direction_id,
            actor_id=actor_id,
            received_at=direction.received_at or now,
            now=now,
        )
        # Part D: registered samples get their research goals auto-assigned by
        # sample type (goals whose indicators cover the sample's sample_type).
        await self._auto_assign_research_for_direction(direction_id, actor_id)
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
        await self.session.flush()
        return CommandResult(id=direction_id, status_id=target_status_id, updated_at=now)

    async def _register_direction_samples(
        self,
        *,
        direction_id: UUID,
        actor_id: UUID,
        received_at: datetime,
        now: datetime,
    ) -> None:
        result = await self.session.execute(
            select(Sample)
            .where(Sample.direction_id == direction_id, Sample.deleted_at.is_(None))
            .with_for_update(),
        )
        samples = result.scalars().all()
        if not samples:
            return

        target_status_id = await self._sample_status_id(SAMPLE_REGISTERED)
        default_deadline = SampleDeadlinePolicy().calculate(received_at)
        for sample in samples:
            current_status_code = await self._sample_status_code(sample.status_id)
            # Регистрируем только образцы в статусе pending; уже
            # зарегистрированные/отклонённые пропускаем без ошибки.
            try:
                ensure_allowed_transition(
                    "samples", current_status_code, SAMPLE_REGISTERED
                )
            except InvalidStatusTransition:
                continue

            previous_received_at = sample.received_at
            previous_deadline = sample.deadline
            # Дедлайн, проставленный при импорте направления (из даты выхода
            # образца), — авторитетный; политика +2 дня от received_at — только
            # запасной вариант для образцов, заведённых без даты выхода.
            deadline = sample.deadline or default_deadline
            sample.status_id = target_status_id
            sample.received_at = received_at
            sample.deadline = deadline
            sample.updated_by = actor_id
            sample.updated_at = now
            self.events.append(
                StatusChanged(
                    entity_type="samples",
                    entity_id=sample.id,
                    event_type="SampleRegistered",
                    from_code=current_status_code,
                    to_code=SAMPLE_REGISTERED,
                    reason="",
                ),
            )
            self.session.add(
                ChangeLog(
                    entity_type="samples",
                    entity_id=sample.id,
                    action="sample_registered",
                    actor_id=actor_id,
                    snapshot={
                        "status_code": SAMPLE_REGISTERED,
                        "received_at": self._json_timestamp(received_at),
                        "deadline": self._json_timestamp(deadline),
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
                            "to": self._json_timestamp(deadline),
                        },
                    },
                ),
            )

    async def _auto_assign_research_for_direction(
        self, direction_id: UUID, actor_id: UUID
    ) -> None:
        """Auto-assign research goals to each freshly-registered sample (Part D).

        For every sample of the direction that has no active research, derive the
        research goals from the sample's type — goals that have at least one
        indicator whose ``sample_type_id`` matches the sample — and create a
        research (in_progress) with its tests via ``assign_research``. Samples
        whose type maps to no goals are skipped silently.
        """
        samples = (
            await self.session.execute(
                select(Sample.id, Sample.sample_type_id).where(
                    Sample.direction_id == direction_id,
                    Sample.deleted_at.is_(None),
                ),
            )
        ).all()
        for sample_id, sample_type_id in samples:
            if sample_type_id is None:
                continue
            existing_research = (
                await self.session.execute(
                    select(Research.id).where(
                        Research.sample_id == sample_id,
                        Research.deleted_at.is_(None),
                    ),
                )
            ).first()
            if existing_research is not None:
                continue
            goal_ids = (
                await self.session.execute(
                    select(Indicator.research_goal_id)
                    .where(
                        Indicator.sample_type_id == sample_type_id,
                        Indicator.deleted_at.is_(None),
                    )
                    .distinct(),
                )
            ).scalars().all()
            for goal_id in goal_ids:
                if goal_id is None:
                    continue
                await self.assign_research(
                    sample_id=sample_id,
                    actor_id=actor_id,
                    research_goal_id=goal_id,
                    comment=None,
                )

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

    async def _ensure_direction_ready_for_registration(self, direction: Direction) -> None:
        missing_direction_fields = [
            name
            for name, value in (
                ("doctor_id", direction.doctor_id),
                ("object_id", direction.object_id),
            )
            if value is None
        ]
        if missing_direction_fields:
            raise DomainConflictError(
                code="direction_missing_doctor_or_object",
                detail=(
                    "Direction must have a sanitary doctor and an object assigned "
                    f"before registration. Missing: {', '.join(missing_direction_fields)}."
                ),
            )

        result = await self.session.execute(
            select(Sample.id, Sample.name, Sample.sample_type_id).where(
                Sample.direction_id == direction.id,
                Sample.deleted_at.is_(None),
            ),
        )
        samples = result.all()
        if not samples:
            raise DomainConflictError(
                code="direction_missing_samples",
                detail="Direction must contain at least one sample before registration.",
            )

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
        await self.session.flush()
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
            ensure_allowed_transition("samples", current_status_code, SAMPLE_REJECTED)
        except InvalidStatusTransition as exc:
            raise DomainConflictError(
                code=exc.code,
                detail=(
                    "Sample can be rejected only from pending status. "
                    f"Current status is {current_status_code}."
                ),
            ) from exc

        target_status_id = await self._sample_status_id(SAMPLE_REJECTED)
        sample.status_id = target_status_id
        sample.updated_by = actor_id
        sample.updated_at = now
        self.events.append(
            StatusChanged(
                entity_type="samples",
                entity_id=sample_id,
                event_type="SampleRejected",
                from_code=current_status_code,
                to_code=SAMPLE_REJECTED,
                reason=reason,
            ),
        )
        self.session.add(
            ChangeLog(
                entity_type="samples",
                entity_id=sample_id,
                action="sample_rejected",
                actor_id=actor_id,
                snapshot={"status_code": SAMPLE_REJECTED, "reason": reason},
                diff={
                    "status_code": {
                        "from": current_status_code,
                        "to": SAMPLE_REJECTED,
                    },
                    "reason": reason,
                },
            ),
        )
        await self._reject_sample_children(sample_id, actor_id, "sample_rejected")
        if sample.direction_id is not None:
            await self._recalculate_direction_status(sample.direction_id, actor_id)
        await self.session.flush()
        return CommandResult(id=sample_id, status_id=target_status_id, updated_at=now)

    async def assign_research(
        self,
        sample_id: UUID,
        actor_id: UUID,
        research_goal_id: UUID,
        comment: str | None,
    ) -> CommandResult:
        now = datetime.now(UTC)
        sample = await self._get_sample_for_update(sample_id)
        sample_status_code = await self._sample_status_code(sample.status_id)
        if sample_status_code in {SAMPLE_COMPLETED, SAMPLE_REJECTED}:
            raise DomainConflictError(
                code="invalid_status_transition",
                detail="Research cannot be assigned to completed or rejected samples.",
            )
        goal = await self._get_research_goal(research_goal_id)
        research_status_id = await self._research_status_id(RESEARCH_IN_PROGRESS)
        research = Research(
            id=uuid4(),
            sample_id=sample_id,
            research_goal_id=research_goal_id,
            lab_id=goal.lab_id,
            comment=comment,
            status_id=research_status_id,
            received_at=now,
            created_by=actor_id,
            updated_by=actor_id,
            created_at=now,
            updated_at=now,
        )
        self.session.add(research)
        test_status_id = await self._test_status_id(TEST_IN_PROGRESS)
        indicators = (
            await self.session.execute(
                select(Indicator.id).where(
                    Indicator.research_goal_id == research_goal_id,
                    Indicator.deleted_at.is_(None),
                ),
            )
        ).scalars().all()
        for indicator_id in indicators:
            self.session.add(
                Test(
                    id=uuid4(),
                    research_id=research.id,
                    indicator_id=indicator_id,
                    status_id=test_status_id,
                    created_by=actor_id,
                    updated_by=actor_id,
                    created_at=now,
                    updated_at=now,
                ),
            )
        self._add_audit(
            entity_type="research",
            entity_id=research.id,
            action="research_assigned",
            actor_id=actor_id,
            diff={"sample_id": str(sample_id), "research_goal_id": str(research_goal_id)},
        )
        await self.session.flush()
        return CommandResult(id=research.id, status_id=research_status_id, updated_at=now)

    async def complete_test(
        self,
        test_id: UUID,
        actor_id: UUID,
        value: str,
        norm: str | None,
        comment: str | None,
        verdict: bool | None,
    ) -> CommandResult:
        test = await self._get_test_for_update(test_id)
        await self._ensure_sample_started_for_test(test, actor_id)
        test.value = value
        test.norm = norm
        test.comment = comment
        test.verdict = verdict
        result = await self._transition_test(
            test=test,
            actor_id=actor_id,
            to_code=TEST_COMPLETED,
            action="test_completed",
            reason=comment,
            commit=False,
        )
        await self._complete_parents_when_terminal(test.research_id, actor_id)
        await self.session.flush()
        return result

    async def reject_research(
        self, research_id: UUID, actor_id: UUID, reason: str
    ) -> CommandResult:
        research = await self._get_research_for_update(research_id)
        research.comment = reason or research.comment
        return await self._transition_research(
            research=research,
            actor_id=actor_id,
            to_code=RESEARCH_REJECTED,
            action="research_rejected",
            reason=reason,
        )

    async def reject_test(self, test_id: UUID, actor_id: UUID, reason: str) -> CommandResult:
        test = await self._get_test_for_update(test_id)
        await self._ensure_sample_started_for_test(test, actor_id)
        test.comment = reason
        result = await self._transition_test(
            test=test,
            actor_id=actor_id,
            to_code=TEST_REJECTED,
            action="test_rejected",
            reason=reason,
            commit=False,
        )
        await self._complete_parents_when_terminal(test.research_id, actor_id)
        await self.session.flush()
        return result

    async def _ensure_sample_started_for_test(self, test: Test, actor_id: UUID) -> None:
        """Move the test's sample (and its direction) into work if still registered.

        The removed ``start_research`` command used to perform this side effect.
        Completing/rejecting the first test is now what starts the sample, which
        preserves the cascade precondition that ``in_progress → analyzed`` is only
        valid once the sample has actually entered work.
        """
        research = await self._get_research_for_update(test.research_id)
        sample = await self._get_sample_for_update(research.sample_id)
        await self._ensure_sample_started(sample, actor_id)

    async def _ensure_sample_started(self, sample: Sample, actor_id: UUID) -> None:
        if await self._sample_status_code(sample.status_id) == SAMPLE_REGISTERED:
            await self._transition_sample(
                sample=sample,
                actor_id=actor_id,
                to_code=SAMPLE_IN_PROGRESS,
                action="sample_started",
                commit=False,
            )
        if sample.direction_id is not None:
            direction = await self._get_direction_for_update(sample.direction_id)
            if await self._direction_status_code(direction.status_id) == DIRECTION_REGISTERED:
                await self._transition_direction(
                    direction=direction,
                    actor_id=actor_id,
                    to_code=DIRECTION_IN_PROGRESS,
                    action="direction_started",
                    commit=False,
                )

    async def close_sample(
        self,
        sample_id: UUID,
        actor_id: UUID,
        verdict: str,
        comment: str | None,
    ) -> CommandResult:
        sample = await self._get_sample_for_update(sample_id)
        active_count = await self._active_nonterminal_research_count(sample_id)
        if active_count:
            raise DomainConflictError(
                code="sample_not_closeable",
                detail="Sample can be closed only after all research is terminal.",
            )
        sample.verdict = verdict
        sample.completed_at = datetime.now(UTC)
        result = await self._transition_sample(
            sample=sample,
            actor_id=actor_id,
            to_code=SAMPLE_COMPLETED,
            action="sample_closed",
            reason=comment,
            commit=False,
        )
        if sample.direction_id is not None:
            await self._recalculate_direction_status(sample.direction_id, actor_id)
        await self.session.flush()
        return result

    async def create_protocol(
        self,
        actor_id: UUID,
        sample_ids: list[UUID],
        protocol_type_id: UUID | None,
        conclusion_id: UUID | None,
        copies: int | None,
    ) -> CommandResult:
        now = datetime.now(UTC)
        # Both terminal sample states may be issued into a protocol: completed
        # samples carry results, rejected ("брак") ones are reported as excerpts.
        issuable_status_ids = {
            await self._sample_status_id(SAMPLE_COMPLETED),
            await self._sample_status_id(SAMPLE_REJECTED),
        }
        samples = (
            await self.session.execute(
                select(Sample).where(Sample.id.in_(sample_ids), Sample.deleted_at.is_(None)),
            )
        ).scalars().all()
        if len(samples) != len(set(sample_ids)):
            raise NotFoundError("One or more samples were not found.")
        if any(sample.status_id not in issuable_status_ids for sample in samples):
            raise DomainConflictError(
                code="protocol_not_issuable",
                detail="Protocol can be created only for completed or rejected samples.",
            )
        protocol = Protocol(
            id=uuid4(),
            year_no=now.year,
            copies=copies,
            protocol_type_id=protocol_type_id,
            conclusion_id=conclusion_id,
            created_by=actor_id,
            updated_by=actor_id,
            created_at=now,
            updated_at=now,
        )
        self.session.add(protocol)
        for sample in samples:
            sample.protocol_id = protocol.id
            sample.updated_by = actor_id
            sample.updated_at = now
        self._add_audit(
            entity_type="protocols",
            entity_id=protocol.id,
            action="protocol_created",
            actor_id=actor_id,
            diff={"sample_ids": [str(sample_id) for sample_id in sample_ids]},
        )
        await self.session.flush()
        return CommandResult(id=protocol.id, status_id=protocol.id, updated_at=now)

    async def update_protocol(
        self,
        protocol_id: UUID,
        actor_id: UUID,
        protocol_type_id: UUID | None,
        conclusion_id: UUID | None,
        copies: int | None,
    ) -> CommandResult:
        now = datetime.now(UTC)
        protocol = await self._get_protocol_for_update(protocol_id)
        if protocol.issued_at is not None:
            raise DomainConflictError(
                code="protocol_not_issuable",
                detail="Issued protocol cannot be updated.",
            )
        protocol.protocol_type_id = protocol_type_id
        protocol.conclusion_id = conclusion_id
        protocol.copies = copies
        protocol.updated_by = actor_id
        protocol.updated_at = now
        self._add_audit(
            entity_type="protocols",
            entity_id=protocol_id,
            action="protocol_updated",
            actor_id=actor_id,
            diff={"copies": copies},
        )
        await self.session.flush()
        return CommandResult(id=protocol_id, status_id=protocol_id, updated_at=now)

    async def issue_protocol(
        self,
        protocol_id: UUID,
        actor_id: UUID,
        issued_at: datetime | None,
    ) -> CommandResult:
        now = datetime.now(UTC)
        protocol = await self._get_protocol_for_update(protocol_id)
        if protocol.issued_at is not None:
            raise DomainConflictError(
                code="protocol_not_issuable",
                detail="Protocol is already issued.",
            )
        protocol.issued_at = issued_at or now
        protocol.is_signed = True
        protocol.updated_by = actor_id
        protocol.updated_at = now
        self._add_audit(
            entity_type="protocols",
            entity_id=protocol_id,
            action="protocol_issued",
            actor_id=actor_id,
            diff={"issued_at": self._json_timestamp(protocol.issued_at)},
        )
        await self.session.flush()
        return CommandResult(id=protocol_id, status_id=protocol_id, updated_at=now)

    async def _get_sample_for_update(self, sample_id: UUID) -> Sample:
        result = await self.session.execute(
            select(Sample)
            .where(Sample.id == sample_id, Sample.deleted_at.is_(None))
            .with_for_update(),
        )
        sample = result.scalar_one_or_none()
        if sample is None:
            raise NotFoundError("Sample was not found.")
        return sample

    async def _get_direction_for_update(self, direction_id: UUID) -> Direction:
        result = await self.session.execute(
            select(Direction)
            .where(Direction.id == direction_id, Direction.deleted_at.is_(None))
            .with_for_update(),
        )
        direction = result.scalar_one_or_none()
        if direction is None:
            raise NotFoundError("Direction was not found.")
        return direction

    async def _get_research_for_update(self, research_id: UUID) -> Research:
        result = await self.session.execute(
            select(Research)
            .where(Research.id == research_id, Research.deleted_at.is_(None))
            .with_for_update(),
        )
        research = result.scalar_one_or_none()
        if research is None:
            raise NotFoundError("Research was not found.")
        return research

    async def _get_test_for_update(self, test_id: UUID) -> Test:
        result = await self.session.execute(
            select(Test).where(Test.id == test_id, Test.deleted_at.is_(None)).with_for_update(),
        )
        test = result.scalar_one_or_none()
        if test is None:
            raise NotFoundError("Test was not found.")
        return test

    async def _get_protocol_for_update(self, protocol_id: UUID) -> Protocol:
        result = await self.session.execute(
            select(Protocol)
            .where(Protocol.id == protocol_id, Protocol.deleted_at.is_(None))
            .with_for_update(),
        )
        protocol = result.scalar_one_or_none()
        if protocol is None:
            raise NotFoundError("Protocol was not found.")
        return protocol

    async def _get_research_goal(self, research_goal_id: UUID) -> ResearchGoal:
        result = await self.session.execute(
            select(ResearchGoal).where(
                ResearchGoal.id == research_goal_id,
                ResearchGoal.deleted_at.is_(None),
            ),
        )
        goal = result.scalar_one_or_none()
        if goal is None:
            raise NotFoundError("Research goal was not found.")
        return goal

    async def _research_status_code(self, status_id: UUID | None) -> str:
        if status_id is None:
            raise DomainConflictError(
                code="status_not_configured",
                detail="Research has no status.",
            )
        result = await self.session.execute(
            select(ResearchStatus.code).where(
                ResearchStatus.id == status_id,
                ResearchStatus.deleted_at.is_(None),
            ),
        )
        code = result.scalar_one_or_none()
        if code is None:
            raise DomainConflictError(
                code="status_not_configured",
                detail="Research status is not configured.",
            )
        return code

    async def _research_status_id(self, code: str) -> UUID:
        result = await self.session.execute(
            select(ResearchStatus.id).where(
                ResearchStatus.code == code,
                ResearchStatus.deleted_at.is_(None),
            ),
        )
        status_id = result.scalar_one_or_none()
        if status_id is None:
            raise DomainConflictError(
                code="status_not_configured",
                detail=f"Research status {code!r} is not configured.",
            )
        return status_id

    async def _test_status_code(self, status_id: UUID | None) -> str:
        if status_id is None:
            raise DomainConflictError(code="status_not_configured", detail="Test has no status.")
        result = await self.session.execute(
            select(TestStatus.code).where(
                TestStatus.id == status_id,
                TestStatus.deleted_at.is_(None),
            ),
        )
        code = result.scalar_one_or_none()
        if code is None:
            raise DomainConflictError(
                code="status_not_configured",
                detail="Test status is not configured.",
            )
        return code

    async def _test_status_id(self, code: str) -> UUID:
        result = await self.session.execute(
            select(TestStatus.id).where(
                TestStatus.code == code,
                TestStatus.deleted_at.is_(None),
            ),
        )
        status_id = result.scalar_one_or_none()
        if status_id is None:
            raise DomainConflictError(
                code="status_not_configured",
                detail=f"Test status {code!r} is not configured.",
            )
        return status_id

    async def _transition_direction(
        self,
        *,
        direction: Direction,
        actor_id: UUID,
        to_code: str,
        action: str,
        reason: str | None = None,
        commit: bool = True,
    ) -> CommandResult:
        now = datetime.now(UTC)
        from_code = await self._direction_status_code(direction.status_id)
        self._ensure_transition("directions", from_code, to_code)
        status_id = await self._direction_status_id(to_code)
        direction.status_id = status_id
        direction.updated_by = actor_id
        direction.updated_at = now
        self._add_status_audit(
            "directions",
            direction.id,
            action,
            actor_id,
            from_code,
            to_code,
            reason,
        )
        if commit:
            await self.session.flush()
        return CommandResult(id=direction.id, status_id=status_id, updated_at=now)

    async def _transition_sample(
        self,
        *,
        sample: Sample,
        actor_id: UUID,
        to_code: str,
        action: str,
        reason: str | None = None,
        commit: bool = True,
    ) -> CommandResult:
        now = datetime.now(UTC)
        from_code = await self._sample_status_code(sample.status_id)
        self._ensure_transition("samples", from_code, to_code)
        status_id = await self._sample_status_id(to_code)
        sample.status_id = status_id
        sample.updated_by = actor_id
        sample.updated_at = now
        self._add_status_audit("samples", sample.id, action, actor_id, from_code, to_code, reason)
        if commit:
            await self.session.flush()
        return CommandResult(id=sample.id, status_id=status_id, updated_at=now)

    async def _transition_research(
        self,
        *,
        research: Research,
        actor_id: UUID,
        to_code: str,
        action: str,
        reason: str | None = None,
        commit: bool = True,
    ) -> CommandResult:
        now = datetime.now(UTC)
        from_code = await self._research_status_code(research.status_id)
        self._ensure_transition("research", from_code, to_code)
        status_id = await self._research_status_id(to_code)
        research.status_id = status_id
        research.updated_by = actor_id
        research.updated_at = now
        if to_code == RESEARCH_COMPLETED:
            research.completed_at = now
        if to_code == RESEARCH_IN_PROGRESS:
            research.received_at = research.received_at or now
        self._add_status_audit(
            "research",
            research.id,
            action,
            actor_id,
            from_code,
            to_code,
            reason,
        )
        if commit:
            await self.session.flush()
        return CommandResult(id=research.id, status_id=status_id, updated_at=now)

    async def _transition_test(
        self,
        *,
        test: Test,
        actor_id: UUID,
        to_code: str,
        action: str,
        reason: str | None = None,
        commit: bool = True,
    ) -> CommandResult:
        now = datetime.now(UTC)
        from_code = await self._test_status_code(test.status_id)
        self._ensure_transition("tests", from_code, to_code)
        status_id = await self._test_status_id(to_code)
        test.status_id = status_id
        test.updated_by = actor_id
        test.updated_at = now
        self._add_status_audit("tests", test.id, action, actor_id, from_code, to_code, reason)
        if commit:
            await self.session.flush()
        return CommandResult(id=test.id, status_id=status_id, updated_at=now)

    def _ensure_transition(self, resource: str, from_code: str, to_code: str) -> None:
        try:
            ensure_allowed_transition(resource, from_code, to_code)
        except InvalidStatusTransition as exc:
            raise DomainConflictError(
                code=exc.code,
                detail=f"Invalid {resource} status transition {from_code} -> {to_code}.",
            ) from exc

    async def _active_nonterminal_research_count(self, sample_id: UUID) -> int:
        terminal_ids = [
            await self._research_status_id(RESEARCH_COMPLETED),
            await self._research_status_id(RESEARCH_REJECTED),
        ]
        result = await self.session.execute(
            select(func.count()).select_from(Research).where(
                Research.sample_id == sample_id,
                Research.deleted_at.is_(None),
                Research.status_id.not_in(terminal_ids),
            ),
        )
        return int(result.scalar_one())

    async def _complete_parents_when_terminal(self, research_id: UUID, actor_id: UUID) -> None:
        research = await self._get_research_for_update(research_id)
        active_count = await self._active_nonterminal_test_count(research_id)
        if active_count:
            return
        current_research_code = await self._research_status_code(research.status_id)
        if current_research_code != RESEARCH_COMPLETED:
            await self._transition_research(
                research=research,
                actor_id=actor_id,
                to_code=RESEARCH_COMPLETED,
                action="research_completed",
                commit=False,
            )
        sample = await self._get_sample_for_update(research.sample_id)
        if not await self._active_nonterminal_research_count(sample.id):
            sample_code = await self._sample_status_code(sample.status_id)
            if sample_code != SAMPLE_ANALYZED:
                await self._transition_sample(
                    sample=sample,
                    actor_id=actor_id,
                    to_code=SAMPLE_ANALYZED,
                    action="sample_analyzed",
                    commit=False,
                )
        if sample.direction_id is not None:
            await self._recalculate_direction_status(sample.direction_id, actor_id)

    async def _active_nonterminal_test_count(self, research_id: UUID) -> int:
        terminal_ids = [
            await self._test_status_id(TEST_COMPLETED),
            await self._test_status_id(TEST_REJECTED),
        ]
        result = await self.session.execute(
            select(func.count()).select_from(Test).where(
                Test.research_id == research_id,
                Test.deleted_at.is_(None),
                Test.is_active.is_(True),
                Test.status_id.not_in(terminal_ids),
            ),
        )
        return int(result.scalar_one())

    async def _recalculate_direction_status(self, direction_id: UUID, actor_id: UUID) -> None:
        direction = await self._get_direction_for_update(direction_id)
        if direction.status_id is not None:
            current_code = await self._direction_status_code(direction.status_id)
            if current_code == DIRECTION_DRAFT:
                # Direction was never registered — completion/partial-completion
                # cascades only make sense once work has actually started.
                return
        completed_id = await self._sample_status_id(SAMPLE_COMPLETED)
        rejected_id = await self._sample_status_id(SAMPLE_REJECTED)
        result = await self.session.execute(
            select(Sample.status_id).where(
                Sample.direction_id == direction_id,
                Sample.deleted_at.is_(None),
            ),
        )
        statuses = list(result.scalars().all())
        if statuses and all(status in {completed_id, rejected_id} for status in statuses):
            await self._transition_direction(
                direction=direction,
                actor_id=actor_id,
                to_code=DIRECTION_COMPLETED,
                action="direction_completed",
                commit=False,
            )
        elif direction.status_id is not None:
            code = await self._direction_status_code(direction.status_id)
            if code == DIRECTION_IN_PROGRESS:
                await self._transition_direction(
                    direction=direction,
                    actor_id=actor_id,
                    to_code=DIRECTION_PARTIALLY_COMPLETED,
                    action="direction_partially_completed",
                    commit=False,
                )

    async def _reject_sample_children(self, sample_id: UUID, actor_id: UUID, reason: str) -> None:
        rejected_research_status_id = await self._research_status_id(RESEARCH_REJECTED)
        rejected_test_status_id = await self._test_status_id(TEST_REJECTED)
        research_result = await self.session.execute(
            select(Research).where(
                Research.sample_id == sample_id,
                Research.deleted_at.is_(None),
            )
        )
        if not hasattr(research_result, "scalars"):
            return
        research_rows = research_result.scalars().all()
        now = datetime.now(UTC)
        for research in research_rows:
            from_code = await self._research_status_code(research.status_id)
            if from_code != RESEARCH_REJECTED:
                research.status_id = rejected_research_status_id
                research.updated_by = actor_id
                research.updated_at = now
                self._add_status_audit(
                    "research",
                    research.id,
                    "research_rejected",
                    actor_id,
                    from_code,
                    RESEARCH_REJECTED,
                    reason,
                )
            test_rows = (
                await self.session.execute(
                    select(Test).where(
                        Test.research_id == research.id,
                        Test.deleted_at.is_(None),
                        Test.is_active.is_(True),
                    ),
                )
            ).scalars().all()
            for test in test_rows:
                test_from_code = await self._test_status_code(test.status_id)
                if test_from_code != TEST_REJECTED:
                    test.status_id = rejected_test_status_id
                    test.comment = reason
                    test.updated_by = actor_id
                    test.updated_at = now
                    self._add_status_audit(
                        "tests",
                        test.id,
                        "test_rejected",
                        actor_id,
                        test_from_code,
                        TEST_REJECTED,
                        reason,
                    )

    def _add_status_audit(
        self,
        entity_type: str,
        entity_id: UUID,
        action: str,
        actor_id: UUID,
        from_code: str,
        to_code: str,
        reason: str | None,
    ) -> None:
        self._add_audit(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_id=actor_id,
            diff={
                "status_code": {"from": from_code, "to": to_code},
                "reason": reason or action,
            },
            snapshot={"status_code": to_code},
        )

    def _add_audit(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        action: str,
        actor_id: UUID,
        diff: dict[str, object],
        snapshot: dict[str, object] | None = None,
    ) -> None:
        self.session.add(
            ChangeLog(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                actor_id=actor_id,
                snapshot=snapshot or {},
                diff=diff,
            ),
        )
