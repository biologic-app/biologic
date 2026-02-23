from collections.abc import Mapping
from typing import ClassVar
from uuid import UUID

from src.core.errors import ValidationError
from src.repositories.change_log_repository import ChangeLogRepository
from src.repositories.crud_repository import SortOrder
from src.schemas import (
    ChangeLogCreateDTO,
    ChangeLogCreateEnvelopeDTO,
    ChangeLogDeleteEnvelopeDTO,
    ChangeLogListEnvelopeDTO,
    ChangeLogReadDTO,
    ChangeLogReadEnvelopeDTO,
    ChangeLogUpdateDTO,
    ChangeLogUpdateEnvelopeDTO,
)
from src.schemas.base import ActionMetaDTO, DeleteMetaDTO, ListMetaDTO, ReadMetaDTO
from src.services.crud_service import CRUDService


class ChangeLogService:
    _sort_fields: ClassVar[set[str]] = {
        "entity_id",
        "actor_id",
        "actor_name",
        "action",
        "id",
        "created_at",
        "branch_id",
        "entity_type",
    }

    def __init__(self, repository: ChangeLogRepository) -> None:
        self._repository = repository
        self._crud = CRUDService(
            repository=repository,
            read_schema=ChangeLogReadDTO,
            allowed_sort_fields=self._sort_fields,
            not_found_message="ChangeLog {entity_id} was not found.",
        )

    def _validate_includes(self, includes: list[str]) -> list[str]:
        if not includes:
            return []
        allowed = sorted(self._repository.allowed_includes)
        invalid = sorted(
            {include for include in includes if include not in self._repository.allowed_includes}
        )
        if invalid:
            raise ValidationError(
                f"Unsupported include: {', '.join(invalid)}",
                extra={"allowed_includes": allowed},
            )
        return includes

    async def create(self, payload: ChangeLogCreateDTO) -> ChangeLogCreateEnvelopeDTO:
        data = await self._crud.create(payload.model_dump(exclude_unset=True))
        return ChangeLogCreateEnvelopeDTO(data=data, meta=ActionMetaDTO(operation="create"))

    async def get(
        self, entity_id: UUID, includes: list[str] | None = None
    ) -> ChangeLogReadEnvelopeDTO:
        includes = self._validate_includes(includes or [])
        data = await self._crud.get(entity_id)
        data = await self._crud.expand_includes(data, includes)
        return ChangeLogReadEnvelopeDTO(
            data=data,
            meta=ReadMetaDTO(
                includes=includes,
                includes_requested=includes,
                includes_applied=includes,
                includes_allowed=sorted(self._repository.allowed_includes),
            ),
        )

    async def list(
        self,
        *,
        offset: int,
        limit: int,
        sort_by: str = "created_at",
        sort_order: SortOrder = "desc",
        includes: list[str] | None = None,
        exact_filters: Mapping[str, str] | None = None,
        range_filters: Mapping[str, tuple[str | None, str | None]] | None = None,
    ) -> ChangeLogListEnvelopeDTO:
        includes = self._validate_includes(includes or [])
        items, page_meta = await self._crud.list(
            offset=offset,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            exact_filters=exact_filters,
            range_filters=range_filters,
        )
        expanded_items = await self._crud.expand_includes_many(items, includes)
        meta = ListMetaDTO(
            total=page_meta.total,
            offset=page_meta.offset,
            limit=page_meta.limit,
            includes_requested=includes,
            includes_applied=includes,
            includes_allowed=sorted(self._repository.allowed_includes),
        )
        return ChangeLogListEnvelopeDTO(items=expanded_items, meta=meta)

    async def update(
        self, entity_id: UUID, payload: ChangeLogUpdateDTO
    ) -> ChangeLogUpdateEnvelopeDTO:
        data = await self._crud.update(entity_id, payload.model_dump(exclude_unset=True))
        return ChangeLogUpdateEnvelopeDTO(data=data, meta=ActionMetaDTO(operation="update"))

    async def delete(
        self, entity_id: UUID, reason: str | None = None
    ) -> ChangeLogDeleteEnvelopeDTO:
        await self._crud.delete(entity_id, reason=reason)
        return ChangeLogDeleteEnvelopeDTO(meta=DeleteMetaDTO(operation="delete", deleted=True))
