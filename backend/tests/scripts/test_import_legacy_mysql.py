import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from scripts import import_legacy_mysql
from scripts.import_legacy_mysql import (
    bool_value,
    configured_values,
    ident,
    normalize_target,
    source_select,
    split_name,
    utc,
)
from scripts.legacy_etl_mapping import (
    DEFAULT_MAPPING_PATH,
    MappingConfigError,
    load_mapping,
)


def test_ident_is_stable_and_namespaced_by_source_table() -> None:
    assert ident("obrs", 42) == ident("obrs", 42)
    assert ident("obrs", 42) != ident("results", 42)


def test_legacy_scalar_conversions() -> None:
    assert bool_value(1) is True
    assert bool_value("0") is False
    assert utc("2024-01-02 03:04:05") == datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC)
    assert utc(None) is None


def test_target_combinations_are_normalized_without_losing_order_or_duplicates() -> None:
    assert normalize_target(" БАК, тх, РВ, бак ") == "бак,т/х,РВ"
    assert normalize_target(None) == ""


def test_name_split_keeps_one_token_in_required_name_field() -> None:
    assert split_name("Иванов Иван Иванович") == ("Иванов", "Иван", "Иванович")
    assert split_name("Иванов Иван") == ("Иванов", "Иван", None)
    assert split_name("Иван") == ("Иван", None, None)


def write_mapping(tmp_path: Path, mutate: Callable[[dict[str, Any]], None] | None = None) -> Path:
    raw: dict[str, Any] = json.loads(DEFAULT_MAPPING_PATH.read_text(encoding="utf-8"))
    if mutate is not None:
        mutate(raw)
    path = tmp_path / "mapping.json"
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return path


def test_mapping_can_rename_tables_and_remove_target_attributes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def mutate(raw: dict[str, Any]) -> None:
        entities = raw["entities"]
        objects = entities["objects"]
        objects["source_table"] = "legacy_objects_v2"
        objects["target_table"] = "objects_v2"
        target_columns = objects["target_columns"]
        target_columns["code"] = "legacy_code"
        target_columns.pop("address")

    config = load_mapping(write_mapping(tmp_path, mutate))
    monkeypatch.setattr(import_legacy_mysql, "MAPPING", config)

    query = source_select("objects", ("id", "name"))
    assert '"legacy_fast"."legacy_objects_v2"' in query
    values = configured_values(
        "objects", {"id": ident("objects", 1), "code": "X", "address": "hidden"}
    )
    assert values["legacy_code"] == "X"
    assert "address" not in values


def test_mapping_rejects_disabled_dependency(tmp_path: Path) -> None:
    def mutate(raw: dict[str, Any]) -> None:
        entities = raw["entities"]
        samples = entities["samples"]
        samples["enabled"] = False

    with pytest.raises(MappingConfigError, match="research.*samples"):
        load_mapping(write_mapping(tmp_path, mutate))


def test_mapping_rejects_unsafe_sql_identifier(tmp_path: Path) -> None:
    def mutate(raw: dict[str, Any]) -> None:
        entities = raw["entities"]
        users = entities["users"]
        users["target_table"] = "users; DROP TABLE users"

    with pytest.raises(MappingConfigError, match="invalid SQL identifier"):
        load_mapping(write_mapping(tmp_path, mutate))
