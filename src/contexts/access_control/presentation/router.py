from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from src.contexts.access_control.application.crud import AccessControlCrudUseCase
from src.contexts.access_control.presentation.dependencies import get_access_control_use_case
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
from src.core.pagination import PaginationDependency
from src.core.responses import ListResponse, SingleResponse

router = APIRouter(tags=["access-control"])


def _deleted_response() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users")
async def list_users(
    params: PaginationDependency,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_users(params)


@router.get("/users/{user_id}")
async def read_user(
    user_id: UUID,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_user(user_id)


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateRequest,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_user(payload)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_user(user_id, payload)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> Response:
    await use_case.delete_user(user_id)
    return _deleted_response()


@router.get("/roles")
async def list_roles(
    params: PaginationDependency,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_roles(params)


@router.get("/roles/{role_id}")
async def read_role(
    role_id: UUID,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_role(role_id)


@router.post("/roles", status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreateRequest,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_role(payload)


@router.patch("/roles/{role_id}")
async def update_role(
    role_id: UUID,
    payload: RoleUpdateRequest,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_role(role_id, payload)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> Response:
    await use_case.delete_role(role_id)
    return _deleted_response()


@router.get("/permissions")
async def list_permissions(
    params: PaginationDependency,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_permissions(params)


@router.get("/permissions/{permission_id}")
async def read_permission(
    permission_id: UUID,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_permission(permission_id)


@router.post("/permissions", status_code=status.HTTP_201_CREATED)
async def create_permission(
    payload: PermissionCreateRequest,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_permission(payload)


@router.patch("/permissions/{permission_id}")
async def update_permission(
    permission_id: UUID,
    payload: PermissionUpdateRequest,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_permission(permission_id, payload)


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    permission_id: UUID,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> Response:
    await use_case.delete_permission(permission_id)
    return _deleted_response()


@router.get("/role_permissions")
async def list_role_permissions(
    params: PaginationDependency,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_role_permissions(params)


@router.get("/role_permissions/{role_permission_id}")
async def read_role_permission(
    role_permission_id: UUID,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_role_permission(role_permission_id)


@router.post("/role_permissions", status_code=status.HTTP_201_CREATED)
async def create_role_permission(
    payload: RolePermissionCreateRequest,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_role_permission(payload)


@router.patch("/role_permissions/{role_permission_id}")
async def update_role_permission(
    role_permission_id: UUID,
    payload: RolePermissionUpdateRequest,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_role_permission(role_permission_id, payload)


@router.delete("/role_permissions/{role_permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role_permission(
    role_permission_id: UUID,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> Response:
    await use_case.delete_role_permission(role_permission_id)
    return _deleted_response()


@router.get("/user_scopes")
async def list_user_scopes(
    params: PaginationDependency,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_user_scopes(params)


@router.get("/user_scopes/{user_scope_id}")
async def read_user_scope(
    user_scope_id: UUID,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_user_scope(user_scope_id)


@router.post("/user_scopes", status_code=status.HTTP_201_CREATED)
async def create_user_scope(
    payload: UserScopeCreateRequest,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_user_scope(payload)


@router.patch("/user_scopes/{user_scope_id}")
async def update_user_scope(
    user_scope_id: UUID,
    payload: UserScopeUpdateRequest,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_user_scope(user_scope_id, payload)


@router.delete("/user_scopes/{user_scope_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_scope(
    user_scope_id: UUID,
    use_case: Annotated[AccessControlCrudUseCase, Depends(get_access_control_use_case)],
) -> Response:
    await use_case.delete_user_scope(user_scope_id)
    return _deleted_response()
