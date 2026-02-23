from __future__ import annotations

from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.core.errors import NotFoundError, ValidationError
from src.schemas.common import PageMeta
from tests._helpers import STEM_TO_ENTITY, build_contract_bundle

STANDARD_SERVICE_STEMS = sorted(stem for stem in STEM_TO_ENTITY if stem not in {"role_permissions"})


class _FakeCRUD:
    def __init__(self, read_data: object) -> None:
        self._read_data = read_data
        self.last_delete_reason: str | None = None

    async def create(self, _values: object) -> object:
        return self._read_data

    async def get(self, _entity_id: object) -> object:
        return self._read_data

    async def expand_includes(self, data: object, includes: list[str]) -> object:
        if not includes or not hasattr(data, "model_copy"):
            return data
        model_fields = getattr(data.__class__, "model_fields", {})
        updates = {include: None for include in includes if include in model_fields}
        return data.model_copy(update=updates) if updates else data

    async def expand_includes_many(self, items: list[object], includes: list[str]) -> list[object]:
        return [await self.expand_includes(item, includes) for item in items]

    async def list(
        self, *, offset: int, limit: int, **_kwargs: object
    ) -> tuple[list[object], PageMeta]:
        return [self._read_data], PageMeta(
            total=1,
            offset=offset,
            limit=limit,
        )

    async def update(self, _entity_id: object, _values: object) -> object:
        return self._read_data

    async def delete(self, _entity_id: object, *, reason: str | None = None) -> None:
        self.last_delete_reason = reason


@pytest.mark.parametrize("stem", STANDARD_SERVICE_STEMS)
async def test_standard_services_crud_flow(stem: str) -> None:
    entity = STEM_TO_ENTITY[stem]
    module = import_module(f"src.services.{stem}_service")
    service_cls = getattr(module, f"{entity}Service")

    bundle = build_contract_bundle(stem)
    repository = SimpleNamespace(
        allowed_includes=set(),
        resolve_include_reference=AsyncMock(return_value=None),
        resolve_include_references=AsyncMock(return_value={}),
    )
    service = service_cls(repository=repository)
    fake_crud = _FakeCRUD(read_data=bundle["read_data"])
    service._crud = fake_crud

    create_response = await service.create(bundle["create_payload"])
    get_response = await service.get(uuid4())
    list_response = await service.list(offset=0, limit=15, sort_by="created_at", sort_order="desc")
    update_response = await service.update(uuid4(), bundle["update_payload"])
    delete_response = await service.delete(uuid4(), reason="cleanup")

    repository.allowed_includes = {"fake"}
    include_response = await service.get(uuid4(), includes=["fake"])
    with pytest.raises(ValidationError):
        await service.get(uuid4(), includes=["missing"])

    assert create_response.meta.operation == "create"
    assert get_response.data == bundle["read_data"]
    assert include_response.meta.includes == ["fake"]
    assert list_response.meta.total == 1
    assert update_response.meta.operation == "update"
    assert delete_response.meta.deleted is True
    assert fake_crud.last_delete_reason == "cleanup"


async def test_standard_service_invalid_include_raises() -> None:
    from src.services.branches_service import BranchService

    service = BranchService(
        repository=SimpleNamespace(
            allowed_includes={"role"},
            resolve_include_reference=AsyncMock(return_value=None),
            resolve_include_references=AsyncMock(return_value={}),
        )
    )
    service._crud = _FakeCRUD(read_data=build_contract_bundle("branches")["read_data"])

    with pytest.raises(ValidationError):
        await service.get(uuid4(), includes=["unknown"])


async def test_lab_service_include_expansion() -> None:
    from src.services.labs_service import LabService

    bundle = build_contract_bundle("labs")
    lab_read = bundle["read_data"].model_copy(update={"branch_id": uuid4()})
    service = LabService(
        repository=SimpleNamespace(
            allowed_includes={"branch"},
            resolve_include_reference=AsyncMock(return_value=None),
            resolve_include_references=AsyncMock(return_value={}),
        )
    )
    service._crud = _FakeCRUD(read_data=lab_read)

    response = await service.get(uuid4(), includes=["branch"])

    assert response.meta.includes == ["branch"]
    assert response.data.branch is None


async def test_role_permissions_service_flow_and_errors() -> None:
    from src.services.role_permissions_service import RolePermissionService

    bundle = build_contract_bundle("role_permissions")
    role_permission_data = bundle["read_data"]
    entity = SimpleNamespace(**role_permission_data.model_dump())

    repository = SimpleNamespace(
        allowed_includes={"fake"},
        resolve_include_reference=AsyncMock(return_value=None),
        resolve_include_references=AsyncMock(return_value={}),
        get_by_pk=AsyncMock(return_value=entity),
        update_by_pk=AsyncMock(return_value=entity),
        delete_by_pk=AsyncMock(return_value=True),
    )
    service = RolePermissionService(repository=repository)
    service._crud = _FakeCRUD(read_data=role_permission_data)

    create_response = await service.create(bundle["create_payload"])
    get_response = await service.get(uuid4(), "sample", "read")
    include_response = await service.get(uuid4(), "sample", "read", includes=["fake"])
    list_response = await service.list(offset=0, limit=15)
    update_response = await service.update(uuid4(), "sample", "read", bundle["update_payload"])
    delete_response = await service.delete(uuid4(), "sample", "read", reason="cleanup")

    assert create_response.meta.operation == "create"
    assert get_response.data == role_permission_data
    assert include_response.meta.includes == ["fake"]
    assert list_response.meta.total == 1
    assert update_response.meta.operation == "update"
    assert delete_response.meta.deleted is True

    with pytest.raises(ValidationError):
        await service.get(uuid4(), "sample", "read", includes=["bad"])

    repository.get_by_pk = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError):
        await service.get(uuid4(), "sample", "read")
