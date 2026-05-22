from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from src.contexts.access_control.presentation.schemas import (
    PermissionCreateRequest,
    PermissionUpdateRequest,
    RoleCreateRequest,
    RolePermissionCreateRequest,
    RolePermissionUpdateRequest,
    RoleUpdateRequest,
    UserCreateRequest,
    UserScopeCreateRequest,
    UserScopeUpdateRequest,
    UserUpdateRequest,
)
from src.core.errors import NotFoundError
from src.core.pagination import PageMeta, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse

router = APIRouter(tags=["access-control"])


def _payload(payload: BaseModel) -> dict[str, object]:
    return payload.model_dump(mode="json", exclude_unset=True)


def _meta(params: PaginationParams) -> PageMeta:
    return PageMeta(
        total=0,
        offset=params.offset,
        limit=params.limit,
        has_more=False,
        includes_requested=params.includes_requested,
        includes_applied=[],
        includes_allowed=[],
    )


def _list_response(params: PaginationParams) -> ListResponse[dict[str, object]]:
    return ListResponse(items=[], meta=_meta(params))


def _read_missing(resource: str, item_id: UUID) -> SingleResponse[dict[str, object]]:
    raise NotFoundError(f"{resource} item {item_id} was not found.")


def _created(resource: str, payload: BaseModel) -> SingleResponse[dict[str, object]]:
    return SingleResponse(
        data={"id": str(uuid4()), **_payload(payload)},
        meta=ResponseMeta(operation=f"{resource}.create"),
    )


def _updated(resource: str, item_id: UUID, payload: BaseModel) -> SingleResponse[dict[str, object]]:
    return SingleResponse(
        data={"id": str(item_id), **_payload(payload)},
        meta=ResponseMeta(operation=f"{resource}.update"),
    )


def _deleted() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users")
async def list_users(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params)


@router.get("/users/{user_id}")
async def read_user(user_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("users", user_id)


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreateRequest) -> SingleResponse[dict[str, object]]:
    return _created("users", payload)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: UUID,
    payload: UserUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("users", user_id, payload)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID) -> Response:
    return _deleted()


@router.get("/roles")
async def list_roles(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params)


@router.get("/roles/{role_id}")
async def read_role(role_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("roles", role_id)


@router.post("/roles", status_code=status.HTTP_201_CREATED)
async def create_role(payload: RoleCreateRequest) -> SingleResponse[dict[str, object]]:
    return _created("roles", payload)


@router.patch("/roles/{role_id}")
async def update_role(
    role_id: UUID,
    payload: RoleUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("roles", role_id, payload)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(role_id: UUID) -> Response:
    return _deleted()


@router.get("/permissions")
async def list_permissions(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params)


@router.get("/permissions/{permission_id}")
async def read_permission(permission_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("permissions", permission_id)


@router.post("/permissions", status_code=status.HTTP_201_CREATED)
async def create_permission(
    payload: PermissionCreateRequest,
) -> SingleResponse[dict[str, object]]:
    return _created("permissions", payload)


@router.patch("/permissions/{permission_id}")
async def update_permission(
    permission_id: UUID,
    payload: PermissionUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("permissions", permission_id, payload)


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(permission_id: UUID) -> Response:
    return _deleted()


@router.get("/role_permissions")
async def list_role_permissions(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params)


@router.get("/role_permissions/{role_permission_id}")
async def read_role_permission(role_permission_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("role_permissions", role_permission_id)


@router.post("/role_permissions", status_code=status.HTTP_201_CREATED)
async def create_role_permission(
    payload: RolePermissionCreateRequest,
) -> SingleResponse[dict[str, object]]:
    return _created("role_permissions", payload)


@router.patch("/role_permissions/{role_permission_id}")
async def update_role_permission(
    role_permission_id: UUID,
    payload: RolePermissionUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("role_permissions", role_permission_id, payload)


@router.delete("/role_permissions/{role_permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role_permission(role_permission_id: UUID) -> Response:
    return _deleted()


@router.get("/user_scopes")
async def list_user_scopes(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params)


@router.get("/user_scopes/{user_scope_id}")
async def read_user_scope(user_scope_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("user_scopes", user_scope_id)


@router.post("/user_scopes", status_code=status.HTTP_201_CREATED)
async def create_user_scope(payload: UserScopeCreateRequest) -> SingleResponse[dict[str, object]]:
    return _created("user_scopes", payload)


@router.patch("/user_scopes/{user_scope_id}")
async def update_user_scope(
    user_scope_id: UUID,
    payload: UserScopeUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("user_scopes", user_scope_id, payload)


@router.delete("/user_scopes/{user_scope_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_scope(user_scope_id: UUID) -> Response:
    return _deleted()
