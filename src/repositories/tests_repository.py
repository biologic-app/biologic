from sqlalchemy import BigInteger, Column, MetaData, String, Table, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from src.models.entities import Test
from src.repositories.crud_repository import CRUDRepository, ListQuery

_COUNTER_TABLE = Table(
    "entity_active_counts",
    MetaData(),
    Column("entity_name", String()),
    Column("active_total", BigInteger()),
)


class TestRepository(CRUDRepository[Test]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Test)

    def _build_total_stmt(
        self,
        *,
        query: ListQuery,
        base_stmt: Select[tuple[Test]],
    ) -> Select[tuple[int]]:
        has_filters = bool(query.exact_filters or query.contains_filters or query.range_filters)
        if has_filters:
            return super()._build_total_stmt(query=query, base_stmt=base_stmt)

        # Fast-path for unfiltered lists: exact active total from counter table.
        return select(
            func.coalesce(
                (
                    select(_COUNTER_TABLE.c.active_total)
                    .where(_COUNTER_TABLE.c.entity_name == "tests")
                    .scalar_subquery()
                ),
                0,
            )
        )
