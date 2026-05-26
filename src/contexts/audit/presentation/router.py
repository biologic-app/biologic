from uuid import UUID

from fastapi import APIRouter

from src.core.errors import NotFoundError
from src.core.pagination import PageMeta, PaginationDependency, PaginationParams
from src.core.responses import ListResponse, SingleResponse

router = APIRouter(tags=["audit"])


def _meta(params: PaginationParams) -> PageMeta:
    return PageMeta(
        total=0,
        limit=params.limit,
        has_more=False,
        includes_requested=params.includes_requested,
        includes_applied=[],
        includes_allowed=[],
    )


@router.get("/history")
async def list_history(
    params: PaginationDependency,
) -> ListResponse[dict[str, object]]:
    return ListResponse(items=[], meta=_meta(params))


@router.get("/history/{history_id}")
async def read_history(history_id: UUID) -> SingleResponse[dict[str, object]]:
    raise NotFoundError(f"history item {history_id} was not found.")
