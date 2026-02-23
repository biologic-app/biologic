from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import BaseModel

from src.core.errors import BadRequestError, NotFoundError
from src.repositories.crud_repository import SortOrder
from src.schemas import BranchReadDTO
from src.schemas.base import EntityRefDTO
from src.services.crud_service import CRUDService


def _entity_from_read_model(read_model: BranchReadDTO) -> SimpleNamespace:
    return SimpleNamespace(**read_model.model_dump())


def _build_service(
    repository: object,
    read_model: BranchReadDTO,
) -> CRUDService[object, BranchReadDTO]:
    return CRUDService(
        repository=repository,
        read_schema=BranchReadDTO,
        allowed_sort_fields={"created_at", "name"},
        not_found_message="Branch {entity_id} was not found.",
    )


@pytest.fixture
def sample_read_model() -> BranchReadDTO:
    return BranchReadDTO(
        id=uuid4(),
        code="b-1",
        name="Branch",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


async def test_crud_service_happy_path(sample_read_model: BranchReadDTO) -> None:
    entity = _entity_from_read_model(sample_read_model)
    repository = SimpleNamespace(
        create=AsyncMock(return_value=entity),
        get=AsyncMock(return_value=entity),
        list=AsyncMock(return_value=([entity], 1)),
        update=AsyncMock(return_value=entity),
        soft_delete_with_reason=AsyncMock(return_value=True),
    )

    service = _build_service(repository, sample_read_model)

    created = await service.create({"code": "b-1", "name": "Branch"})
    fetched = await service.get(sample_read_model.id)
    items, meta = await service.list(
        offset=0,
        limit=15,
        sort_by="created_at",
        sort_order="desc",
    )
    updated = await service.update(sample_read_model.id, {"name": "Updated"})
    await service.delete(sample_read_model.id, reason="cleanup")

    assert created == sample_read_model
    assert fetched == sample_read_model
    assert items == [sample_read_model]
    assert meta.total == 1
    assert updated == sample_read_model


async def test_crud_service_get_update_not_found(sample_read_model: BranchReadDTO) -> None:
    repository = SimpleNamespace(
        create=AsyncMock(),
        get=AsyncMock(return_value=None),
        list=AsyncMock(),
        update=AsyncMock(return_value=None),
        soft_delete_with_reason=AsyncMock(return_value=False),
    )
    service = _build_service(repository, sample_read_model)

    with pytest.raises(NotFoundError):
        await service.get(uuid4())

    with pytest.raises(NotFoundError):
        await service.update(uuid4(), {"name": "Updated"})

    with pytest.raises(NotFoundError):
        await service.delete(uuid4())


async def test_crud_service_bad_request_branches(sample_read_model: BranchReadDTO) -> None:
    entity = _entity_from_read_model(sample_read_model)
    repository = SimpleNamespace(
        create=AsyncMock(return_value=entity),
        get=AsyncMock(return_value=entity),
        list=AsyncMock(side_effect=ValueError("invalid filter")),
        update=AsyncMock(return_value=entity),
        soft_delete_with_reason=AsyncMock(side_effect=ValueError("invalid reason")),
    )
    service = _build_service(repository, sample_read_model)

    with pytest.raises(BadRequestError):
        await service.list(offset=0, limit=15, sort_by="bad", sort_order="desc")

    with pytest.raises(BadRequestError):
        await service.list(
            offset=0,
            limit=15,
            sort_by="created_at",
            sort_order="desc",
            exact_filters={"code": "x"},
        )

    with pytest.raises(BadRequestError):
        await service.delete(uuid4(), reason="bad")


def test_crud_service_sort_order_type_alias() -> None:
    order: SortOrder = "asc"
    assert order == "asc"


class _IncludeReadModel(BaseModel):
    id: object
    role_id: object | None = None
    branch_id: object | None = None
    role: EntityRefDTO | None = None
    branch: EntityRefDTO | None = None


async def test_crud_service_expand_includes_single_item() -> None:
    role_id = uuid4()
    item = _IncludeReadModel(id=uuid4(), role_id=role_id)
    role_ref = EntityRefDTO(id=role_id, name="Role", code="R")
    repository = SimpleNamespace(
        resolve_include_reference=AsyncMock(return_value=role_ref),
    )
    service: CRUDService[object, _IncludeReadModel] = CRUDService(
        repository=repository,
        read_schema=_IncludeReadModel,
        allowed_sort_fields={"id"},
        not_found_message="Not found.",
    )

    expanded = await service.expand_includes(item, ["role"])
    assert expanded.role == role_ref
    repository.resolve_include_reference.assert_awaited_once_with("role", role_id)


async def test_crud_service_expand_includes_many_batch_lookup() -> None:
    role_id = uuid4()
    branch_id = uuid4()
    role_ref = EntityRefDTO(id=role_id, name="Role", code="R")
    branch_ref = EntityRefDTO(id=branch_id, name="Branch", code="B")
    items = [
        _IncludeReadModel(id=uuid4(), role_id=role_id, branch_id=branch_id),
        _IncludeReadModel(id=uuid4(), role_id=role_id, branch_id=None),
    ]
    repository = SimpleNamespace(
        resolve_include_references=AsyncMock(
            side_effect=[{role_id: role_ref}, {branch_id: branch_ref}]
        ),
    )
    service: CRUDService[object, _IncludeReadModel] = CRUDService(
        repository=repository,
        read_schema=_IncludeReadModel,
        allowed_sort_fields={"id"},
        not_found_message="Not found.",
    )

    expanded = await service.expand_includes_many(items, ["role", "branch"])
    assert expanded[0].role == role_ref
    assert expanded[0].branch == branch_ref
    assert expanded[1].role == role_ref
    assert expanded[1].branch is None
    assert repository.resolve_include_references.await_count == 2
