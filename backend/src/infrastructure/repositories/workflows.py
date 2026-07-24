from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud_query import (
    apply_outer_joins,
    attach_sort_values,
    build_crud_query_parts,
    cursor_sort_value,
)
from src.core.cursor_pagination import CursorState, decode_cursor, encode_cursor
from src.core.errors import BadRequestError, NotFoundError
from src.core.pagination import PaginationParams
from src.infrastructure.db.models import (
    Direction,
    DirectionStatus,
    Research,
    ResearchStatus,
    Sample,
    SampleStatus,
    Test,
    TestStatus,
    WorkflowAttachment,
    WorkflowRun,
    WorkflowRunEvent,
    WorkflowSchemaVersion,
    WorkflowStepExecution,
    WorkflowTemplate,
)
from src.infrastructure.repositories.catalogs import RepositoryPage

_TEMPLATE_SORTABLE = ("id", "title", "current_version", "created_at", "updated_at")
_RUN_SORTABLE = ("id", "template_id", "title", "status", "scope_kind", "created_at", "updated_at")

# Maps a domain resource to its entity/status models so execute-step can read
# the current status code for a fast transition pre-check.
_STATUS_ENTITY: dict[str, tuple[type[Any], type[Any]]] = {
    "tests": (Test, TestStatus),
    "samples": (Sample, SampleStatus),
    "research": (Research, ResearchStatus),
    "directions": (Direction, DirectionStatus),
}


class SqlAlchemyWorkflowsRepository:
    """Workflows aggregate repository. Only flushes; the single Unit of Work owns
    the transaction boundary, so execute-step and its domain mutations commit
    atomically on one session."""

    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    # Templates -----------------------------------------------------------
    async def list_templates(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, WorkflowTemplate, params, _TEMPLATE_SORTABLE)

    async def get_template(self, template_id: UUID) -> WorkflowTemplate:
        row = await self.session.execute(
            select(WorkflowTemplate).where(
                WorkflowTemplate.id == template_id,
                WorkflowTemplate.deleted_at.is_(None),
            ),
        )
        template = row.scalar_one_or_none()
        if template is None:
            raise NotFoundError(f"Workflow template {template_id} was not found.")
        return template

    async def create_template(self, values: dict[str, Any]) -> WorkflowTemplate:
        template = WorkflowTemplate(
            title=values["title"],
            current_version=values.get("current_version", 0),
        )
        self.session.add(template)
        await self.session.flush()
        await self.session.refresh(template)
        return template

    async def update_template(self, template_id: UUID, values: dict[str, Any]) -> WorkflowTemplate:
        template = await self.get_template(template_id)
        for field in ("title", "current_version"):
            if field in values:
                setattr(template, field, values[field])
        template.updated_at = datetime.now(UTC)
        self.session.add(template)
        await self.session.flush()
        await self.session.refresh(template)
        return template

    async def delete_template(self, template_id: UUID) -> None:
        template = await self.get_template(template_id)
        now = datetime.now(UTC)
        template.deleted_at = now
        template.updated_at = now
        self.session.add(template)
        await self.session.flush()

    # Schema versions -----------------------------------------------------
    async def list_versions(self, template_id: UUID) -> list[WorkflowSchemaVersion]:
        rows = await self.session.execute(
            select(WorkflowSchemaVersion)
            .where(WorkflowSchemaVersion.template_id == template_id)
            .order_by(asc(WorkflowSchemaVersion.version)),
        )
        return list(rows.scalars().all())

    async def get_version(self, template_id: UUID, version: int) -> WorkflowSchemaVersion | None:
        rows = await self.session.execute(
            select(WorkflowSchemaVersion).where(
                WorkflowSchemaVersion.template_id == template_id,
                WorkflowSchemaVersion.version == version,
            ),
        )
        return rows.scalar_one_or_none()

    async def next_version_number(self, template_id: UUID) -> int:
        result = await self.session.execute(
            select(func.max(WorkflowSchemaVersion.version)).where(
                WorkflowSchemaVersion.template_id == template_id,
            ),
        )
        current = result.scalar_one_or_none()
        return int(current) + 1 if current is not None else 1

    async def create_version(
        self,
        template_id: UUID,
        version: int,
        schema: dict[str, Any],
    ) -> WorkflowSchemaVersion:
        row = WorkflowSchemaVersion(template_id=template_id, version=version, schema=schema)
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    # Runs ----------------------------------------------------------------
    async def list_runs(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, WorkflowRun, params, _RUN_SORTABLE)

    async def get_run(self, run_id: UUID) -> WorkflowRun:
        row = await self.session.execute(
            select(WorkflowRun).where(
                WorkflowRun.id == run_id,
                WorkflowRun.deleted_at.is_(None),
            ),
        )
        run = row.scalar_one_or_none()
        if run is None:
            raise NotFoundError(f"Workflow run {run_id} was not found.")
        return run

    async def create_run(self, values: dict[str, Any]) -> WorkflowRun:
        run = WorkflowRun(
            template_id=values["template_id"],
            schema_version=values["schema_version"],
            title=values["title"],
            scope_kind=values.get("scope_kind"),
            scope_id=values.get("scope_id"),
            status=values.get("status", "draft"),
            answers=values.get("answers", {}),
            loops=values.get("loops", {}),
            history=values.get("history", []),
            current_node_id=values.get("current_node_id"),
            created_by=values.get("created_by"),
        )
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_run(self, run_id: UUID, values: dict[str, Any]) -> WorkflowRun:
        run = await self.get_run(run_id)
        for field in ("title", "answers", "loops", "current_node_id", "history"):
            if field in values:
                setattr(run, field, values[field])
        run.updated_at = datetime.now(UTC)
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def delete_run(self, run_id: UUID) -> None:
        run = await self.get_run(run_id)
        now = datetime.now(UTC)
        run.deleted_at = now
        run.updated_at = now
        self.session.add(run)
        await self.session.flush()

    async def set_run_status(self, run_id: UUID, status: str) -> WorkflowRun:
        run = await self.get_run(run_id)
        run.status = status
        run.updated_at = datetime.now(UTC)
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    # Events --------------------------------------------------------------
    async def append_event(
        self,
        run_id: UUID,
        kind: str,
        node_id: str | None,
        payload: dict[str, Any],
        author: str | None,
    ) -> WorkflowRunEvent:
        event = WorkflowRunEvent(
            run_id=run_id,
            kind=kind,
            node_id=node_id,
            payload=payload,
            author=author,
        )
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def list_events(self, run_id: UUID) -> list[WorkflowRunEvent]:
        rows = await self.session.execute(
            select(WorkflowRunEvent)
            .where(WorkflowRunEvent.run_id == run_id)
            .order_by(asc(WorkflowRunEvent.created_at)),
        )
        return list(rows.scalars().all())

    # Step executions -----------------------------------------------------
    async def find_step_execution(
        self,
        run_id: UUID,
        node_id: str,
        attempt: int,
    ) -> WorkflowStepExecution | None:
        rows = await self.session.execute(
            select(WorkflowStepExecution).where(
                WorkflowStepExecution.run_id == run_id,
                WorkflowStepExecution.node_id == node_id,
                WorkflowStepExecution.attempt == attempt,
            ),
        )
        return rows.scalar_one_or_none()

    async def record_step_execution(
        self,
        run_id: UUID,
        node_id: str,
        attempt: int,
        status: str,
        result: dict[str, Any],
    ) -> WorkflowStepExecution:
        row = WorkflowStepExecution(
            run_id=run_id,
            node_id=node_id,
            attempt=attempt,
            status=status,
            result=result,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    # Attachments ---------------------------------------------------------
    async def create_attachment(
        self,
        run_id: UUID,
        field_id: str,
        filename: str,
        content_type: str | None,
        size_bytes: int,
        data: bytes,
    ) -> WorkflowAttachment:
        attachment = WorkflowAttachment(
            run_id=run_id,
            field_id=field_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            data=data,
        )
        self.session.add(attachment)
        await self.session.flush()
        await self.session.refresh(attachment)
        return attachment

    async def get_attachment(self, attachment_id: UUID) -> WorkflowAttachment:
        row = await self.session.execute(
            select(WorkflowAttachment).where(WorkflowAttachment.id == attachment_id),
        )
        attachment = row.scalar_one_or_none()
        if attachment is None:
            raise NotFoundError(f"Workflow attachment {attachment_id} was not found.")
        return attachment

    # Domain correlation read --------------------------------------------
    async def read_status_code(self, resource: str, entity_id: UUID) -> str | None:
        entry = _STATUS_ENTITY.get(resource)
        if entry is None:
            raise BadRequestError(f"Unknown domain resource {resource!r}.")
        entity_model, status_model = entry
        result = await self.session.execute(
            select(status_model.code)
            .join(entity_model, entity_model.status_id == status_model.id)
            .where(entity_model.id == entity_id, entity_model.deleted_at.is_(None)),
        )
        return result.scalar_one_or_none()


async def _list_rows(
    session: AsyncSession,
    model: type[Any],
    params: PaginationParams,
    sortable_fields: tuple[str, ...],
) -> RepositoryPage:
    query_parts = build_crud_query_parts(
        model=model,
        params=params,
        sortable_fields=sortable_fields,
        base_filters=[model.deleted_at.is_(None)],
    )
    sort_by = query_parts.sort_by
    sort_column = query_parts.sort_column
    id_column = model.id

    filters = list(query_parts.filters)
    total_filters = list(filters)
    cursor = decode_cursor(params.cursor) if params.cursor else None
    if cursor is not None:
        if cursor.sort_by != sort_by or cursor.sort_order != params.sort_order:
            raise BadRequestError("Pagination cursor does not match requested sorting.")
        filters.append(_cursor_filter(cursor, sort_column, id_column))

    total_query = apply_outer_joins(
        select(func.count()).select_from(model),
        query_parts.joins,
    ).where(*total_filters)
    total = int((await session.execute(total_query)).scalar_one())

    order_fn = asc if params.sort_order == "asc" else desc
    query = apply_outer_joins(select(model, sort_column), query_parts.joins)
    query = (
        query.where(*filters)
        .order_by(order_fn(sort_column), order_fn(id_column))
        .limit(params.limit + 1)
    )
    rows = attach_sort_values(list((await session.execute(query)).all()))
    items = rows[: params.limit]
    has_more = len(rows) > params.limit
    next_cursor = _next_cursor(items, sort_by, params.sort_order) if has_more else None
    return RepositoryPage(items=items, total=total, has_more=has_more, next_cursor=next_cursor)


def _cursor_filter(cursor: CursorState, sort_column: Any, id_column: Any) -> Any:
    sort_value = _coerce_cursor_value(sort_column, cursor.sort_value)
    if cursor.sort_order == "asc":
        return or_(
            sort_column > sort_value,
            and_(sort_column == sort_value, id_column > cursor.item_id),
        )
    return or_(
        sort_column < sort_value,
        and_(sort_column == sort_value, id_column < cursor.item_id),
    )


def _coerce_cursor_value(column: Any, value: Any) -> Any:
    try:
        python_type = column.property.columns[0].type.python_type
    except (AttributeError, NotImplementedError):
        return value
    if python_type is datetime and isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if python_type is UUID and isinstance(value, str):
        return UUID(value)
    if python_type is int and not isinstance(value, int):
        return int(value)
    return value


def _next_cursor(items: list[Any], sort_by: str, sort_order: str) -> str | None:
    if not items:
        return None
    last = items[-1]
    return encode_cursor(
        sort_by=sort_by,
        sort_order=sort_order,
        sort_value=cursor_sort_value(last, sort_by),
        item_id=last.id,
    )
