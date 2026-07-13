from datetime import UTC
from os import environ
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy import delete, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql import Select

from src.contexts.laboratory_workflow.infrastructure.repositories import (
    SqlAlchemyWorkflowRepository,
)
from src.core.errors import DomainConflictError, NotFoundError
from src.infrastructure.db.models import (
    ChangeLog,
    Direction,
    DirectionStatus,
    Doctor,
    Object,
    Research,
    ResearchGoal,
    Sample,
    SampleStatus,
    SampleType,
)

DIRECTION_ID = UUID("00000000-0000-0000-0000-000000000001")
DRAFT_STATUS_ID = UUID("00000000-0000-0000-0000-000000000002")
REGISTERED_STATUS_ID = UUID("00000000-0000-0000-0000-000000000003")
ACTOR_ID = UUID("00000000-0000-0000-0000-000000000004")
SAMPLE_ID = UUID("00000000-0000-0000-0000-000000000005")
SAMPLE_TYPE_ID = UUID("00000000-0000-0000-0000-000000000006")
RESEARCH_ID = UUID("00000000-0000-0000-0000-000000000007")
RESEARCH_GOAL_ID = UUID("00000000-0000-0000-0000-000000000008")
SAMPLE_PENDING_STATUS_ID = UUID("00000000-0000-0000-0000-000000000009")
SAMPLE_REGISTERED_STATUS_ID = UUID("00000000-0000-0000-0000-00000000000a")
DOCTOR_ID = UUID("00000000-0000-0000-0000-00000000000b")
OBJECT_ID = UUID("00000000-0000-0000-0000-00000000000c")


class RowResult:
    def __init__(self, row: Direction | None) -> None:
        self.row = row

    def scalar_one_or_none(self) -> Direction | None:
        return self.row


class ScalarResult:
    def __init__(self, value: UUID | str | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> UUID | str | None:
        return self.value


class ScalarList:
    def __init__(self, values: list[UUID]) -> None:
        self.values = values

    def all(self) -> list[UUID]:
        return self.values


class ListResult:
    def __init__(self, rows: list[tuple[UUID, str, UUID | None]]) -> None:
        self.rows = rows

    def all(self) -> list[tuple[UUID, str, UUID | None]]:
        return self.rows

    def scalars(self) -> ScalarList:
        return ScalarList([row[0] for row in self.rows])


class SampleScalars:
    def __init__(self, values: list[Sample]) -> None:
        self.values = values

    def all(self) -> list[Sample]:
        return self.values


class SampleListResult:
    def __init__(self, values: list[Sample]) -> None:
        self.values = values

    def scalars(self) -> SampleScalars:
        return SampleScalars(self.values)


class FakeAsyncSession:
    def __init__(
        self,
        *,
        direction: Direction | None,
        current_status_code: str | None = "draft",
        samples: list[tuple[UUID, str, UUID | None]] | None = None,
        research_sample_ids: list[UUID] | None = None,
        sample_objects: list[Sample] | None = None,
    ) -> None:
        self.direction = direction
        self.current_status_code = current_status_code
        self.samples: list[tuple[UUID, str, UUID | None]] = (
            samples if samples is not None else [(SAMPLE_ID, "Sample", SAMPLE_TYPE_ID)]
        )
        self.research_sample_ids = (
            research_sample_ids if research_sample_ids is not None else [SAMPLE_ID]
        )
        # Каскадная регистрация образцов подгружает Sample-объекты; по умолчанию
        # оставляем пустым, чтобы позиционные проверки других тестов не менялись.
        self.sample_objects: list[Sample] = sample_objects if sample_objects is not None else []
        self.statements: list[Select[tuple[Any, ...]]] = []
        self.added: list[object] = []
        self.flushed = False

    async def execute(
        self,
        statement: Select[tuple[Any, ...]],
    ) -> RowResult | ScalarResult | ListResult | SampleListResult:
        self.statements.append(statement)
        if len(self.statements) == 1:
            return RowResult(self.direction)
        if len(self.statements) == 2:
            return ScalarResult(self.current_status_code)
        if len(self.statements) == 3:
            return ListResult(self.samples)
        if len(self.statements) == 4:
            return ListResult([(sample_id, "", None) for sample_id in self.research_sample_ids])
        if len(self.statements) == 5:
            # _direction_status_id(registered)
            return ScalarResult(REGISTERED_STATUS_ID)
        if len(self.statements) == 6:
            # Каскад: подгрузка Sample-объектов направления.
            return SampleListResult(self.sample_objects)
        if len(self.statements) == 7:
            # _sample_status_id(registered)
            return ScalarResult(SAMPLE_REGISTERED_STATUS_ID)
        # _sample_status_code для каждого образца.
        return ScalarResult("pending")

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        self.flushed = True


@pytest.mark.asyncio
async def test_register_direction_changes_draft_to_registered_and_writes_audit() -> None:
    direction = Direction(
        id=DIRECTION_ID,
        year_no=2026,
        status_id=DRAFT_STATUS_ID,
        doctor_id=DOCTOR_ID,
        object_id=OBJECT_ID,
    )
    fake_session = FakeAsyncSession(direction=direction, current_status_code="draft")
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    result = await repository.register_direction(
        direction_id=DIRECTION_ID,
        actor_id=ACTOR_ID,
        comment="Ready for laboratory workflow",
    )

    assert result.id == DIRECTION_ID
    assert result.status_id == REGISTERED_STATUS_ID
    assert result.updated_at.tzinfo is not None
    assert result.updated_at.utcoffset() == UTC.utcoffset(result.updated_at)
    assert direction.status_id == REGISTERED_STATUS_ID
    assert direction.updated_by == ACTOR_ID
    assert fake_session.flushed

    audit_entry = next(item for item in fake_session.added if isinstance(item, ChangeLog))
    assert audit_entry.entity_type == "directions"
    assert audit_entry.entity_id == DIRECTION_ID
    assert audit_entry.action == "direction_registered"
    assert audit_entry.actor_id == ACTOR_ID
    assert audit_entry.diff == {
        "status_code": {"from": "draft", "to": "registered"},
        "comment": "Ready for laboratory workflow",
    }
    assert len(repository.events) == 1
    assert repository.events[0].event_type == "DirectionRegistered"
    assert repository.events[0].from_code == "draft"
    assert repository.events[0].to_code == "registered"


@pytest.mark.asyncio
async def test_register_direction_cascades_samples_to_registered() -> None:
    direction = Direction(
        id=DIRECTION_ID,
        year_no=2026,
        status_id=DRAFT_STATUS_ID,
        doctor_id=DOCTOR_ID,
        object_id=OBJECT_ID,
    )
    sample = Sample(
        id=SAMPLE_ID,
        name="Sample",
        direction_id=DIRECTION_ID,
        sample_type_id=SAMPLE_TYPE_ID,
        status_id=SAMPLE_PENDING_STATUS_ID,
    )
    fake_session = FakeAsyncSession(
        direction=direction,
        current_status_code="draft",
        sample_objects=[sample],
    )
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    await repository.register_direction(
        direction_id=DIRECTION_ID,
        actor_id=ACTOR_ID,
        comment=None,
    )

    assert sample.status_id == SAMPLE_REGISTERED_STATUS_ID
    assert sample.updated_by == ACTOR_ID
    sample_audit = next(
        item
        for item in fake_session.added
        if isinstance(item, ChangeLog) and item.entity_type == "samples"
    )
    assert sample_audit.action == "sample_registered"
    assert sample_audit.diff["status_code"] == {"from": "pending", "to": "registered"}
    sample_events = [e for e in repository.events if e.entity_type == "samples"]
    assert len(sample_events) == 1
    assert sample_events[0].to_code == "registered"


@pytest.mark.asyncio
async def test_register_direction_rejects_invalid_initial_status() -> None:
    direction = Direction(id=DIRECTION_ID, year_no=2026, status_id=REGISTERED_STATUS_ID)
    fake_session = FakeAsyncSession(direction=direction, current_status_code="registered")
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    with pytest.raises(DomainConflictError) as exc:
        await repository.register_direction(
            direction_id=DIRECTION_ID,
            actor_id=ACTOR_ID,
            comment=None,
        )

    assert exc.value.extra["code"] == "invalid_status_transition"
    assert direction.status_id == REGISTERED_STATUS_ID
    assert not fake_session.flushed


@pytest.mark.parametrize(
    ("samples", "research_sample_ids", "error_code"),
    [
        ([], [], "direction_missing_samples"),
        ([(SAMPLE_ID, "Sample", None)], [SAMPLE_ID], "direction_missing_sample_data"),
        ([(SAMPLE_ID, "Sample", SAMPLE_TYPE_ID)], [], "direction_missing_research_assignments"),
    ],
)
@pytest.mark.asyncio
async def test_register_direction_validates_required_samples_and_research(
    samples: list[tuple[UUID, str, UUID | None]],
    research_sample_ids: list[UUID],
    error_code: str,
) -> None:
    direction = Direction(
        id=DIRECTION_ID,
        year_no=2026,
        status_id=DRAFT_STATUS_ID,
        doctor_id=DOCTOR_ID,
        object_id=OBJECT_ID,
    )
    fake_session = FakeAsyncSession(
        direction=direction,
        samples=samples,
        research_sample_ids=research_sample_ids,
    )
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    with pytest.raises(DomainConflictError) as exc:
        await repository.register_direction(
            direction_id=DIRECTION_ID,
            actor_id=ACTOR_ID,
            comment=None,
        )

    assert exc.value.extra["code"] == error_code
    assert direction.status_id == DRAFT_STATUS_ID
    assert not fake_session.flushed


@pytest.mark.parametrize(
    ("doctor_id", "object_id"),
    [
        (None, OBJECT_ID),
        (DOCTOR_ID, None),
        (None, None),
    ],
)
@pytest.mark.asyncio
async def test_register_direction_requires_doctor_and_object(
    doctor_id: UUID | None,
    object_id: UUID | None,
) -> None:
    direction = Direction(
        id=DIRECTION_ID,
        year_no=2026,
        status_id=DRAFT_STATUS_ID,
        doctor_id=doctor_id,
        object_id=object_id,
    )
    fake_session = FakeAsyncSession(direction=direction, current_status_code="draft")
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    with pytest.raises(DomainConflictError) as exc:
        await repository.register_direction(
            direction_id=DIRECTION_ID,
            actor_id=ACTOR_ID,
            comment=None,
        )

    assert exc.value.extra["code"] == "direction_missing_doctor_or_object"
    assert direction.status_id == DRAFT_STATUS_ID
    assert not fake_session.flushed


@pytest.mark.asyncio
async def test_register_direction_returns_not_found_for_missing_direction() -> None:
    fake_session = FakeAsyncSession(direction=None)
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    with pytest.raises(NotFoundError):
        await repository.register_direction(
            direction_id=DIRECTION_ID,
            actor_id=ACTOR_ID,
            comment=None,
        )

    assert not fake_session.flushed


@pytest.mark.asyncio
async def test_register_direction_rejects_missing_or_deleted_current_status() -> None:
    direction = Direction(id=DIRECTION_ID, year_no=2026, status_id=DRAFT_STATUS_ID)
    fake_session = FakeAsyncSession(direction=direction, current_status_code=None)
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    with pytest.raises(DomainConflictError) as exc:
        await repository.register_direction(
            direction_id=DIRECTION_ID,
            actor_id=ACTOR_ID,
            comment=None,
        )

    assert exc.value.extra["code"] == "status_not_configured"
    assert not fake_session.flushed


@pytest.mark.asyncio
async def test_register_direction_status_lookup_uses_stable_code() -> None:
    direction = Direction(
        id=DIRECTION_ID,
        year_no=2026,
        status_id=DRAFT_STATUS_ID,
        doctor_id=DOCTOR_ID,
        object_id=OBJECT_ID,
    )
    fake_session = FakeAsyncSession(direction=direction, current_status_code="draft")
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    await repository.register_direction(
        direction_id=DIRECTION_ID,
        actor_id=ACTOR_ID,
        comment=None,
    )

    compiled_lookup = str(
        fake_session.statements[4].compile(
            dialect=postgresql.dialect(),  # type: ignore[no-untyped-call]
            compile_kwargs={"literal_binds": True},
        ),
    )
    assert "direction_statuses.code = 'registered'" in compiled_lookup
    assert "direction_statuses.name" not in compiled_lookup

    compiled_current_status_lookup = str(
        fake_session.statements[1].compile(
            dialect=postgresql.dialect(),  # type: ignore[no-untyped-call]
            compile_kwargs={"literal_binds": True},
        ),
    )
    assert "direction_statuses.deleted_at IS NULL" in compiled_current_status_lookup


@pytest.mark.asyncio
async def test_register_direction_persists_with_real_postgres_when_configured() -> None:
    database_url = environ.get("APP_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("APP_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with session_factory() as session:
            await _cleanup_register_direction_rows(session)
            session.add_all(
                [
                    DirectionStatus(id=DRAFT_STATUS_ID, code="draft", name="Draft"),
                    DirectionStatus(id=REGISTERED_STATUS_ID, code="registered", name="Registered"),
                    SampleStatus(id=SAMPLE_PENDING_STATUS_ID, code="pending", name="Pending"),
                    SampleStatus(
                        id=SAMPLE_REGISTERED_STATUS_ID, code="registered", name="Registered"
                    ),
                    SampleType(id=SAMPLE_TYPE_ID, code="sample", name="Sample"),
                    ResearchGoal(id=RESEARCH_GOAL_ID, code="goal", name="Goal"),
                    Doctor(id=DOCTOR_ID, first_name="Test"),
                    Object(id=OBJECT_ID, code="test-object", name="Test object"),
                ],
            )
            # Flushed separately: SQLAlchemy's flush ordering only sorts by
            # declared relationship() dependencies, not bare FK columns — Doctor
            # and Object have neither here, so an insert order relative to
            # Direction can't be inferred without this explicit boundary.
            await session.flush()
            session.add_all(
                [
                    Direction(
                        id=DIRECTION_ID,
                        year_no=2026,
                        status_id=DRAFT_STATUS_ID,
                        doctor_id=DOCTOR_ID,
                        object_id=OBJECT_ID,
                    ),
                    Sample(
                        id=SAMPLE_ID,
                        name="Sample",
                        direction_id=DIRECTION_ID,
                        sample_type_id=SAMPLE_TYPE_ID,
                        status_id=SAMPLE_PENDING_STATUS_ID,
                    ),
                    Research(
                        id=RESEARCH_ID,
                        sample_id=SAMPLE_ID,
                        research_goal_id=RESEARCH_GOAL_ID,
                    ),
                ],
            )
            await session.commit()

            repository = SqlAlchemyWorkflowRepository(session=session)
            result = await repository.register_direction(
                direction_id=DIRECTION_ID,
                actor_id=ACTOR_ID,
                comment="Ready for laboratory workflow",
            )

            persisted_direction = await session.get(Direction, DIRECTION_ID)
            audit_entries = (
                await session.execute(
                    select(ChangeLog).where(
                        ChangeLog.entity_type == "directions",
                        ChangeLog.entity_id == DIRECTION_ID,
                        ChangeLog.action == "direction_registered",
                    ),
                )
            ).scalars().all()

            persisted_sample = await session.get(Sample, SAMPLE_ID)

            assert result.status_id == REGISTERED_STATUS_ID
            assert persisted_direction is not None
            assert persisted_direction.status_id == REGISTERED_STATUS_ID
            assert persisted_direction.updated_by == ACTOR_ID
            assert len(audit_entries) == 1
            assert persisted_sample is not None
            assert persisted_sample.status_id == SAMPLE_REGISTERED_STATUS_ID
            assert persisted_sample.received_at is not None
    finally:
        async with session_factory() as session:
            await _cleanup_register_direction_rows(session)
            await session.commit()
        await engine.dispose()


async def _cleanup_register_direction_rows(session: AsyncSession) -> None:
    await session.execute(delete(ChangeLog).where(ChangeLog.entity_id == DIRECTION_ID))
    await session.execute(delete(Research).where(Research.id == RESEARCH_ID))
    await session.execute(delete(Sample).where(Sample.id == SAMPLE_ID))
    await session.execute(delete(Direction).where(Direction.id == DIRECTION_ID))
    await session.execute(delete(Doctor).where(Doctor.id == DOCTOR_ID))
    await session.execute(delete(Object).where(Object.id == OBJECT_ID))
    await session.execute(delete(ResearchGoal).where(ResearchGoal.id == RESEARCH_GOAL_ID))
    await session.execute(delete(SampleType).where(SampleType.id == SAMPLE_TYPE_ID))
    await session.execute(
        delete(SampleStatus).where(
            SampleStatus.id.in_([SAMPLE_PENDING_STATUS_ID, SAMPLE_REGISTERED_STATUS_ID]),
        ),
    )
    await session.execute(
        delete(DirectionStatus).where(
            DirectionStatus.id.in_([DRAFT_STATUS_ID, REGISTERED_STATUS_ID]),
        ),
    )
