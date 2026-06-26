from datetime import UTC, datetime
from os import environ
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy import delete, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql import Select

from src.contexts.laboratory_workflow.domain.status_policy import SampleDeadlinePolicy
from src.contexts.laboratory_workflow.infrastructure.repositories import (
    SqlAlchemyWorkflowRepository,
)
from src.core.errors import DomainConflictError, NotFoundError
from src.infrastructure.db.models import ChangeLog, Role, RoleScopeType, Sample, SampleStatus, User

SAMPLE_ID = UUID("00000000-0000-0000-0000-000000000101")
PENDING_STATUS_ID = UUID("00000000-0000-0000-0000-000000000102")
REGISTERED_STATUS_ID = UUID("00000000-0000-0000-0000-000000000103")
ACTOR_ID = UUID("00000000-0000-0000-0000-000000000104")
ROLE_ID = UUID("00000000-0000-0000-0000-000000000105")
RECEIVED_AT = datetime(2026, 5, 14, 10, 0, tzinfo=UTC)
DEADLINE = datetime(2026, 5, 16, 10, 0, tzinfo=UTC)


class RowResult:
    def __init__(self, row: Sample | None) -> None:
        self.row = row

    def scalar_one_or_none(self) -> Sample | None:
        return self.row


class ScalarResult:
    def __init__(self, value: UUID | str | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> UUID | str | None:
        return self.value


class FakeAsyncSession:
    def __init__(
        self,
        *,
        sample: Sample | None,
        current_status_code: str | None = "pending",
        target_status_id: UUID | None = REGISTERED_STATUS_ID,
    ) -> None:
        self.sample = sample
        self.current_status_code = current_status_code
        self.target_status_id = target_status_id
        self.statements: list[Select[tuple[Any, ...]]] = []
        self.added: list[object] = []
        self.flushed = False

    async def execute(
        self,
        statement: Select[tuple[Any, ...]],
    ) -> RowResult | ScalarResult:
        self.statements.append(statement)
        if len(self.statements) == 1:
            return RowResult(self.sample)
        if len(self.statements) == 2:
            return ScalarResult(self.current_status_code)
        return ScalarResult(self.target_status_id)

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        self.flushed = True


@pytest.mark.asyncio
async def test_register_sample_changes_pending_to_registered_and_writes_audit() -> None:
    sample = Sample(id=SAMPLE_ID, name="Sample", status_id=PENDING_STATUS_ID)
    fake_session = FakeAsyncSession(sample=sample, current_status_code="pending")
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    result = await repository.register_sample(
        sample_id=SAMPLE_ID,
        actor_id=ACTOR_ID,
        received_at=RECEIVED_AT,
        deadline=DEADLINE,
    )

    assert result.id == SAMPLE_ID
    assert result.status_id == REGISTERED_STATUS_ID
    assert result.updated_at.tzinfo is not None
    assert result.updated_at.utcoffset() == UTC.utcoffset(result.updated_at)
    assert sample.status_id == REGISTERED_STATUS_ID
    assert sample.received_at == RECEIVED_AT
    assert sample.deadline == DEADLINE
    assert sample.updated_by == ACTOR_ID
    assert fake_session.flushed

    audit_entry = next(item for item in fake_session.added if isinstance(item, ChangeLog))
    assert audit_entry.entity_type == "samples"
    assert audit_entry.entity_id == SAMPLE_ID
    assert audit_entry.action == "sample_registered"
    assert audit_entry.actor_id == ACTOR_ID
    assert audit_entry.diff == {
        "status_code": {"from": "pending", "to": "registered"},
        "received_at": {"from": None, "to": RECEIVED_AT.isoformat()},
        "deadline": {"from": None, "to": DEADLINE.isoformat()},
    }
    assert len(repository.events) == 1
    assert repository.events[0].event_type == "SampleRegistered"
    assert repository.events[0].from_code == "pending"
    assert repository.events[0].to_code == "registered"


@pytest.mark.asyncio
async def test_register_sample_calculates_deadline_when_omitted() -> None:
    sample = Sample(id=SAMPLE_ID, name="Sample", status_id=PENDING_STATUS_ID)
    fake_session = FakeAsyncSession(sample=sample, current_status_code="pending")
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    await repository.register_sample(
        sample_id=SAMPLE_ID,
        actor_id=ACTOR_ID,
        received_at=RECEIVED_AT,
        deadline=None,
    )

    assert sample.deadline == SampleDeadlinePolicy().calculate(RECEIVED_AT)


@pytest.mark.asyncio
async def test_register_sample_rejects_invalid_initial_status() -> None:
    sample = Sample(id=SAMPLE_ID, name="Sample", status_id=REGISTERED_STATUS_ID)
    fake_session = FakeAsyncSession(sample=sample, current_status_code="registered")
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    with pytest.raises(DomainConflictError) as exc:
        await repository.register_sample(
            sample_id=SAMPLE_ID,
            actor_id=ACTOR_ID,
            received_at=RECEIVED_AT,
            deadline=DEADLINE,
        )

    assert exc.value.extra["code"] == "invalid_status_transition"
    assert sample.status_id == REGISTERED_STATUS_ID
    assert not fake_session.flushed


@pytest.mark.asyncio
async def test_register_sample_returns_not_found_for_missing_sample() -> None:
    fake_session = FakeAsyncSession(sample=None)
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    with pytest.raises(NotFoundError):
        await repository.register_sample(
            sample_id=SAMPLE_ID,
            actor_id=ACTOR_ID,
            received_at=RECEIVED_AT,
            deadline=DEADLINE,
        )

    assert not fake_session.flushed


@pytest.mark.asyncio
async def test_register_sample_rejects_missing_or_deleted_current_status() -> None:
    sample = Sample(id=SAMPLE_ID, name="Sample", status_id=PENDING_STATUS_ID)
    fake_session = FakeAsyncSession(sample=sample, current_status_code=None)
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    with pytest.raises(DomainConflictError) as exc:
        await repository.register_sample(
            sample_id=SAMPLE_ID,
            actor_id=ACTOR_ID,
            received_at=RECEIVED_AT,
            deadline=DEADLINE,
        )

    assert exc.value.extra["code"] == "status_not_configured"
    assert not fake_session.flushed


@pytest.mark.asyncio
async def test_register_sample_status_lookup_uses_stable_code() -> None:
    sample = Sample(id=SAMPLE_ID, name="Sample", status_id=PENDING_STATUS_ID)
    fake_session = FakeAsyncSession(sample=sample, current_status_code="pending")
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    await repository.register_sample(
        sample_id=SAMPLE_ID,
        actor_id=ACTOR_ID,
        received_at=RECEIVED_AT,
        deadline=DEADLINE,
    )

    compiled_lookup = str(
        fake_session.statements[2].compile(
            dialect=postgresql.dialect(),  # type: ignore[no-untyped-call]
            compile_kwargs={"literal_binds": True},
        ),
    )
    assert "sample_statuses.code = 'registered'" in compiled_lookup
    assert "sample_statuses.name" not in compiled_lookup

    compiled_current_status_lookup = str(
        fake_session.statements[1].compile(
            dialect=postgresql.dialect(),  # type: ignore[no-untyped-call]
            compile_kwargs={"literal_binds": True},
        ),
    )
    assert "sample_statuses.deleted_at IS NULL" in compiled_current_status_lookup


@pytest.mark.asyncio
async def test_register_sample_persists_with_real_postgres_when_configured() -> None:
    database_url = environ.get("APP_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("APP_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with session_factory() as session:
            await _cleanup_register_sample_rows(session)

            pending_row = await session.execute(
                select(SampleStatus).where(
                    SampleStatus.code == "pending",
                    SampleStatus.deleted_at.is_(None),
                ),
            )
            pending_status = pending_row.scalar_one_or_none()
            if pending_status is None:
                pytest.skip("Seeded sample_statuses not found in test database")

            registered_row = await session.execute(
                select(SampleStatus).where(
                    SampleStatus.code == "registered",
                    SampleStatus.deleted_at.is_(None),
                ),
            )
            registered_status = registered_row.scalar_one_or_none()
            if registered_status is None:
                pytest.skip("Seeded sample_statuses not found in test database")

            role_row = await session.execute(
                select(Role).where(Role.key == "registrar-test").limit(1),
            )
            role = role_row.scalar_one_or_none()
            if role is None:
                role = Role(
                    id=ROLE_ID,
                    key="registrar-test",
                    name="Registrar",
                    scope_type=RoleScopeType.GLOBAL,
                )
                session.add(role)

            user_row = await session.execute(
                select(User).where(User.username == "register-sample-test"),
            )
            user = user_row.scalar_one_or_none()
            if user is None:
                user = User(
                    id=ACTOR_ID,
                    username="register-sample-test",
                    password_hash="test",
                    role_id=role.id,
                )
                session.add(user)

            sample = Sample(
                id=SAMPLE_ID,
                name="Sample",
                status_id=pending_status.id,
            )
            session.add(sample)
            await session.commit()

            repository = SqlAlchemyWorkflowRepository(session=session)
            result = await repository.register_sample(
                sample_id=SAMPLE_ID,
                actor_id=ACTOR_ID,
                received_at=RECEIVED_AT,
                deadline=DEADLINE,
            )

            persisted_sample = await session.get(Sample, SAMPLE_ID)
            audit_entries = (
                await session.execute(
                    select(ChangeLog).where(
                        ChangeLog.entity_type == "samples",
                        ChangeLog.entity_id == SAMPLE_ID,
                        ChangeLog.action == "sample_registered",
                    ),
                )
            ).scalars().all()

            assert result.status_id == registered_status.id
            assert persisted_sample is not None
            assert persisted_sample.status_id == registered_status.id
            assert persisted_sample.received_at == RECEIVED_AT
            assert persisted_sample.deadline == DEADLINE
            assert persisted_sample.updated_by == ACTOR_ID
            assert len(audit_entries) == 1
    finally:
        async with session_factory() as session:
            await _cleanup_register_sample_rows(session)
            await session.commit()
        await engine.dispose()


async def _cleanup_register_sample_rows(session: AsyncSession) -> None:
    await session.execute(delete(ChangeLog).where(ChangeLog.entity_id == SAMPLE_ID))
    await session.execute(delete(Sample).where(Sample.id == SAMPLE_ID))
    await session.execute(delete(User).where(User.username == "register-sample-test"))
    await session.execute(delete(Role).where(Role.key == "registrar-test"))
