from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import and_, asc, delete, desc, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud_query import (
    JoinSpec,
    RelatedField,
    apply_outer_joins,
    attach_sort_values,
    build_crud_query_parts,
    cursor_sort_value,
)
from src.core.cursor_pagination import (
    CursorState,
    decode_cursor,
    encode_cursor,
    json_value,
)
from src.core.errors import BadRequestError, DomainConflictError, NotFoundError
from src.core.pagination import PaginationParams
from src.core.status_codes import DIRECTION_DRAFT, SAMPLE_PENDING
from src.infrastructure.db.models import (
    ChangeLog,
    Conclusion,
    Direction,
    DirectionStatus,
    Doctor,
    Indicator,
    Lab,
    Object,
    Protocol,
    ProtocolType,
    Research,
    ResearchGoal,
    ResearchStatus,
    Role,
    RoleSubscriptionRule,
    Sample,
    SampleLab,
    SampleStatus,
    SampleType,
    Subscription,
    Test,
    TestStatus,
    User,
)


@dataclass(frozen=True)
class RepositoryPage:
    items: list[Any]
    total: int
    has_more: bool
    next_cursor: str | None


class DirectionCrudRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        page = await _list_rows(
            self.session, Direction, params, _direction_sortable_fields()
        )
        await _populate_direction_includes(
            self.session, page.items, params.includes_requested
        )
        return page

    async def read(self, direction_id: UUID) -> Any:
        row = await _read_row(self.session, Direction, "directions", direction_id)
        # Единичное чтение не принимает произвольные include-параметры от клиента
        # (в отличие от list()), но карточка направления всегда должна показывать
        # ФИО автора — поэтому резолвим его безусловно.
        await _populate_direction_includes(self.session, [row], ["creator"])
        return row

    async def find_by_year_and_base_no(
        self,
        year_no: int,
        base_no: int | None,
        *,
        exclude_id: UUID | None = None,
    ) -> Any | None:
        # Отсутствующий base_no — не надёжный бизнес-ключ (например, номер
        # документа не распознан при импорте скан-формы), поэтому направления
        # без base_no между собой дубликатами не считаются.
        if base_no is None:
            return None
        filters = [
            Direction.year_no == year_no,
            Direction.base_no == base_no,
            Direction.deleted_at.is_(None),
        ]
        if exclude_id is not None:
            filters.append(Direction.id != exclude_id)
        result = await self.session.execute(select(Direction).where(*filters))
        return result.scalars().first()

    async def create(self, values: dict[str, Any], *, created_by: UUID | None = None) -> Any:
        payload = _pick(values, _direction_write_fields())
        payload.setdefault(
            "status_id",
            await _default_status_id(self.session, DirectionStatus, DIRECTION_DRAFT),
        )
        if created_by is not None:
            payload["created_by"] = created_by
        if "year_no" in payload:
            await self._ensure_year_base_no_available(payload["year_no"], payload.get("base_no"))
        try:
            row = await _create_row(self.session, Direction, payload)
        except IntegrityError as exc:
            await self.session.rollback()
            raise _direction_duplicate_conflict() from exc
        # Фиксируем «переход» в начальный статус: таймлайн статусов в UI
        # показывает дату и автора для каждой точки, включая «Черновик».
        self.session.add(
            ChangeLog(
                entity_type="directions",
                entity_id=row.id,
                action="direction_created",
                actor_id=created_by,
                snapshot={"status_code": DIRECTION_DRAFT},
                diff={"status_code": {"from": None, "to": DIRECTION_DRAFT}},
            ),
        )
        await self.session.commit()
        return row

    async def update(self, direction_id: UUID, values: dict[str, Any]) -> Any:
        _reject_status_update("directions", values)
        payload = _pick(values, _direction_write_fields())
        row = await self.read(direction_id)
        if "year_no" in payload or "base_no" in payload:
            year_no = payload.get("year_no", row.year_no)
            base_no = payload.get("base_no", row.base_no)
            await self._ensure_year_base_no_available(
                year_no, base_no, exclude_id=direction_id
            )
        try:
            return await _update_row(
                self.session,
                row,
                payload,
                audit_resource="directions",
            )
        except IntegrityError as exc:
            await self.session.rollback()
            raise _direction_duplicate_conflict() from exc

    async def _read_draft(self, direction_id: UUID, *, action: str) -> Any:
        direction = await self.read(direction_id)
        status_code = await _row_status_code(
            self.session, DirectionStatus, direction.status_id
        )
        if status_code != DIRECTION_DRAFT:
            raise DomainConflictError(
                code="direction_not_draft",
                detail=(
                    f"Direction can be {action} only in draft status. "
                    f"Current status is {status_code}."
                ),
            )
        return direction

    async def _ensure_year_base_no_available(
        self,
        year_no: int,
        base_no: int | None,
        *,
        exclude_id: UUID | None = None,
    ) -> None:
        existing = await self.find_by_year_and_base_no(
            year_no, base_no, exclude_id=exclude_id
        )
        if existing is not None:
            raise _direction_duplicate_conflict()

    async def delete(self, direction_id: UUID) -> None:
        await _delete_row(self.session, await self.read(direction_id))

    async def assert_draft(self, direction_id: UUID) -> None:
        """Raises NotFoundError if the direction does not exist, DomainConflictError
        if it exists but is not in draft status."""
        await self._read_draft(direction_id, action="modified")

    async def delete_draft_cascade(self, direction_id: UUID) -> None:
        """Soft-deletes a draft direction together with every sample it owns,
        their research and the research' tests, atomically in one transaction.
        Deletion is only allowed while the direction is still a draft."""
        direction = await self._read_draft(direction_id, action="deleted")

        now = datetime.now(UTC)
        sample_ids = list(
            (
                await self.session.execute(
                    select(Sample.id).where(
                        Sample.direction_id == direction_id,
                        Sample.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        research_ids: list[UUID] = []
        if sample_ids:
            research_ids = list(
                (
                    await self.session.execute(
                        select(Research.id).where(
                            Research.sample_id.in_(sample_ids),
                            Research.deleted_at.is_(None),
                        )
                    )
                )
                .scalars()
                .all()
            )
        if research_ids:
            await self.session.execute(
                update(Test)
                .where(
                    Test.research_id.in_(research_ids),
                    Test.deleted_at.is_(None),
                )
                .values(deleted_at=now, updated_at=now)
            )
            await self.session.execute(
                update(Research)
                .where(Research.id.in_(research_ids))
                .values(deleted_at=now, updated_at=now)
            )
        if sample_ids:
            await self.session.execute(
                update(Sample)
                .where(Sample.id.in_(sample_ids))
                .values(deleted_at=now, updated_at=now)
            )
        direction.deleted_at = now
        direction.updated_at = now
        self.session.add(direction)
        await self.session.commit()


class SampleCrudRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        page = await _list_rows(self.session, Sample, params, _sample_sortable_fields())
        await _populate_sample_includes(
            self.session, page.items, params.includes_requested
        )
        return page

    async def read(self, sample_id: UUID) -> Any:
        row = await _read_row(self.session, Sample, "samples", sample_id)
        # Аналогично направлению: карточка образца всегда должна показывать
        # ФИО автора, даже без явного include-параметра от клиента.
        await _populate_sample_includes(self.session, [row], ["creator"])
        return row

    async def create(self, values: dict[str, Any], *, created_by: UUID | None = None) -> Any:
        payload = _pick(values, _sample_write_fields())
        payload.setdefault(
            "status_id",
            await _default_status_id(self.session, SampleStatus, SAMPLE_PENDING),
        )
        if created_by is not None:
            payload["created_by"] = created_by
        row = await _create_row(self.session, Sample, payload)
        # Аналогично направлениям: точка «На регистрации» в таймлайне должна
        # иметь дату и автора.
        self.session.add(
            ChangeLog(
                entity_type="samples",
                entity_id=row.id,
                action="sample_created",
                actor_id=created_by,
                snapshot={"status_code": SAMPLE_PENDING},
                diff={"status_code": {"from": None, "to": SAMPLE_PENDING}},
            ),
        )
        await self.session.commit()
        return row

    async def update(self, sample_id: UUID, values: dict[str, Any]) -> Any:
        _reject_status_update("samples", values)
        return await _update_row(
            self.session,
            await self.read(sample_id),
            _pick(values, _sample_write_fields()),
            audit_resource="samples",
        )

    async def delete(self, sample_id: UUID) -> None:
        await _delete_row(self.session, await self.read(sample_id))


class SubscriptionCrudRepository:
    """Followers of a direction or a sample.

    The returned list merges four sources, deduplicated by user in priority
    order (role → owner → doctor → manual):
    - role — users whose role has a matching RoleSubscriptionRule (mandatory,
      admin-configured, optionally scoped to the entity's branch, lab and/or
      current lifecycle status, e.g. "lab chiefs follow only rejected samples");
    - owner — the user who created the parent direction (their own entities);
    - doctor — the user linked to the direction's sanitary doctor
      (Doctor.user_id), following the direction and all its samples;
    - manual — explicit rows in the subscriptions table (the follow button).
    Everything but ``manual`` is derived at read time and cannot unsubscribe.
    """

    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def _owner_id(self, entity_type: str, entity_id: UUID) -> UUID | None:
        if entity_type == "directions":
            row = await _read_row(self.session, Direction, "directions", entity_id)
            return cast(UUID | None, row.created_by)
        row = await _read_row(self.session, Sample, "samples", entity_id)
        if row.direction_id is None:
            return None
        result = await self.session.execute(
            select(Direction.created_by).where(Direction.id == row.direction_id)
        )
        return result.scalar_one_or_none()

    async def _doctor_user_id(self, entity_type: str, entity_id: UUID) -> UUID | None:
        """The user behind the direction's sanitary doctor, if any
        (Direction.doctor_id → Doctor.user_id)."""
        if entity_type == "directions":
            doctor_id_query = select(Direction.doctor_id).where(Direction.id == entity_id)
        else:
            doctor_id_query = (
                select(Direction.doctor_id)
                .join(Sample, Sample.direction_id == Direction.id)
                .where(Sample.id == entity_id)
            )
        doctor_id = (await self.session.execute(doctor_id_query)).scalar_one_or_none()
        if doctor_id is None:
            return None
        result = await self.session.execute(
            select(Doctor.user_id).where(Doctor.id == doctor_id, Doctor.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def _scope_for_entity(
        self, entity_type: str, entity_id: UUID
    ) -> tuple[UUID | None, set[UUID], str | None]:
        """Branch, labs and current status code of the entity, used to match
        scoped rules.

        A direction's branch comes from its object; it has no direct lab, so its
        lab set is always empty. A sample inherits both from its parent direction
        (branch) and its own lab assignments. The status code is the entity's own
        current lifecycle status (direction_statuses/sample_statuses.code).
        """
        if entity_type == "directions":
            branch_query = (
                select(Object.branch_id, DirectionStatus.code)
                .join(Direction, Direction.object_id == Object.id)
                .outerjoin(DirectionStatus, DirectionStatus.id == Direction.status_id)
                .where(Direction.id == entity_id)
            )
            row = (await self.session.execute(branch_query)).first()
            if row is None:
                return None, set(), None
            return row[0], set(), row[1]

        branch_query = (
            select(Object.branch_id, SampleStatus.code)
            .join(Direction, Direction.object_id == Object.id)
            .join(Sample, Sample.direction_id == Direction.id)
            .outerjoin(SampleStatus, SampleStatus.id == Sample.status_id)
            .where(Sample.id == entity_id)
        )
        row = (await self.session.execute(branch_query)).first()
        branch_id = row[0] if row is not None else None
        status_code = row[1] if row is not None else None
        lab_rows = await self.session.execute(
            select(SampleLab.lab_id).where(
                SampleLab.sample_id == entity_id,
                SampleLab.deleted_at.is_(None),
            )
        )
        return branch_id, set(lab_rows.scalars().all()), status_code

    def _role_rule_conditions(
        self,
        entity_type: str,
        branch_id: UUID | None,
        lab_ids: set[UUID],
        status_code: str | None,
    ) -> list[Any]:
        # branch_id being None must NOT be spelled as ``branch_id == None`` —
        # SQLAlchemy would translate that to ``IS NULL`` and silently make a
        # branch-specific rule match a branch-less entity. Only unscoped rules
        # may match an entity with no branch. Same reasoning applies to
        # status_code below.
        branch_condition = (
            RoleSubscriptionRule.branch_id.is_(None)
            if branch_id is None
            else or_(
                RoleSubscriptionRule.branch_id.is_(None),
                RoleSubscriptionRule.branch_id == branch_id,
            )
        )
        # ``lab_id.in_(())`` yields a valid false clause, so an empty lab set
        # (always the case for directions) simply matches only unscoped rules.
        lab_condition = or_(
            RoleSubscriptionRule.lab_id.is_(None),
            RoleSubscriptionRule.lab_id.in_(lab_ids),
        )
        status_condition = (
            RoleSubscriptionRule.status_code.is_(None)
            if status_code is None
            else or_(
                RoleSubscriptionRule.status_code.is_(None),
                RoleSubscriptionRule.status_code == status_code,
            )
        )
        return [
            RoleSubscriptionRule.entity_type == entity_type,
            RoleSubscriptionRule.deleted_at.is_(None),
            branch_condition,
            lab_condition,
            status_condition,
            User.deleted_at.is_(None),
        ]

    async def list_for_entity(
        self, entity_type: str, entity_id: UUID
    ) -> list[dict[str, object]]:
        owner_id = await self._owner_id(entity_type, entity_id)
        doctor_user_id = await self._doctor_user_id(entity_type, entity_id)
        branch_id, lab_ids, status_code = await self._scope_for_entity(entity_type, entity_id)

        subscribers: dict[UUID, dict[str, object]] = {}

        def _add(user_row: Any, source: str) -> None:
            if user_row.id in subscribers:
                return
            subscribers[user_row.id] = {
                "user_id": user_row.id,
                "username": user_row.username,
                "first_name": user_row.first_name,
                "last_name": user_row.last_name,
                "patronymic": user_row.patronymic,
                "source": source,
            }

        user_fields = (
            User.id,
            User.username,
            User.first_name,
            User.last_name,
            User.patronymic,
        )

        role_matches = await self.session.execute(
            select(*user_fields)
            .join(Role, Role.id == User.role_id)
            .join(RoleSubscriptionRule, RoleSubscriptionRule.role_id == Role.id)
            .where(*self._role_rule_conditions(entity_type, branch_id, lab_ids, status_code))
            .order_by(asc(User.username))
        )
        for row in role_matches.all():
            _add(row, "role")

        if owner_id is not None:
            owner = await self.session.execute(
                select(*user_fields).where(User.id == owner_id, User.deleted_at.is_(None))
            )
            owner_row = owner.first()
            if owner_row is not None:
                _add(owner_row, "owner")

        if doctor_user_id is not None:
            doctor = await self.session.execute(
                select(*user_fields).where(
                    User.id == doctor_user_id, User.deleted_at.is_(None)
                )
            )
            doctor_row = doctor.first()
            if doctor_row is not None:
                _add(doctor_row, "doctor")

        manual = await self.session.execute(
            select(*user_fields)
            .join(Subscription, Subscription.user_id == User.id)
            .where(
                Subscription.entity_type == entity_type,
                Subscription.entity_id == entity_id,
                Subscription.deleted_at.is_(None),
                User.deleted_at.is_(None),
            )
            .order_by(asc(User.username))
        )
        for row in manual.all():
            _add(row, "manual")

        return list(subscribers.values())

    async def resolve_notification_targets(
        self, entity_type: str, entity_id: UUID
    ) -> set[UUID]:
        """User ids that should be notified about an event on this entity.

        The lean sibling of ``list_for_entity`` for the per-event notification
        fan-out: same four-source derivation, but selects only user ids and
        returns a set. An empty set means nobody follows the entity — the
        notification is dropped rather than broadcast to everyone.
        """
        if entity_type not in ("directions", "samples"):
            return set()

        owner_id = await self._owner_id(entity_type, entity_id)
        doctor_user_id = await self._doctor_user_id(entity_type, entity_id)
        branch_id, lab_ids, status_code = await self._scope_for_entity(entity_type, entity_id)

        targets: set[UUID] = set()

        role_matches = await self.session.execute(
            select(User.id)
            .join(Role, Role.id == User.role_id)
            .join(RoleSubscriptionRule, RoleSubscriptionRule.role_id == Role.id)
            .where(*self._role_rule_conditions(entity_type, branch_id, lab_ids, status_code))
        )
        targets.update(role_matches.scalars().all())

        for candidate in (owner_id, doctor_user_id):
            if candidate is not None:
                targets.add(candidate)

        manual = await self.session.execute(
            select(Subscription.user_id).where(
                Subscription.entity_type == entity_type,
                Subscription.entity_id == entity_id,
                Subscription.deleted_at.is_(None),
            )
        )
        targets.update(manual.scalars().all())

        return targets

    async def subscribe(
        self, entity_type: str, entity_id: UUID, user_id: UUID
    ) -> list[dict[str, object]]:
        await self._owner_id(entity_type, entity_id)
        await _read_row(self.session, User, "users", user_id)
        existing = await self.session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.entity_type == entity_type,
                Subscription.entity_id == entity_id,
                Subscription.deleted_at.is_(None),
            )
        )
        if existing.scalars().first() is None:
            self.session.add(
                Subscription(user_id=user_id, entity_type=entity_type, entity_id=entity_id)
            )
            await self.session.commit()
        return await self.list_for_entity(entity_type, entity_id)

    async def unsubscribe(
        self, entity_type: str, entity_id: UUID, user_id: UUID
    ) -> list[dict[str, object]]:
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.entity_type == entity_type,
                Subscription.entity_id == entity_id,
                Subscription.deleted_at.is_(None),
            )
        )
        row = result.scalars().first()
        if row is not None:
            await _delete_row(self.session, row)
        return await self.list_for_entity(entity_type, entity_id)

    async def list_user_subscription_ids(
        self, entity_type: str, user_id: UUID
    ) -> list[UUID]:
        """Entity ids the user follows *manually* (explicit rows in ``subscriptions``).

        Role/owner/doctor followers are derived at read time and never stored, so
        they are intentionally excluded — the pin column tracks only a user's own
        manual subscriptions (specific directions/samples they chose to watch).
        """
        result = await self.session.execute(
            select(Subscription.entity_id).where(
                Subscription.user_id == user_id,
                Subscription.entity_type == entity_type,
                Subscription.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())


class SampleLabCrudRepository:
    """Sample ↔ laboratory assignments and the (type + lab) → goals derivation."""

    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def get_lab_id_by_code(self, code: str) -> UUID | None:
        result = await self.session.execute(
            select(Lab.id).where(Lab.code == code, Lab.deleted_at.is_(None))
        )
        return result.scalars().first()

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(
            self.session, SampleLab, _pick(values, ("sample_id", "lab_id"))
        )

    async def list_labs_for_sample(self, sample_id: UUID) -> list[dict[str, object]]:
        await _read_row(self.session, Sample, "samples", sample_id)
        result = await self.session.execute(
            select(Lab.id, Lab.code, Lab.name)
            .join(SampleLab, SampleLab.lab_id == Lab.id)
            .where(
                SampleLab.sample_id == sample_id,
                SampleLab.deleted_at.is_(None),
                Lab.deleted_at.is_(None),
            )
            .order_by(asc(Lab.code), asc(Lab.id))
        )
        return [
            {"id": lab_id, "code": code, "name": name}
            for lab_id, code, name in result.all()
        ]

    async def set_labs_for_sample(
        self, sample_id: UUID, lab_ids: list[UUID]
    ) -> list[dict[str, object]]:
        await _read_row(self.session, Sample, "samples", sample_id)
        desired = set(lab_ids)
        if desired:
            result = await self.session.execute(
                select(Lab.id).where(Lab.id.in_(desired), Lab.deleted_at.is_(None))
            )
            missing = desired - set(result.scalars().all())
            if missing:
                raise NotFoundError(
                    f"labs items {sorted(str(lab_id) for lab_id in missing)} were not found."
                )
        links_result = await self.session.execute(
            select(SampleLab).where(
                SampleLab.sample_id == sample_id,
                SampleLab.deleted_at.is_(None),
            )
        )
        existing = list(links_result.scalars().all())
        now = datetime.now(UTC)
        for link in existing:
            if link.lab_id not in desired:
                link.deleted_at = now
                if hasattr(link, "updated_at"):
                    link.updated_at = now
                self.session.add(link)
        existing_lab_ids = {link.lab_id for link in existing}
        for lab_id in desired - existing_lab_ids:
            self.session.add(SampleLab(sample_id=sample_id, lab_id=lab_id))
        await self.session.commit()
        return await self.list_labs_for_sample(sample_id)

    async def suggest_research_goals(
        self, sample_id: UUID, sample_type_id: UUID
    ) -> list[dict[str, object]]:
        await _read_row(self.session, Sample, "samples", sample_id)
        lab_ids = (
            select(SampleLab.lab_id)
            .where(SampleLab.sample_id == sample_id, SampleLab.deleted_at.is_(None))
            .scalar_subquery()
        )
        indicator_exists = (
            select(Indicator.id)
            .where(
                Indicator.research_goal_id == ResearchGoal.id,
                Indicator.sample_type_id == sample_type_id,
                Indicator.deleted_at.is_(None),
            )
            .exists()
        )
        result = await self.session.execute(
            select(ResearchGoal, Lab.name)
            .outerjoin(Lab, ResearchGoal.lab_id == Lab.id)
            .where(
                ResearchGoal.lab_id.in_(lab_ids),
                ResearchGoal.deleted_at.is_(None),
                indicator_exists,
            )
            .order_by(asc(Lab.name), asc(ResearchGoal.name), asc(ResearchGoal.id))
        )
        return [
            {
                "id": goal.id,
                "code": goal.code,
                "name": goal.name,
                "comment": goal.comment,
                "lab_id": goal.lab_id,
                "lab_name": lab_name,
            }
            for goal, lab_name in result.all()
        ]


class ResearchCrudRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        page = await _list_rows(
            self.session, Research, params, _research_sortable_fields()
        )
        await _populate_research_includes(
            self.session, page.items, params.includes_requested
        )
        return page

    async def read(self, research_id: UUID) -> Any:
        return await _read_row(self.session, Research, "research", research_id)

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(
            self.session, Research, _pick(values, _research_write_fields())
        )

    async def get_goal_id_by_code(self, code: str) -> UUID | None:
        result = await self.session.execute(
            select(ResearchGoal.id).where(
                ResearchGoal.code == code, ResearchGoal.deleted_at.is_(None)
            )
        )
        return result.scalars().first()

    async def update(self, research_id: UUID, values: dict[str, Any]) -> Any:
        _reject_status_update("research", values)
        return await _update_row(
            self.session,
            await self.read(research_id),
            _pick(values, _research_write_fields()),
            audit_resource="research",
        )

    async def delete(self, research_id: UUID) -> None:
        await _delete_row(self.session, await self.read(research_id))


class TestCrudRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        page = await _list_rows(self.session, Test, params, _test_sortable_fields())
        await _populate_test_includes(
            self.session, page.items, params.includes_requested
        )
        return page

    async def read(self, test_id: UUID) -> Any:
        return await _read_row(self.session, Test, "tests", test_id)

    async def update(self, test_id: UUID, values: dict[str, Any]) -> Any:
        _reject_status_update("tests", values)
        return await _update_row(
            self.session,
            await self.read(test_id),
            _pick(values, _test_write_fields()),
            audit_resource="tests",
        )

    async def delete(self, test_id: UUID) -> None:
        await _delete_row(self.session, await self.read(test_id))


class ProtocolCrudRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        page = await _list_rows(
            self.session, Protocol, params, _protocol_sortable_fields()
        )
        await _populate_protocol_includes(
            self.session, page.items, params.includes_requested
        )
        return page

    async def read(self, protocol_id: UUID) -> Any:
        return await _read_row(self.session, Protocol, "protocols", protocol_id)

    async def delete(self, protocol_id: UUID) -> None:
        await _delete_row(self.session, await self.read(protocol_id))


def _direction_duplicate_conflict() -> DomainConflictError:
    return DomainConflictError(
        code="direction_duplicate",
        detail="Направление с таким годом и номером уже существует.",
    )


async def _list_rows(
    session: AsyncSession,
    model: type[Any],
    params: PaginationParams,
    sortable_fields: tuple[str, ...],
) -> RepositoryPage:
    query_parts = build_crud_query_parts(
        model=model,
        params=params,
        sortable_fields=sortable_fields,
        base_filters=_base_filters(model),
        related_fields=_related_fields(model),
    )
    sort_by = query_parts.sort_by
    sort_column = query_parts.sort_column
    id_column = getattr(model, "id")
    filters = list(query_parts.filters)
    total_filters = list(filters)
    cursor = decode_cursor(params.cursor) if params.cursor else None
    if cursor is not None:
        if cursor.sort_by != sort_by or cursor.sort_order != params.sort_order:
            raise BadRequestError("Pagination cursor does not match requested sorting.")
        filters.append(_cursor_filter(cursor, sort_column, id_column))

    total_query = apply_outer_joins(
        select(func.count()).select_from(model),
        query_parts.joins,
    ).where(*total_filters)
    total_result = await session.execute(total_query)
    total = int(total_result.scalar_one())
    order_fn = asc if params.sort_order == "asc" else desc
    query = apply_outer_joins(
        select(model, sort_column),
        query_parts.joins,
    )
    query = (
        query.where(*filters)
        .order_by(order_fn(sort_column), order_fn(id_column))
        .limit(params.limit + 1)
    )
    result = await session.execute(query)
    rows = attach_sort_values(list(result.all()))
    items = rows[: params.limit]
    has_more = len(rows) > params.limit
    next_cursor = _next_cursor(items, sort_by, params.sort_order) if has_more else None
    return RepositoryPage(
        items=items, total=total, has_more=has_more, next_cursor=next_cursor
    )


async def _read_row(
    session: AsyncSession,
    model: type[Any],
    resource: str,
    item_id: UUID,
) -> Any:
    result = await session.execute(
        select(model).where(getattr(model, "id") == item_id, *_base_filters(model)),
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError(f"{resource} item {item_id} was not found.")
    return row


async def _create_row(
    session: AsyncSession, model: type[Any], values: dict[str, Any]
) -> Any:
    row = model(**values)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def _update_row(
    session: AsyncSession,
    row: Any,
    values: dict[str, Any],
    *,
    audit_resource: str,
) -> Any:
    diff = _audit_diff(row, values)
    for field, value in values.items():
        setattr(row, field, value)
    if hasattr(row, "updated_at"):
        setattr(row, "updated_at", datetime.now(UTC))
    session.add(row)
    if diff:
        session.add(
            ChangeLog(
                entity_type=audit_resource,
                entity_id=row.id,
                action=f"{audit_resource}.update",
                actor_name="api",
                snapshot={field: change["to"] for field, change in diff.items()},
                diff=diff,
            ),
        )
    await session.commit()
    await session.refresh(row)
    return row


def _audit_diff(row: Any, values: dict[str, Any]) -> dict[str, dict[str, Any]]:
    diff: dict[str, dict[str, Any]] = {}
    for field, next_value in values.items():
        previous_value = getattr(row, field)
        if previous_value == next_value:
            continue
        diff[field] = {
            "from": json_value(previous_value),
            "to": json_value(next_value),
        }
    return diff


async def _delete_row(session: AsyncSession, row: Any) -> None:
    if hasattr(row, "deleted_at"):
        setattr(row, "deleted_at", datetime.now(UTC))
        if hasattr(row, "updated_at"):
            setattr(row, "updated_at", datetime.now(UTC))
        session.add(row)
    else:
        await session.execute(delete(type(row)).where(type(row).id == row.id))
    await session.commit()


def _reject_status_update(resource: str, values: dict[str, Any]) -> None:
    if "status_id" in values:
        raise DomainConflictError(
            code="invalid_status_transition",
            detail=f"{resource} lifecycle status must be changed through commands.",
        )


def _base_filters(model: type[Any]) -> list[Any]:
    if hasattr(model, "deleted_at"):
        return [getattr(model, "deleted_at").is_(None)]
    return []


async def _populate_research_includes(
    session: AsyncSession,
    items: list[Any],
    includes_requested: list[str],
) -> None:
    includes = set(includes_requested) & {"sample", "research_goal", "lab", "status"}
    if not items or not includes:
        return

    if "sample" in includes:
        sample_ids = {item.sample_id for item in items if item.sample_id is not None}
        samples = await _research_sample_includes(session, sample_ids)
        for item in items:
            setattr(item, "sample", samples.get(item.sample_id))

    if "research_goal" in includes:
        research_goal_ids = {
            item.research_goal_id for item in items if item.research_goal_id is not None
        }
        research_goals = await _research_goal_includes(session, research_goal_ids)
        for item in items:
            setattr(item, "research_goal", research_goals.get(item.research_goal_id))

    if "lab" in includes:
        lab_ids = {item.lab_id for item in items if item.lab_id is not None}
        labs = await _lab_includes(session, lab_ids)
        for item in items:
            setattr(item, "lab", labs.get(item.lab_id))

    if "status" in includes:
        status_ids = {item.status_id for item in items if item.status_id is not None}
        statuses = await _research_status_includes(session, status_ids)
        for item in items:
            setattr(item, "status", statuses.get(item.status_id))


async def _populate_direction_includes(
    session: AsyncSession,
    items: list[Any],
    includes_requested: list[str],
) -> None:
    includes = set(includes_requested) & {"status", "doctor", "object", "creator"}
    if not items or not includes:
        return

    if "status" in includes:
        status_ids = {item.status_id for item in items if item.status_id is not None}
        statuses = await _direction_status_includes(session, status_ids)
        for item in items:
            setattr(item, "status", statuses.get(item.status_id))

    if "doctor" in includes:
        doctor_ids = {item.doctor_id for item in items if item.doctor_id is not None}
        doctors = await _doctor_includes(session, doctor_ids)
        for item in items:
            setattr(item, "doctor", doctors.get(item.doctor_id))

    if "object" in includes:
        object_ids = {item.object_id for item in items if item.object_id is not None}
        objects = await _object_includes(session, object_ids)
        for item in items:
            setattr(item, "object", objects.get(item.object_id))

    if "creator" in includes:
        creator_ids = {item.created_by for item in items if item.created_by is not None}
        creators = await _created_by_includes(session, creator_ids)
        for item in items:
            setattr(item, "creator", creators.get(item.created_by))


async def _populate_sample_includes(
    session: AsyncSession,
    items: list[Any],
    includes_requested: list[str],
) -> None:
    includes = set(includes_requested) & {"status", "creator"}
    if not items or not includes:
        return

    if "status" in includes:
        status_ids = {item.status_id for item in items if item.status_id is not None}
        statuses = await _sample_status_includes(session, status_ids)
        for item in items:
            setattr(item, "status", statuses.get(item.status_id))

    if "creator" in includes:
        creator_ids = {item.created_by for item in items if item.created_by is not None}
        creators = await _created_by_includes(session, creator_ids)
        for item in items:
            setattr(item, "creator", creators.get(item.created_by))


async def _populate_protocol_includes(
    session: AsyncSession,
    items: list[Any],
    includes_requested: list[str],
) -> None:
    includes = set(includes_requested) & {"protocol_type", "conclusion"}
    if not items or not includes:
        return

    if "protocol_type" in includes:
        protocol_type_ids = {
            item.protocol_type_id for item in items if item.protocol_type_id is not None
        }
        protocol_types = await _protocol_type_includes(session, protocol_type_ids)
        for item in items:
            setattr(item, "protocol_type", protocol_types.get(item.protocol_type_id))

    if "conclusion" in includes:
        conclusion_ids = {
            item.conclusion_id for item in items if item.conclusion_id is not None
        }
        conclusions = await _conclusion_includes(session, conclusion_ids)
        for item in items:
            setattr(item, "conclusion", conclusions.get(item.conclusion_id))


async def _protocol_type_includes(
    session: AsyncSession,
    protocol_type_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not protocol_type_ids:
        return {}
    result = await session.execute(
        select(ProtocolType.id, ProtocolType.code, ProtocolType.name).where(
            ProtocolType.id.in_(protocol_type_ids),
            *_base_filters(ProtocolType),
        ),
    )
    return {
        row_id: {"id": row_id, "code": code, "name": name}
        for row_id, code, name in result.all()
    }


async def _conclusion_includes(
    session: AsyncSession,
    conclusion_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not conclusion_ids:
        return {}
    result = await session.execute(
        select(
            Conclusion.id,
            Conclusion.code,
            Conclusion.name,
            Conclusion.text_singular,
            Conclusion.text_plural,
        ).where(
            Conclusion.id.in_(conclusion_ids),
            *_base_filters(Conclusion),
        ),
    )
    return {
        row_id: {
            "id": row_id,
            "code": code,
            "name": name,
            "text_singular": text_singular,
            "text_plural": text_plural,
        }
        for row_id, code, name, text_singular, text_plural in result.all()
    }


async def _populate_test_includes(
    session: AsyncSession,
    items: list[Any],
    includes_requested: list[str],
) -> None:
    includes = set(includes_requested) & {"research", "indicator", "status"}
    if not items or not includes:
        return

    if "research" in includes:
        research_ids = {item.research_id for item in items if item.research_id is not None}
        research = await _test_research_includes(session, research_ids)
        for item in items:
            setattr(item, "research", research.get(item.research_id))

    if "indicator" in includes:
        indicator_ids = {
            item.indicator_id for item in items if item.indicator_id is not None
        }
        indicators = await _indicator_includes(session, indicator_ids)
        for item in items:
            setattr(item, "indicator", indicators.get(item.indicator_id))

    if "status" in includes:
        status_ids = {item.status_id for item in items if item.status_id is not None}
        statuses = await _test_status_includes(session, status_ids)
        for item in items:
            setattr(item, "status", statuses.get(item.status_id))


async def _direction_status_includes(
    session: AsyncSession,
    status_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not status_ids:
        return {}
    result = await session.execute(
        select(DirectionStatus.id, DirectionStatus.code, DirectionStatus.name).where(
            DirectionStatus.id.in_(status_ids),
            *_base_filters(DirectionStatus),
        ),
    )
    return {
        row_id: {"id": row_id, "code": code, "name": name}
        for row_id, code, name in result.all()
    }


async def _doctor_includes(
    session: AsyncSession,
    doctor_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not doctor_ids:
        return {}
    result = await session.execute(
        select(
            Doctor.id, Doctor.first_name, Doctor.last_name, Doctor.patronymic
        ).where(Doctor.id.in_(doctor_ids), *_base_filters(Doctor)),
    )
    return {
        row_id: {
            "id": row_id,
            "first_name": first_name,
            "last_name": last_name,
            "patronymic": patronymic,
        }
        for row_id, first_name, last_name, patronymic in result.all()
    }


async def _created_by_includes(
    session: AsyncSession,
    user_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not user_ids:
        return {}
    result = await session.execute(
        select(
            User.id, User.last_name, User.first_name, User.patronymic
        ).where(User.id.in_(user_ids), *_base_filters(User)),
    )
    return {
        row_id: {
            "id": row_id,
            "last_name": last_name,
            "first_name": first_name,
            "patronymic": patronymic,
        }
        for row_id, last_name, first_name, patronymic in result.all()
    }


async def _object_includes(
    session: AsyncSession,
    object_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not object_ids:
        return {}
    result = await session.execute(
        select(Object.id, Object.code, Object.name).where(
            Object.id.in_(object_ids), *_base_filters(Object)
        ),
    )
    return {
        row_id: {"id": row_id, "code": code, "name": name}
        for row_id, code, name in result.all()
    }


async def _sample_status_includes(
    session: AsyncSession,
    status_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not status_ids:
        return {}
    result = await session.execute(
        select(SampleStatus.id, SampleStatus.code, SampleStatus.name).where(
            SampleStatus.id.in_(status_ids),
            *_base_filters(SampleStatus),
        ),
    )
    return {
        row_id: {"id": row_id, "code": code, "name": name}
        for row_id, code, name in result.all()
    }


async def _test_research_includes(
    session: AsyncSession,
    research_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not research_ids:
        return {}
    result = await session.execute(
        select(Research.id, Research.sample_id, Research.research_goal_id).where(
            Research.id.in_(research_ids),
            *_base_filters(Research),
        ),
    )
    return {
        row_id: {
            "id": row_id,
            "sample_id": sample_id,
            "research_goal_id": research_goal_id,
        }
        for row_id, sample_id, research_goal_id in result.all()
    }


async def _indicator_includes(
    session: AsyncSession,
    indicator_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not indicator_ids:
        return {}
    result = await session.execute(
        select(Indicator.id, Indicator.name, Indicator.unit, Indicator.norm_text).where(
            Indicator.id.in_(indicator_ids),
            *_base_filters(Indicator),
        ),
    )
    return {
        row_id: {
            "id": row_id,
            "name": name,
            "unit": unit,
            "norm_text": norm_text,
        }
        for row_id, name, unit, norm_text in result.all()
    }


async def _test_status_includes(
    session: AsyncSession,
    status_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not status_ids:
        return {}
    result = await session.execute(
        select(TestStatus.id, TestStatus.code, TestStatus.name).where(
            TestStatus.id.in_(status_ids),
            *_base_filters(TestStatus),
        ),
    )
    return {
        row_id: {"id": row_id, "code": code, "name": name}
        for row_id, code, name in result.all()
    }


async def _research_sample_includes(
    session: AsyncSession,
    sample_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not sample_ids:
        return {}
    result = await session.execute(
        select(Sample.id, Sample.name).where(
            Sample.id.in_(sample_ids), *_base_filters(Sample)
        ),
    )
    return {row_id: {"id": row_id, "name": name} for row_id, name in result.all()}


async def _research_goal_includes(
    session: AsyncSession,
    research_goal_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not research_goal_ids:
        return {}
    result = await session.execute(
        select(ResearchGoal.id, ResearchGoal.code, ResearchGoal.name).where(
            ResearchGoal.id.in_(research_goal_ids),
            *_base_filters(ResearchGoal),
        ),
    )
    return {
        row_id: {"id": row_id, "code": code, "name": name}
        for row_id, code, name in result.all()
    }


async def _lab_includes(
    session: AsyncSession,
    lab_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not lab_ids:
        return {}
    result = await session.execute(
        select(Lab.id, Lab.code, Lab.name).where(
            Lab.id.in_(lab_ids), *_base_filters(Lab)
        ),
    )
    return {
        row_id: {"id": row_id, "code": code, "name": name}
        for row_id, code, name in result.all()
    }


async def _research_status_includes(
    session: AsyncSession,
    status_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not status_ids:
        return {}
    result = await session.execute(
        select(ResearchStatus.id, ResearchStatus.code, ResearchStatus.name).where(
            ResearchStatus.id.in_(status_ids),
            *_base_filters(ResearchStatus),
        ),
    )
    return {
        row_id: {"id": row_id, "code": code, "name": name}
        for row_id, code, name in result.all()
    }


def _related_fields(model: type[Any]) -> dict[str, RelatedField]:
    if model is Direction:
        doctor = JoinSpec("direction.doctor", Doctor, Direction.doctor_id == Doctor.id)
        object_ = JoinSpec("direction.object", Object, Direction.object_id == Object.id)
        status = JoinSpec(
            "direction.status",
            DirectionStatus,
            Direction.status_id == DirectionStatus.id,
        )
        return {
            "doctor.name": RelatedField(Doctor.last_name, (doctor,)),
            "object.name": RelatedField(Object.name, (object_,)),
            "status.name": RelatedField(DirectionStatus.name, (status,)),
        }

    if model is Sample:
        sample_type = JoinSpec(
            "sample.sample_type",
            SampleType,
            Sample.sample_type_id == SampleType.id,
        )
        direction = JoinSpec("sample.direction", Direction, Sample.direction_id == Direction.id)
        status = JoinSpec("sample.status", SampleStatus, Sample.status_id == SampleStatus.id)
        return {
            "sample_type.name": RelatedField(SampleType.name, (sample_type,)),
            "direction.name": RelatedField(Direction.id, (direction,)),
            "status.name": RelatedField(SampleStatus.name, (status,)),
        }

    if model is Research:
        sample = JoinSpec("research.sample", Sample, Research.sample_id == Sample.id)
        research_goal = JoinSpec(
            "research.research_goal",
            ResearchGoal,
            Research.research_goal_id == ResearchGoal.id,
        )
        lab = JoinSpec("research.lab", Lab, Research.lab_id == Lab.id)
        status = JoinSpec(
            "research.status",
            ResearchStatus,
            Research.status_id == ResearchStatus.id,
        )
        return {
            "sample.name": RelatedField(Sample.name, (sample,)),
            "research_goal.name": RelatedField(ResearchGoal.name, (research_goal,)),
            "lab.name": RelatedField(Lab.name, (lab,)),
            "status.name": RelatedField(ResearchStatus.name, (status,)),
        }

    if model is Test:
        research = JoinSpec("test.research", Research, Test.research_id == Research.id)
        indicator = JoinSpec("test.indicator", Indicator, Test.indicator_id == Indicator.id)
        status = JoinSpec("test.status", TestStatus, Test.status_id == TestStatus.id)
        return {
            "research.name": RelatedField(Research.id, (research,)),
            "indicator.name": RelatedField(Indicator.name, (indicator,)),
            "status.name": RelatedField(TestStatus.name, (status,)),
        }

    if model is Protocol:
        protocol_type = JoinSpec(
            "protocol.protocol_type",
            ProtocolType,
            Protocol.protocol_type_id == ProtocolType.id,
        )
        conclusion = JoinSpec(
            "protocol.conclusion",
            Conclusion,
            Protocol.conclusion_id == Conclusion.id,
        )
        return {
            "protocol_type.name": RelatedField(ProtocolType.name, (protocol_type,)),
            "conclusion.name": RelatedField(Conclusion.name, (conclusion,)),
        }

    return {}


def _cursor_filter(cursor: CursorState, sort_column: Any, id_column: Any) -> Any:
    sort_value = _coerce_cursor_value(sort_column, cursor.sort_value)
    if cursor.sort_order == "asc":
        return or_(
            sort_column > sort_value,
            and_(sort_column == sort_value, id_column > cursor.item_id),
        )
    return or_(
        sort_column < sort_value,
        and_(sort_column == sort_value, id_column < cursor.item_id),
    )


def _coerce_cursor_value(column: Any, value: Any) -> Any:
    try:
        python_type = column.property.columns[0].type.python_type
    except (AttributeError, NotImplementedError):
        return value
    if python_type is datetime and isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if python_type is UUID and isinstance(value, str):
        return UUID(value)
    if python_type is int and not isinstance(value, int):
        return int(value)
    return value


def _next_cursor(items: list[Any], sort_by: str, sort_order: str) -> str | None:
    if not items:
        return None
    last = items[-1]
    return encode_cursor(
        sort_by=sort_by,
        sort_order=sort_order,
        sort_value=cursor_sort_value(last, sort_by),
        item_id=getattr(last, "id"),
    )


def _default_sort_field(sortable_fields: tuple[str, ...]) -> str:
    return "created_at" if "created_at" in sortable_fields else "id"


def _pick(values: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: values[field] for field in fields if field in values}


async def _row_status_code(
    session: AsyncSession, model: type[Any], status_id: UUID | None
) -> str | None:
    if status_id is None:
        return None
    result = await session.execute(
        select(model.code).where(model.id == status_id, *_base_filters(model))
    )
    return cast(str | None, result.scalar_one_or_none())


async def _default_status_id(session: AsyncSession, model: type[Any], code: str) -> UUID:
    result = await session.execute(select(model.id).where(model.code == code))
    status_id = result.scalar_one_or_none()
    if status_id is None:
        raise DomainConflictError(
            code="missing_default_status",
            detail=f"Default status '{code}' is not configured for {model.__tablename__}.",
        )
    return cast(UUID, status_id)


def _direction_sortable_fields() -> tuple[str, ...]:
    return _direction_write_fields() + ("id", "status_id", "created_at", "updated_at")


def _direction_write_fields() -> tuple[str, ...]:
    return (
        "year_no",
        "base_no",
        "is_done",
        "is_urgent",
        "doctor_id",
        "object_id",
        "sampled_at",
        "received_at",
        "completed_at",
        "import_warnings",
    )


def _sample_sortable_fields() -> tuple[str, ...]:
    return _sample_write_fields() + ("id", "status_id", "created_at", "updated_at")


def _sample_write_fields() -> tuple[str, ...]:
    return (
        "month_no",
        "name",
        "alternate_name",
        "mass",
        "target_description",
        "comment",
        "section",
        "delivery",
        "nomenclature_code",
        "batch_code",
        "supplier",
        "is_urgent",
        "is_done",
        "sample_type_id",
        "direction_id",
        "protocol_id",
        "sampled_at",
        "received_at",
        "completed_at",
        "deadline",
        "verdict",
    )


def _research_sortable_fields() -> tuple[str, ...]:
    return _research_write_fields() + ("id", "status_id", "created_at", "updated_at")


def _research_write_fields() -> tuple[str, ...]:
    return (
        "sample_id",
        "research_goal_id",
        "lab_id",
        "comment",
        "recommendation",
        "received_at",
        "completed_at",
    )


def _test_sortable_fields() -> tuple[str, ...]:
    return _test_write_fields() + ("id", "status_id", "created_at", "updated_at")


def _test_write_fields() -> tuple[str, ...]:
    return (
        "value",
        "comment",
        "norm",
        "verdict",
        "is_active",
        "research_id",
        "indicator_id",
    )


def _protocol_sortable_fields() -> tuple[str, ...]:
    return (
        "id",
        "year_no",
        "copies",
        "is_signed",
        "protocol_copy_name",
        "excerpt_copy_name",
        "conclusion_id",
        "protocol_type_id",
        "issued_at",
        "created_at",
        "updated_at",
    )
