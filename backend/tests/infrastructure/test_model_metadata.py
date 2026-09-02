from typing import cast

from sqlalchemy import Table

from src.infrastructure.db.models import Direction, Protocol, Research, Sample


def test_mvp_workflow_fields_exist_on_models() -> None:
    assert "import_warnings" in Direction.__table__.columns
    assert "deadline" in Sample.__table__.columns
    assert "verdict" in Sample.__table__.columns
    assert "protocol_id" in Sample.__table__.columns
    assert "lab_id" in Research.__table__.columns
    assert "issued_at" in Protocol.__table__.columns


def test_research_lab_id_metadata() -> None:
    table = cast(Table, Research.__table__)
    column = table.columns["lab_id"]

    assert column.nullable is True
    constraint_names = set()
    for foreign_key in column.foreign_keys:
        assert foreign_key.constraint is not None
        constraint_names.add(foreign_key.constraint.name)
    assert constraint_names == set()
    assert "research_research_lab_id" in {idx.name for idx in table.indexes}
