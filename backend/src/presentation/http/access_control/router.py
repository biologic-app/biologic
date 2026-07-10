from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from src.application.access_control.use_cases.permission_crud import PermissionCrudUseCase
from src.application.access_control.use_cases.role_crud import RoleCrudUseCase
from src.application.access_control.use_cases.role_permission_crud import (
    RolePermissionCrudUseCase,
)
from src.application.access_control.use_cases.role_permission_set import (
    RolePermissionSetUseCase,
)
from src.application.access_control.use_cases.role_subscription_rule_crud import (
    RoleSubscriptionRuleCrudUseCase,
)
from src.application.access_control.use_cases.user_crud import UserCrudUseCase
from src.application.access_control.use_cases.user_permission_set import (
    UserPermissionSetUseCase,
)
from src.application.access_control.use_cases.user_scope_crud import UserScopeCrudUseCase
from src.core.pagination import PaginationDependency
from src.core.responses import ListResponse, SingleResponse
from src.presentation.http.access_control.dependencies import (
    get_actor_id,
    get_permission_use_case,
    get_role_permission_set_use_case,
    get_role_permission_use_case,
    get_role_subscription_rule_use_case,
    get_role_use_case,
    get_user_permission_set_use_case,
    get_user_scope_use_case,
    get_user_use_case,
)
from src.presentation.http.access_control.schemas import (
    PermissionCreateRequest,
    PermissionUpdateRequest,
    RoleCreateRequest,
    RolePermissionCreateRequest,
    RolePermissionsReplaceRequest,
    RolePermissionUpdateRequest,
    RoleSubscriptionRuleCreateRequest,
    RoleSubscriptionRuleUpdateRequest,
    RoleUpdateRequest,
    UserCreateRequest,
    UserPermissionOverridesReplaceRequest,
    UserScopeCreateRequest,
    UserScopeUpdateRequest,
    UserUpdateRequest,
)

router = APIRouter(tags=["access-control"])

UserUseCase = Annotated[UserCrudUseCase, Depends(get_user_use_case)]
RoleUseCase = Annotated[RoleCrudUseCase, Depends(get_role_use_case)]
PermissionUseCase = Annotated[PermissionCrudUseCase, Depends(get_permission_use_case)]
RolePermissionUseCase = Annotated[RolePermissionCrudUseCase, Depends(get_role_permission_use_case)]
UserScopeUseCase = Annotated[UserScopeCrudUseCase, Depends(get_user_scope_use_case)]
RoleSubscriptionRuleUseCase = Annotated[
    RoleSubscriptionRuleCrudUseCase, Depends(get_role_subscription_rule_use_case)
]
RolePermissionSet = Annotated[RolePermissionSetUseCase, Depends(get_role_permission_set_use_case)]
UserPermissionSet = Annotated[UserPermissionSetUseCase, Depends(get_user_permission_set_use_case)]


def _deleted_response() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users")
async def list_users(
    params: PaginationDependency,
    use_case: UserUseCase,
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/users/{user_id}")
async def read_user(
    user_id: UUID,
    use_case: UserUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(user_id)


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateRequest,
    use_case: UserUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    use_case: UserUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(user_id, payload)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    use_case: UserUseCase,
) -> Response:
    await use_case.delete(user_id)
    return _deleted_response()


@router.get("/users/{user_id}/permissions")
async def read_user_permissions(
    user_id: UUID,
    use_case: UserPermissionSet,
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_effective(user_id)


@router.get("/user/me/permissions")
async def read_current_user_permissions(
    actor_id: Annotated[UUID, Depends(get_actor_id)],
    use_case: UserPermissionSet,
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_effective(actor_id)


@router.get("/users/{user_id}/overrides")
async def read_user_permission_overrides(
    user_id: UUID,
    use_case: UserPermissionSet,
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_overrides(user_id)


@router.put("/users/{user_id}/overrides")
async def replace_user_permission_overrides(
    user_id: UUID,
    payload: UserPermissionOverridesReplaceRequest,
    use_case: UserPermissionSet,
) -> SingleResponse[dict[str, object]]:
    return await use_case.replace_overrides(user_id, payload)


@router.get("/roles")
async def list_roles(
    params: PaginationDependency,
    use_case: RoleUseCase,
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/roles/{role_id}")
async def read_role(
    role_id: UUID,
    use_case: RoleUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(role_id)


@router.post("/roles", status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreateRequest,
    use_case: RoleUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


@router.patch("/roles/{role_id}")
async def update_role(
    role_id: UUID,
    payload: RoleUpdateRequest,
    use_case: RoleUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(role_id, payload)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    use_case: RoleUseCase,
) -> Response:
    await use_case.delete(role_id)
    return _deleted_response()


@router.get("/roles/{role_id}/permissions")
async def read_role_permissions(
    role_id: UUID,
    use_case: RolePermissionSet,
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(role_id)


@router.put("/roles/{role_id}/permissions")
async def replace_role_permissions(
    role_id: UUID,
    payload: RolePermissionsReplaceRequest,
    use_case: RolePermissionSet,
) -> SingleResponse[dict[str, object]]:
    return await use_case.replace(role_id, payload)


@router.get("/permissions")
async def list_permissions(
    params: PaginationDependency,
    use_case: PermissionUseCase,
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/permissions/{permission_id}")
async def read_permission(
    permission_id: UUID,
    use_case: PermissionUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(permission_id)


@router.post("/permissions", status_code=status.HTTP_201_CREATED)
async def create_permission(
    payload: PermissionCreateRequest,
    use_case: PermissionUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


@router.patch("/permissions/{permission_id}")
async def update_permission(
    permission_id: UUID,
    payload: PermissionUpdateRequest,
    use_case: PermissionUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(permission_id, payload)


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    permission_id: UUID,
    use_case: PermissionUseCase,
) -> Response:
    await use_case.delete(permission_id)
    return _deleted_response()


@router.get("/role_permissions")
async def list_role_permissions(
    params: PaginationDependency,
    use_case: RolePermissionUseCase,
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/role_permissions/{role_permission_id}")
async def read_role_permission(
    role_permission_id: UUID,
    use_case: RolePermissionUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(role_permission_id)


@router.post("/role_permissions", status_code=status.HTTP_201_CREATED)
async def create_role_permission(
    payload: RolePermissionCreateRequest,
    use_case: RolePermissionUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


@router.patch("/role_permissions/{role_permission_id}")
async def update_role_permission(
    role_permission_id: UUID,
    payload: RolePermissionUpdateRequest,
    use_case: RolePermissionUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(role_permission_id, payload)


@router.delete("/role_permissions/{role_permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role_permission(
    role_permission_id: UUID,
    use_case: RolePermissionUseCase,
) -> Response:
    await use_case.delete(role_permission_id)
    return _deleted_response()


@router.get("/role_subscription_rules")
async def list_role_subscription_rules(
    params: PaginationDependency,
    use_case: RoleSubscriptionRuleUseCase,
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/role_subscription_rules/{role_subscription_rule_id}")
async def read_role_subscription_rule(
    role_subscription_rule_id: UUID,
    use_case: RoleSubscriptionRuleUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(role_subscription_rule_id)


@router.post("/role_subscription_rules", status_code=status.HTTP_201_CREATED)
async def create_role_subscription_rule(
    payload: RoleSubscriptionRuleCreateRequest,
    use_case: RoleSubscriptionRuleUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


@router.patch("/role_subscription_rules/{role_subscription_rule_id}")
async def update_role_subscription_rule(
    role_subscription_rule_id: UUID,
    payload: RoleSubscriptionRuleUpdateRequest,
    use_case: RoleSubscriptionRuleUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(role_subscription_rule_id, payload)


@router.delete(
    "/role_subscription_rules/{role_subscription_rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_role_subscription_rule(
    role_subscription_rule_id: UUID,
    use_case: RoleSubscriptionRuleUseCase,
) -> Response:
    await use_case.delete(role_subscription_rule_id)
    return _deleted_response()


@router.get("/user_scopes")
async def list_user_scopes(
    params: PaginationDependency,
    use_case: UserScopeUseCase,
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/user_scopes/{user_scope_id}")
async def read_user_scope(
    user_scope_id: UUID,
    use_case: UserScopeUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(user_scope_id)


@router.post("/user_scopes", status_code=status.HTTP_201_CREATED)
async def create_user_scope(
    payload: UserScopeCreateRequest,
    use_case: UserScopeUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


@router.patch("/user_scopes/{user_scope_id}")
async def update_user_scope(
    user_scope_id: UUID,
    payload: UserScopeUpdateRequest,
    use_case: UserScopeUseCase,
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(user_scope_id, payload)


@router.delete("/user_scopes/{user_scope_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_scope(
    user_scope_id: UUID,
    use_case: UserScopeUseCase,
) -> Response:
    await use_case.delete(user_scope_id)
    return _deleted_response()
