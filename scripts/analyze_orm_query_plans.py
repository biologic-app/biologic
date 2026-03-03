from __future__ import annotations

import argparse
import asyncio
import importlib
import inspect
import json
import pkgutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import Select, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from scripts import seed_data
from src.models.base import Base
from src.repositories.crud_repository import CRUDRepository, ListQuery


@dataclass(slots=True, frozen=True)
class AnalysisSettings:
    database_url: str
    report_path: Path
    report_json_path: Path
    catalog_path: Path
    list_limit: int
    execution_time_warn_ms: float
    seq_scan_warn_rows: int
    row_mismatch_ratio_warn: float
    include_seed: bool
    seed_profile: str


@dataclass(slots=True, frozen=True)
class QuerySpec:
    query_id: str
    repository: str
    model: str
    table: str
    method: str
    purpose: str
    sql: str


@dataclass(slots=True, frozen=True)
class PlanIssue:
    severity: str
    code: str
    message: str


@dataclass(slots=True, frozen=True)
class QueryAnalysis:
    query_id: str
    repository: str
    model: str
    table: str
    method: str
    purpose: str
    sql: str
    planning_time_ms: float
    execution_time_ms: float
    node_types: list[str]
    relations: list[str]
    issues: list[PlanIssue]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Seed test data and analyze EXPLAIN plans for every ORM query in repositories."
        )
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database DSN. Defaults to APP_ALEMBIC_DATABASE_URL/APP_DATABASE_URL.",
    )
    parser.add_argument(
        "--seed-profile",
        choices=sorted(seed_data.PROFILE_DEFAULTS.keys()),
        default="perf-lite",
        help="Seed profile used before plan analysis.",
    )
    parser.add_argument(
        "--skip-seed",
        action="store_true",
        help="Skip seed generation and analyze the current database state.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Pass --truncate to seed generation.",
    )
    parser.add_argument(
        "--reference-count",
        type=int,
        default=None,
        help="Override reference entities count for seed phase.",
    )
    parser.add_argument(
        "--directions",
        type=int,
        default=None,
        help="Override directions count for seed phase.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=None,
        help="Override samples count for seed phase.",
    )
    parser.add_argument(
        "--research",
        type=int,
        default=None,
        help="Override research count for seed phase.",
    )
    parser.add_argument(
        "--tests",
        type=int,
        default=None,
        help="Override tests count for seed phase.",
    )
    parser.add_argument(
        "--list-limit",
        type=int,
        default=25,
        help="LIMIT used for repository list() items query.",
    )
    parser.add_argument(
        "--execution-time-warn-ms",
        type=float,
        default=50.0,
        help="Warn when Execution Time exceeds this value.",
    )
    parser.add_argument(
        "--seq-scan-warn-rows",
        type=int,
        default=1000,
        help="Warn on Seq Scan nodes with Actual Rows >= threshold.",
    )
    parser.add_argument(
        "--row-mismatch-ratio-warn",
        type=float,
        default=20.0,
        help="Warn when |planned rows / actual rows| exceeds this ratio.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("artifacts/orm-query-plan-report.md"),
        help="Markdown output with plan analysis findings.",
    )
    parser.add_argument(
        "--report-json-path",
        type=Path,
        default=Path("artifacts/orm-query-plan-report.json"),
        help="JSON output with plan analysis findings.",
    )
    parser.add_argument(
        "--catalog-path",
        type=Path,
        default=Path("docs/content/repository-query-catalog.md"),
        help="Markdown output documenting SQL queries and their purpose.",
    )
    return parser.parse_args()


def _to_async_sqlalchemy_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + database_url.split("://", 1)[1]
    return database_url


def _mask_database_url(database_url: str) -> str:
    try:
        parsed = make_url(database_url)
    except Exception:
        return database_url
    if parsed.password is None:
        return str(parsed)
    return str(parsed.set(password="***"))


def _build_settings(args: argparse.Namespace, resolved_database_url: str) -> AnalysisSettings:
    return AnalysisSettings(
        database_url=resolved_database_url,
        report_path=args.report_path,
        report_json_path=args.report_json_path,
        catalog_path=args.catalog_path,
        list_limit=args.list_limit,
        execution_time_warn_ms=args.execution_time_warn_ms,
        seq_scan_warn_rows=args.seq_scan_warn_rows,
        row_mismatch_ratio_warn=args.row_mismatch_ratio_warn,
        include_seed=not args.skip_seed,
        seed_profile=args.seed_profile,
    )


def _compile_sql(statement: Select[Any]) -> str:
    dialect_factory = cast(Any, postgresql.dialect)
    return str(
        statement.compile(
            dialect=dialect_factory(),
            compile_kwargs={"literal_binds": True},
        )
    )


def _discover_repository_classes() -> list[type[CRUDRepository[Any]]]:
    package = importlib.import_module("src.repositories")
    classes: list[type[CRUDRepository[Any]]] = []

    for module_info in pkgutil.iter_modules(package.__path__):
        module_name = module_info.name
        if module_name == "crud_repository" or not module_name.endswith("_repository"):
            continue
        module = importlib.import_module(f"src.repositories.{module_name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module.__name__:
                continue
            if obj is CRUDRepository or not issubclass(obj, CRUDRepository):
                continue
            init_sig = inspect.signature(obj.__init__)
            if "session" not in init_sig.parameters:
                continue
            classes.append(obj)

    return sorted(classes, key=lambda cls: (cls.__module__, cls.__name__))


def _column_names(model: type[Base]) -> list[str]:
    return [column.name for column in model.__table__.columns]


def _pick_sort_field(model: type[Base]) -> str:
    names = _column_names(model)
    for candidate in ("created_at", "updated_at", "id"):
        if candidate in names:
            return candidate
    return names[0]


def _soft_delete_condition(model: type[Base]) -> Any | None:
    deleted_at = getattr(model, "deleted_at", None)
    if deleted_at is None:
        return None
    return deleted_at.is_(None)


async def _fetch_first_id(session: AsyncSession, model: type[Base]) -> Any | None:
    id_column = getattr(model, "id", None)
    if id_column is None:
        return None
    stmt = select(id_column)
    condition = _soft_delete_condition(model)
    if condition is not None:
        stmt = stmt.where(condition)
    stmt = stmt.limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _build_repository_query_specs(
    session: AsyncSession,
    repository_class: type[CRUDRepository[Any]],
    settings: AnalysisSettings,
) -> list[QuerySpec]:
    repository = cast(Any, repository_class)(session=session)
    model = cast(type[Base], repository._model)
    repository_name = f"{repository_class.__module__}.{repository_class.__name__}"
    model_name = model.__name__
    table_name = model.__tablename__
    query_specs: list[QuerySpec] = []

    entity_id = await _fetch_first_id(session, model)
    if entity_id is None and hasattr(model, "id"):
        entity_id = uuid4()

    if entity_id is not None and hasattr(model, "id"):
        model_id_column = cast(Any, model.id)
        get_stmt = select(model).where(model_id_column == entity_id)
        get_stmt = repository._with_soft_delete_filter(get_stmt)
        query_specs.append(
            QuerySpec(
                query_id=f"{repository_name}.get",
                repository=repository_name,
                model=model_name,
                table=table_name,
                method="get",
                purpose=("Fetch a single entity by primary key with soft-delete filter."),
                sql=_compile_sql(get_stmt),
            )
        )

    sort_field = _pick_sort_field(model)
    list_query = ListQuery(
        offset=0,
        limit=settings.list_limit,
        sort_by=sort_field,
        sort_order="desc",
    )
    base_stmt = select(model)
    base_stmt = repository._with_soft_delete_filter(base_stmt)
    base_stmt = repository._with_list_filters(base_stmt, list_query)
    sort_clause = repository._resolve_sort_column(
        list_query,
        allowed_sort_fields=set(_column_names(model)),
    )
    total_stmt = repository._build_total_stmt(query=list_query, base_stmt=base_stmt)
    items_stmt = base_stmt.order_by(sort_clause).offset(list_query.offset).limit(list_query.limit)

    query_specs.append(
        QuerySpec(
            query_id=f"{repository_name}.list.total",
            repository=repository_name,
            model=model_name,
            table=table_name,
            method="list.total",
            purpose="Подсчет общего количества строк для pagination meta.total.",
            sql=_compile_sql(total_stmt),
        )
    )
    query_specs.append(
        QuerySpec(
            query_id=f"{repository_name}.list.items",
            repository=repository_name,
            model=model_name,
            table=table_name,
            method="list.items",
            purpose="Чтение страницы данных c сортировкой, offset и limit.",
            sql=_compile_sql(items_stmt),
        )
    )

    for include_name in sorted(repository.allowed_includes):
        target_model = repository._include_targets.get(include_name)
        if target_model is None:
            continue
        target_id = await _fetch_first_id(session, target_model)
        if target_id is None:
            target_id = uuid4()
        target_id_column = getattr(target_model, "id", None)
        if target_id_column is None:
            continue
        stmt = select(target_model).where(target_id_column == target_id)
        target_deleted_at = getattr(target_model, "deleted_at", None)
        if target_deleted_at is not None:
            stmt = stmt.where(target_deleted_at.is_(None))
        query_specs.append(
            QuerySpec(
                query_id=f"{repository_name}.resolve_include_reference.{include_name}",
                repository=repository_name,
                model=model_name,
                table=target_model.__tablename__,
                method=f"resolve_include_reference({include_name})",
                purpose=(f"Загрузка include-ссылки `{include_name}` по FK для обогащения DTO."),
                sql=_compile_sql(stmt),
            )
        )

    return query_specs


def _walk_plan_nodes(plan_node: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    stack = [plan_node]
    while stack:
        node = stack.pop()
        nodes.append(node)
        children = node.get("Plans")
        if isinstance(children, list):
            stack.extend(child for child in children if isinstance(child, dict))
    return nodes


def _extract_issue_candidates(
    explain_json: dict[str, Any],
    settings: AnalysisSettings,
) -> tuple[float, float, list[str], list[str], list[PlanIssue]]:
    planning_ms = float(explain_json.get("Planning Time", 0.0))
    execution_ms = float(explain_json.get("Execution Time", 0.0))
    root_plan = cast(dict[str, Any], explain_json["Plan"])
    nodes = _walk_plan_nodes(root_plan)

    node_types = sorted({str(node.get("Node Type")) for node in nodes if node.get("Node Type")})
    relations = sorted(
        {str(node.get("Relation Name")) for node in nodes if node.get("Relation Name")}
    )
    issues: list[PlanIssue] = []

    if execution_ms >= settings.execution_time_warn_ms:
        issues.append(
            PlanIssue(
                severity="medium",
                code="slow_execution_time",
                message=(
                    f"Execution Time {execution_ms:.2f} ms >= "
                    f"{settings.execution_time_warn_ms:.2f} ms."
                ),
            )
        )

    for node in nodes:
        if node.get("Node Type") != "Seq Scan":
            continue
        actual_rows = float(node.get("Actual Rows", 0.0))
        if actual_rows < settings.seq_scan_warn_rows:
            continue
        relation = str(node.get("Relation Name", "<unknown_table>"))
        issues.append(
            PlanIssue(
                severity="high",
                code="large_seq_scan",
                message=(
                    f"Seq Scan on `{relation}` with Actual Rows={actual_rows:.0f} "
                    f"(threshold={settings.seq_scan_warn_rows})."
                ),
            )
        )

    max_mismatch_ratio = 1.0
    for node in nodes:
        plan_rows_raw = node.get("Plan Rows")
        actual_rows_raw = node.get("Actual Rows")
        if not isinstance(plan_rows_raw, (int, float)) or not isinstance(
            actual_rows_raw,
            (int, float),
        ):
            continue
        plan_rows = float(plan_rows_raw)
        actual_rows = float(actual_rows_raw)
        if plan_rows <= 0 or actual_rows <= 0:
            continue
        ratio = max(actual_rows / plan_rows, plan_rows / actual_rows)
        max_mismatch_ratio = max(max_mismatch_ratio, ratio)
    if max_mismatch_ratio >= settings.row_mismatch_ratio_warn:
        issues.append(
            PlanIssue(
                severity="medium",
                code="row_estimate_mismatch",
                message=(
                    "Large row estimate mismatch: "
                    f"max ratio={max_mismatch_ratio:.2f}, "
                    f"threshold={settings.row_mismatch_ratio_warn:.2f}."
                ),
            )
        )

    for node in nodes:
        if node.get("Node Type") != "Sort":
            continue
        sort_method = str(node.get("Sort Method", "")).lower()
        if "external" not in sort_method:
            continue
        issues.append(
            PlanIssue(
                severity="high",
                code="external_sort",
                message=f"External sort detected: `{node.get('Sort Method')}`.",
            )
        )

    return planning_ms, execution_ms, node_types, relations, issues


async def _explain_query(
    session: AsyncSession, query_spec: QuerySpec, settings: AnalysisSettings
) -> QueryAnalysis:
    explain_sql = (
        "EXPLAIN (ANALYZE true, BUFFERS true, SETTINGS true, WAL true, "
        f"TIMING false, SUMMARY true, FORMAT JSON) {query_spec.sql}"
    )
    result = await session.execute(text(explain_sql))
    payload = result.scalar_one()
    parsed = json.loads(payload) if isinstance(payload, str) else payload
    if not isinstance(parsed, list) or not parsed or not isinstance(parsed[0], dict):
        raise RuntimeError(f"Unexpected EXPLAIN JSON payload for `{query_spec.query_id}`.")
    explain_json = cast(dict[str, Any], parsed[0])

    planning_ms, execution_ms, node_types, relations, issues = _extract_issue_candidates(
        explain_json=explain_json,
        settings=settings,
    )

    return QueryAnalysis(
        query_id=query_spec.query_id,
        repository=query_spec.repository,
        model=query_spec.model,
        table=query_spec.table,
        method=query_spec.method,
        purpose=query_spec.purpose,
        sql=query_spec.sql,
        planning_time_ms=planning_ms,
        execution_time_ms=execution_ms,
        node_types=node_types,
        relations=relations,
        issues=issues,
    )


def _render_catalog_markdown(
    *,
    generated_at: datetime,
    masked_database_url: str,
    query_specs: list[QuerySpec],
    analyses: list[QueryAnalysis],
) -> str:
    del analyses

    def _describe_query_behavior(spec: QuerySpec) -> str:
        method = spec.method
        if method == "get":
            return "Читает одну запись по первичному ключу " "c учетом правил soft-delete."
        if method == "list.total":
            return "Считает общее количество строк для `pagination.meta.total`."
        if method == "list.items":
            return (
                "Возвращает страницу данных по `offset/limit` "
                "c сортировкой и примененными фильтрами."
            )
        if method.startswith("resolve_include_reference(") and method.endswith(")"):
            include_name = method[len("resolve_include_reference(") : -1]
            return (
                f"Загружает связанную сущность `{include_name}` "
                "по внешнему ключу для include-обогащения ответа."
            )
        if method == "get_by_pk":
            return "Читает запись по составному первичному ключу."
        return (
            "Выполняет специализированный ORM-запрос репозитория " "в рамках CRUD/бизнес-операции."
        )

    def _display_name(spec: QuerySpec) -> str:
        repository_name = spec.repository.rsplit(".", maxsplit=1)[-1]
        return f"{repository_name}.{spec.method}"

    lines: list[str] = [
        "---",
        "icon: lucide/database-zap",
        "tags:",
        "  - Database",
        "  - SQL",
        "  - Performance",
        "---",
        "",
        "# Каталог ORM SQL-запросов репозиториев",
        "",
        f"_Сгенерировано: {generated_at.isoformat()}_",
        "",
        f"_База: `{masked_database_url}`_",
        "",
        '!!! note "Назначение документа"',
        (
            "    Это автоматически сгенерированный каталог SQL-запросов, "
            "которые формируются ORM-слоем `app/repositories`."
        ),
        (
            "    Каталог содержит только детализацию запросов: "
            "подзаголовок, текст запроса и раскрывающийся блок пояснений."
        ),
        "",
        "## Детализация запросов",
        "",
    ]
    for spec in query_specs:
        display_name = _display_name(spec)
        behavior = _describe_query_behavior(spec)
        lines.extend(
            [
                f"### `{display_name}`",
                "",
                "```sql",
                spec.sql.rstrip(),
                "```",
                "",
                '??? note "Детали запроса"',
                "",
                f"    - Для чего нужен: {spec.purpose}",
                f"    - Что делает: {behavior}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _render_analysis_markdown(
    *,
    generated_at: datetime,
    masked_database_url: str,
    settings: AnalysisSettings,
    analyses: list[QueryAnalysis],
) -> str:
    total = len(analyses)
    with_issues = sum(1 for analysis in analyses if analysis.issues)
    high = sum(1 for analysis in analyses for issue in analysis.issues if issue.severity == "high")
    medium = sum(
        1 for analysis in analyses for issue in analysis.issues if issue.severity == "medium"
    )

    lines: list[str] = [
        "# ORM Query Plan Analysis Report",
        "",
        f"_Generated at: {generated_at.isoformat()}_",
        "",
        f"_Database: `{masked_database_url}`_",
        "",
        "## Summary",
        "",
        f"- Total queries analyzed: `{total}`",
        f"- Queries with issues: `{with_issues}`",
        f"- High severity issues: `{high}`",
        f"- Medium severity issues: `{medium}`",
        f"- Execution time warning threshold: `{settings.execution_time_warn_ms:.2f} ms`",
        f"- Seq Scan rows warning threshold: `{settings.seq_scan_warn_rows}`",
        f"- Plan/actual mismatch warning threshold: `{settings.row_mismatch_ratio_warn:.2f}`",
        "",
    ]

    def _describe_query_behavior(*, method: str) -> str:
        if method == "get":
            return "Читает одну запись по первичному ключу " "c учетом правил soft-delete."
        if method == "list.total":
            return "Считает общее количество строк для `pagination.meta.total`."
        if method == "list.items":
            return (
                "Возвращает страницу данных по `offset/limit` "
                "c сортировкой и примененными фильтрами."
            )
        if method.startswith("resolve_include_reference(") and method.endswith(")"):
            include_name = method[len("resolve_include_reference(") : -1]
            return (
                f"Загружает связанную сущность `{include_name}` "
                "по внешнему ключу для include-обогащения ответа."
            )
        if method == "get_by_pk":
            return "Читает запись по составному первичному ключу."
        return (
            "Выполняет специализированный ORM-запрос репозитория " "в рамках CRUD/бизнес-операции."
        )

    for analysis in analyses:
        repository_name = analysis.repository.rsplit(".", maxsplit=1)[-1]
        report_heading = f"{repository_name}.{analysis.method}"
        behavior = _describe_query_behavior(method=analysis.method)
        issue_total = len(analysis.issues)
        issue_high = sum(1 for issue in analysis.issues if issue.severity == "high")
        issue_medium = sum(1 for issue in analysis.issues if issue.severity == "medium")

        lines.extend(
            [
                f"### `{report_heading}`",
                "",
                "```sql",
                analysis.sql.rstrip(),
                "```",
                "",
                '??? note "Детали запроса"',
                "",
                f"    - Для чего нужен: {analysis.purpose}",
                f"    - Что делает: {behavior}",
                f"    - Метрики: planning=`{analysis.planning_time_ms:.3f} ms`, "
                f"execution=`{analysis.execution_time_ms:.3f} ms`",
                f"    - Операторы плана: `{', '.join(analysis.node_types) or '-'}`",
                f"    - Отношения: `{', '.join(analysis.relations) or '-'}`",
                (
                    f"    - Проблемы: total=`{issue_total}`, "
                    f"high=`{issue_high}`, medium=`{issue_medium}`"
                ),
            ]
        )

        if analysis.issues:
            for issue in analysis.issues:
                lines.append(
                    "    - Проблема: " f"[{issue.severity}] `{issue.code}` — {issue.message}"
                )
        else:
            lines.append("    - Проблема: не обнаружено")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _serialize_json_payload(
    *,
    generated_at: datetime,
    masked_database_url: str,
    settings: AnalysisSettings,
    analyses: list[QueryAnalysis],
) -> dict[str, Any]:
    return {
        "generated_at": generated_at.isoformat(),
        "database_url": masked_database_url,
        "settings": {
            "list_limit": settings.list_limit,
            "execution_time_warn_ms": settings.execution_time_warn_ms,
            "seq_scan_warn_rows": settings.seq_scan_warn_rows,
            "row_mismatch_ratio_warn": settings.row_mismatch_ratio_warn,
            "include_seed": settings.include_seed,
            "seed_profile": settings.seed_profile,
        },
        "summary": {
            "total_queries": len(analyses),
            "queries_with_issues": sum(1 for analysis in analyses if analysis.issues),
            "high_issues": sum(
                1 for analysis in analyses for issue in analysis.issues if issue.severity == "high"
            ),
            "medium_issues": sum(
                1
                for analysis in analyses
                for issue in analysis.issues
                if issue.severity == "medium"
            ),
        },
        "queries": [
            {
                "query_id": analysis.query_id,
                "repository": analysis.repository,
                "model": analysis.model,
                "table": analysis.table,
                "method": analysis.method,
                "purpose": analysis.purpose,
                "sql": analysis.sql,
                "planning_time_ms": analysis.planning_time_ms,
                "execution_time_ms": analysis.execution_time_ms,
                "node_types": analysis.node_types,
                "relations": analysis.relations,
                "issues": [asdict(issue) for issue in analysis.issues],
            }
            for analysis in analyses
        ],
    }


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def _seed_if_requested(args: argparse.Namespace) -> str:
    seed_args = argparse.Namespace(
        profile=args.seed_profile,
        database_url=args.database_url,
        reference_count=args.reference_count,
        directions=args.directions,
        samples=args.samples,
        research=args.research,
        tests=args.tests,
        truncate=args.truncate,
    )
    plan = seed_data.build_plan(seed_args)
    if args.skip_seed:
        return plan.database_url
    print(f"[seed] Running seed profile `{args.seed_profile}`...")
    await seed_data.run_seed(plan)
    return plan.database_url


async def run() -> None:
    args = parse_args()
    resolved_database_url = await _seed_if_requested(args)
    settings = _build_settings(args, resolved_database_url)
    masked_url = _mask_database_url(settings.database_url)
    async_database_url = _to_async_sqlalchemy_url(settings.database_url)

    engine = create_async_engine(async_database_url, pool_pre_ping=True)
    all_specs: list[QuerySpec] = []
    analyses: list[QueryAnalysis] = []
    try:
        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                await session.execute(text("ANALYZE"))

                repository_classes = _discover_repository_classes()
                for repository_class in repository_classes:
                    specs = await _build_repository_query_specs(session, repository_class, settings)
                    all_specs.extend(specs)

                for query_spec in all_specs:
                    analyses.append(await _explain_query(session, query_spec, settings))
        except SQLAlchemyError as exc:
            raise RuntimeError(
                "Failed to run ORM query plan analysis. "
                "Check database credentials, connection, and applied migrations."
            ) from exc
    finally:
        await engine.dispose()

    generated_at = datetime.now(UTC)
    catalog_md = _render_catalog_markdown(
        generated_at=generated_at,
        masked_database_url=masked_url,
        query_specs=all_specs,
        analyses=analyses,
    )
    report_md = _render_analysis_markdown(
        generated_at=generated_at,
        masked_database_url=masked_url,
        settings=settings,
        analyses=analyses,
    )
    report_json = _serialize_json_payload(
        generated_at=generated_at,
        masked_database_url=masked_url,
        settings=settings,
        analyses=analyses,
    )

    _write_text(settings.catalog_path, catalog_md)
    _write_text(settings.report_path, report_md)
    _write_json(settings.report_json_path, report_json)

    issue_count = sum(len(analysis.issues) for analysis in analyses)
    print(f"[done] Query specs analyzed: {len(analyses)}")
    print(f"[done] Issues detected: {issue_count}")
    print(f"[done] SQL catalog: {settings.catalog_path}")
    print(f"[done] Markdown report: {settings.report_path}")
    print(f"[done] JSON report: {settings.report_json_path}")


def main() -> None:
    try:
        asyncio.run(run())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
