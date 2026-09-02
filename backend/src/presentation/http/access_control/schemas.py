from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from src.infrastructure.db.models.enums import AccessScopeType, RoleScopeType


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserCreateRequest(StrictRequest):
    username: str
    password_hash: str
    token_version: int | None = None
    status: str = "active"
    code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    role_id: UUID
    lab_id: UUID | None = None
    branch_id: UUID | None = None


class UserUpdateRequest(StrictRequest):
    username: str | None = None
    password_hash: str | None = None
    token_version: int | None = None
    status: str | None = None
    code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    role_id: UUID | None = None
    lab_id: UUID | None = None
    branch_id: UUID | None = None


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


# Совпадает со status_codes.py (DIRECTION_*/SAMPLE_*) и с CHECK-констрейнтом
# role_subscription_rules_status_code_check в базе — держать в синхроне.
_DIRECTION_STATUS_CODES = {"draft", "registered", "in_progress", "partially_completed", "completed"}
_SAMPLE_STATUS_CODES = {"pending", "registered", "in_progress", "analyzed", "completed", "rejected"}


def _validate_status_code(entity_type: str | None, status_code: str | None) -> None:
    if status_code is None or entity_type is None:
        return
    allowed = _DIRECTION_STATUS_CODES if entity_type == "directions" else _SAMPLE_STATUS_CODES
    if status_code not in allowed:
        raise ValueError(
            f"status_code {status_code!r} is not valid for entity_type {entity_type!r}."
        )


class RoleSubscriptionRuleCreateRequest(StrictRequest):
    role_id: UUID
    entity_type: Literal["directions", "samples"]
    branch_id: UUID | None = None
    lab_id: UUID | None = None
    status_code: str | None = None

    @model_validator(mode="after")
    def check_status_code(self) -> "RoleSubscriptionRuleCreateRequest":
        _validate_status_code(self.entity_type, self.status_code)
        return self


class RoleSubscriptionRuleUpdateRequest(StrictRequest):
    role_id: UUID | None = None
    entity_type: Literal["directions", "samples"] | None = None
    branch_id: UUID | None = None
    lab_id: UUID | None = None
    status_code: str | None = None

    @model_validator(mode="after")
    def check_status_code(self) -> "RoleSubscriptionRuleUpdateRequest":
        # entity_type может отсутствовать в PATCH (не меняется) — тогда
        # комбинацию с текущим entity_type из БД проверит CHECK-констрейнт.
        if "entity_type" in self.model_fields_set:
            _validate_status_code(self.entity_type, self.status_code)
        return self


class UserScopeCreateRequest(StrictRequest):
    user_id: UUID
    scope_kind: Literal["branch", "lab", "object"] = "object"
    scope_id: UUID | None = None


class UserScopeUpdateRequest(StrictRequest):
    user_id: UUID | None = None
    scope_kind: Literal["branch", "lab", "object"] | None = None
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
