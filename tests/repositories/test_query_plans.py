from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import Select, insert, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from src.core.database import get_engine
from src.models.entities import Branch, Role, RolePermission
from src.repositories.crud_repository import CRUDRepository, ListQuery

pytestmark = [pytest.mark.integration, pytest.mark.db_plan]

_REQUIRED_TABLES = ("branches", "roles", "role_permissions")
_SCAN_NODES = {"Index Scan", "Index Only Scan", "Bitmap Heap Scan", "Seq Scan"}


@pytest.fixture
async def db_plan_session() -> AsyncIterator[AsyncSession]:
    engine = get_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("db_plan tests require PostgreSQL")

    try:
        async with engine.connect() as connection:
            await _ensure_required_tables(connection, _REQUIRED_TABLES)
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)
            try:
                yield session
            finally:
                await session.close()
                await transaction.rollback()
    except Exception as exc:
        pytest.skip(f"PostgreSQL unavailable for db_plan tests: {exc}")


async def _ensure_required_tables(connection: AsyncConnection, tables: tuple[str, ...]) -> None:
    missing: list[str] = []
    for table_name in tables:
        result = await connection.execute(
            text("SELECT to_regclass(:table_name)"),
            {"table_name": f"public.{table_name}"},
        )
        if result.scalar_one_or_none() is None:
            missing.append(table_name)

    if missing:
        missing_names = ", ".join(sorted(missing))
        pytest.skip(
            f"db_plan tests require migrated schema; missing tables: {missing_names}. "
            "Run alembic migrations on test database first."
        )


def _compile_sql(stmt: Select[Any]) -> str:
    return str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


async def _explain_json(session: AsyncSession, stmt: Select[Any]) -> dict[str, Any]:
    explain_sql = (
        "EXPLAIN (ANALYZE true, BUFFERS true, SETTINGS true, WAL true, "
        f"TIMING false, SUMMARY true, FORMAT JSON) {_compile_sql(stmt)}"
    )
    result = await session.execute(text(explain_sql))
    payload = result.scalar_one()

    parsed: Any = json.loads(payload) if isinstance(payload, str) else payload
    if not isinstance(parsed, list) or not parsed or not isinstance(parsed[0], dict):
        raise AssertionError("Expected EXPLAIN FORMAT JSON payload with one plan object")
    return parsed[0]


def _walk_plan_nodes(plan_root: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    stack = [plan_root]
    while stack:
        node = stack.pop()
        nodes.append(node)
        children = node.get("Plans")
        if isinstance(children, list):
            stack.extend(child for child in children if isinstance(child, dict))
    return nodes


def _collect_node_types(plan_root: dict[str, Any]) -> set[str]:
    node_types: set[str] = set()
    for node in _walk_plan_nodes(plan_root):
        node_type = node.get("Node Type")
        if isinstance(node_type, str):
            node_types.add(node_type)
    return node_types


def _collect_relations(plan_root: dict[str, Any]) -> set[str]:
    relations: set[str] = set()
    for node in _walk_plan_nodes(plan_root):
        relation = node.get("Relation Name")
        if isinstance(relation, str):
            relations.add(relation)
    return relations


async def test_crud_get_query_explain_json(db_plan_session: AsyncSession) -> None:
    branch_id = uuid4()
    await db_plan_session.execute(
        insert(Branch).values(
            id=branch_id,
            code=f"plan-get-{branch_id.hex[:8]}",
            name="Plan Get",
        )
    )

    stmt = select(Branch).where(Branch.id == branch_id).where(Branch.deleted_at.is_(None))
    explain = await _explain_json(db_plan_session, stmt)

    assert "Planning Time" in explain
    assert "Execution Time" in explain

    plan = explain["Plan"]
    assert isinstance(plan, dict)
    assert "branches" in _collect_relations(plan)
    assert _collect_node_types(plan) & _SCAN_NODES


async def test_crud_list_total_and_items_explain_json(db_plan_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    rows: list[dict[str, Any]] = []
    for idx in range(6):
        rows.append(
            {
                "id": uuid4(),
                "code": f"plan-live-{idx}-{uuid4().hex[:6]}",
                "name": f"Live {idx}",
                "created_at": now - timedelta(minutes=idx),
                "updated_at": now - timedelta(minutes=idx),
                "deleted_at": None,
            }
        )
    for idx in range(40):
        rows.append(
            {
                "id": uuid4(),
                "code": f"plan-deleted-{idx}-{uuid4().hex[:6]}",
                "name": f"Deleted {idx}",
                "created_at": now - timedelta(days=1, minutes=idx),
                "updated_at": now - timedelta(days=1, minutes=idx),
                "deleted_at": now - timedelta(minutes=idx),
            }
        )
    await db_plan_session.execute(insert(Branch), rows)

    repository = CRUDRepository(session=db_plan_session, model=Branch)
    query = ListQuery(offset=0, limit=5, sort_by="created_at", sort_order="desc")
    base_stmt = select(Branch)
    base_stmt = repository._with_soft_delete_filter(base_stmt)
    base_stmt = repository._with_list_filters(base_stmt, query)
    sort_clause = repository._resolve_sort_column(query, {"created_at"})

    total_stmt = repository._build_total_stmt(query=query, base_stmt=base_stmt)
    items_stmt = base_stmt.order_by(sort_clause).offset(query.offset).limit(query.limit)

    total_explain = await _explain_json(db_plan_session, total_stmt)
    items_explain = await _explain_json(db_plan_session, items_stmt)

    total_plan = total_explain["Plan"]
    items_plan = items_explain["Plan"]
    assert isinstance(total_plan, dict)
    assert isinstance(items_plan, dict)

    assert "Aggregate" in _collect_node_types(total_plan)
    items_node_types = _collect_node_types(items_plan)
    assert "Limit" in items_node_types
    assert items_node_types & _SCAN_NODES
    assert "branches" in _collect_relations(items_plan)


async def test_crud_resolve_include_reference_explain_json(db_plan_session: AsyncSession) -> None:
    role_id = uuid4()
    await db_plan_session.execute(
        insert(Role).values(
            id=role_id,
            key=f"plan-role-{role_id.hex[:8]}",
            name="Plan Role",
        )
    )

    stmt = select(Role).where(Role.id == role_id).where(Role.deleted_at.is_(None))
    explain = await _explain_json(db_plan_session, stmt)
    plan = explain["Plan"]
    assert isinstance(plan, dict)

    assert "roles" in _collect_relations(plan)
    assert _collect_node_types(plan) & _SCAN_NODES


async def test_role_permission_get_by_pk_explain_prefers_index(
    db_plan_session: AsyncSession,
) -> None:
    role_id = uuid4()
    await db_plan_session.execute(
        insert(Role).values(
            id=role_id,
            key=f"plan-rp-role-{role_id.hex[:8]}",
            name="Plan RP Role",
        )
    )

    target_resource = "plan_target_resource"
    target_action = "read"
    permission_rows = [
        {"role_id": role_id, "resource": f"plan_resource_{idx}", "action": "read"}
        for idx in range(200)
    ]
    permission_rows.append(
        {"role_id": role_id, "resource": target_resource, "action": target_action}
    )
    await db_plan_session.execute(insert(RolePermission), permission_rows)
    await db_plan_session.execute(text("SET LOCAL enable_seqscan = off"))

    stmt = (
        select(RolePermission)
        .where(RolePermission.role_id == role_id)
        .where(RolePermission.resource == target_resource)
        .where(RolePermission.action == target_action)
        .where(RolePermission.deleted_at.is_(None))
    )
    explain = await _explain_json(db_plan_session, stmt)
    plan = explain["Plan"]
    assert isinstance(plan, dict)

    node_types = _collect_node_types(plan)
    assert "role_permissions" in _collect_relations(plan)
    assert {"Index Scan", "Index Only Scan", "Bitmap Heap Scan"} & node_types
    assert "Seq Scan" not in node_types
