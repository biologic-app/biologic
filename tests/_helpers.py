from __future__ import annotations

import inspect
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, get_args, get_origin
from uuid import UUID, uuid4

from pydantic import BaseModel

import src.schemas as contracts
from src.schemas.base import ActionMetaDTO, DeleteMetaDTO, ListMetaDTO, ReadMetaDTO

STEM_TO_ENTITY: dict[str, str] = {
    "branches": "Branch",
    "change_log": "ChangeLog",
    "conclusions": "Conclusion",
    "direction_statuses": "DirectionStatus",
    "directions": "Direction",
    "doctors": "Doctor",
    "indicators": "Indicator",
    "labs": "Lab",
    "objects": "Object",
    "permissions": "Permission",
    "protocol_types": "ProtocolType",
    "protocols": "Protocol",
    "research": "Research",
    "research_goals": "ResearchGoal",
    "research_statuses": "ResearchStatus",
    "role_permissions": "RolePermission",
    "roles": "Role",
    "sample_statuses": "SampleStatus",
    "sample_types": "SampleType",
    "samples": "Sample",
    "test_statuses": "TestStatus",
    "tests": "Test",
    "user_scopes": "UserScope",
    "users": "User",
}


def endpoint_stems() -> list[str]:
    stems: list[str] = []
    for path in sorted(Path("src/api/v1/endpoints").glob("*.py")):
        stem = path.stem
        if stem in {"__init__", "_helpers", "health", "auth", "dashboard"}:
            continue
        stems.append(stem)
    return stems


def _strip_annotated(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is None:
        return annotation
    if str(origin) == "<class 'typing.Annotated'>":
        return get_args(annotation)[0]
    return annotation


def build_value(annotation: Any, field_name: str = "value", *, depth: int = 0) -> Any:
    if depth > 5:
        return None

    annotation = _strip_annotated(annotation)

    if annotation in {Any, object}:
        return f"{field_name}_value"

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is not None:
        origin_name = getattr(origin, "__name__", str(origin))
        if origin_name in {"Union", "types.UnionType"}:
            non_none_args = [arg for arg in args if arg is not type(None)]
            if not non_none_args:
                return None
            return build_value(non_none_args[0], field_name, depth=depth + 1)
        if origin_name == "Literal":
            return args[0]
        if origin in {list, tuple, set, frozenset}:
            item_type = args[0] if args else str
            item = build_value(item_type, f"{field_name}_item", depth=depth + 1)
            if origin is tuple:
                return (item,)
            if origin is set:
                return {item}
            if origin is frozenset:
                return frozenset({item})
            return [item]
        if origin is dict:
            key = "k"
            value_type = args[1] if len(args) > 1 else str
            return {key: build_value(value_type, f"{field_name}_value", depth=depth + 1)}

    if inspect.isclass(annotation):
        if issubclass(annotation, BaseModel):
            return build_model_instance(annotation, depth=depth + 1)
        if issubclass(annotation, Enum):
            return next(iter(annotation))

    if annotation is bool:
        return True
    if annotation is int:
        return 1
    if annotation is float:
        return 1.5
    if annotation is str:
        return f"{field_name}_value"
    if annotation is UUID:
        return uuid4()
    if annotation is datetime:
        return datetime.now(UTC)
    if annotation is date:
        return datetime.now(UTC).date()

    return f"{field_name}_value"


def build_model_instance(model_cls: type[BaseModel], *, depth: int = 0) -> BaseModel:
    values: dict[str, Any] = {}
    for field_name, field_info in model_cls.model_fields.items():
        if not field_info.is_required():
            continue
        values[field_name] = build_value(field_info.annotation, field_name, depth=depth + 1)
    return model_cls(**values)


def build_contract_bundle(stem: str) -> dict[str, Any]:
    entity = STEM_TO_ENTITY[stem]
    create_dto_cls = getattr(contracts, f"{entity}CreateDTO")
    update_dto_cls = getattr(contracts, f"{entity}UpdateDTO")
    read_dto_cls = getattr(contracts, f"{entity}ReadDTO")
    list_read_dto_cls = getattr(contracts, f"{entity}ListReadDTO", read_dto_cls)

    create_payload = build_model_instance(create_dto_cls)
    update_payload = build_model_instance(update_dto_cls)
    read_data = build_model_instance(read_dto_cls)
    list_item = build_model_instance(list_read_dto_cls)

    create_envelope_cls = getattr(contracts, f"{entity}CreateEnvelopeDTO")
    read_envelope_cls = getattr(contracts, f"{entity}ReadEnvelopeDTO")
    list_envelope_cls = getattr(contracts, f"{entity}ListEnvelopeDTO")
    update_envelope_cls = getattr(contracts, f"{entity}UpdateEnvelopeDTO")
    delete_envelope_cls = getattr(contracts, f"{entity}DeleteEnvelopeDTO")

    return {
        "create_payload": create_payload,
        "update_payload": update_payload,
        "read_data": read_data,
        "create_envelope": create_envelope_cls(
            data=read_data,
            meta=ActionMetaDTO(operation="create"),
        ),
        "read_envelope": read_envelope_cls(
            data=read_data,
            meta=ReadMetaDTO(),
        ),
        "list_envelope": list_envelope_cls(
            items=[list_item],
            meta=ListMetaDTO(total=1, offset=0, limit=15),
        ),
        "update_envelope": update_envelope_cls(
            data=read_data,
            meta=ActionMetaDTO(operation="update"),
        ),
        "delete_envelope": delete_envelope_cls(
            meta=DeleteMetaDTO(operation="soft_delete", deleted=True),
        ),
    }
