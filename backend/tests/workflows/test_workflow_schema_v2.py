from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from src.core.errors import ValidationError
from src.domain.workflows.schema import validate_workflow_schema


def _valid_schema() -> dict[str, Any]:
    return {
        "formatVersion": 2,
        "title": "Sample",
        "nodes": [
            {"id": "n1", "type": "start", "data": {"label": "Start"}},
            {
                "id": "n2",
                "type": "step",
                "data": {
                    "label": "Step",
                    "screen": {
                        "rows": [
                            {
                                "id": "r1",
                                "blocks": [
                                    {
                                        "id": "b1",
                                        "span": 6,
                                        "kind": "field",
                                        "field": {"id": "f1", "label": "F1", "type": "text"},
                                    },
                                    {
                                        "id": "b2",
                                        "span": 6,
                                        "kind": "field",
                                        "field": {"id": "f2", "label": "F2", "type": "number"},
                                    },
                                ],
                            }
                        ]
                    },
                },
            },
            {"id": "n3", "type": "end", "data": {"label": "End"}},
        ],
        "edges": [
            {"id": "e1", "source": "n1", "target": "n2"},
            {"id": "e2", "source": "n2", "target": "n3"},
        ],
    }


def _condition_schema() -> dict[str, Any]:
    return {
        "formatVersion": 2,
        "title": "Cond",
        "nodes": [
            {"id": "n1", "type": "start", "data": {"label": "Start"}},
            {"id": "n2", "type": "condition", "data": {"label": "?", "rule": {}}},
            {"id": "n3", "type": "end", "data": {"label": "End"}},
        ],
        "edges": [
            {"id": "e1", "source": "n1", "target": "n2"},
            {"id": "e2", "source": "n2", "sourceHandle": "true", "target": "n3"},
            {"id": "e3", "source": "n2", "sourceHandle": "false", "target": "n3"},
        ],
    }


def test_valid_schema_passes() -> None:
    schema = validate_workflow_schema(_valid_schema())
    assert schema.formatVersion == 2


def test_valid_condition_schema_passes() -> None:
    assert validate_workflow_schema(_condition_schema()).title == "Cond"


def test_rejects_wrong_format_version() -> None:
    raw = _valid_schema()
    raw["formatVersion"] = 1
    with pytest.raises(ValidationError):
        validate_workflow_schema(raw)


def test_rejects_missing_start() -> None:
    raw = _valid_schema()
    raw["nodes"][0]["type"] = "step"
    raw["nodes"][0]["data"] = {"label": "x", "screen": {"rows": []}}
    with pytest.raises(ValidationError):
        validate_workflow_schema(raw)


def test_rejects_missing_end() -> None:
    raw = _valid_schema()
    raw["nodes"][2]["type"] = "step"
    raw["nodes"][2]["data"] = {"label": "x", "screen": {"rows": []}}
    with pytest.raises(ValidationError):
        validate_workflow_schema(raw)


def test_rejects_broken_edge() -> None:
    raw = _valid_schema()
    raw["edges"][1]["target"] = "does-not-exist"
    with pytest.raises(ValidationError):
        validate_workflow_schema(raw)


def test_rejects_condition_without_both_branches() -> None:
    raw = _condition_schema()
    # Drop the 'false' edge.
    raw["edges"] = [e for e in raw["edges"] if e.get("sourceHandle") != "false"]
    with pytest.raises(ValidationError):
        validate_workflow_schema(raw)


def test_rejects_span_over_12() -> None:
    raw = _valid_schema()
    raw["nodes"][1]["data"]["screen"]["rows"][0]["blocks"][0]["span"] = 13
    with pytest.raises(ValidationError):
        validate_workflow_schema(raw)


def test_rejects_nested_table() -> None:
    raw = _valid_schema()
    raw["nodes"][1]["data"]["screen"]["rows"][0]["blocks"] = [
        {
            "id": "t1",
            "span": 12,
            "kind": "table",
            "table": {
                "fieldId": "rows",
                "label": "Rows",
                "columns": [
                    {"id": "c1", "label": "C1", "type": "text"},
                    {"id": "c2", "label": "C2", "type": "table"},
                ],
            },
        }
    ]
    with pytest.raises(ValidationError):
        validate_workflow_schema(raw)


def test_rejects_duplicate_field_ids() -> None:
    raw = _valid_schema()
    blocks = raw["nodes"][1]["data"]["screen"]["rows"][0]["blocks"]
    blocks[1]["field"]["id"] = "f1"
    with pytest.raises(ValidationError):
        validate_workflow_schema(raw)


def test_rejects_computed_cycle() -> None:
    raw = _valid_schema()
    raw["nodes"][1]["data"]["screen"]["rows"][0]["blocks"] = [
        {
            "id": "b1",
            "span": 6,
            "kind": "field",
            "field": {
                "id": "a",
                "label": "A",
                "type": "computed",
                "expr": {"+": [{"var": "b"}, 1]},
            },
        },
        {
            "id": "b2",
            "span": 6,
            "kind": "field",
            "field": {
                "id": "b",
                "label": "B",
                "type": "computed",
                "expr": {"+": [{"var": "a"}, 1]},
            },
        },
    ]
    with pytest.raises(ValidationError):
        validate_workflow_schema(raw)


def test_accepts_computed_without_cycle() -> None:
    raw = _valid_schema()
    raw["nodes"][1]["data"]["screen"]["rows"][0]["blocks"][1]["field"] = {
        "id": "f2",
        "label": "F2",
        "type": "computed",
        "expr": {"+": [{"var": "f1"}, 1]},
    }
    assert validate_workflow_schema(deepcopy(raw)).formatVersion == 2
