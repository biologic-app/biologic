"""Read-only data access backing the protocol XLS document and excerpt routes.

Loads a protocol together with its linked samples (resolving human-readable
names for type/status/direction) and, for rejected samples, the rejection reason
recorded in ``change_log`` — all in a bounded number of queries (no per-sample
N+1). The result is a plain :class:`ProtocolDocumentData` for the renderer.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.laboratory_workflow.application.protocol_document import (
    ProtocolDocumentData,
    ProtocolSampleRow,
)
from src.core.errors import NotFoundError
from src.core.status_codes import SAMPLE_REJECTED
from src.infrastructure.db.models import (
    ChangeLog,
    Conclusion,
    Direction,
    Protocol,
    ProtocolType,
    Sample,
    SampleStatus,
    SampleType,
)


class ProtocolReportRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def load(
        self, protocol_id: UUID, *, only_rejected: bool
    ) -> ProtocolDocumentData:
        protocol = (
            await self.session.execute(
                select(Protocol).where(
                    Protocol.id == protocol_id,
                    Protocol.deleted_at.is_(None),
                ),
            )
        ).scalar_one_or_none()
        if protocol is None:
            raise NotFoundError(f"protocols item {protocol_id} was not found.")

        return ProtocolDocumentData(
            protocol_id=protocol.id,
            year_no=protocol.year_no,
            formed_at=protocol.issued_at or protocol.created_at,
            protocol_type=await self._name(ProtocolType, protocol.protocol_type_id),
            conclusion=await self._name(Conclusion, protocol.conclusion_id),
            copies=protocol.copies,
            rows=await self._sample_rows(protocol_id, only_rejected=only_rejected),
        )

    async def _name(self, model: type[Any], entity_id: UUID | None) -> str | None:
        if entity_id is None:
            return None
        value = (
            await self.session.execute(
                select(model.name).where(model.id == entity_id),
            )
        ).scalar_one_or_none()
        return value if isinstance(value, str) else None

    async def _sample_rows(
        self, protocol_id: UUID, *, only_rejected: bool
    ) -> tuple[ProtocolSampleRow, ...]:
        query = (
            select(
                Sample.id,
                Sample.name,
                SampleType.name,
                SampleStatus.code,
                Direction.year_no,
                Direction.base_no,
                Sample.received_at,
                Sample.sampled_at,
            )
            .select_from(Sample)
            .outerjoin(SampleType, SampleType.id == Sample.sample_type_id)
            .outerjoin(SampleStatus, SampleStatus.id == Sample.status_id)
            .outerjoin(Direction, Direction.id == Sample.direction_id)
            .where(Sample.protocol_id == protocol_id, Sample.deleted_at.is_(None))
            .order_by(Sample.created_at, Sample.id)
        )
        if only_rejected:
            query = query.where(SampleStatus.code == SAMPLE_REJECTED)

        records = (await self.session.execute(query)).all()
        rejected_ids = [record[0] for record in records if record[3] == SAMPLE_REJECTED]
        reasons = await self._reject_reasons(rejected_ids)

        rows: list[ProtocolSampleRow] = []
        for record in records:
            rows.append(
                ProtocolSampleRow(
                    name=record[1],
                    sample_type=record[2],
                    status=record[3],
                    direction_no=_direction_no(record[4], record[5]),
                    received_at=record[6] or record[7],
                    reject_reason=reasons.get(record[0]),
                ),
            )
        return tuple(rows)

    async def _reject_reasons(self, sample_ids: list[UUID]) -> dict[UUID, str]:
        reasons: dict[UUID, str] = {}
        if not sample_ids:
            return reasons
        query = (
            select(ChangeLog.entity_id, ChangeLog.diff, ChangeLog.snapshot)
            .where(
                ChangeLog.entity_type == "samples",
                ChangeLog.entity_id.in_(sample_ids),
                ChangeLog.action == "sample_rejected",
            )
            .order_by(ChangeLog.created_at)
        )
        # Ascending order means the latest rejection wins on overwrite.
        for entity_id, diff, snapshot in (await self.session.execute(query)).all():
            reason = _reason_from(diff) or _reason_from(snapshot)
            if entity_id is not None and reason is not None:
                reasons[entity_id] = reason
        return reasons


def _direction_no(year_no: int | None, base_no: int | None) -> str | None:
    if year_no is None:
        return None
    if base_no is None:
        return str(year_no)
    return f"{year_no}-{base_no}"


def _reason_from(payload: Any) -> str | None:
    if isinstance(payload, dict):
        reason = payload.get("reason")
        if isinstance(reason, str) and reason:
            return reason
    return None
