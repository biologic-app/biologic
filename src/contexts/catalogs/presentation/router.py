from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.catalogs.application.crud import CatalogCrudUseCase
from src.contexts.catalogs.infrastructure.repositories import (
    BranchRepository,
    ConclusionRepository,
    DirectionStatusRepository,
    DoctorRepository,
    IndicatorRepository,
    LabRepository,
    ObjectRepository,
    ProtocolTypeRepository,
    ResearchGoalRepository,
    ResearchStatusRepository,
    SampleStatusRepository,
    SampleTypeRepository,
    TestStatusRepository,
)
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
from src.core.database import get_db_session
from src.core.pagination import PaginationDependency
from src.core.responses import ListResponse, SingleResponse

router = APIRouter(tags=["catalogs"])


async def get_catalog_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CatalogCrudUseCase:
    return CatalogCrudUseCase(
        branches=BranchRepository(session=session),
        labs=LabRepository(session=session),
        objects=ObjectRepository(session=session),
        doctors=DoctorRepository(session=session),
        sample_types=SampleTypeRepository(session=session),
        research_goals=ResearchGoalRepository(session=session),
        indicators=IndicatorRepository(session=session),
        conclusions=ConclusionRepository(session=session),
        protocol_types=ProtocolTypeRepository(session=session),
        direction_statuses=DirectionStatusRepository(session=session),
        sample_statuses=SampleStatusRepository(session=session),
        research_statuses=ResearchStatusRepository(session=session),
        test_statuses=TestStatusRepository(session=session),
    )


def _deleted_response() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/branches")
async def list_branches(
    params: PaginationDependency,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_branches(params)


@router.get("/branches/{item_id}")
async def read_branch(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_branch(item_id)


@router.post("/branches", status_code=status.HTTP_201_CREATED)
async def create_branch(
    payload: BranchCreateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_branch(payload)


@router.patch("/branches/{item_id}")
async def update_branch(
    item_id: UUID,
    payload: BranchUpdateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_branch(item_id, payload)


@router.delete("/branches/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> Response:
    await use_case.delete_branch(item_id)
    return _deleted_response()


@router.get("/labs")
async def list_labs(
    params: PaginationDependency,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_labs(params)


@router.get("/labs/{item_id}")
async def read_lab(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_lab(item_id)


@router.post("/labs", status_code=status.HTTP_201_CREATED)
async def create_lab(
    payload: LabCreateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_lab(payload)


@router.patch("/labs/{item_id}")
async def update_lab(
    item_id: UUID,
    payload: LabUpdateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_lab(item_id, payload)


@router.delete("/labs/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lab(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> Response:
    await use_case.delete_lab(item_id)
    return _deleted_response()


@router.get("/objects")
async def list_objects(
    params: PaginationDependency,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_objects(params)


@router.get("/objects/{item_id}")
async def read_object(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_object(item_id)


@router.post("/objects", status_code=status.HTTP_201_CREATED)
async def create_object(
    payload: ObjectCreateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_object(payload)


@router.patch("/objects/{item_id}")
async def update_object(
    item_id: UUID,
    payload: ObjectUpdateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_object(item_id, payload)


@router.delete("/objects/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_object(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> Response:
    await use_case.delete_object(item_id)
    return _deleted_response()


@router.get("/doctors")
async def list_doctors(
    params: PaginationDependency,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_doctors(params)


@router.get("/doctors/{item_id}")
async def read_doctor(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_doctor(item_id)


@router.post("/doctors", status_code=status.HTTP_201_CREATED)
async def create_doctor(
    payload: DoctorCreateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_doctor(payload)


@router.patch("/doctors/{item_id}")
async def update_doctor(
    item_id: UUID,
    payload: DoctorUpdateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_doctor(item_id, payload)


@router.delete("/doctors/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doctor(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> Response:
    await use_case.delete_doctor(item_id)
    return _deleted_response()


@router.get("/sample_types")
async def list_sample_types(
    params: PaginationDependency,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_sample_types(params)


@router.get("/sample_types/{item_id}")
async def read_sample_type(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_sample_type(item_id)


@router.post("/sample_types", status_code=status.HTTP_201_CREATED)
async def create_sample_type(
    payload: SampleTypeCreateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_sample_type(payload)


@router.patch("/sample_types/{item_id}")
async def update_sample_type(
    item_id: UUID,
    payload: SampleTypeUpdateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_sample_type(item_id, payload)


@router.delete("/sample_types/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample_type(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> Response:
    await use_case.delete_sample_type(item_id)
    return _deleted_response()


@router.get("/research_goals")
async def list_research_goals(
    params: PaginationDependency,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_research_goals(params)


@router.get("/research_goals/{item_id}")
async def read_research_goal(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_research_goal(item_id)


@router.post("/research_goals", status_code=status.HTTP_201_CREATED)
async def create_research_goal(
    payload: ResearchGoalCreateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_research_goal(payload)


@router.patch("/research_goals/{item_id}")
async def update_research_goal(
    item_id: UUID,
    payload: ResearchGoalUpdateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_research_goal(item_id, payload)


@router.delete("/research_goals/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_research_goal(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> Response:
    await use_case.delete_research_goal(item_id)
    return _deleted_response()


@router.get("/indicators")
async def list_indicators(
    params: PaginationDependency,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_indicators(params)


@router.get("/indicators/{item_id}")
async def read_indicator(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_indicator(item_id)


@router.post("/indicators", status_code=status.HTTP_201_CREATED)
async def create_indicator(
    payload: IndicatorCreateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_indicator(payload)


@router.patch("/indicators/{item_id}")
async def update_indicator(
    item_id: UUID,
    payload: IndicatorUpdateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_indicator(item_id, payload)


@router.delete("/indicators/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_indicator(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> Response:
    await use_case.delete_indicator(item_id)
    return _deleted_response()


@router.get("/conclusions")
async def list_conclusions(
    params: PaginationDependency,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_conclusions(params)


@router.get("/conclusions/{item_id}")
async def read_conclusion(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_conclusion(item_id)


@router.post("/conclusions", status_code=status.HTTP_201_CREATED)
async def create_conclusion(
    payload: ConclusionCreateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_conclusion(payload)


@router.patch("/conclusions/{item_id}")
async def update_conclusion(
    item_id: UUID,
    payload: ConclusionUpdateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_conclusion(item_id, payload)


@router.delete("/conclusions/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conclusion(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> Response:
    await use_case.delete_conclusion(item_id)
    return _deleted_response()


@router.get("/protocol_types")
async def list_protocol_types(
    params: PaginationDependency,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_protocol_types(params)


@router.get("/protocol_types/{item_id}")
async def read_protocol_type(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_protocol_type(item_id)


@router.post("/protocol_types", status_code=status.HTTP_201_CREATED)
async def create_protocol_type(
    payload: ProtocolTypeCreateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_protocol_type(payload)


@router.patch("/protocol_types/{item_id}")
async def update_protocol_type(
    item_id: UUID,
    payload: ProtocolTypeUpdateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_protocol_type(item_id, payload)


@router.delete("/protocol_types/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_protocol_type(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> Response:
    await use_case.delete_protocol_type(item_id)
    return _deleted_response()


@router.get("/direction_statuses")
async def list_direction_statuses(
    params: PaginationDependency,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_direction_statuses(params)


@router.get("/direction_statuses/{item_id}")
async def read_direction_status(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_direction_status(item_id)


@router.post("/direction_statuses", status_code=status.HTTP_409_CONFLICT)
async def create_direction_status(
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> None:
    use_case.reject_read_only_status_write("direction_statuses")


@router.patch("/direction_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def update_direction_status(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> None:
    use_case.reject_read_only_status_write("direction_statuses")


@router.delete("/direction_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def delete_direction_status(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> None:
    use_case.reject_read_only_status_write("direction_statuses")


@router.get("/sample_statuses")
async def list_sample_statuses(
    params: PaginationDependency,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_sample_statuses(params)


@router.get("/sample_statuses/{item_id}")
async def read_sample_status(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_sample_status(item_id)


@router.post("/sample_statuses", status_code=status.HTTP_409_CONFLICT)
async def create_sample_status(
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> None:
    use_case.reject_read_only_status_write("sample_statuses")


@router.patch("/sample_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def update_sample_status(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> None:
    use_case.reject_read_only_status_write("sample_statuses")


@router.delete("/sample_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def delete_sample_status(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> None:
    use_case.reject_read_only_status_write("sample_statuses")


@router.get("/research_statuses")
async def list_research_statuses(
    params: PaginationDependency,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_research_statuses(params)


@router.get("/research_statuses/{item_id}")
async def read_research_status(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_research_status(item_id)


@router.post("/research_statuses", status_code=status.HTTP_409_CONFLICT)
async def create_research_status(
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> None:
    use_case.reject_read_only_status_write("research_statuses")


@router.patch("/research_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def update_research_status(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> None:
    use_case.reject_read_only_status_write("research_statuses")


@router.delete("/research_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def delete_research_status(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> None:
    use_case.reject_read_only_status_write("research_statuses")


@router.get("/test_statuses")
async def list_test_statuses(
    params: PaginationDependency,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_test_statuses(params)


@router.get("/test_statuses/{item_id}")
async def read_test_status(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_test_status(item_id)


@router.post("/test_statuses", status_code=status.HTTP_409_CONFLICT)
async def create_test_status(
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> None:
    use_case.reject_read_only_status_write("test_statuses")


@router.patch("/test_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def update_test_status(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> None:
    use_case.reject_read_only_status_write("test_statuses")


@router.delete("/test_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def delete_test_status(
    item_id: UUID,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> None:
    use_case.reject_read_only_status_write("test_statuses")
