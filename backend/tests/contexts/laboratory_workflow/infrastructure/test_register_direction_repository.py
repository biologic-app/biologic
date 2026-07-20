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


class FakeResult:
    """Flexible result double dispatched by the fake session's SQL matcher."""

    def __init__(
        self,
        *,
        scalar: Any = None,
        rows: list[Any] | None = None,
        scalar_list: list[Any] | None = None,
        first: Any = None,
    ) -> None:
        self._scalar = scalar
        self._rows = rows or []
        self._scalar_list = scalar_list or []
        self._first = first

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def all(self) -> list[Any]:
        return self._rows

    def first(self) -> Any:
        return self._first

    def scalars(self) -> "FakeResult":
        return FakeResult(rows=self._scalar_list)


def _compiled(statement: Select[tuple[Any, ...]]) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),  # type: ignore[no-untyped-call]
            compile_kwargs={"literal_binds": True},
        )
    )


class FakeAsyncSession:
    """Dispatch-based fake session that keys results off the compiled SQL.

    Order-independent so it tolerates the auto-assign queries added after sample
    registration without brittle positional counting.
    """

    def __init__(
        self,
        *,
        direction: Direction | None,
        current_status_code: str | None = "draft",
        samples: list[tuple[UUID, str, UUID | None]] | None = None,
        sample_objects: list[Sample] | None = None,
        indicator_goal_ids: list[UUID] | None = None,
    ) -> None:
        self.direction = direction
        self.current_status_code = current_status_code
        self.samples: list[tuple[UUID, str, UUID | None]] = (
            samples if samples is not None else [(SAMPLE_ID, "Sample", SAMPLE_TYPE_ID)]
        )
        # Каскадная регистрация образцов подгружает Sample-объекты; по умолчанию
        # пусто, чтобы тесты, не проверяющие каскад, оставались лаконичными.
        self.sample_objects: list[Sample] = sample_objects if sample_objects is not None else []
        # Цели авто-назначения по типу образца: по умолчанию пусто — авто-назначение
        # ничего не создаёт, а assign_research тестируется отдельно / на реальной БД.
        self.indicator_goal_ids = indicator_goal_ids or []
        self.statements: list[Select[tuple[Any, ...]]] = []
        self.added: list[object] = []
        self.flushed = False

    async def execute(self, statement: Select[tuple[Any, ...]]) -> FakeResult:
        self.statements.append(statement)
        sql = _compiled(statement)
        if "FROM directions" in sql:
            return FakeResult(scalar=self.direction)
        # Disambiguate by the projected column (SELECT <table>.<col>), since both
        # the id-by-code and code-by-id lookups mention id and code (WHERE vs SELECT).
        if "SELECT direction_statuses.code" in sql:
            return FakeResult(scalar=self.current_status_code)
        if "SELECT direction_statuses.id" in sql:
            return FakeResult(scalar=REGISTERED_STATUS_ID)
        if "SELECT sample_statuses.id" in sql:
            return FakeResult(scalar=SAMPLE_REGISTERED_STATUS_ID)
        if "SELECT sample_statuses.code" in sql:
            return FakeResult(scalar="pending")
        if "FROM research" in sql:
            return FakeResult(first=None, scalar_list=[])
        if "FROM indicators" in sql:
            return FakeResult(scalar_list=list(self.indicator_goal_ids))
        if "FROM samples" in sql:
            if "FOR UPDATE" in sql:
                # _register_direction_samples: Sample-объекты направления.
                return FakeResult(scalar_list=self.sample_objects)
            if "samples.name" in sql:
                # _ensure_direction_ready_for_registration: (id, name, type).
                return FakeResult(rows=self.samples)
            # _auto_assign_research_for_direction: (id, sample_type_id).
            return FakeResult(rows=[(row[0], row[2]) for row in self.samples])
        raise AssertionError(f"Unexpected statement: {sql}")

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
    assert sample_audit.diff is not None
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
    ("samples", "error_code"),
    [
        ([], "direction_missing_samples"),
        ([(SAMPLE_ID, "Sample", None)], "direction_missing_sample_data"),
    ],
)
@pytest.mark.asyncio
async def test_register_direction_validates_required_samples(
    samples: list[tuple[UUID, str, UUID | None]],
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

    compiled_statements = [_compiled(statement) for statement in fake_session.statements]
    compiled_lookup = next(
        sql
        for sql in compiled_statements
        if "direction_statuses.id" in sql and "direction_statuses.code = 'registered'" in sql
    )
    assert "direction_statuses.name" not in compiled_lookup

    compiled_current_status_lookup = next(
        sql
        for sql in compiled_statements
        if "direction_statuses.code" in sql and "WHERE direction_statuses.id" in sql
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
                    DirectionStatus(id=DRAFT_STATUS_ID, code="draft"),
                    DirectionStatus(id=REGISTERED_STATUS_ID, code="registered"),
                    SampleStatus(id=SAMPLE_PENDING_STATUS_ID, code="pending"),
                    SampleStatus(id=SAMPLE_REGISTERED_STATUS_ID, code="registered"),
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
