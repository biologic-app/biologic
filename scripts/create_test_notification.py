from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.contexts.notifications.application.service import NotificationService
from src.contexts.notifications.domain.contracts import NotificationDraft
from src.contexts.notifications.infrastructure.repositories import SqlAlchemyNotificationRepository
from src.core.config import get_settings


DEFAULT_TITLE = "Test notification"
DEFAULT_MESSAGE = "This notification was created by scripts.create_test_notification."


async def create_test_notification(
    *,
    database_url: str | None = None,
    title: str = DEFAULT_TITLE,
    message: str = DEFAULT_MESSAGE,
    entity_type: str = "manual_tests",
    entity_id: UUID | None = None,
) -> None:
    engine = create_async_engine(database_url or get_settings().database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        service = NotificationService(
            repository=SqlAlchemyNotificationRepository(session=session),
        )
        records = await service.repository.create_many(
            [
                NotificationDraft(
                    kind="manual.test_notification",
                    title=title,
                    message=message,
                    entity_type=entity_type,
                    entity_id=entity_id or uuid4(),
                    source_event_type="ManualTestNotificationCreated",
                    payload={"source": "scripts.create_test_notification"},
                ),
            ],
        )
    await engine.dispose()

    record = records[0]
    print("Created test notification:")
    print(f"  id={record.id}")
    print(f"  title={record.title}")
    print(f"  message={record.message}")
    print(f"  created_at={record.created_at.isoformat()}")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create one global unread notification for local SSE/frontend testing.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="SQLAlchemy async database URL. Defaults to APP_DATABASE_URL from .env.",
    )
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--message", default=DEFAULT_MESSAGE)
    parser.add_argument("--entity-type", default="manual_tests")
    parser.add_argument("--entity-id", type=UUID, default=None)
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(
        create_test_notification(
            database_url=args.database_url,
            title=args.title,
            message=args.message,
            entity_type=args.entity_type,
            entity_id=args.entity_id,
        ),
    )
