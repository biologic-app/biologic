from __future__ import annotations

import pytest

from src.core.errors import ForbiddenError, NotFoundError
from src.schemas.dashboard import DashboardQuickActionCreateDTO, DashboardQuickActionUpdateDTO
from src.services.dashboard_service import DashboardQuickActionsService


async def test_dashboard_service_seeds_role_defaults_by_permissions() -> None:
    service = DashboardQuickActionsService()

    response = await service.list(
        role_key="admin",
        permissions={("objects", "create"), ("samples", "view"), ("users", "view")},
    )

    assert response.meta.total == 3
    assert [item.resource for item in response.items] == ["objects", "samples", "users"]


async def test_dashboard_service_create_requires_permission() -> None:
    service = DashboardQuickActionsService()

    with pytest.raises(ForbiddenError):
        await service.create(
            role_key="doctor",
            payload=DashboardQuickActionCreateDTO(
                label="Пользователи",
                resource="users",
                action="view",
                to="/admin/users",
                icon="pi pi-users",
            ),
            permissions={("directions", "view")},
        )


async def test_dashboard_service_update_and_delete() -> None:
    service = DashboardQuickActionsService()
    permissions = {("objects", "create"), ("objects", "view")}

    created = await service.create(
        role_key="admin",
        payload=DashboardQuickActionCreateDTO(
            label="Создать объект",
            resource="objects",
            action="create",
            to="/objects#create",
            icon="pi pi-cog",
        ),
        permissions=permissions,
    )

    updated = await service.update(
        role_key="admin",
        quick_action_id=created.data.id,
        payload=DashboardQuickActionUpdateDTO(
            label="Создать новый объект",
            action="view",
            to="/objects",
        ),
        permissions=permissions,
    )

    assert updated.data.label == "Создать новый объект"
    assert updated.data.action == "view"
    assert updated.data.to == "/objects"

    deleted = await service.delete(
        role_key="admin",
        quick_action_id=created.data.id,
        permissions=permissions,
    )

    assert deleted is True

    with pytest.raises(NotFoundError):
        await service.delete(
            role_key="admin",
            quick_action_id=created.data.id,
            permissions=permissions,
        )
