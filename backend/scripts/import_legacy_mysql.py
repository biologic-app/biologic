"""Idempotent ETL from the PostgreSQL staging copy of the MySQL 5.1 dump.

The dump is restored by pgloader into ``biologic_legacy_stage`` (schema
``legacy_fast``).  This script performs the semantic mapping into the
canonical ``biologic`` database.  It never deletes rows and defaults to a
read-only ``--dry-run``; pass ``--apply`` explicitly to write canonical data.

The source is deliberately PostgreSQL staging rather than MySQL: pgloader has
already converted cp1251 text and old MySQL scalar types, while this module is
responsible for the domain-level split/join and FK mapping.
"""

# SQL column lists are intentionally kept close to their INSERT statements;
# ruff's line-length rule is not useful for these executable SQL literals.
# ruff: noqa: E501

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

from scripts.legacy_etl_mapping import (
    DEFAULT_MAPPING_PATH,
    EntityMapping,
    GenericEntityMapping,
    MappingConfig,
    MappingConfigError,
    load_mapping,
    quote_identifier,
)
from src.core.config import get_settings
from src.core.security import hash_password

DEFAULT_SOURCE_DSN = os.getenv(
    "LEGACY_SOURCE_DATABASE_URL",
    "postgresql://biologic:biologic@127.0.0.1:5434/biologic_legacy_stage",
)
NAMESPACE = uuid.UUID("7e9a8af6-f5b4-4f05-89c1-f31ec7b6cf60")
BATCH_SIZE = 2_000
ROW_LIMIT: int | None = None
PROGRESS_TOTALS: dict[str, int] = {}
PROGRESS_COUNTS: dict[str, int] = {}
PROGRESS_LOG_PATH = Path(os.getenv("LEGACY_ETL_PROGRESS_LOG", "legacy_etl_progress.log"))


def report_progress(name: str, count: int) -> None:
    """Print row counters for long-running imports."""

    PROGRESS_COUNTS[name] = PROGRESS_COUNTS.get(name, 0) + count
    total = PROGRESS_TOTALS.get(name)
    suffix = f"/{total}" if total is not None else ""
    current = PROGRESS_COUNTS[name]
    # Single-row importers call this for every row; keep output usable while
    # still exposing a precise counter at regular intervals.
    if count > 1 or current % 1_000 == 0 or (total is not None and current == total):
        message = f"[ETL] {name}: {current}{suffix} rows"
        print(message, flush=True)
        with PROGRESS_LOG_PATH.open("a", encoding="utf-8") as progress_log:
            progress_log.write(message + "\n")
MAPPING: MappingConfig = load_mapping(DEFAULT_MAPPING_PATH)

LEGACY_ENTITY_ALIASES = {
    "podrs": "labs",
    "sandoctors": "doctors",
    "resobjects": "objects",
    "obr_types": "sample_types",
    "obrs": "samples",
    "poks": "indicators",
    "zakls": "conclusions",
    "naprs": "directions",
    "results": "research",
    "obr_targets": "obr_targets_audit",
}


def ident(table: str, source_id: object) -> uuid.UUID:
    """Generate a stable UUID for a legacy integer identity."""

    return uuid.uuid5(NAMESPACE, f"{table}:{source_id}")


def mapping() -> MappingConfig:
    return MAPPING


def entity(key: str) -> EntityMapping:
    return mapping().entity(LEGACY_ENTITY_ALIASES.get(key, key))


def bool_value(value: object) -> bool:
    return value is True or value == 1 or value == "1"


def utc(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or UTC)
    try:
        return datetime.fromisoformat(str(value)).replace(tzinfo=UTC)
    except ValueError:
        return None


def deleted_at(row: asyncpg.Record) -> datetime | None:
    if not bool_value(row.get("deleted")):
        return None
    return utc(row.get("updated_at")) or utc(row.get("created_at")) or datetime.now(UTC)


def clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def split_name(value: object) -> tuple[str, str | None, str | None]:
    """Return last name, first name and patronymic without guessing initials."""

    parts = (clean(value) or "").split()
    if len(parts) >= 3:
        return parts[0], parts[1], " ".join(parts[2:])
    if len(parts) == 2:
        return parts[0], parts[1], None
    if parts:
        # Keep a one-token value intact; the doctor importer promotes it to
        # ``first_name`` because that canonical column is mandatory.
        return parts[0], None, None
    return "Legacy user", None, None


def normalize_target(value: object) -> str:
    tokens: list[str] = []
    for raw in (clean(value) or "").split(","):
        token = clean(raw)
        if not token:
            continue
        canonical = mapping().target_aliases.get(token.casefold(), token)
        if canonical not in tokens:
            tokens.append(canonical)
    return ",".join(tokens)


def source_table(name: str) -> str:
    config = entity(name)
    if config.source_table is None:
        raise MappingConfigError(f"entities.{config.key}.source_table is required")
    return f"{quote_identifier(mapping().source_schema)}.{quote_identifier(config.source_table)}"


def target_table(name: str) -> str:
    return quote_identifier(entity(name).target_table)


def source_column(name: str, logical_name: str) -> str:
    config = entity(name)
    physical_name = config.source_column(logical_name)
    if physical_name is None:
        raise MappingConfigError(
            f"entities.{config.key}.source_columns.{logical_name}: mapping is required"
        )
    return quote_identifier(physical_name)


def target_column(name: str, logical_name: str) -> str:
    config = entity(name)
    physical_name = config.target_column(logical_name)
    if physical_name is None:
        raise MappingConfigError(
            f"entities.{config.key}.target_columns.{logical_name}: mapping is required"
        )
    return quote_identifier(physical_name)


def source_select(
    name: str,
    logical_fields: tuple[str, ...],
    *,
    distinct: bool = False,
    order_by: str | None = "id",
) -> str:
    config = entity(name)
    expressions: list[str] = []
    for logical_name in logical_fields:
        physical_name = config.source_column(logical_name)
        expression = "NULL" if physical_name is None else quote_identifier(physical_name)
        expressions.append(f"{expression} AS {quote_identifier(logical_name)}")
    for index, extra in enumerate(config.extra_columns):
        expressions.append(
            f"{quote_identifier(extra.source)} AS {quote_identifier(f'__extra_{index}')}"
        )
    distinct_sql = "DISTINCT " if distinct else ""
    query = f"SELECT {distinct_sql}{','.join(expressions)} FROM {source_table(name)}"
    if order_by is not None:
        physical_order = config.source_column(order_by)
        if physical_order is None:
            raise MappingConfigError(
                f"entities.{config.key}.source_columns.{order_by}: required for ordering"
            )
        query += f" ORDER BY {quote_identifier(physical_order)}"
    return query


def _transform_extra(value: object, transform: str) -> object:
    if value is None or transform == "raw":
        return value
    if transform == "text":
        return clean(value)
    if transform == "int":
        return int(str(value))
    if transform == "bool":
        return bool_value(value)
    if transform == "datetime_utc":
        return utc(value)
    raise MappingConfigError(f"unsupported extra column transform: {transform}")


def configured_values(
    name: str,
    logical_values: dict[str, object],
    source_row: asyncpg.Record | None = None,
) -> dict[str, object]:
    config = entity(name)
    result = {
        physical_name: logical_values[logical_name]
        for logical_name, physical_name in config.target_columns.items()
        if logical_name in logical_values
    }
    if source_row is not None:
        for index, extra in enumerate(config.extra_columns):
            result[extra.target] = _transform_extra(source_row[f"__extra_{index}"], extra.transform)
    return result


def insert_sql(name: str, columns: tuple[str, ...]) -> str:
    if not columns:
        raise MappingConfigError(f"entities.{entity(name).key}: no target columns selected")
    column_sql = ",".join(quote_identifier(column) for column in columns)
    placeholders = ",".join(f"${index}" for index in range(1, len(columns) + 1))
    return (
        f"INSERT INTO {target_table(name)}({column_sql}) "
        f"VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    )


async def insert_configured(
    target: asyncpg.Connection,
    name: str,
    logical_values: dict[str, object],
    source_row: asyncpg.Record | None = None,
) -> None:
    values = configured_values(name, logical_values, source_row)
    columns = tuple(values)
    await target.execute(insert_sql(name, columns), *(values[column] for column in columns))
    report_progress(name, 1)


async def insert_configured_batch(
    target: asyncpg.Connection,
    name: str,
    rows: list[dict[str, object]],
) -> None:
    if not rows:
        return
    columns = tuple(rows[0])
    if any(tuple(row) != columns for row in rows):
        raise MappingConfigError(f"entities.{entity(name).key}: batch columns differ")
    await target.executemany(
        insert_sql(name, columns),
        [tuple(row[column] for column in columns) for row in rows],
    )
    report_progress(name, len(rows))


async def target_rows(
    target: asyncpg.Connection, name: str, logical_fields: tuple[str, ...]
) -> list[asyncpg.Record]:
    selections = ",".join(
        f"{target_column(name, logical_name)} AS {quote_identifier(logical_name)}"
        for logical_name in logical_fields
    )
    return list(await target.fetch(f"SELECT {selections} FROM {target_table(name)}"))


async def target_id_by(
    target: asyncpg.Connection, name: str, logical_name: str, value: object
) -> uuid.UUID | None:
    result = await target.fetchval(
        f"SELECT {target_column(name, 'id')} FROM {target_table(name)} "
        f"WHERE {target_column(name, logical_name)}=$1",
        value,
    )
    return result if isinstance(result, uuid.UUID) else None


def require_uuid(value: object, context: str) -> uuid.UUID:
    if not isinstance(value, uuid.UUID):
        raise MappingConfigError(f"{context}: target UUID was not found")
    return value


async def target_statuses(target: asyncpg.Connection, name: str) -> dict[str, uuid.UUID]:
    return {row["code"]: row["id"] for row in await target_rows(target, name, ("id", "code"))}


async def count_rows(source: asyncpg.Connection, table: str) -> int:
    return int(await source.fetchval(f"SELECT count(*) FROM {source_table(table)}"))


def limited(query: str) -> str:
    """Apply the optional integration-test limit to an ordered source query."""

    return f"{query} LIMIT {ROW_LIMIT}" if ROW_LIMIT is not None else query


async def iter_source(source: asyncpg.Connection, query: str) -> AsyncIterator[asyncpg.Record]:
    """Stream source rows without materialising million-row tables in RAM."""

    async with source.transaction():
        async for row in source.cursor(limited(query), prefetch=BATCH_SIZE):
            yield row


async def ensure_import_schema(target: asyncpg.Connection) -> None:
    await target.execute("CREATE SCHEMA IF NOT EXISTS legacy_import")
    await target.execute(
        """
        CREATE TABLE IF NOT EXISTS legacy_import.id_map (
            source_table text NOT NULL,
            source_id text NOT NULL,
            target_table text NOT NULL,
            target_id uuid NOT NULL,
            PRIMARY KEY (source_table, source_id)
        )
        """
    )
    await target.execute(
        """
        CREATE TABLE IF NOT EXISTS legacy_import.warning (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            source_table text NOT NULL,
            source_id text,
            code text NOT NULL,
            detail text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


async def save_map(
    target: asyncpg.Connection,
    source_table_name: str,
    source_id: object,
    target_table_name: str,
    target_id: uuid.UUID,
) -> None:
    await target.execute(
        """
        INSERT INTO legacy_import.id_map(source_table, source_id, target_table, target_id)
        VALUES ($1,$2,$3,$4)
        ON CONFLICT (source_table, source_id) DO UPDATE
          SET target_table=EXCLUDED.target_table, target_id=EXCLUDED.target_id
        """,
        source_table_name,
        str(source_id),
        target_table_name,
        target_id,
    )


async def save_map_batch(
    target: asyncpg.Connection,
    source_table_name: str,
    target_table_name: str,
    rows: list[tuple[object, uuid.UUID]],
) -> None:
    if not rows:
        return
    await target.executemany(
        """
        INSERT INTO legacy_import.id_map(source_table, source_id, target_table, target_id)
        VALUES ($1,$2,$3,$4)
        ON CONFLICT (source_table, source_id) DO UPDATE
          SET target_table=EXCLUDED.target_table, target_id=EXCLUDED.target_id
        """,
        [
            (source_table_name, str(source_id), target_table_name, target_id)
            for source_id, target_id in rows
        ],
    )


async def warn(
    target: asyncpg.Connection,
    table: str,
    source_id: object,
    code: str,
    detail: str,
) -> None:
    await target.execute(
        """
        INSERT INTO legacy_import.warning(source_table,source_id,code,detail)
        SELECT $1,$2,$3,$4
        WHERE NOT EXISTS (
            SELECT 1 FROM legacy_import.warning
            WHERE source_table=$1
              AND source_id IS NOT DISTINCT FROM $2
              AND code=$3
              AND detail=$4
        )
        """,
        table,
        str(source_id),
        code,
        detail,
    )


async def target_roles(target: asyncpg.Connection) -> dict[str, uuid.UUID]:
    return {row["key"]: row["id"] for row in await target_rows(target, "roles", ("id", "key"))}


async def import_roles(target: asyncpg.Connection) -> dict[int, uuid.UUID]:
    roles = await target_roles(target)
    observer_id = roles.get("observer") or ident("roles", "observer")
    if "observer" not in roles:
        await insert_configured(
            target,
            "roles",
            {
                "id": observer_id,
                "key": "observer",
                "name": "Observer",
                "scope_type": "global",
                "is_system": False,
            },
        )
        roles = await target_roles(target)
        observer_id = roles["observer"]
    result: dict[int, uuid.UUID] = {}
    for legacy_type, key in mapping().roles.items():
        role_id = roles.get(key)
        if role_id is not None:
            result[legacy_type] = role_id
    return result


async def import_users(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    role_map: dict[int, uuid.UUID],
) -> dict[int, uuid.UUID]:
    result: dict[int, uuid.UUID] = {}
    existing = {
        row["username"]: row["id"] for row in await target_rows(target, "users", ("id", "username"))
    }
    reset_hash = hash_password(os.urandom(32).hex())
    rows = await source.fetch(
        limited(
            source_select(
                "users",
                (
                    "id",
                    "username",
                    "full_name",
                    "code",
                    "role_source_id",
                    "created_at",
                    "updated_at",
                    "deleted",
                ),
            )
        )
    )
    for row in rows:
        username = clean(row["username"]) or f"legacy_{row['id']}"
        target_id = existing.get(username)
        if target_id is None:
            target_id = ident("users", row["id"])
            role_id = role_map.get(int(row["role_source_id"]), role_map.get(7))
            if role_id is None:
                await warn(target, "users", row["id"], "missing_role", "No role mapping")
                continue
            last_name, first_name, patronymic = split_name(row["full_name"])
            await insert_configured(
                target,
                "users",
                {
                    "id": target_id,
                    "username": username,
                    "password_hash": reset_hash,
                    "token_version": 0,
                    "status": "blocked",
                    "code": clean(row["code"]),
                    "first_name": first_name,
                    "last_name": last_name,
                    "patronymic": patronymic,
                    "role_id": role_id,
                    "created_at": utc(row["created_at"]) or datetime.now(UTC),
                    "updated_at": utc(row["updated_at"]) or datetime.now(UTC),
                    "deleted_at": deleted_at(row),
                },
                row,
            )
            target_id = require_uuid(
                await target_id_by(target, "users", "username", username),
                f"users.username={username}",
            )
            await warn(
                target,
                "users",
                row["id"],
                "password_reset",
                "Legacy SHA-1 replaced; reset required",
            )
        result[int(row["id"])] = target_id
        await save_map(target, "users", row["id"], "users", target_id)
    return result


async def import_labs(
    source: asyncpg.Connection, target: asyncpg.Connection
) -> dict[int, uuid.UUID]:
    result: dict[int, uuid.UUID] = {}
    existing = {row["code"]: row["id"] for row in await target_rows(target, "labs", ("id", "code"))}
    for row in await source.fetch(
        limited(
            source_select(
                "labs", ("id", "name", "code", "full_name", "created_at", "updated_at", "deleted")
            )
        )
    ):
        code = mapping().lab_codes.get(
            (clean(row["code"]) or "").casefold(), f"LEGACY-LAB-{row['id']}"
        )
        target_id = existing.get(code) or ident("labs", row["id"])
        await insert_configured(
            target,
            "labs",
            {
                "id": target_id,
                "code": code,
                "name": clean(row["name"]) or code,
                "full_name": clean(row["full_name"]),
                "created_at": utc(row["created_at"]) or datetime.now(UTC),
                "updated_at": utc(row["updated_at"]) or datetime.now(UTC),
                "deleted_at": deleted_at(row),
            },
            row,
        )
        target_id = require_uuid(
            await target_id_by(target, "labs", "code", code), f"labs.code={code}"
        )
        result[int(row["id"])] = target_id
        await save_map(target, "podrs", row["id"], "labs", target_id)
    return result


async def import_doctors(
    source: asyncpg.Connection, target: asyncpg.Connection, users: dict[int, uuid.UUID]
) -> dict[int, uuid.UUID]:
    result: dict[int, uuid.UUID] = {}
    for row in await source.fetch(
        limited(
            source_select(
                "doctors",
                (
                    "id",
                    "name",
                    "full_name",
                    "user_source_id",
                    "created_at",
                    "updated_at",
                    "deleted",
                ),
            )
        )
    ):
        last_name, first_name, patronymic = split_name(row["full_name"] or row["name"])
        doctor_first_name = first_name or last_name or "Legacy doctor"
        doctor_last_name: str | None = last_name
        if first_name is None:
            # ``doctors.first_name`` is mandatory in canonical schema; retain
            # a one-token legacy value there rather than inserting NULL.
            doctor_first_name, doctor_last_name = last_name or "Legacy doctor", None
        target_id = ident("sandoctors", row["id"])
        await insert_configured(
            target,
            "doctors",
            {
                "id": target_id,
                "first_name": doctor_first_name,
                "last_name": doctor_last_name,
                "patronymic": patronymic,
                "user_id": users.get(int(row["user_source_id"])),
                "created_at": utc(row["created_at"]) or datetime.now(UTC),
                "updated_at": utc(row["updated_at"]) or datetime.now(UTC),
                "deleted_at": deleted_at(row),
            },
            row,
        )
        result[int(row["id"])] = target_id
        await save_map(target, "sandoctors", row["id"], "doctors", target_id)
    return result


async def import_objects(
    source: asyncpg.Connection, target: asyncpg.Connection
) -> dict[int, uuid.UUID]:
    result: dict[int, uuid.UUID] = {}
    for row in await source.fetch(
        limited(
            source_select(
                "objects",
                ("id", "name", "full_name", "address", "created_at", "updated_at", "deleted"),
            )
        )
    ):
        target_id = ident("resobjects", row["id"])
        code = f"LEGACY-OBJECT-{row['id']}"
        await insert_configured(
            target,
            "objects",
            {
                "id": target_id,
                "code": code,
                "name": clean(row["name"]) or code,
                "full_name": clean(row["full_name"]),
                "address": clean(row["address"]),
                "created_at": utc(row["created_at"]) or datetime.now(UTC),
                "updated_at": utc(row["updated_at"]) or datetime.now(UTC),
                "deleted_at": deleted_at(row),
            },
            row,
        )
        target_id = require_uuid(
            await target_id_by(target, "objects", "code", code), f"objects.code={code}"
        )
        result[int(row["id"])] = target_id
        await save_map(target, "resobjects", row["id"], "objects", target_id)
    return result


async def import_sample_types(
    source: asyncpg.Connection, target: asyncpg.Connection
) -> dict[int, uuid.UUID]:
    result: dict[int, uuid.UUID] = {}
    existing = {
        row["name"].casefold(): row["id"]
        for row in await target_rows(target, "sample_types", ("id", "name"))
    }
    for row in await source.fetch(
        limited(
            source_select("sample_types", ("id", "name", "created_at", "updated_at", "deleted"))
        )
    ):
        name = clean(row["name"]) or f"Legacy type {row['id']}"
        code = f"LEGACY-OBR-TYPE-{row['id']}"
        target_id = existing.get(name.casefold()) or ident("obr_types", row["id"])
        await insert_configured(
            target,
            "sample_types",
            {
                "id": target_id,
                "code": code,
                "name": name,
                "created_at": utc(row["created_at"]) or datetime.now(UTC),
                "updated_at": utc(row["updated_at"]) or datetime.now(UTC),
                "deleted_at": deleted_at(row),
            },
            row,
        )
        result[int(row["id"])] = target_id
        await save_map(target, "obr_types", row["id"], "sample_types", target_id)
    return result


async def import_goals(
    source: asyncpg.Connection, target: asyncpg.Connection
) -> dict[str, uuid.UUID]:
    values = [
        row["target"]
        for row in await source.fetch(
            limited(source_select("research_goals", ("target",), distinct=True, order_by=None))
        )
    ]
    normalized = {normalize_target(value) for value in values}
    normalized.discard("")
    normalized.add("UNSPECIFIED")
    result: dict[str, uuid.UUID] = {}
    for value in sorted(normalized):
        goal_id = ident("research_goals", value)
        code = (
            "LEGACY-TARGET-UNSPECIFIED"
            if value == "UNSPECIFIED"
            else f"LEGACY-TARGET-{hashlib.sha256(value.encode()).hexdigest()[:12].upper()}"
        )
        await insert_configured(
            target,
            "research_goals",
            {
                "id": goal_id,
                "code": code,
                "name": value,
                "comment": (
                    "Original legacy target value; UNSPECIFIED means source was empty."
                    if value == "UNSPECIFIED"
                    else "Legacy MySQL target combination."
                ),
            },
        )
        goal_id = require_uuid(
            await target_id_by(target, "research_goals", "code", code),
            f"research_goals.code={code}",
        )
        result[value] = goal_id
        await save_map(target, "obrs.target", value, "research_goals", goal_id)
    return result


async def import_indicators(
    source: asyncpg.Connection, target: asyncpg.Connection, sample_types: dict[int, uuid.UUID]
) -> dict[int, uuid.UUID]:
    result: dict[int, uuid.UUID] = {}
    for row in await source.fetch(
        limited(
            source_select(
                "indicators",
                (
                    "id",
                    "sample_type_source_id",
                    "name",
                    "unit",
                    "norm_text",
                    "norm_value",
                    "default_text",
                    "comment",
                    "created_at",
                    "updated_at",
                    "deleted",
                ),
            )
        )
    ):
        target_id = ident("poks", row["id"])
        await insert_configured(
            target,
            "indicators",
            {
                "id": target_id,
                "name": clean(row["name"]) or f"Legacy indicator {row['id']}",
                "unit": clean(row["unit"]),
                "norm_text": clean(row["norm_text"]),
                "norm_value": clean(row["norm_value"]),
                "default_text": clean(row["default_text"]),
                "comment": clean(row["comment"]),
                "sample_type_id": sample_types.get(int(row["sample_type_source_id"])),
                "created_at": utc(row["created_at"]) or datetime.now(UTC),
                "updated_at": utc(row["updated_at"]) or datetime.now(UTC),
                "deleted_at": deleted_at(row),
            },
            row,
        )
        result[int(row["id"])] = target_id
        await save_map(target, "poks", row["id"], "indicators", target_id)
    return result


async def import_conclusions(
    source: asyncpg.Connection, target: asyncpg.Connection
) -> dict[int, uuid.UUID]:
    result: dict[int, uuid.UUID] = {}
    for row in await source.fetch(
        limited(
            source_select(
                "conclusions", ("id", "name", "text", "created_at", "updated_at", "deleted")
            )
        )
    ):
        target_id = ident("zakls", row["id"])
        text_value = clean(row["text"]) or ""
        await insert_configured(
            target,
            "conclusions",
            {
                "id": target_id,
                "code": f"LEGACY-ZAKL-{row['id']}",
                "name": clean(row["name"]) or f"Legacy conclusion {row['id']}",
                "text_singular": text_value,
                "text_plural": text_value,
                "created_at": utc(row["created_at"]) or datetime.now(UTC),
                "updated_at": utc(row["updated_at"]) or datetime.now(UTC),
                "deleted_at": deleted_at(row),
            },
            row,
        )
        result[int(row["id"])] = target_id
        await save_map(target, "zakls", row["id"], "conclusions", target_id)
    return result


async def import_protocol_types(
    source: asyncpg.Connection, target: asyncpg.Connection
) -> dict[int, uuid.UUID]:
    result: dict[int, uuid.UUID] = {}
    for row in await source.fetch(
        limited(
            source_select("protocol_types", ("id", "name", "created_at", "updated_at", "deleted"))
        )
    ):
        target_id = ident("protocol_types", row["id"])
        await insert_configured(
            target,
            "protocol_types",
            {
                "id": target_id,
                "code": f"LEGACY-PROTOCOL-TYPE-{row['id']}",
                "name": clean(row["name"]) or f"Legacy protocol type {row['id']}",
                "created_at": utc(row["created_at"]) or datetime.now(UTC),
                "updated_at": utc(row["updated_at"]) or datetime.now(UTC),
                "deleted_at": deleted_at(row),
            },
            row,
        )
        result[int(row["id"])] = target_id
        await save_map(target, "protocol_types", row["id"], "protocol_types", target_id)
    return result


async def import_protocols(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    conclusions: dict[int, uuid.UUID],
    protocol_types: dict[int, uuid.UUID],
    users: dict[int, uuid.UUID],
) -> dict[int, uuid.UUID]:
    result: dict[int, uuid.UUID] = {}
    for row in await source.fetch(
        limited(
            source_select(
                "protocols",
                (
                    "id",
                    "year_no",
                    "conclusion_source_id",
                    "protocol_type_source_id",
                    "copies",
                    "is_signed",
                    "protocol_copy_name",
                    "excerpt_copy_name",
                    "user_source_id",
                    "created_at",
                    "updated_at",
                    "deleted",
                ),
            )
        )
    ):
        target_id = ident("protocols", row["id"])
        actor_id = users.get(int(row["user_source_id"]))
        await insert_configured(
            target,
            "protocols",
            {
                "id": target_id,
                "year_no": int(row["year_no"]),
                "copies": row["copies"],
                "is_signed": bool_value(row["is_signed"]),
                "protocol_copy_name": clean(row["protocol_copy_name"]),
                "excerpt_copy_name": clean(row["excerpt_copy_name"]),
                "conclusion_id": conclusions.get(int(row["conclusion_source_id"])),
                "protocol_type_id": protocol_types.get(int(row["protocol_type_source_id"])),
                "created_by": actor_id,
                "updated_by": actor_id,
                "created_at": utc(row["created_at"]) or datetime.now(UTC),
                "updated_at": utc(row["updated_at"]) or datetime.now(UTC),
                "deleted_at": deleted_at(row),
            },
            row,
        )
        result[int(row["id"])] = target_id
        await save_map(target, "protocols", row["id"], "protocols", target_id)
    return result


async def import_directions(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    doctors: dict[int, uuid.UUID],
    objects: dict[int, uuid.UUID],
    users: dict[int, uuid.UUID],
) -> dict[int, uuid.UUID]:
    result: dict[int, uuid.UUID] = {}
    for row in await source.fetch(
        limited(
            source_select(
                "directions",
                (
                    "id",
                    "base_no",
                    "year_no",
                    "doctor_source_id",
                    "object_source_id",
                    "is_done",
                    "is_urgent",
                    "sampled_at",
                    "received_at",
                    "completed_at",
                    "user_source_id",
                    "created_at",
                    "updated_at",
                    "deleted",
                ),
            )
        )
    ):
        target_id = ident("naprs", row["id"])
        year_no = int(row["year_no"])
        base_no: int | None = int(row["base_no"])
        config = entity("directions")
        year_column = config.target_column("year_no")
        base_column = config.target_column("base_no")
        id_column = config.target_column("id")
        if year_column and base_column and id_column:
            existing_id = await target.fetchval(
                f"SELECT {quote_identifier(id_column)} FROM {target_table('directions')} "
                f"WHERE {quote_identifier(year_column)}=$1 AND {quote_identifier(base_column)}=$2",
                year_no,
                base_no,
            )
            if existing_id is not None and existing_id != target_id:
                await warn(
                    target,
                    "naprs",
                    row["id"],
                    "direction_key_conflict",
                    f"(year_no,base_no)=({year_no},{base_no}); base_no set NULL",
                )
                base_no = None
        actor_id = users.get(int(row["user_source_id"]))
        await insert_configured(
            target,
            "directions",
            {
                "id": target_id,
                "year_no": year_no,
                "base_no": base_no,
                "is_done": bool_value(row["is_done"]),
                "is_urgent": bool_value(row["is_urgent"]),
                "doctor_id": doctors.get(int(row["doctor_source_id"])),
                "object_id": objects.get(int(row["object_source_id"])),
                "created_by": actor_id,
                "updated_by": actor_id,
                "sampled_at": utc(row["sampled_at"]),
                "received_at": utc(row["received_at"]),
                "completed_at": utc(row["completed_at"]),
                "created_at": utc(row["created_at"]) or datetime.now(UTC),
                "updated_at": utc(row["updated_at"]) or datetime.now(UTC),
                "deleted_at": deleted_at(row),
            },
            row,
        )
        result[int(row["id"])] = target_id
        await save_map(target, "naprs", row["id"], "directions", target_id)
    return result


async def import_samples(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    directions: dict[int, uuid.UUID],
    sample_types: dict[int, uuid.UUID],
    protocols: dict[int, uuid.UUID],
    users: dict[int, uuid.UUID],
) -> tuple[dict[int, uuid.UUID], dict[int, str]]:
    result: dict[int, uuid.UUID] = {}
    targets: dict[int, str] = {}
    statuses = await target_statuses(target, "sample_statuses")
    for row in await source.fetch(
        limited(
            source_select(
                "samples",
                (
                    "id",
                    "month_no",
                    "name",
                    "alternate_name",
                    "mass",
                    "target_description",
                    "comment",
                    "section",
                    "delivery",
                    "nomenclature_code",
                    "batch_code",
                    "supplier",
                    "is_urgent",
                    "is_done",
                    "direction_source_id",
                    "sample_type_source_id",
                    "protocol_source_id",
                    "received_at",
                    "completed_at",
                    "user_source_id",
                    "created_at",
                    "updated_at",
                    "deleted",
                ),
            )
        )
    ):
        target_id = ident("obrs", row["id"])
        target_text = normalize_target(row["target_description"])
        targets[int(row["id"])] = target_text or "UNSPECIFIED"
        is_done = bool_value(row["is_done"])
        actor_id = users.get(int(row["user_source_id"]))
        received_at = utc(row["received_at"])
        await insert_configured(
            target,
            "samples",
            {
                "id": target_id,
                "month_no": row["month_no"],
                "name": clean(row["name"]) or f"Legacy sample {row['id']}",
                "alternate_name": clean(row["alternate_name"]),
                "mass": clean(row["mass"]),
                "target_description": clean(row["target_description"]),
                "comment": clean(row["comment"]),
                "section": clean(row["section"]),
                "delivery": clean(row["delivery"]),
                "nomenclature_code": clean(row["nomenclature_code"]),
                "batch_code": clean(row["batch_code"]),
                "supplier": clean(row["supplier"]),
                "is_urgent": bool_value(row["is_urgent"]),
                "is_done": is_done,
                "sample_type_id": sample_types.get(int(row["sample_type_source_id"])),
                "status_id": statuses.get("completed" if is_done else "in_progress"),
                "direction_id": directions.get(int(row["direction_source_id"])),
                "protocol_id": protocols.get(int(row["protocol_source_id"])),
                "sampled_at": received_at,
                "received_at": received_at,
                "completed_at": utc(row["completed_at"]),
                "created_by": actor_id,
                "updated_by": actor_id,
                "created_at": utc(row["created_at"]) or datetime.now(UTC),
                "updated_at": utc(row["updated_at"]) or datetime.now(UTC),
                "deleted_at": deleted_at(row),
            },
            row,
        )
        result[int(row["id"])] = target_id
        await save_map(target, "obrs", row["id"], "samples", target_id)
    return result, targets


async def import_research(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    samples: dict[int, uuid.UUID],
    sample_targets: dict[int, str],
    labs: dict[int, uuid.UUID],
    users: dict[int, uuid.UUID],
    goals: dict[str, uuid.UUID],
) -> dict[int, uuid.UUID]:
    result: dict[int, uuid.UUID] = {}
    statuses = await target_statuses(target, "research_statuses")
    batch: list[dict[str, object]] = []
    map_batch: list[tuple[object, uuid.UUID]] = []
    query = source_select(
        "research",
        (
            "id",
            "sample_source_id",
            "lab_source_id",
            "status_source_id",
            "comment",
            "recommendation",
            "received_at",
            "completed_at",
            "user_source_id",
            "created_at",
            "updated_at",
            "deleted",
        ),
    )
    async for row in iter_source(source, query):
        sample_source_id = int(row["sample_source_id"])
        sample_id = samples.get(sample_source_id)
        if sample_id is None:
            await warn(
                target,
                "results",
                row["id"],
                "orphan_sample",
                f"sample_source_id={sample_source_id}",
            )
            continue
        goal_id = goals.get(
            sample_targets.get(sample_source_id, "UNSPECIFIED"), goals["UNSPECIFIED"]
        )
        target_id = ident("results", row["id"])
        lab_source_id = int(row["lab_source_id"])
        lab_id = labs.get(lab_source_id)
        if lab_id is None:
            await warn(target, "results", row["id"], "orphan_lab", f"lab_source_id={lab_source_id}")
        status_source_id = int(row["status_source_id"])
        actor_id = users.get(int(row["user_source_id"]))
        batch.append(
            configured_values(
                "research",
                {
                    "id": target_id,
                    "sample_id": sample_id,
                    "research_goal_id": goal_id,
                    "lab_id": lab_id,
                    "comment": clean(row["comment"]),
                    "recommendation": clean(row["recommendation"]),
                    "status_id": statuses.get(
                        mapping().statuses.get(status_source_id, "in_progress")
                    ),
                    "created_by": actor_id,
                    "updated_by": actor_id,
                    "received_at": utc(row["received_at"]),
                    "completed_at": utc(row["completed_at"]),
                    "created_at": utc(row["created_at"]) or datetime.now(UTC),
                    "updated_at": utc(row["updated_at"]) or datetime.now(UTC),
                    "deleted_at": deleted_at(row),
                },
                row,
            )
        )
        map_batch.append((row["id"], target_id))
        result[int(row["id"])] = target_id
        if len(batch) >= BATCH_SIZE:
            await insert_configured_batch(target, "research", batch)
            await save_map_batch(target, "results", "research", map_batch)
            batch.clear()
            map_batch.clear()
    if batch:
        await insert_configured_batch(target, "research", batch)
        await save_map_batch(target, "results", "research", map_batch)
    return result


async def import_tests(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    research: dict[int, uuid.UUID],
    indicators: dict[int, uuid.UUID],
    users: dict[int, uuid.UUID],
) -> int:
    inserted = 0
    statuses = await target_statuses(target, "test_statuses")
    query = source_select(
        "tests",
        (
            "id",
            "research_source_id",
            "indicator_source_id",
            "is_active",
            "value",
            "comment",
            "norm",
            "status_source_id",
            "user_source_id",
            "created_at",
            "updated_at",
            "deleted",
        ),
    )
    batch: list[dict[str, object]] = []
    map_batch: list[tuple[object, uuid.UUID]] = []
    async for row in iter_source(source, query):
        research_source_id = int(row["research_source_id"])
        research_id = research.get(research_source_id)
        if research_id is None:
            await warn(
                target,
                "tests",
                row["id"],
                "orphan_research",
                f"research_source_id={research_source_id}",
            )
            continue
        test_id = ident("tests", row["id"])
        status_source_id = int(row["status_source_id"])
        actor_id = users.get(int(row["user_source_id"]))
        batch.append(
            configured_values(
                "tests",
                {
                    "id": test_id,
                    "value": clean(row["value"]),
                    "comment": clean(row["comment"]),
                    "norm": clean(row["norm"]),
                    "verdict": (
                        True if status_source_id == 1 else False if status_source_id == 2 else None
                    ),
                    "is_active": bool_value(row["is_active"]),
                    "research_id": research_id,
                    "indicator_id": indicators.get(int(row["indicator_source_id"])),
                    "status_id": statuses.get(
                        mapping().statuses.get(status_source_id, "in_progress")
                    ),
                    "created_by": actor_id,
                    "updated_by": actor_id,
                    "created_at": utc(row["created_at"]) or datetime.now(UTC),
                    "updated_at": utc(row["updated_at"]) or datetime.now(UTC),
                    "deleted_at": deleted_at(row),
                },
                row,
            )
        )
        map_batch.append((row["id"], test_id))
        if len(batch) >= BATCH_SIZE:
            await insert_configured_batch(target, "tests", batch)
            await save_map_batch(target, "tests", "tests", map_batch)
            inserted += len(batch)
            batch.clear()
            map_batch.clear()
    if batch:
        await insert_configured_batch(target, "tests", batch)
        await save_map_batch(target, "tests", "tests", map_batch)
        inserted += len(batch)
    return inserted


async def import_sample_labs(
    target: asyncpg.Connection,
    source: asyncpg.Connection,
    samples: dict[int, uuid.UUID],
    labs: dict[int, uuid.UUID],
) -> int:
    sample_source_column = source_column("sample_labs", "sample_source_id")
    lab_source_column = source_column("sample_labs", "lab_source_id")
    pairs = await source.fetch(
        limited(
            source_select(
                "sample_labs",
                ("sample_source_id", "lab_source_id"),
                distinct=True,
                order_by=None,
            )
            + f" WHERE {sample_source_column}<>0 AND {lab_source_column}<>0"
        )
    )
    inserted = 0
    for row in pairs:
        sample_source_id = int(row["sample_source_id"])
        lab_source_id = int(row["lab_source_id"])
        sample_id, lab_id = samples.get(sample_source_id), labs.get(lab_source_id)
        if sample_id is None or lab_id is None:
            continue
        await insert_configured(
            target,
            "sample_labs",
            {
                "id": ident("sample_labs", f"{sample_source_id}:{lab_source_id}"),
                "sample_id": sample_id,
                "lab_id": lab_id,
            },
            row,
        )
        inserted += 1
    return inserted


async def import_generic_entity(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    config: GenericEntityMapping,
) -> int:
    """Copy a flat additional table declared entirely in JSON.

    Generic mappings intentionally do not resolve cross-table UUID foreign
    keys. Tables with domain joins or FK remapping need a named adapter above.
    """

    source_table_sql = (
        f"{quote_identifier(mapping().source_schema)}.{quote_identifier(config.source_table)}"
    )
    source_expressions = [
        f"{quote_identifier(config.source_pk)} AS {quote_identifier('__source_pk')}"
    ]
    source_expressions.extend(
        f"{quote_identifier(column.source)} AS {quote_identifier(f'__column_{index}')}"
        for index, column in enumerate(config.columns)
    )
    query = (
        f"SELECT {','.join(source_expressions)} FROM {source_table_sql} "
        f"ORDER BY {quote_identifier(config.source_pk)}"
    )
    target_columns = (config.target_pk, *(column.target for column in config.columns))
    target_sql = quote_identifier(config.target_table)
    column_sql = ",".join(quote_identifier(column) for column in target_columns)
    placeholders = ",".join(f"${index}" for index in range(1, len(target_columns) + 1))
    sql = f"INSERT INTO {target_sql}({column_sql}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    batch: list[tuple[object, ...]] = []
    maps: list[tuple[object, uuid.UUID]] = []
    inserted = 0
    async for row in iter_source(source, query):
        source_pk = row["__source_pk"]
        target_pk: object = (
            ident(config.key, source_pk) if config.id_strategy == "uuid5" else source_pk
        )
        values = [target_pk]
        values.extend(
            _transform_extra(row[f"__column_{index}"], column.transform)
            for index, column in enumerate(config.columns)
        )
        batch.append(tuple(values))
        if isinstance(target_pk, uuid.UUID):
            maps.append((source_pk, target_pk))
        if len(batch) >= BATCH_SIZE:
            await target.executemany(sql, batch)
            await save_map_batch(target, config.source_table, config.target_table, maps)
            inserted += len(batch)
            batch.clear()
            maps.clear()
    if batch:
        await target.executemany(sql, batch)
        await save_map_batch(target, config.source_table, config.target_table, maps)
        inserted += len(batch)
    return inserted


async def dry_run(source: asyncpg.Connection, target: asyncpg.Connection) -> None:
    del target
    entity_keys = (
        "users",
        "labs",
        "doctors",
        "objects",
        "directions",
        "sample_types",
        "samples",
        "indicators",
        "conclusions",
        "protocol_types",
        "protocols",
        "research",
        "tests",
        "obr_targets_audit",
    )
    counts = {
        entity(key).source_table or key: await count_rows(source, key)
        for key in entity_keys
        if mapping().enabled(key)
    }
    for generic in mapping().generic_entities:
        if generic.enabled:
            table_sql = (
                f"{quote_identifier(mapping().source_schema)}."
                f"{quote_identifier(generic.source_table)}"
            )
            counts[generic.source_table] = int(
                await source.fetchval(f"SELECT count(*) FROM {table_sql}")
            )
    target_source_column = source_column("research_goals", "target")
    targets = await source.fetchval(
        f"SELECT count(DISTINCT {target_source_column}) FROM {source_table('research_goals')} "
        f"WHERE {target_source_column} IS NOT NULL AND btrim({target_source_column})<>''"
    )
    empty_targets = await source.fetchval(
        f"SELECT count(*) FROM {source_table('research_goals')} "
        f"WHERE {target_source_column} IS NULL OR btrim({target_source_column})=''"
    )
    research_sample = source_column("research", "sample_source_id")
    research_lab = source_column("research", "lab_source_id")
    lab_id = source_column("labs", "id")
    sample_protocol = source_column("samples", "protocol_source_id")
    protocol_id = source_column("protocols", "id")
    audit_sample = source_column("obr_targets_audit", "sample_source_id")
    audit_target = source_column("obr_targets_audit", "target_source_id")
    orphans = {
        "results_without_sample": await source.fetchval(
            f"SELECT count(*) FROM {source_table('research')} WHERE {research_sample}=0"
        ),
        "results_without_lab": await source.fetchval(
            f"SELECT count(*) FROM {source_table('research')} r "
            f"LEFT JOIN {source_table('labs')} p ON p.{lab_id}=r.{research_lab} "
            f"WHERE p.{lab_id} IS NULL"
        ),
        "samples_without_protocol": await source.fetchval(
            f"SELECT count(*) FROM {source_table('samples')} "
            f"WHERE {sample_protocol} NOT IN "
            f"(SELECT {protocol_id} FROM {source_table('protocols')})"
        ),
        "orphan_obr_targets": await source.fetchval(
            f"SELECT count(*) FROM {source_table('obr_targets_audit')} "
            f"WHERE {audit_sample}=0 OR {audit_target}=0"
        ),
    }
    print("Legacy ETL dry-run (no writes)")
    for table, count in counts.items():
        print(f"  {table:16} {count:>10}")
    print(
        f"  research_goals   {int(targets) + 1:>10} ({targets} combinations + UNSPECIFIED for {empty_targets} rows)"
    )
    print("Orphans:")
    for key, count in orphans.items():
        print(f"  {key:24} {count}")
    print("Target database was not modified.")


async def apply(source: asyncpg.Connection, target: asyncpg.Connection) -> None:
    PROGRESS_TOTALS.clear()
    PROGRESS_COUNTS.clear()
    for progress_name in (
        "users", "labs", "doctors", "objects", "sample_types", "research_goals",
        "indicators", "conclusions", "protocol_types", "protocols", "directions",
        "samples", "research", "tests", "sample_labs",
    ):
        if mapping().enabled(progress_name):
            PROGRESS_TOTALS[progress_name] = await count_rows(source, progress_name)
    print("[ETL] progress counters: processed/total source rows", flush=True)
    await ensure_import_schema(target)
    generic_counts: dict[str, int] = {}
    async with target.transaction():
        # Updating the same aggregate row once per test serializes 1.3M
        # inserts. Recompute it once after the bulk load instead.
        await target.execute(
            "ALTER TABLE tests DISABLE TRIGGER tests_active_total_row_trigger"
        )
        print("[ETL] disabled tests aggregate trigger for bulk load", flush=True)
        roles = await import_roles(target) if mapping().enabled("roles") else {}
        users = await import_users(source, target, roles) if mapping().enabled("users") else {}
        labs = await import_labs(source, target) if mapping().enabled("labs") else {}
        doctors = (
            await import_doctors(source, target, users) if mapping().enabled("doctors") else {}
        )
        objects = await import_objects(source, target) if mapping().enabled("objects") else {}
        sample_types = (
            await import_sample_types(source, target) if mapping().enabled("sample_types") else {}
        )
        goals = await import_goals(source, target) if mapping().enabled("research_goals") else {}
        indicators = (
            await import_indicators(source, target, sample_types)
            if mapping().enabled("indicators")
            else {}
        )
        conclusions = (
            await import_conclusions(source, target) if mapping().enabled("conclusions") else {}
        )
        protocol_types = (
            await import_protocol_types(source, target)
            if mapping().enabled("protocol_types")
            else {}
        )
        protocols = (
            await import_protocols(source, target, conclusions, protocol_types, users)
            if mapping().enabled("protocols")
            else {}
        )
        directions = (
            await import_directions(source, target, doctors, objects, users)
            if mapping().enabled("directions")
            else {}
        )
        samples, sample_targets = (
            await import_samples(source, target, directions, sample_types, protocols, users)
            if mapping().enabled("samples")
            else ({}, {})
        )
        research = (
            await import_research(source, target, samples, sample_targets, labs, users, goals)
            if mapping().enabled("research")
            else {}
        )
        tests = (
            await import_tests(source, target, research, indicators, users)
            if mapping().enabled("tests")
            else 0
        )
        sample_labs = (
            await import_sample_labs(target, source, samples, labs)
            if mapping().enabled("sample_labs")
            else 0
        )
        for generic in mapping().generic_entities:
            if generic.enabled:
                generic_counts[generic.key] = await import_generic_entity(source, target, generic)
        await target.execute(
            """
            UPDATE entity_active_counts
            SET active_total = (SELECT count(*) FROM tests WHERE deleted_at IS NULL),
                updated_at = CURRENT_TIMESTAMP
            WHERE entity_name = 'tests'
            """
        )
        await target.execute(
            "ALTER TABLE tests ENABLE TRIGGER tests_active_total_row_trigger"
        )
        print("[ETL] tests aggregate recomputed; trigger enabled", flush=True)
    print("Legacy ETL applied without deletes")
    print(f"  users={len(users)} labs={len(labs)} doctors={len(doctors)} objects={len(objects)}")
    print(
        f"  directions={len(directions)} samples={len(samples)} research={len(research)} tests={tests}"
    )
    print(f"  sample_labs={sample_labs} goals={len(goals)}")
    for key, count in generic_counts.items():
        print(f"  generic.{key}={count}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-database-url", default=DEFAULT_SOURCE_DSN)
    parser.add_argument("--target-database-url", default=None)
    parser.add_argument(
        "--mapping-file",
        type=Path,
        default=Path(os.getenv("LEGACY_MAPPING_FILE", DEFAULT_MAPPING_PATH)),
        help="JSON mapping file",
    )
    parser.add_argument(
        "--validate-mapping",
        action="store_true",
        help="Validate mapping JSON and exit without database connections",
    )
    parser.add_argument(
        "--apply", action="store_true", help="Write canonical data; default is dry-run"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit source SELECTs during --apply (for a safe integration smoke test)",
    )
    return parser.parse_args()


async def main() -> None:
    global BATCH_SIZE, MAPPING, ROW_LIMIT
    args = parse_args()
    MAPPING = load_mapping(args.mapping_file)
    BATCH_SIZE = MAPPING.batch_size
    if args.validate_mapping:
        enabled = sum(item.enabled for item in MAPPING.entities.values())
        generic = sum(item.enabled for item in MAPPING.generic_entities)
        print(
            f"Mapping valid: version={MAPPING.version} enabled_entities={enabled} "
            f"enabled_generic={generic}"
        )
        return
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be a positive integer")
    ROW_LIMIT = args.limit
    target_dsn = args.target_database_url or get_settings().database_url.replace("+asyncpg", "")
    source = await asyncpg.connect(args.source_database_url)
    target = await asyncpg.connect(target_dsn)
    try:
        if args.apply:
            await apply(source, target)
        else:
            await dry_run(source, target)
    finally:
        await source.close()
        await target.close()


if __name__ == "__main__":
    asyncio.run(main())
