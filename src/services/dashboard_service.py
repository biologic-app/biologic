from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, ClassVar

from src.core.errors import ForbiddenError, NotFoundError
from src.schemas.base import ActionMetaDTO, ListMetaDTO
from src.schemas.dashboard import (
    DashboardQuickActionCreateDTO,
    DashboardQuickActionCreateEnvelopeDTO,
    DashboardQuickActionDTO,
    DashboardQuickActionListEnvelopeDTO,
    DashboardQuickActionUpdateDTO,
    DashboardQuickActionUpdateEnvelopeDTO,
)


@dataclass(slots=True)
class _QuickActionRecord:
    id: int
    label: str
    resource: str
    action: str
    to: str
    icon: str
    created_at: datetime
    updated_at: datetime


class DashboardQuickActionsService:
    _defaults_by_role: ClassVar[dict[str, list[dict[str, str]]]] = {
        "admin": [
            {
                "label": "Создать объект",
                "resource": "objects",
                "action": "create",
                "to": "/objects#create",
                "icon": "pi pi-cog",
            },
            {
                "label": "Реестр образцов",
                "resource": "samples",
                "action": "view",
                "to": "/samples",
                "icon": "pi pi-box",
            },
            {
                "label": "Пользователи",
                "resource": "users",
                "action": "view",
                "to": "/admin/users",
                "icon": "pi pi-users",
            },
        ],
        "doctor": [
            {
                "label": "Направления",
                "resource": "directions",
                "action": "view",
                "to": "/directions",
                "icon": "pi pi-file",
            },
            {
                "label": "Протоколы",
                "resource": "protocols",
                "action": "view",
                "to": "/protocols",
                "icon": "pi pi-file-edit",
            },
            {
                "label": "Заключения",
                "resource": "conclusions",
                "action": "view",
                "to": "/conclusions",
                "icon": "pi pi-file-check",
            },
        ],
        "technician": [
            {
                "label": "Образцы",
                "resource": "samples",
                "action": "view",
                "to": "/samples",
                "icon": "pi pi-box",
            },
            {
                "label": "Результаты",
                "resource": "results",
                "action": "view",
                "to": "/results",
                "icon": "pi pi-chart-bar",
            },
            {
                "label": "Показатели",
                "resource": "indicators",
                "action": "view",
                "to": "/indicators",
                "icon": "pi pi-chart-line",
            },
        ],
    }

    def __init__(self) -> None:
        self._store_by_role: dict[str, list[_QuickActionRecord]] = {}
        self._next_id_by_role: dict[str, int] = {}

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _permissions_set(
        permissions: list[tuple[str, str]] | set[tuple[str, str]],
    ) -> set[tuple[str, str]]:
        return set(permissions)

    @staticmethod
    def _to_dto(item: _QuickActionRecord) -> DashboardQuickActionDTO:
        return DashboardQuickActionDTO(
            id=item.id,
            label=item.label,
            resource=item.resource,
            action=item.action,
            to=item.to,
            icon=item.icon,
            createdAt=item.created_at,
            updatedAt=item.updated_at,
        )

    @staticmethod
    def _check_permission(
        resource: str,
        action: str,
        permissions: set[tuple[str, str]],
    ) -> None:
        if (resource, action) not in permissions:
            raise ForbiddenError("Недостаточно прав для выбранного быстрого действия.")

    def _seed_role_if_needed(self, role_key: str, permissions: set[tuple[str, str]]) -> None:
        if role_key in self._store_by_role:
            return

        seeded: list[_QuickActionRecord] = []
        next_id = 1
        for candidate in self._defaults_by_role.get(role_key, []):
            resource = candidate["resource"]
            action = candidate["action"]
            if (resource, action) not in permissions:
                continue
            now = self._now()
            seeded.append(
                _QuickActionRecord(
                    id=next_id,
                    label=candidate["label"],
                    resource=resource,
                    action=action,
                    to=candidate["to"],
                    icon=candidate["icon"],
                    created_at=now,
                    updated_at=now,
                )
            )
            next_id += 1

        self._store_by_role[role_key] = seeded
        self._next_id_by_role[role_key] = next_id

    def _role_items(
        self,
        role_key: str,
        permissions: set[tuple[str, str]],
    ) -> list[_QuickActionRecord]:
        self._seed_role_if_needed(role_key, permissions)
        return self._store_by_role[role_key]

    async def list(
        self,
        *,
        role_key: str,
        permissions: list[tuple[str, str]] | set[tuple[str, str]],
        offset: int = 0,
        limit: int = 50,
    ) -> DashboardQuickActionListEnvelopeDTO:
        normalized_permissions = self._permissions_set(permissions)
        items = self._role_items(role_key, normalized_permissions)
        sliced = items[offset : offset + limit]
        return DashboardQuickActionListEnvelopeDTO(
            items=[self._to_dto(item) for item in sliced],
            meta=ListMetaDTO(total=len(items), offset=offset, limit=limit),
        )

    async def create(
        self,
        *,
        role_key: str,
        payload: DashboardQuickActionCreateDTO,
        permissions: list[tuple[str, str]] | set[tuple[str, str]],
    ) -> DashboardQuickActionCreateEnvelopeDTO:
        normalized_permissions = self._permissions_set(permissions)
        self._check_permission(payload.resource, payload.action, normalized_permissions)
        items = self._role_items(role_key, normalized_permissions)

        next_id = self._next_id_by_role.get(role_key, 1)
        now = self._now()
        created = _QuickActionRecord(
            id=next_id,
            label=payload.label,
            resource=payload.resource,
            action=payload.action,
            to=payload.to,
            icon=payload.icon,
            created_at=now,
            updated_at=now,
        )
        items.insert(0, created)
        self._next_id_by_role[role_key] = next_id + 1

        return DashboardQuickActionCreateEnvelopeDTO(
            data=self._to_dto(created),
            meta=ActionMetaDTO(operation="create"),
        )

    async def update(
        self,
        *,
        role_key: str,
        quick_action_id: int,
        payload: DashboardQuickActionUpdateDTO,
        permissions: list[tuple[str, str]] | set[tuple[str, str]],
    ) -> DashboardQuickActionUpdateEnvelopeDTO:
        normalized_permissions = self._permissions_set(permissions)
        items = self._role_items(role_key, normalized_permissions)

        record = next((item for item in items if item.id == quick_action_id), None)
        if record is None:
            raise NotFoundError(f"Quick action {quick_action_id} was not found.")

        next_values: dict[str, Any] = payload.model_dump(exclude_none=True)
        next_resource = str(next_values.get("resource", record.resource))
        next_action = str(next_values.get("action", record.action))
        self._check_permission(next_resource, next_action, normalized_permissions)

        if "label" in next_values:
            record.label = str(next_values["label"])
        if "resource" in next_values:
            record.resource = next_resource
        if "action" in next_values:
            record.action = next_action
        if "to" in next_values:
            record.to = str(next_values["to"])
        if "icon" in next_values:
            record.icon = str(next_values["icon"])
        record.updated_at = self._now()

        return DashboardQuickActionUpdateEnvelopeDTO(
            data=self._to_dto(record),
            meta=ActionMetaDTO(operation="update"),
        )

    async def delete(
        self,
        *,
        role_key: str,
        quick_action_id: int,
        permissions: list[tuple[str, str]] | set[tuple[str, str]],
    ) -> bool:
        normalized_permissions = self._permissions_set(permissions)
        items = self._role_items(role_key, normalized_permissions)

        index = next((idx for idx, item in enumerate(items) if item.id == quick_action_id), None)
        if index is None:
            raise NotFoundError(f"Quick action {quick_action_id} was not found.")

        del items[index]
        return True
