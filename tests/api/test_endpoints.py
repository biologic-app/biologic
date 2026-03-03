from __future__ import annotations

from importlib import import_module
from uuid import uuid4

import pytest
from starlette.requests import Request

from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.api.v1.endpoints.health import health_check
from src.schemas.base import DeleteRequestDTO
from tests._helpers import build_contract_bundle, endpoint_stems


def make_request(query_string: str = "") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/resources",
        "headers": [],
        "query_string": query_string.encode(),
    }
    return Request(scope)


class _FakeEndpointService:
    def __init__(self, bundle: dict[str, object]) -> None:
        self.bundle = bundle

    async def create(self, _payload: object) -> object:
        return self.bundle["create_envelope"]

    async def get(self, *args: object, **kwargs: object) -> object:
        return self.bundle["read_envelope"]

    async def list(self, *args: object, **kwargs: object) -> object:
        return self.bundle["list_envelope"]

    async def update(self, *args: object, **kwargs: object) -> object:
        return self.bundle["update_envelope"]

    async def delete(self, *args: object, **kwargs: object) -> object:
        return self.bundle["delete_envelope"]


@pytest.mark.parametrize("stem", endpoint_stems())
async def test_endpoint_module_crud_handlers(stem: str) -> None:
    module = import_module(f"src.api.v1.endpoints.{stem}")
    bundle = build_contract_bundle(stem)
    service = _FakeEndpointService(bundle)

    create_fn = getattr(module, f"create_{stem}")
    get_fn = getattr(module, f"get_{stem}")
    list_fn = getattr(module, f"list_{stem}")
    update_fn = getattr(module, f"update_{stem}")
    delete_fn = getattr(module, f"delete_{stem}")

    created = await create_fn(payload=bundle["create_payload"], service=service)

    fetched = await get_fn(entity_id=uuid4(), include="role,branch", service=service)
    updated = await update_fn(
        entity_id=uuid4(),
        payload=bundle["update_payload"],
        service=service,
    )
    deleted = await delete_fn(
        entity_id=uuid4(),
        payload=DeleteRequestDTO(reason="cleanup"),
        service=service,
    )

    listed = await list_fn(
        request=make_request("code=X&created_at_from=2025-01-01T00:00:00Z"),
        service=service,
        offset=0,
        limit=15,
        sort_by="created_at",
        sort_order="desc",
        include="role",
    )

    assert created == bundle["create_envelope"]
    assert fetched == bundle["read_envelope"]
    assert listed == bundle["list_envelope"]
    assert updated == bundle["update_envelope"]
    assert deleted == bundle["delete_envelope"]


async def test_health_endpoint() -> None:
    response = await health_check()
    assert response.status == "ok"


def test_endpoint_helper_parsers() -> None:
    assert parse_includes(None) == []
    assert parse_includes("role, branch") == ["role", "branch"]

    exact, ranges = parse_list_filters(
        {
            "offset": "0",
            "limit": "10",
            "sort_by": "created_at",
            "sort_order": "desc",
            "include": "role",
            "code": "X",
            "created_at_from": "2025-01-01T00:00:00Z",
            "created_at_to": "2025-01-31T00:00:00Z",
        }
    )

    assert exact == {"code": "X"}
    assert ranges == {"created_at": ("2025-01-01T00:00:00Z", "2025-01-31T00:00:00Z")}
