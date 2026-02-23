from collections.abc import Mapping
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

from src.core.errors import BadRequestError, NotFoundError
from src.models.base import Base
from src.repositories.crud_repository import CRUDRepository, ListQuery, SortOrder
from src.schemas.common import PageMeta

ModelT = TypeVar("ModelT", bound=Base)
ReadSchemaT = TypeVar("ReadSchemaT", bound=BaseModel)


class CRUDService(Generic[ModelT, ReadSchemaT]):
    def __init__(
        self,
        repository: CRUDRepository[ModelT],
        *,
        read_schema: type[ReadSchemaT],
        allowed_sort_fields: set[str],
        not_found_message: str,
    ) -> None:
        self._repository = repository
        self._read_schema = read_schema
        self._allowed_sort_fields = allowed_sort_fields
        self._not_found_message = not_found_message

    def _to_schema(self, entity: ModelT) -> ReadSchemaT:
        return self._read_schema.model_validate(entity, from_attributes=True)

    def _validate_sort_field(self, sort_by: str) -> None:
        if sort_by not in self._allowed_sort_fields:
            allowed = ", ".join(sorted(self._allowed_sort_fields))
            raise BadRequestError(f"Unsupported sort field: {sort_by}. Allowed values: {allowed}.")

    def _not_found(self, entity_id: UUID) -> NotFoundError:
        return NotFoundError(self._not_found_message.format(entity_id=entity_id))

    async def create(self, values: Mapping[str, Any]) -> ReadSchemaT:
        entity = await self._repository.create(values)
        return self._to_schema(entity)

    async def get(self, entity_id: UUID) -> ReadSchemaT:
        entity = await self._repository.get(entity_id)
        if entity is None:
            raise self._not_found(entity_id)
        return self._to_schema(entity)

    async def expand_includes(self, item: ReadSchemaT, includes: list[str]) -> ReadSchemaT:
        if not includes:
            return item
        updates: dict[str, object | None] = {}
        for include in includes:
            fk_field = f"{include}_id"
            fk_value = getattr(item, fk_field, None)
            updates[include] = await self._repository.resolve_include_reference(include, fk_value)
        if not updates:
            return item
        return item.model_copy(update=updates)

    async def expand_includes_many(
        self,
        items: list[ReadSchemaT],
        includes: list[str],
    ) -> list[ReadSchemaT]:
        if not includes or not items:
            return items

        include_maps: dict[str, Mapping[UUID, object]] = {}
        for include in includes:
            fk_field = f"{include}_id"
            fk_values = [getattr(item, fk_field, None) for item in items]
            include_maps[include] = await self._repository.resolve_include_references(
                include,
                fk_values,
            )

        expanded_items: list[ReadSchemaT] = []
        for item in items:
            updates: dict[str, object | None] = {}
            for include in includes:
                fk_value = getattr(item, f"{include}_id", None)
                updates[include] = (
                    include_maps[include].get(fk_value) if fk_value is not None else None
                )
            expanded_items.append(item.model_copy(update=updates) if updates else item)
        return expanded_items

    async def list(
        self,
        *,
        offset: int,
        limit: int,
        sort_by: str,
        sort_order: SortOrder,
        exact_filters: Mapping[str, Any] | None = None,
        contains_filters: Mapping[str, str] | None = None,
        range_filters: Mapping[str, tuple[Any | None, Any | None]] | None = None,
    ) -> tuple[list[ReadSchemaT], PageMeta]:
        self._validate_sort_field(sort_by)
        query = ListQuery(
            offset=offset,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            exact_filters=exact_filters or {},
            contains_filters=contains_filters or {},
            range_filters=range_filters or {},
        )
        try:
            items, total = await self._repository.list(
                query=query,
                allowed_sort_fields=self._allowed_sort_fields,
            )
        except ValueError as exc:
            raise BadRequestError(str(exc)) from exc
        return [self._to_schema(item) for item in items], PageMeta(
            total=total,
            offset=offset,
            limit=limit,
        )

    async def update(self, entity_id: UUID, values: Mapping[str, Any]) -> ReadSchemaT:
        entity = await self._repository.update(entity_id, values)
        if entity is None:
            raise self._not_found(entity_id)
        return self._to_schema(entity)

    async def delete(self, entity_id: UUID, reason: str | None = None) -> None:
        try:
            deleted = await self._repository.soft_delete_with_reason(entity_id, reason)
        except ValueError as exc:
            raise BadRequestError(str(exc)) from exc
        if not deleted:
            raise self._not_found(entity_id)
