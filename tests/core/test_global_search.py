from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from src.core.global_search import build_global_search_filter
from src.infrastructure.db.models import Sample


def test_global_search_filter_matches_text_and_identifier_columns() -> None:
    predicate = build_global_search_filter(Sample, "Сыворотка")
    assert predicate is not None

    compiled = str(
        select(Sample).where(predicate).compile(
            dialect=postgresql.dialect(),  # type: ignore[no-untyped-call]
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "samples.name ILIKE" in compiled
    assert "similarity(" not in compiled
    assert "CAST(samples.id AS TEXT) ILIKE" in compiled


def test_global_search_filter_ignores_blank_search() -> None:
    assert build_global_search_filter(Sample, "  ") is None
