from typing import Annotated

from fastapi import APIRouter, Depends

from src.core.errors import DomainConflictError
from src.core.pagination import PaginationParams
from src.core.responses import ListResponse

router = APIRouter(tags=["catalogs"])


@router.get("/branches")
async def list_branches(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    raise DomainConflictError(
        code="catalog_repository_not_wired",
        detail=(
            "Catalog CRUD route is registered. Wire SQLAlchemy list/read/create/update/delete "
            "in the catalog repository before enabling runtime data access."
        ),
    )
