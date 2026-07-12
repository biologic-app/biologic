from datetime import UTC, datetime
from os import environ
from uuid import UUID

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.contexts.laboratory_workflow.infrastructure.repositories import (
    SqlAlchemyWorkflowRepository,
)
from src.infrastructure.db.models import (
    ChangeLog,
    Research,
    ResearchGoal,
    Role,
    RoleScopeType,
    Sample,
    Test,
    TestStatus,
    User,
)

ACTOR_ID = UUID("00000000-0000-0000-0000-000000000201")
ROLE_ID = UUID("00000000-0000-0000-0000-000000000202")
RESEARCH_GOAL_ID = UUID("00000000-0000-0000-0000-000000000203")
SAMPLE_ID = UUID("00000000-0000-0000-0000-000000000204")
RESEARCH_ID = UUID("00000000-0000-0000-0000-000000000205")
TEST_ID = UUID("00000000-0000-0000-0000-000000000206")
OTHER_TEST_ID = UUID("00000000-0000-0000-0000-000000000207")


@pytest.mark.asyncio
async def test_complete_test_persists_verdict_and_completes_status() -> None:
    database_url = environ.get("APP_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("APP_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with session_factory() as session:
            await _cleanup_rows(session)

            in_progress_status = await _test_status(session, "in_progress")
            completed_status = await _test_status(session, "completed")
            if in_progress_status is None or completed_status is None:
                pytest.skip("Seeded test_statuses not found in test database")

            role_row = await session.execute(
                select(Role).where(Role.key == "complete-test-fixture"),
            )
            role = role_row.scalar_one_or_none()
            if role is None:
                role = Role(
                    id=ROLE_ID,
                    key="complete-test-fixture",
                    name="Complete Test Fixture",
                    scope_type=RoleScopeType.GLOBAL,
                )
                session.add(role)

            user_row = await session.execute(
                select(User).where(User.username == "complete-test-fixture"),
            )
            user = user_row.scalar_one_or_none()
            if user is None:
                user = User(
                    id=ACTOR_ID,
                    username="complete-test-fixture",
                    password_hash="test",
                    role_id=role.id,
                )
                session.add(user)

            session.add(
                ResearchGoal(id=RESEARCH_GOAL_ID, code="complete-test-fixture", name="Fixture goal")
            )
            session.add(Sample(id=SAMPLE_ID, name="Fixture sample"))
            session.add(
                Research(
                    id=RESEARCH_ID,
                    sample_id=SAMPLE_ID,
                    research_goal_id=RESEARCH_GOAL_ID,
                )
            )
            now = datetime.now(UTC)
            session.add(
                Test(
                    id=TEST_ID,
                    research_id=RESEARCH_ID,
                    status_id=in_progress_status.id,
                    created_at=now,
                    updated_at=now,
                )
            )
            # Второй активный тест того же исследования — блокирует каскад
            # завершения research/sample, чтобы тест проверял только complete_test.
            session.add(
                Test(
                    id=OTHER_TEST_ID,
                    research_id=RESEARCH_ID,
                    status_id=in_progress_status.id,
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.commit()

            repository = SqlAlchemyWorkflowRepository(session=session)
            result = await repository.complete_test(
                test_id=TEST_ID,
                actor_id=ACTOR_ID,
                value="10",
                norm="5-15",
                comment="в норме",
                verdict=True,
            )

            assert result.status_id == completed_status.id

            persisted_test = await session.get(Test, TEST_ID)
            assert persisted_test is not None
            assert persisted_test.verdict is True
            assert persisted_test.value == "10"
            assert persisted_test.status_id == completed_status.id

            audit_entries = (
                await session.execute(
                    select(ChangeLog).where(
                        ChangeLog.entity_type == "tests",
                        ChangeLog.entity_id == TEST_ID,
                        ChangeLog.action == "test_completed",
                    ),
                )
            ).scalars().all()
            assert len(audit_entries) == 1
            diff = audit_entries[0].diff
            assert diff is not None
            assert diff["status_code"] == {"from": "in_progress", "to": "completed"}
    finally:
        async with session_factory() as session:
            await _cleanup_rows(session)
            await session.commit()
        await engine.dispose()


async def _test_status(session: AsyncSession, code: str) -> TestStatus | None:
    result = await session.execute(
        select(TestStatus).where(TestStatus.code == code, TestStatus.deleted_at.is_(None)),
    )
    return result.scalar_one_or_none()


async def _cleanup_rows(session: AsyncSession) -> None:
    await session.execute(
        delete(ChangeLog).where(ChangeLog.entity_id.in_([TEST_ID, OTHER_TEST_ID]))
    )
    await session.execute(delete(Test).where(Test.id.in_([TEST_ID, OTHER_TEST_ID])))
    await session.execute(delete(Research).where(Research.id == RESEARCH_ID))
    await session.execute(delete(Sample).where(Sample.id == SAMPLE_ID))
    await session.execute(delete(ResearchGoal).where(ResearchGoal.id == RESEARCH_GOAL_ID))
    await session.execute(delete(User).where(User.username == "complete-test-fixture"))
    await session.execute(delete(Role).where(Role.key == "complete-test-fixture"))
