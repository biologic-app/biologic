from __future__ import annotations

import builtins
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, asc, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud_query import (
    JoinSpec,
    RelatedField,
    apply_outer_joins,
    attach_sort_values,
    build_crud_query_parts,
    cursor_sort_value,
)
from src.core.cursor_pagination import CursorState, decode_cursor, encode_cursor
from src.core.errors import BadRequestError, NotFoundError
from src.core.pagination import PaginationParams
from src.infrastructure.db.models import (
    Branch,
    Lab,
    Permission,
    Role,
    RolePermission,
    RoleSubscriptionRule,
    User,
    UserPermissionOverride,
    UserScope,
)


@dataclass(frozen=True)
class RepositoryPage:
    items: list[Any]
    total: int
    has_more: bool
    next_cursor: str | None


class UserRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, User, params, _user_sortable_fields())

    async def read(self, user_id: UUID) -> Any:
        return await _read_row(self.session, User, "users", user_id)

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(self.session, User, _pick(values, _user_write_fields()))

    async def update(self, user_id: UUID, values: dict[str, Any]) -> Any:
        return await _update_row(
            self.session,
            await self.read(user_id),
            _pick(values, _user_write_fields()),
        )

    async def delete(self, user_id: UUID) -> None:
        await _delete_row(self.session, await self.read(user_id))

    async def get_by_username(self, username: str) -> Any | None:
        result = await self.session.execute(
            select(User).where(
                User.username == username,
                User.deleted_at.is_(None),
            ),
        )
        return result.scalar_one_or_none()


class RoleRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, Role, params, _role_sortable_fields())

    async def read(self, role_id: UUID) -> Any:
        return await _read_row(self.session, Role, "roles", role_id)

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(self.session, Role, _pick(values, ("key", "name", "scope_type")))

    async def update(self, role_id: UUID, values: dict[str, Any]) -> Any:
        return await _update_row(
            self.session,
            await self.read(role_id),
            _pick(values, ("key", "name", "scope_type")),
        )

    async def delete(self, role_id: UUID) -> None:
        await _delete_row(self.session, await self.read(role_id))


class PermissionRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, Permission, params, _permission_sortable_fields())

    async def read(self, permission_id: UUID) -> Any:
        return await _read_row(self.session, Permission, "permissions", permission_id)

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(self.session, Permission, _pick(values, ("resource", "action")))

    async def update(self, permission_id: UUID, values: dict[str, Any]) -> Any:
        return await _update_row(
            self.session,
            await self.read(permission_id),
            _pick(values, ("resource", "action")),
        )

    async def delete(self, permission_id: UUID) -> None:
        await _delete_row(self.session, await self.read(permission_id))


class RolePermissionRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(
            self.session,
            RolePermission,
            params,
            _role_permission_sortable_fields(),
        )

    async def read(self, role_permission_id: UUID) -> Any:
        return await _read_row(
            self.session,
            RolePermission,
            "role_permissions",
            role_permission_id,
        )

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(
            self.session,
            RolePermission,
            _pick(values, ("role_id", "permission_id", "scope")),
        )

    async def update(self, role_permission_id: UUID, values: dict[str, Any]) -> Any:
        return await _update_row(
            self.session,
            await self.read(role_permission_id),
            _pick(values, ("role_id", "permission_id", "scope")),
        )

    async def delete(self, role_permission_id: UUID) -> None:
        await _delete_row(self.session, await self.read(role_permission_id))

    async def list_for_role(self, role_id: UUID) -> builtins.list[tuple[Any, Any]]:
        result = await self.session.execute(
            select(RolePermission, Permission)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(RolePermission.role_id == role_id)
            .order_by(Permission.resource, Permission.action, Permission.id),
        )
        return [(role_permission, permission) for role_permission, permission in result.all()]

    async def replace_for_role(
        self,
        role_id: UUID,
        permissions: builtins.list[dict[str, Any]],
    ) -> builtins.list[tuple[Any, Any]]:
        await self.session.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
        for item in permissions:
            self.session.add(
                RolePermission(
                    role_id=role_id,
                    permission_id=item["permission_id"],
                    scope=item["scope"],
                ),
            )
        await self.session.commit()
        return await self.list_for_role(role_id)


class RoleSubscriptionRuleRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(
            self.session,
            RoleSubscriptionRule,
            params,
            _role_subscription_rule_sortable_fields(),
        )

    async def read(self, item_id: UUID) -> Any:
        return await _read_row(
            self.session,
            RoleSubscriptionRule,
            "role_subscription_rules",
            item_id,
        )

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(
            self.session,
            RoleSubscriptionRule,
            _pick(values, ("role_id", "entity_type", "branch_id", "lab_id", "status_code")),
        )

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any:
        return await _update_row(
            self.session,
            await self.read(item_id),
            _pick(values, ("role_id", "entity_type", "branch_id", "lab_id", "status_code")),
        )

    async def delete(self, item_id: UUID) -> None:
        await _delete_row(self.session, await self.read(item_id))


class UserPermissionOverrideRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: UUID) -> list[tuple[Any, Any]]:
        result = await self.session.execute(
            select(UserPermissionOverride, Permission)
            .join(Permission, Permission.id == UserPermissionOverride.permission_id)
            .where(UserPermissionOverride.user_id == user_id)
            .order_by(Permission.resource, Permission.action, Permission.id),
        )
        return [(override, permission) for override, permission in result.all()]

    async def replace_for_user(
        self,
        user_id: UUID,
        overrides: list[dict[str, Any]],
    ) -> list[tuple[Any, Any]]:
        await self.session.execute(
            delete(UserPermissionOverride).where(UserPermissionOverride.user_id == user_id),
        )
        for item in overrides:
            self.session.add(
                UserPermissionOverride(
                    user_id=user_id,
                    permission_id=item["permission_id"],
                    allowed=item["allowed"],
                    scope=item["scope"],
                ),
            )
        await self.session.commit()
        return await self.list_for_user(user_id)


class UserScopeRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, UserScope, params, _user_scope_sortable_fields())

    async def read(self, user_scope_id: UUID) -> Any:
        return await _read_row(self.session, UserScope, "user_scopes", user_scope_id)

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(
            self.session, UserScope, _pick(values, ("user_id", "scope_kind", "scope_id"))
        )

    async def update(self, user_scope_id: UUID, values: dict[str, Any]) -> Any:
        return await _update_row(
            self.session,
            await self.read(user_scope_id),
            _pick(values, ("user_id", "scope_kind", "scope_id")),
        )

    async def delete(self, user_scope_id: UUID) -> None:
        await _delete_row(self.session, await self.read(user_scope_id))


async def _list_rows(
    session: AsyncSession,
    model: type[Any],
    params: PaginationParams,
    sortable_fields: tuple[str, ...],
) -> RepositoryPage:
    query_parts = build_crud_query_parts(
        model=model,
        params=params,
        sortable_fields=sortable_fields,
        base_filters=_base_filters(model),
        related_fields=_related_fields(model),
    )
    sort_by = query_parts.sort_by
    sort_column = query_parts.sort_column
    id_column = getattr(model, "id")
    filters = list(query_parts.filters)
    total_filters = list(filters)
    cursor = decode_cursor(params.cursor) if params.cursor else None
    if cursor is not None:
        if cursor.sort_by != sort_by or cursor.sort_order != params.sort_order:
            raise BadRequestError("Pagination cursor does not match requested sorting.")
        filters.append(_cursor_filter(cursor, sort_column, id_column))

    total_query = apply_outer_joins(
        select(func.count()).select_from(model),
        query_parts.joins,
    ).where(*total_filters)
    total_result = await session.execute(total_query)
    total = int(total_result.scalar_one())
    order_fn = asc if params.sort_order == "asc" else desc
    query = apply_outer_joins(
        select(model, sort_column),
        query_parts.joins,
    )
    query = (
        query.where(*filters)
        .order_by(order_fn(sort_column), order_fn(id_column))
        .limit(params.limit + 1)
    )
    result = await session.execute(query)
    rows = attach_sort_values(list(result.all()))
    items = rows[: params.limit]
    has_more = len(rows) > params.limit
    next_cursor = _next_cursor(items, sort_by, params.sort_order) if has_more else None
    return RepositoryPage(items=items, total=total, has_more=has_more, next_cursor=next_cursor)


async def _read_row(
    session: AsyncSession,
    model: type[Any],
    resource: str,
    item_id: UUID,
) -> Any:
    result = await session.execute(
        select(model).where(getattr(model, "id") == item_id, *_base_filters(model)),
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError(f"{resource} item {item_id} was not found.")
    return row


async def _create_row(session: AsyncSession, model: type[Any], values: dict[str, Any]) -> Any:
    row = model(**values)
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def _update_row(session: AsyncSession, row: Any, values: dict[str, Any]) -> Any:
    for field, value in values.items():
        setattr(row, field, value)
    if hasattr(row, "updated_at"):
        setattr(row, "updated_at", datetime.now(UTC))
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def _delete_row(session: AsyncSession, row: Any) -> None:
    if hasattr(row, "deleted_at"):
        setattr(row, "deleted_at", datetime.now(UTC))
        if hasattr(row, "updated_at"):
            setattr(row, "updated_at", datetime.now(UTC))
        session.add(row)
    else:
        await session.execute(delete(type(row)).where(type(row).id == row.id))
    await session.flush()


def _base_filters(model: type[Any]) -> list[Any]:
    if hasattr(model, "deleted_at"):
        return [getattr(model, "deleted_at").is_(None)]
    return []


def _related_fields(model: type[Any]) -> dict[str, RelatedField]:
    if model is User:
        role = JoinSpec("user.role", Role, User.role_id == Role.id)
        lab = JoinSpec("user.lab", Lab, User.lab_id == Lab.id)
        branch = JoinSpec("user.branch", Branch, User.branch_id == Branch.id)
        return {
            "role.name": RelatedField(Role.name, (role,)),
            "lab.name": RelatedField(Lab.name, (lab,)),
            "branch.name": RelatedField(Branch.name, (branch,)),
        }

    if model is RolePermission:
        role = JoinSpec("role_permission.role", Role, RolePermission.role_id == Role.id)
        permission = JoinSpec(
            "role_permission.permission",
            Permission,
            RolePermission.permission_id == Permission.id,
        )
        return {
            "role.name": RelatedField(Role.name, (role,)),
            "permission.resource": RelatedField(Permission.resource, (permission,)),
            "permission.action": RelatedField(Permission.action, (permission,)),
        }

    if model is RoleSubscriptionRule:
        role = JoinSpec(
            "role_subscription_rule.role",
            Role,
            RoleSubscriptionRule.role_id == Role.id,
        )
        branch = JoinSpec(
            "role_subscription_rule.branch",
            Branch,
            RoleSubscriptionRule.branch_id == Branch.id,
        )
        lab = JoinSpec(
            "role_subscription_rule.lab",
            Lab,
            RoleSubscriptionRule.lab_id == Lab.id,
        )
        return {
            "role.name": RelatedField(Role.name, (role,)),
            "branch.name": RelatedField(Branch.name, (branch,)),
            "lab.name": RelatedField(Lab.name, (lab,)),
        }

    return {}


def _cursor_filter(cursor: CursorState, sort_column: Any, id_column: Any) -> Any:
    sort_value = _coerce_cursor_value(sort_column, cursor.sort_value)
    if cursor.sort_order == "asc":
        return or_(
            sort_column > sort_value,
            and_(sort_column == sort_value, id_column > cursor.item_id),
        )
    return or_(
        sort_column < sort_value,
        and_(sort_column == sort_value, id_column < cursor.item_id),
    )


def _coerce_cursor_value(column: Any, value: Any) -> Any:
    try:
        python_type = column.property.columns[0].type.python_type
    except (AttributeError, NotImplementedError):
        return value
    if python_type is datetime and isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if python_type is UUID and isinstance(value, str):
        return UUID(value)
    if python_type is int and not isinstance(value, int):
        return int(value)
    return value


def _next_cursor(items: list[Any], sort_by: str, sort_order: str) -> str | None:
    if not items:
        return None
    last = items[-1]
    return encode_cursor(
        sort_by=sort_by,
        sort_order=sort_order,
        sort_value=cursor_sort_value(last, sort_by),
        item_id=getattr(last, "id"),
    )


def _default_sort_field(sortable_fields: tuple[str, ...]) -> str:
    return "created_at" if "created_at" in sortable_fields else "id"


def _pick(values: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: values[field] for field in fields if field in values}


def _user_sortable_fields() -> tuple[str, ...]:
    return _user_write_fields() + ("id", "created_at", "updated_at")


def _user_write_fields() -> tuple[str, ...]:
    return (
        "username",
        "password_hash",
        "status",
        "code",
        "first_name",
        "last_name",
        "patronymic",
        "role_id",
        "lab_id",
        "branch_id",
    )


def _role_sortable_fields() -> tuple[str, ...]:
    return ("id", "key", "name", "scope_type", "is_system", "created_at", "updated_at")


def _permission_sortable_fields() -> tuple[str, ...]:
    return ("id", "resource", "action")


def _role_permission_sortable_fields() -> tuple[str, ...]:
    return ("id", "role_id", "permission_id", "scope")


def _user_scope_sortable_fields() -> tuple[str, ...]:
    return ("id", "user_id", "scope_kind", "scope_id")


def _role_subscription_rule_sortable_fields() -> tuple[str, ...]:
    return ("id", "entity_type", "created_at", "updated_at")
