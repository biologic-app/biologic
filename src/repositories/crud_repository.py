from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Generic, Literal, TypeVar, cast
from uuid import UUID

from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.sqltypes import Boolean, DateTime, Integer, SmallInteger

from src.models.base import Base
from src.models.entities import ChangeLog
from src.schemas.base import EntityRefDTO

SortOrder = Literal["asc", "desc"]


@dataclass(frozen=True, slots=True)
class ListQuery:
    offset: int = 0
    limit: int = 15
    sort_by: str = "created_at"
    sort_order: SortOrder = "desc"
    exact_filters: Mapping[str, Any] = field(default_factory=dict)
    contains_filters: Mapping[str, str] = field(default_factory=dict)
    range_filters: Mapping[str, tuple[Any | None, Any | None]] = field(default_factory=dict)


ModelT = TypeVar("ModelT", bound=Base)


class CRUDRepository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self._session = session
        self._model = model
        self._models_by_table: dict[str, type[Base]] = {}
        for mapper in Base.registry.mappers:
            table_name = getattr(mapper.persist_selectable, "name", None)
            if not isinstance(table_name, str):
                continue
            self._models_by_table[table_name] = cast(type[Base], mapper.class_)
        self._include_targets = self._build_include_targets()

    @property
    def allowed_includes(self) -> set[str]:
        return set(self._include_targets.keys())

    def _build_include_targets(self) -> dict[str, type[Base]]:
        include_targets: dict[str, type[Base]] = {}
        for column in self._model.__table__.columns:
            if not column.name.endswith("_id") or not column.foreign_keys:
                continue
            include_name = column.name[:-3]
            fk = next(iter(column.foreign_keys))
            target_table_name = fk.column.table.name
            target_model = self._models_by_table.get(target_table_name)
            if target_model is None:
                continue
            include_targets[include_name] = target_model
        return include_targets

    def _column(self, field_name: str) -> Any:
        column = getattr(self._model, field_name, None)
        if column is None:
            raise ValueError(f"Unknown field: {field_name}")
        return column

    async def resolve_include_reference(
        self,
        include_name: str,
        raw_id: UUID | None,
    ) -> EntityRefDTO | None:
        if raw_id is None:
            return None
        references = await self.resolve_include_references(include_name, [raw_id])
        return references.get(raw_id)

    async def resolve_include_references(
        self,
        include_name: str,
        raw_ids: Collection[UUID | None],
    ) -> dict[UUID, EntityRefDTO]:
        ids = list(dict.fromkeys(raw_id for raw_id in raw_ids if raw_id is not None))
        if not ids:
            return {}
        target_model = self._include_targets.get(include_name)
        if target_model is None:
            return {}

        id_column = getattr(target_model, "id", None)
        if id_column is None:
            return {}
        name_column = getattr(target_model, "name", None)
        code_column = getattr(target_model, "code", None)
        first_name_column = getattr(target_model, "first_name", None)
        last_name_column = getattr(target_model, "last_name", None)

        projected_columns = [
            id_column.label("_ref_id"),
            name_column.label("_ref_name") if name_column is not None else None,
            code_column.label("_ref_code") if code_column is not None else None,
            first_name_column.label("_ref_first_name") if first_name_column is not None else None,
            last_name_column.label("_ref_last_name") if last_name_column is not None else None,
        ]
        stmt = select(*[column for column in projected_columns if column is not None]).where(
            id_column.in_(ids)
        )
        deleted_at_column = getattr(target_model, "deleted_at", None)
        if deleted_at_column is not None:
            stmt = stmt.where(deleted_at_column.is_(None))

        result = await self._session.execute(stmt)
        references: dict[UUID, EntityRefDTO] = {}
        for row in result:
            row_map = row._mapping
            ref_id = cast(UUID | None, row_map.get("_ref_id"))
            if ref_id is None:
                continue
            ref_name = cast(str | None, row_map.get("_ref_name"))
            if ref_name is None:
                first_name = cast(str | None, row_map.get("_ref_first_name"))
                last_name = cast(str | None, row_map.get("_ref_last_name"))
                ref_name = " ".join(part for part in [first_name, last_name] if part) or None
            references[ref_id] = EntityRefDTO(
                id=ref_id,
                name=ref_name,
                code=cast(str | None, row_map.get("_ref_code")),
            )
        return references

    def _with_soft_delete_filter(self, stmt: Select[tuple[ModelT]]) -> Select[tuple[ModelT]]:
        deleted_at_column = getattr(self._model, "deleted_at", None)
        if deleted_at_column is None:
            return stmt
        return stmt.where(deleted_at_column.is_(None))

    def _with_list_filters(
        self,
        stmt: Select[tuple[ModelT]],
        query: ListQuery,
    ) -> Select[tuple[ModelT]]:
        for field_name, field_value in query.exact_filters.items():
            stmt = stmt.where(
                self._column(field_name) == self._coerce_filter_value(field_name, field_value)
            )

        for field_name, field_value in query.contains_filters.items():
            stmt = stmt.where(self._column(field_name).ilike(f"%{field_value}%"))

        for field_name, (field_from, field_to) in query.range_filters.items():
            column = self._column(field_name)
            if field_from is not None:
                stmt = stmt.where(column >= self._coerce_filter_value(field_name, field_from))
            if field_to is not None:
                stmt = stmt.where(column <= self._coerce_filter_value(field_name, field_to))
        return stmt

    def _coerce_filter_value(self, field_name: str, value: Any) -> Any:
        if value is None or not isinstance(value, str):
            return value

        column_type = self._column(field_name).property.columns[0].type

        if isinstance(column_type, PGUUID):
            return UUID(value)
        if isinstance(column_type, (Integer, SmallInteger)):
            return int(value)
        if isinstance(column_type, Boolean):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "t", "yes", "y", "on"}:
                return True
            if normalized in {"0", "false", "f", "no", "n", "off"}:
                return False
        if isinstance(column_type, DateTime):
            normalized_value = value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized_value)

        return value

    def _resolve_sort_column(self, query: ListQuery, allowed_sort_fields: Collection[str]) -> Any:
        if query.sort_by not in allowed_sort_fields:
            raise ValueError(f"Unsupported sort field: {query.sort_by}")
        column = self._column(query.sort_by)
        if query.sort_order == "asc":
            return asc(column)
        return desc(column)

    async def create(self, values: Mapping[str, Any]) -> ModelT:
        entity = self._model(**dict(values))
        self._session.add(entity)
        await self._session.commit()
        await self._session.refresh(entity)
        return entity

    async def get(self, entity_id: UUID) -> ModelT | None:
        stmt = select(self._model).where(self._column("id") == entity_id)
        stmt = self._with_soft_delete_filter(stmt)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        query: ListQuery,
        *,
        allowed_sort_fields: Collection[str],
    ) -> tuple[list[ModelT], int]:
        base_stmt = select(self._model)
        base_stmt = self._with_soft_delete_filter(base_stmt)
        base_stmt = self._with_list_filters(base_stmt, query)
        sort_clause = self._resolve_sort_column(query, allowed_sort_fields)

        total_stmt = self._build_total_stmt(query=query, base_stmt=base_stmt)
        total_result = await self._session.execute(total_stmt)
        total = int(total_result.scalar_one())

        items_stmt = base_stmt.order_by(sort_clause).offset(query.offset).limit(query.limit)
        items_result = await self._session.execute(items_stmt)
        items = list(items_result.scalars().all())
        return items, total

    def _build_total_stmt(
        self,
        *,
        query: ListQuery,
        base_stmt: Select[tuple[ModelT]],
    ) -> Select[tuple[int]]:
        del query
        return base_stmt.order_by(None).with_only_columns(
            func.count(),
            maintain_column_froms=True,
        )

    async def update(self, entity_id: UUID, values: Mapping[str, Any]) -> ModelT | None:
        entity = await self.get(entity_id)
        if entity is None:
            return None

        for key, value in values.items():
            setattr(entity, key, value)

        if hasattr(entity, "updated_at"):
            entity.updated_at = datetime.now(UTC)

        await self._session.commit()
        await self._session.refresh(entity)
        return entity

    async def soft_delete(self, entity_id: UUID) -> bool:
        return await self.soft_delete_with_reason(entity_id, reason=None)

    async def soft_delete_with_reason(self, entity_id: UUID, reason: str | None) -> bool:
        entity = await self.get(entity_id)
        if entity is None:
            return False
        has_soft_delete = hasattr(entity, "deleted_at")

        now = datetime.now(UTC)
        if has_soft_delete:
            cast(Any, entity).deleted_at = now
        if hasattr(entity, "updated_at"):
            cast(Any, entity).updated_at = now

        diff_payload: dict[str, object] | None = None
        if reason:
            diff_payload = {"reason": reason}

        if not has_soft_delete:
            await self._session.delete(entity)

        if self._model is not ChangeLog:
            self._session.add(
                ChangeLog(
                    entity_type=self._model.__tablename__,
                    entity_id=entity_id,
                    action="soft_delete" if has_soft_delete else "delete",
                    diff=diff_payload,
                )
            )

        await self._session.commit()
        return True
