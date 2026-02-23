from collections.abc import Mapping
from typing import ClassVar
from uuid import UUID

from src.core.errors import NotFoundError, ValidationError
from src.repositories.crud_repository import SortOrder
from src.repositories.role_permissions_repository import RolePermissionRepository
from src.schemas import (
    RolePermissionCreateDTO,
    RolePermissionCreateEnvelopeDTO,
    RolePermissionDeleteEnvelopeDTO,
    RolePermissionListEnvelopeDTO,
    RolePermissionReadDTO,
    RolePermissionReadEnvelopeDTO,
    RolePermissionUpdateDTO,
    RolePermissionUpdateEnvelopeDTO,
)
from src.schemas.base import ActionMetaDTO, DeleteMetaDTO, ListMetaDTO, ReadMetaDTO
from src.services.crud_service import CRUDService


class RolePermissionService:
    _sort_fields: ClassVar[set[str]] = {"role_id", "resource", "action", "created_at", "updated_at"}

    def __init__(self, repository: RolePermissionRepository) -> None:
        self._repository = repository
        self._crud = CRUDService(
            repository=repository,
            read_schema=RolePermissionReadDTO,
            allowed_sort_fields=self._sort_fields,
            not_found_message="RolePermission was not found.",
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

    async def create(self, payload: RolePermissionCreateDTO) -> RolePermissionCreateEnvelopeDTO:
        data = await self._crud.create(payload.model_dump(exclude_unset=True))
        return RolePermissionCreateEnvelopeDTO(data=data, meta=ActionMetaDTO(operation="create"))

    async def get(
        self, role_id: UUID, resource: str, action: str, includes: list[str] | None = None
    ) -> RolePermissionReadEnvelopeDTO:
        includes = self._validate_includes(includes or [])
        entity = await self._repository.get_by_pk(role_id, resource, action)
        if entity is None:
            raise NotFoundError("RolePermission was not found.")
        data = RolePermissionReadDTO.model_validate(entity, from_attributes=True)
        data = await self._crud.expand_includes(data, includes)
        return RolePermissionReadEnvelopeDTO(
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
    ) -> RolePermissionListEnvelopeDTO:
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
        return RolePermissionListEnvelopeDTO(items=expanded_items, meta=meta)

    async def update(
        self, role_id: UUID, resource: str, action: str, payload: RolePermissionUpdateDTO
    ) -> RolePermissionUpdateEnvelopeDTO:
        entity = await self._repository.update_by_pk(
            role_id, resource, action, payload.model_dump(exclude_unset=True)
        )
        if entity is None:
            raise NotFoundError("RolePermission was not found.")
        data = RolePermissionReadDTO.model_validate(entity, from_attributes=True)
        return RolePermissionUpdateEnvelopeDTO(data=data, meta=ActionMetaDTO(operation="update"))

    async def delete(
        self, role_id: UUID, resource: str, action: str, reason: str | None = None
    ) -> RolePermissionDeleteEnvelopeDTO:
        deleted = await self._repository.delete_by_pk(role_id, resource, action, reason=reason)
        if not deleted:
            raise NotFoundError("RolePermission was not found.")
        return RolePermissionDeleteEnvelopeDTO(
            meta=DeleteMetaDTO(operation="soft_delete", deleted=True)
        )
