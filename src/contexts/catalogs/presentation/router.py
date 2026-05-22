from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from src.contexts.catalogs.presentation.schemas import (
    BranchCreateRequest,
    BranchUpdateRequest,
    ConclusionCreateRequest,
    ConclusionUpdateRequest,
    DoctorCreateRequest,
    DoctorUpdateRequest,
    IndicatorCreateRequest,
    IndicatorUpdateRequest,
    LabCreateRequest,
    LabUpdateRequest,
    ObjectCreateRequest,
    ObjectUpdateRequest,
    ProtocolTypeCreateRequest,
    ProtocolTypeUpdateRequest,
    ResearchGoalCreateRequest,
    ResearchGoalUpdateRequest,
    SampleTypeCreateRequest,
    SampleTypeUpdateRequest,
)
from src.core.errors import DomainConflictError, NotFoundError
from src.core.pagination import PageMeta, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse

router = APIRouter(tags=["catalogs"])


def _payload(payload: BaseModel) -> dict[str, object]:
    return payload.model_dump(mode="json", exclude_unset=True)


def _meta(params: PaginationParams, *, allowed: tuple[str, ...] = ()) -> PageMeta:
    requested = params.includes_requested
    applied = [item for item in requested if item in allowed]
    return PageMeta(
        total=0,
        offset=params.offset,
        limit=params.limit,
        has_more=False,
        includes_requested=requested,
        includes_applied=applied,
        includes_allowed=list(allowed),
    )


def _list_response(
    params: PaginationParams,
    *,
    allowed: tuple[str, ...] = (),
) -> ListResponse[dict[str, object]]:
    return ListResponse(items=[], meta=_meta(params, allowed=allowed))


def _read_missing(resource: str, item_id: UUID) -> SingleResponse[dict[str, object]]:
    raise NotFoundError(f"{resource} item {item_id} was not found.")


def _created(resource: str, payload: BaseModel) -> SingleResponse[dict[str, object]]:
    return SingleResponse(
        data={"id": str(uuid4()), **_payload(payload)},
        meta=ResponseMeta(operation=f"{resource}.create"),
    )


def _updated(resource: str, item_id: UUID, payload: BaseModel) -> SingleResponse[dict[str, object]]:
    return SingleResponse(
        data={"id": str(item_id), **_payload(payload)},
        meta=ResponseMeta(operation=f"{resource}.update"),
    )


def _deleted() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _read_only(resource: str) -> None:
    raise DomainConflictError(
        code="resource_read_only",
        detail=f"{resource} cannot be changed through catalog CRUD.",
    )


@router.get("/branches")
async def list_branches(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params)


@router.get("/branches/{item_id}")
async def read_branch(item_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("branches", item_id)


@router.post("/branches", status_code=status.HTTP_201_CREATED)
async def create_branch(payload: BranchCreateRequest) -> SingleResponse[dict[str, object]]:
    return _created("branches", payload)


@router.patch("/branches/{item_id}")
async def update_branch(
    item_id: UUID,
    payload: BranchUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("branches", item_id, payload)


@router.delete("/branches/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch(item_id: UUID) -> Response:
    return _deleted()


@router.get("/labs")
async def list_labs(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params, allowed=("branch",))


@router.get("/labs/{item_id}")
async def read_lab(item_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("labs", item_id)


@router.post("/labs", status_code=status.HTTP_201_CREATED)
async def create_lab(payload: LabCreateRequest) -> SingleResponse[dict[str, object]]:
    return _created("labs", payload)


@router.patch("/labs/{item_id}")
async def update_lab(item_id: UUID, payload: LabUpdateRequest) -> SingleResponse[dict[str, object]]:
    return _updated("labs", item_id, payload)


@router.delete("/labs/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lab(item_id: UUID) -> Response:
    return _deleted()


@router.get("/objects")
async def list_objects(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params, allowed=("branch",))


@router.get("/objects/{item_id}")
async def read_object(item_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("objects", item_id)


@router.post("/objects", status_code=status.HTTP_201_CREATED)
async def create_object(payload: ObjectCreateRequest) -> SingleResponse[dict[str, object]]:
    return _created("objects", payload)


@router.patch("/objects/{item_id}")
async def update_object(
    item_id: UUID,
    payload: ObjectUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("objects", item_id, payload)


@router.delete("/objects/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_object(item_id: UUID) -> Response:
    return _deleted()


@router.get("/doctors")
async def list_doctors(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params)


@router.get("/doctors/{item_id}")
async def read_doctor(item_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("doctors", item_id)


@router.post("/doctors", status_code=status.HTTP_201_CREATED)
async def create_doctor(payload: DoctorCreateRequest) -> SingleResponse[dict[str, object]]:
    return _created("doctors", payload)


@router.patch("/doctors/{item_id}")
async def update_doctor(
    item_id: UUID,
    payload: DoctorUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("doctors", item_id, payload)


@router.delete("/doctors/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doctor(item_id: UUID) -> Response:
    return _deleted()


@router.get("/sample_types")
async def list_sample_types(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params)


@router.get("/sample_types/{item_id}")
async def read_sample_type(item_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("sample_types", item_id)


@router.post("/sample_types", status_code=status.HTTP_201_CREATED)
async def create_sample_type(
    payload: SampleTypeCreateRequest,
) -> SingleResponse[dict[str, object]]:
    return _created("sample_types", payload)


@router.patch("/sample_types/{item_id}")
async def update_sample_type(
    item_id: UUID,
    payload: SampleTypeUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("sample_types", item_id, payload)


@router.delete("/sample_types/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample_type(item_id: UUID) -> Response:
    return _deleted()


@router.get("/research_goals")
async def list_research_goals(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params, allowed=("lab",))


@router.get("/research_goals/{item_id}")
async def read_research_goal(item_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("research_goals", item_id)


@router.post("/research_goals", status_code=status.HTTP_201_CREATED)
async def create_research_goal(
    payload: ResearchGoalCreateRequest,
) -> SingleResponse[dict[str, object]]:
    return _created("research_goals", payload)


@router.patch("/research_goals/{item_id}")
async def update_research_goal(
    item_id: UUID,
    payload: ResearchGoalUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("research_goals", item_id, payload)


@router.delete("/research_goals/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_research_goal(item_id: UUID) -> Response:
    return _deleted()


@router.get("/indicators")
async def list_indicators(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params, allowed=("research_goal", "sample_type"))


@router.get("/indicators/{item_id}")
async def read_indicator(item_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("indicators", item_id)


@router.post("/indicators", status_code=status.HTTP_201_CREATED)
async def create_indicator(payload: IndicatorCreateRequest) -> SingleResponse[dict[str, object]]:
    return _created("indicators", payload)


@router.patch("/indicators/{item_id}")
async def update_indicator(
    item_id: UUID,
    payload: IndicatorUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("indicators", item_id, payload)


@router.delete("/indicators/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_indicator(item_id: UUID) -> Response:
    return _deleted()


@router.get("/conclusions")
async def list_conclusions(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params)


@router.get("/conclusions/{item_id}")
async def read_conclusion(item_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("conclusions", item_id)


@router.post("/conclusions", status_code=status.HTTP_201_CREATED)
async def create_conclusion(payload: ConclusionCreateRequest) -> SingleResponse[dict[str, object]]:
    return _created("conclusions", payload)


@router.patch("/conclusions/{item_id}")
async def update_conclusion(
    item_id: UUID,
    payload: ConclusionUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("conclusions", item_id, payload)


@router.delete("/conclusions/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conclusion(item_id: UUID) -> Response:
    return _deleted()


@router.get("/protocol_types")
async def list_protocol_types(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params)


@router.get("/protocol_types/{item_id}")
async def read_protocol_type(item_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("protocol_types", item_id)


@router.post("/protocol_types", status_code=status.HTTP_201_CREATED)
async def create_protocol_type(
    payload: ProtocolTypeCreateRequest,
) -> SingleResponse[dict[str, object]]:
    return _created("protocol_types", payload)


@router.patch("/protocol_types/{item_id}")
async def update_protocol_type(
    item_id: UUID,
    payload: ProtocolTypeUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("protocol_types", item_id, payload)


@router.delete("/protocol_types/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_protocol_type(item_id: UUID) -> Response:
    return _deleted()


@router.get("/direction_statuses")
async def list_direction_statuses(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params)


@router.get("/direction_statuses/{item_id}")
async def read_direction_status(item_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("direction_statuses", item_id)


@router.post("/direction_statuses", status_code=status.HTTP_409_CONFLICT)
async def create_direction_status() -> None:
    _read_only("direction_statuses")


@router.patch("/direction_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def update_direction_status(item_id: UUID) -> None:
    _read_only("direction_statuses")


@router.delete("/direction_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def delete_direction_status(item_id: UUID) -> None:
    _read_only("direction_statuses")


@router.get("/sample_statuses")
async def list_sample_statuses(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params)


@router.get("/sample_statuses/{item_id}")
async def read_sample_status(item_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("sample_statuses", item_id)


@router.post("/sample_statuses", status_code=status.HTTP_409_CONFLICT)
async def create_sample_status() -> None:
    _read_only("sample_statuses")


@router.patch("/sample_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def update_sample_status(item_id: UUID) -> None:
    _read_only("sample_statuses")


@router.delete("/sample_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def delete_sample_status(item_id: UUID) -> None:
    _read_only("sample_statuses")


@router.get("/research_statuses")
async def list_research_statuses(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params)


@router.get("/research_statuses/{item_id}")
async def read_research_status(item_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("research_statuses", item_id)


@router.post("/research_statuses", status_code=status.HTTP_409_CONFLICT)
async def create_research_status() -> None:
    _read_only("research_statuses")


@router.patch("/research_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def update_research_status(item_id: UUID) -> None:
    _read_only("research_statuses")


@router.delete("/research_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def delete_research_status(item_id: UUID) -> None:
    _read_only("research_statuses")


@router.get("/test_statuses")
async def list_test_statuses(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params)


@router.get("/test_statuses/{item_id}")
async def read_test_status(item_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("test_statuses", item_id)


@router.post("/test_statuses", status_code=status.HTTP_409_CONFLICT)
async def create_test_status() -> None:
    _read_only("test_statuses")


@router.patch("/test_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def update_test_status(item_id: UUID) -> None:
    _read_only("test_statuses")


@router.delete("/test_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def delete_test_status(item_id: UUID) -> None:
    _read_only("test_statuses")
