from os import environ
from uuid import UUID

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.contexts.notifications.infrastructure.push_subscription_repository import (
    SqlAlchemyPushSubscriptionStore,
)
from src.infrastructure.db.models import PushSubscription, Role, User
from src.infrastructure.db.models.enums import RoleScopeType

ROLE_ID = UUID("00000000-0000-0000-0000-000000000b01")
USER_ID = UUID("00000000-0000-0000-0000-000000000b02")
OTHER_USER_ID = UUID("00000000-0000-0000-0000-000000000b03")
ENDPOINT = "https://push.example/subscription-store-test"


@pytest.mark.asyncio
async def test_upsert_list_and_delete_round_trip_against_real_postgres() -> None:
    database_url = environ.get("APP_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("APP_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with session_factory() as session:
            await _cleanup(session)
            session.add_all(
                [
                    Role(
                        id=ROLE_ID,
                        key="test-push-role",
                        name="Test",
                        scope_type=RoleScopeType.GLOBAL,
                    ),
                    User(
                        id=USER_ID,
                        username="push-store-test-user",
                        password_hash="x",
                        role_id=ROLE_ID,
                    ),
                    User(
                        id=OTHER_USER_ID,
                        username="push-store-test-other-user",
                        password_hash="x",
                        role_id=ROLE_ID,
                    ),
                ],
            )
            await session.commit()

            store = SqlAlchemyPushSubscriptionStore(session=session)

            created = await store.upsert(
                user_id=USER_ID,
                endpoint=ENDPOINT,
                p256dh="p256dh-1",
                auth="auth-1",
                user_agent="pytest",
            )
            assert created.endpoint == ENDPOINT

            # Re-subscribing the same endpoint (e.g. browser refreshed its
            # push subscription for the same device) updates in place rather
            # than creating a duplicate row.
            updated = await store.upsert(
                user_id=USER_ID,
                endpoint=ENDPOINT,
                p256dh="p256dh-2",
                auth="auth-2",
                user_agent="pytest",
            )
            assert updated.id == created.id
            assert updated.p256dh == "p256dh-2"

            for_target_user = await store.list_for_users([USER_ID])
            assert [s.endpoint for s in for_target_user] == [ENDPOINT]

            for_other_user = await store.list_for_users([OTHER_USER_ID])
            assert for_other_user == []

            await store.delete_by_endpoint(ENDPOINT)
            assert await store.list_for_users([USER_ID]) == []
    finally:
        async with session_factory() as session:
            await _cleanup(session)
            await session.commit()
        await engine.dispose()


async def _cleanup(session: AsyncSession) -> None:
    await session.execute(delete(PushSubscription).where(PushSubscription.endpoint == ENDPOINT))
    await session.execute(delete(User).where(User.id.in_([USER_ID, OTHER_USER_ID])))
    await session.execute(delete(Role).where(Role.id == ROLE_ID))
