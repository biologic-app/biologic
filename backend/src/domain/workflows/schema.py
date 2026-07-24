"""Workflow schema v2 format contract and validator.

Pure format logic: no web framework, no ORM. A schema version is only ever
persisted after passing :func:`validate_workflow_schema`, so the JSONB stored in
``workflow_schema_versions`` is structurally trustworthy. See
``docs/architecture/2026-07-22-workflow-schema-v2.md``.
"""

from __future__ import annotations

from typing import Any, Literal, NoReturn

from pydantic import BaseModel, ConfigDict
from pydantic import ValidationError as PydanticValidationError

from src.core.errors import ValidationError

NodeType = Literal["start", "step", "condition", "loop", "end"]


class SchemaEdge(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    source: str
    target: str
    sourceHandle: str | None = None


class SchemaNode(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    type: NodeType
    data: dict[str, Any] = {}


class WorkflowSchemaV2(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str
    formatVersion: int
    nodes: list[SchemaNode]
    edges: list[SchemaEdge]


def validate_workflow_schema(raw: dict[str, Any]) -> WorkflowSchemaV2:
    """Parse and validate a v2 schema, raising ``ValidationError`` (422) on any
    structural or semantic violation."""
    try:
        schema = WorkflowSchemaV2.model_validate(raw)
    except PydanticValidationError as exc:
        raise ValidationError(
            "Workflow schema is structurally invalid.",
            extra={"errors": [_safe_error(e) for e in exc.errors()]},
        ) from exc

    _validate_format_version(schema)
    _validate_nodes(schema)
    _validate_edges(schema)
    _validate_screens(schema)
    return schema


def _fail(detail: str) -> NoReturn:
    raise ValidationError(detail)


def _validate_format_version(schema: WorkflowSchemaV2) -> None:
    if schema.formatVersion != 2:
        _fail(f"formatVersion must be 2, got {schema.formatVersion}.")


def _validate_nodes(schema: WorkflowSchemaV2) -> None:
    node_ids = [node.id for node in schema.nodes]
    if len(node_ids) != len(set(node_ids)):
        _fail("Node ids must be unique.")

    starts = [n for n in schema.nodes if n.type == "start"]
    if len(starts) != 1:
        _fail(f"Schema must have exactly one start node, found {len(starts)}.")

    ends = [n for n in schema.nodes if n.type == "end"]
    if not ends:
        _fail("Schema must have at least one end node.")


def _validate_edges(schema: WorkflowSchemaV2) -> None:
    node_ids = {node.id for node in schema.nodes}
    for edge in schema.edges:
        if edge.source not in node_ids:
            _fail(f"Edge {edge.id!r} references unknown source node {edge.source!r}.")
        if edge.target not in node_ids:
            _fail(f"Edge {edge.id!r} references unknown target node {edge.target!r}.")

    for node in schema.nodes:
        if node.type != "condition":
            continue
        handles = {
            edge.sourceHandle
            for edge in schema.edges
            if edge.source == node.id
        }
        if "true" not in handles or "false" not in handles:
            _fail(
                f"Condition node {node.id!r} must have both 'true' and 'false' edges."
            )


def _validate_screens(schema: WorkflowSchemaV2) -> None:
    field_ids: list[str] = []
    computed_exprs: dict[str, Any] = {}

    for node in schema.nodes:
        if node.type not in {"step", "loop"}:
            continue
        screen = node.data.get("screen")
        if screen is None:
            continue
        if not isinstance(screen, dict):
            _fail(f"Node {node.id!r} screen must be an object.")
        for row in _as_list(screen.get("rows"), f"Node {node.id!r} screen.rows"):
            for block in _as_list(row.get("blocks"), f"Node {node.id!r} row.blocks"):
                _validate_block(node.id, block, field_ids, computed_exprs)

    if len(field_ids) != len(set(field_ids)):
        _fail("Field ids must be unique across the schema.")

    _validate_no_computed_cycles(computed_exprs)


def _validate_block(
    node_id: str,
    block: dict[str, Any],
    field_ids: list[str],
    computed_exprs: dict[str, Any],
) -> None:
    span = block.get("span")
    if not isinstance(span, int) or isinstance(span, bool) or not (1 <= span <= 12):
        _fail(f"Block in node {node_id!r} must have span between 1 and 12, got {span!r}.")

    kind = block.get("kind")
    if kind == "field":
        _collect_field(block.get("field"), field_ids, computed_exprs, allow_table=True)
    elif kind == "table":
        table = block.get("table")
        if not isinstance(table, dict):
            _fail(f"Table block in node {node_id!r} must carry a table object.")
        for column in _as_list(table.get("columns"), f"Table in node {node_id!r} columns"):
            if column.get("type") == "table" or column.get("kind") == "table":
                _fail("Nested tables are not allowed: table columns cannot be tables.")
            _collect_field(column, field_ids, computed_exprs, allow_table=False)
    elif kind == "section":
        return
    else:
        _fail(f"Unknown block kind {kind!r} in node {node_id!r}.")


def _collect_field(
    field: Any,
    field_ids: list[str],
    computed_exprs: dict[str, Any],
    *,
    allow_table: bool,
) -> None:
    if not isinstance(field, dict):
        _fail("Field block must carry a field object.")
    field_id = field.get("id")
    if not isinstance(field_id, str) or not field_id:
        _fail("Every field must have a non-empty string id.")
    field_ids.append(field_id)
    if field.get("type") == "computed" and "expr" in field:
        computed_exprs[field_id] = field["expr"]


def _validate_no_computed_cycles(computed_exprs: dict[str, Any]) -> None:
    computed_ids = set(computed_exprs)
    deps = {
        field_id: _referenced_vars(expr) & computed_ids
        for field_id, expr in computed_exprs.items()
    }
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(field_id: str) -> None:
        if field_id in done:
            return
        if field_id in visiting:
            _fail(f"Computed field {field_id!r} is part of a dependency cycle.")
        visiting.add(field_id)
        for dep in deps.get(field_id, set()):
            visit(dep)
        visiting.discard(field_id)
        done.add(field_id)

    for field_id in computed_ids:
        visit(field_id)


def _referenced_vars(expr: Any) -> set[str]:
    """Collect field ids referenced via json-logic ``{"var": "field"}`` nodes."""
    found: set[str] = set()
    if isinstance(expr, dict):
        for key, value in expr.items():
            if key == "var":
                if isinstance(value, str):
                    found.add(value.split(".")[0])
                elif isinstance(value, list) and value and isinstance(value[0], str):
                    found.add(value[0].split(".")[0])
            else:
                found |= _referenced_vars(value)
    elif isinstance(expr, list):
        for item in expr:
            found |= _referenced_vars(item)
    return found


def _as_list(value: Any, label: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        _fail(f"{label} must be a list of objects.")
    return list(value)


def _safe_error(error: Any) -> dict[str, Any]:
    data = dict(error)
    return {key: value for key, value in data.items() if key in {"loc", "msg", "type"}}
