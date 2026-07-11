from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.notifications.application.push_ports import PushSubscriptionRecord
from src.infrastructure.db.models import PushSubscription


class SqlAlchemyPushSubscriptionStore:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        *,
        user_id: UUID,
        endpoint: str,
        p256dh: str,
        auth: str,
        user_agent: str | None,
    ) -> PushSubscriptionRecord:
        stmt = (
            pg_insert(PushSubscription)
            .values(
                user_id=user_id,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                user_agent=user_agent,
            )
            .on_conflict_do_update(
                index_elements=[PushSubscription.endpoint],
                set_={
                    "user_id": user_id,
                    "p256dh": p256dh,
                    "auth": auth,
                    "user_agent": user_agent,
                },
            )
            .returning(PushSubscription)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one()
        await self.session.commit()
        return self._record(row)

    async def delete_by_endpoint(self, endpoint: str) -> None:
        await self.session.execute(
            delete(PushSubscription).where(PushSubscription.endpoint == endpoint)
        )
        await self.session.commit()

    async def list_for_users(self, user_ids: Iterable[UUID]) -> list[PushSubscriptionRecord]:
        user_ids = list(user_ids)
        if not user_ids:
            return []
        result = await self.session.execute(
            select(PushSubscription).where(PushSubscription.user_id.in_(user_ids))
        )
        return [self._record(row) for row in result.scalars().all()]

    def _record(self, row: PushSubscription) -> PushSubscriptionRecord:
        return PushSubscriptionRecord(
            id=row.id,
            user_id=row.user_id,
            endpoint=row.endpoint,
            p256dh=row.p256dh,
            auth=row.auth,
        )
