from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from src.infrastructure.db.models.entities import AccessScopeType, RoleScopeType


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserCreateRequest(StrictRequest):
    username: str
    password_hash: str
    refresh_token_version: int | None = None
    code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    is_registrar: bool | None = None
    is_lab_head: bool | None = None
    is_branch_head: bool | None = None
    role_id: UUID
    lab_id: UUID | None = None


class UserUpdateRequest(StrictRequest):
    username: str | None = None
    password_hash: str | None = None
    refresh_token_version: int | None = None
    code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    is_registrar: bool | None = None
    is_lab_head: bool | None = None
    is_branch_head: bool | None = None
    role_id: UUID | None = None
    lab_id: UUID | None = None


class RoleCreateRequest(StrictRequest):
    key: str
    name: str
    scope_type: RoleScopeType


class RoleUpdateRequest(StrictRequest):
    key: str | None = None
    name: str | None = None
    scope_type: RoleScopeType | None = None


class PermissionCreateRequest(StrictRequest):
    resource: str
    action: str


class PermissionUpdateRequest(StrictRequest):
    resource: str | None = None
    action: str | None = None


class RolePermissionCreateRequest(StrictRequest):
    role_id: UUID
    permission_id: UUID
    scope: AccessScopeType = AccessScopeType.ALL


class RolePermissionUpdateRequest(StrictRequest):
    role_id: UUID | None = None
    permission_id: UUID | None = None
    scope: AccessScopeType | None = None


class UserScopeCreateRequest(StrictRequest):
    user_id: UUID
    scope_id: UUID | None = None


class UserScopeUpdateRequest(StrictRequest):
    user_id: UUID | None = None
    scope_id: UUID | None = None


class RolePermissionAssignmentRequest(StrictRequest):
    permission_id: UUID
    scope: AccessScopeType = AccessScopeType.ALL


class RolePermissionsReplaceRequest(StrictRequest):
    permissions: list[RolePermissionAssignmentRequest]


class UserPermissionOverrideRequest(StrictRequest):
    permission_id: UUID
    allowed: bool
    scope: AccessScopeType | None = None

    @model_validator(mode="after")
    def normalize_scope(self) -> "UserPermissionOverrideRequest":
        if not self.allowed:
            self.scope = None
        elif self.scope is None:
            self.scope = AccessScopeType.ALL
        return self


class UserPermissionOverridesReplaceRequest(StrictRequest):
    overrides: list[UserPermissionOverrideRequest]
