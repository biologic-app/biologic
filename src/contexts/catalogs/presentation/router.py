from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response, status

from src.core.errors import DomainConflictError, NotFoundError
from src.core.pagination import PageMeta, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse

router = APIRouter(tags=["crud"])

CATALOG_RESOURCES = {
    "branches",
    "labs",
    "objects",
    "doctors",
    "sample_types",
    "research_goals",
    "indicators",
    "conclusions",
    "protocol_types",
}
STATUS_RESOURCES = {
    "direction_statuses",
    "sample_statuses",
    "research_statuses",
    "test_statuses",
}
ACCESS_RESOURCES = {
    "users",
    "roles",
    "permissions",
    "role_permissions",
    "user_scopes",
}
WORKFLOW_RESOURCES = {"directions", "samples", "research", "tests", "protocols"}
READ_ONLY_RESOURCES = STATUS_RESOURCES | {"history"}
SYSTEM_CREATED_RESOURCES = {"alerts", "tests"}
ALL_RESOURCES = (
    CATALOG_RESOURCES
    | STATUS_RESOURCES
    | ACCESS_RESOURCES
    | WORKFLOW_RESOURCES
    | {"history", "alerts"}
)
STATUS_PATCH_FORBIDDEN = {"directions", "samples", "research", "tests"}


def _ensure_resource(resource: str) -> None:
    if resource not in ALL_RESOURCES:
        raise NotFoundError("Resource was not found.")


def _meta(params: PaginationParams, *, allowed: tuple[str, ...] = ()) -> PageMeta:
    requested = params.includes_requested
    applied = [item for item in requested if item in allowed]
    return PageMeta(
        total=0,
        offset=params.offset,
        limit=params.limit,
        has_more=False,
        includes_requested=requested,
        includes_applied=applied,
        includes_allowed=list(allowed),
    )


@router.get("/{resource}")
async def list_resource(
    resource: str,
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    _ensure_resource(resource)
    return ListResponse(items=[], meta=_meta(params))


@router.get("/{resource}/{item_id}")
async def read_resource(resource: str, item_id: UUID) -> SingleResponse[dict[str, object]]:
    _ensure_resource(resource)
    raise NotFoundError(f"{resource} item {item_id} was not found.")


@router.post("/{resource}", status_code=status.HTTP_201_CREATED)
async def create_resource(
    resource: str,
    payload: dict[str, object],
) -> SingleResponse[dict[str, object]]:
    _ensure_resource(resource)
    if resource in READ_ONLY_RESOURCES or resource in SYSTEM_CREATED_RESOURCES:
        raise DomainConflictError(
            code="resource_read_only",
            detail=f"{resource} cannot be created through generic CRUD.",
        )
    item = {"id": str(uuid4()), **payload}
    return SingleResponse(data=item, meta=ResponseMeta(operation=f"{resource}.create"))


@router.patch("/{resource}/{item_id}")
async def update_resource(
    resource: str,
    item_id: UUID,
    payload: dict[str, object],
) -> SingleResponse[dict[str, object]]:
    _ensure_resource(resource)
    if resource in READ_ONLY_RESOURCES:
        raise DomainConflictError(
            code="resource_read_only",
            detail=f"{resource} cannot be updated through generic CRUD.",
        )
    if resource in STATUS_PATCH_FORBIDDEN and "status_id" in payload:
        raise DomainConflictError(
            code="invalid_status_transition",
            detail=f"{resource} lifecycle status must be changed through commands.",
        )
    return SingleResponse(
        data={"id": str(item_id), **payload},
        meta=ResponseMeta(operation=f"{resource}.update"),
    )


@router.delete("/{resource}/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(resource: str, item_id: UUID) -> Response:
    _ensure_resource(resource)
    if resource in READ_ONLY_RESOURCES:
        raise DomainConflictError(
            code="resource_read_only",
            detail=f"{resource} cannot be deleted through generic CRUD.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
