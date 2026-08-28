"""Validated external mapping contract for the legacy ETL."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DEFAULT_MAPPING_PATH = Path(__file__).resolve().parents[1] / "config" / "legacy_etl_mapping.json"


class MappingConfigError(ValueError):
    """Raised when the external ETL mapping is unsafe or inconsistent."""


def identifier(value: object, path: str) -> str:
    text = str(value or "")
    if not IDENTIFIER_RE.fullmatch(text):
        raise MappingConfigError(f"{path}: invalid SQL identifier {text!r}")
    return text


def quote_identifier(value: str) -> str:
    """Quote an identifier that has already passed strict validation."""

    return f'"{identifier(value, "SQL identifier")}"'


@dataclass(frozen=True)
class ExtraColumn:
    source: str
    target: str
    transform: str = "raw"


@dataclass(frozen=True)
class EntityMapping:
    key: str
    enabled: bool
    source_table: str | None
    target_table: str
    source_columns: dict[str, str] = field(default_factory=dict)
    target_columns: dict[str, str] = field(default_factory=dict)
    extra_columns: tuple[ExtraColumn, ...] = ()

    def source_column(self, logical_name: str) -> str | None:
        return self.source_columns.get(logical_name)

    def target_column(self, logical_name: str) -> str | None:
        return self.target_columns.get(logical_name)


@dataclass(frozen=True)
class GenericEntityMapping:
    key: str
    enabled: bool
    source_table: str
    target_table: str
    source_pk: str
    target_pk: str
    id_strategy: str
    columns: tuple[ExtraColumn, ...]


@dataclass(frozen=True)
class MappingConfig:
    version: int
    source_schema: str
    batch_size: int
    entities: dict[str, EntityMapping]
    generic_entities: tuple[GenericEntityMapping, ...]
    lab_codes: dict[str, str]
    statuses: dict[int, str]
    roles: dict[int, str]
    target_aliases: dict[str, str]

    def entity(self, key: str) -> EntityMapping:
        try:
            return self.entities[key]
        except KeyError as exc:
            raise MappingConfigError(f"entities.{key}: mapping is missing") from exc

    def enabled(self, key: str) -> bool:
        entity = self.entities.get(key)
        return entity is not None and entity.enabled


DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "users": ("roles",),
    "protocols": ("conclusions", "protocol_types"),
    "directions": ("doctors", "objects"),
    "samples": ("directions", "sample_types", "sample_statuses"),
    "research": ("samples", "research_goals", "research_statuses"),
    "tests": ("research", "test_statuses"),
    "sample_labs": ("samples", "labs"),
}


def _dict(value: object, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MappingConfigError(f"{path}: expected object")
    return {str(key): item for key, item in value.items()}


def _columns(value: object, path: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for logical_name, physical_name in _dict(value or {}, path).items():
        identifier(logical_name, f"{path}.{logical_name}")
        result[logical_name] = identifier(physical_name, f"{path}.{logical_name}")
    return result


def _extra_columns(value: object, path: str) -> tuple[ExtraColumn, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise MappingConfigError(f"{path}: expected array")
    result: list[ExtraColumn] = []
    for index, raw in enumerate(value):
        item = _dict(raw, f"{path}[{index}]")
        transform = str(item.get("transform", "raw"))
        if transform not in {"raw", "text", "int", "bool", "datetime_utc"}:
            raise MappingConfigError(f"{path}[{index}].transform: unsupported {transform!r}")
        result.append(
            ExtraColumn(
                source=identifier(item.get("source"), f"{path}[{index}].source"),
                target=identifier(item.get("target"), f"{path}[{index}].target"),
                transform=transform,
            )
        )
    return tuple(result)


def _load_entities(value: object) -> dict[str, EntityMapping]:
    result: dict[str, EntityMapping] = {}
    for key, raw in _dict(value, "entities").items():
        identifier(key, f"entities.{key}")
        item = _dict(raw, f"entities.{key}")
        source_raw = item.get("source_table")
        result[key] = EntityMapping(
            key=key,
            enabled=bool(item.get("enabled", True)),
            source_table=(
                identifier(source_raw, f"entities.{key}.source_table")
                if source_raw is not None
                else None
            ),
            target_table=identifier(item.get("target_table"), f"entities.{key}.target_table"),
            source_columns=_columns(
                item.get("source_columns", {}), f"entities.{key}.source_columns"
            ),
            target_columns=_columns(
                item.get("target_columns", {}), f"entities.{key}.target_columns"
            ),
            extra_columns=_extra_columns(
                item.get("extra_columns"), f"entities.{key}.extra_columns"
            ),
        )
    return result


def _load_generic_entities(value: object) -> tuple[GenericEntityMapping, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise MappingConfigError("generic_entities: expected array")
    result: list[GenericEntityMapping] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        path = f"generic_entities[{index}]"
        item = _dict(raw, path)
        key = identifier(item.get("key"), f"{path}.key")
        if key in seen:
            raise MappingConfigError(f"{path}.key: duplicate {key!r}")
        seen.add(key)
        strategy = str(item.get("id_strategy", "uuid5"))
        if strategy not in {"uuid5", "raw"}:
            raise MappingConfigError(f"{path}.id_strategy: expected 'uuid5' or 'raw'")
        result.append(
            GenericEntityMapping(
                key=key,
                enabled=bool(item.get("enabled", True)),
                source_table=identifier(item.get("source_table"), f"{path}.source_table"),
                target_table=identifier(item.get("target_table"), f"{path}.target_table"),
                source_pk=identifier(item.get("source_pk", "id"), f"{path}.source_pk"),
                target_pk=identifier(item.get("target_pk", "id"), f"{path}.target_pk"),
                id_strategy=strategy,
                columns=_extra_columns(item.get("columns", []), f"{path}.columns"),
            )
        )
    return tuple(result)


def load_mapping(path: Path) -> MappingConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MappingConfigError(f"mapping file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise MappingConfigError(f"{path}:{exc.lineno}:{exc.colno}: invalid JSON") from exc

    root = _dict(raw, "root")
    version = int(root.get("version", 0))
    if version != 1:
        raise MappingConfigError(f"version: expected 1, got {version}")
    batch_size = int(root.get("batch_size", 2000))
    if batch_size <= 0:
        raise MappingConfigError("batch_size: must be positive")

    value_maps = _dict(root.get("value_maps", {}), "value_maps")
    entities = _load_entities(root.get("entities"))
    config = MappingConfig(
        version=version,
        source_schema=identifier(root.get("source_schema"), "source_schema"),
        batch_size=batch_size,
        entities=entities,
        generic_entities=_load_generic_entities(root.get("generic_entities", [])),
        lab_codes={
            str(key).casefold(): str(item)
            for key, item in _dict(value_maps.get("labs", {}), "value_maps.labs").items()
        },
        statuses={
            int(key): str(item)
            for key, item in _dict(value_maps.get("statuses", {}), "value_maps.statuses").items()
        },
        roles={
            int(key): str(item)
            for key, item in _dict(value_maps.get("roles", {}), "value_maps.roles").items()
        },
        target_aliases={
            str(key).casefold(): str(item)
            for key, item in _dict(
                value_maps.get("target_aliases", {}), "value_maps.target_aliases"
            ).items()
        },
    )
    _validate_dependencies(config)
    return config


def _validate_dependencies(config: MappingConfig) -> None:
    for entity_key, dependencies in DEPENDENCIES.items():
        if not config.enabled(entity_key):
            continue
        missing = [dependency for dependency in dependencies if not config.enabled(dependency)]
        if missing:
            joined = ", ".join(missing)
            raise MappingConfigError(
                f"entities.{entity_key}: enabled but dependencies are disabled: {joined}"
            )
