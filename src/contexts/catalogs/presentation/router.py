from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from src.contexts.catalogs.application.use_cases.branch_crud import BranchCrudUseCase
from src.contexts.catalogs.application.use_cases.conclusion_crud import ConclusionCrudUseCase
from src.contexts.catalogs.application.use_cases.direction_status_crud import (
    DirectionStatusCrudUseCase,
)
from src.contexts.catalogs.application.use_cases.doctor_crud import DoctorCrudUseCase
from src.contexts.catalogs.application.use_cases.indicator_crud import IndicatorCrudUseCase
from src.contexts.catalogs.application.use_cases.lab_crud import LabCrudUseCase
from src.contexts.catalogs.application.use_cases.object_crud import ObjectCrudUseCase
from src.contexts.catalogs.application.use_cases.protocol_type_crud import ProtocolTypeCrudUseCase
from src.contexts.catalogs.application.use_cases.research_goal_crud import ResearchGoalCrudUseCase
from src.contexts.catalogs.application.use_cases.research_status_crud import (
    ResearchStatusCrudUseCase,
)
from src.contexts.catalogs.application.use_cases.sample_status_crud import SampleStatusCrudUseCase
from src.contexts.catalogs.application.use_cases.sample_type_crud import SampleTypeCrudUseCase
from src.contexts.catalogs.application.use_cases.test_status_crud import TestStatusCrudUseCase
from src.contexts.catalogs.presentation.dependencies import (
    get_branch_use_case,
    get_conclusion_use_case,
    get_direction_status_use_case,
    get_doctor_use_case,
    get_indicator_use_case,
    get_lab_use_case,
    get_object_use_case,
    get_protocol_type_use_case,
    get_research_goal_use_case,
    get_research_status_use_case,
    get_sample_status_use_case,
    get_sample_type_use_case,
    get_test_status_use_case,
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
    StatusUpdateRequest,
)
from src.core.pagination import PaginationDependency
from src.core.responses import ListResponse, SingleResponse

router = APIRouter(tags=["catalogs"])


def _deleted_response() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/branches")
async def list_branches(
    params: PaginationDependency,
    use_case: Annotated[BranchCrudUseCase, Depends(get_branch_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/branches/{item_id}")
async def read_branch(
    item_id: UUID,
    use_case: Annotated[BranchCrudUseCase, Depends(get_branch_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(item_id)


@router.post("/branches", status_code=status.HTTP_201_CREATED)
async def create_branch(
    payload: BranchCreateRequest,
    use_case: Annotated[BranchCrudUseCase, Depends(get_branch_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


@router.patch("/branches/{item_id}")
async def update_branch(
    item_id: UUID,
    payload: BranchUpdateRequest,
    use_case: Annotated[BranchCrudUseCase, Depends(get_branch_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(item_id, payload)


@router.delete("/branches/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch(
    item_id: UUID,
    use_case: Annotated[BranchCrudUseCase, Depends(get_branch_use_case)],
) -> Response:
    await use_case.delete(item_id)
    return _deleted_response()


@router.get("/labs")
async def list_labs(
    params: PaginationDependency,
    use_case: Annotated[LabCrudUseCase, Depends(get_lab_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/labs/{item_id}")
async def read_lab(
    item_id: UUID,
    use_case: Annotated[LabCrudUseCase, Depends(get_lab_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(item_id)


@router.post("/labs", status_code=status.HTTP_201_CREATED)
async def create_lab(
    payload: LabCreateRequest,
    use_case: Annotated[LabCrudUseCase, Depends(get_lab_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


@router.patch("/labs/{item_id}")
async def update_lab(
    item_id: UUID,
    payload: LabUpdateRequest,
    use_case: Annotated[LabCrudUseCase, Depends(get_lab_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(item_id, payload)


@router.delete("/labs/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lab(
    item_id: UUID,
    use_case: Annotated[LabCrudUseCase, Depends(get_lab_use_case)],
) -> Response:
    await use_case.delete(item_id)
    return _deleted_response()


@router.get("/objects")
async def list_objects(
    params: PaginationDependency,
    use_case: Annotated[ObjectCrudUseCase, Depends(get_object_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/objects/{item_id}")
async def read_object(
    item_id: UUID,
    use_case: Annotated[ObjectCrudUseCase, Depends(get_object_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(item_id)


@router.post("/objects", status_code=status.HTTP_201_CREATED)
async def create_object(
    payload: ObjectCreateRequest,
    use_case: Annotated[ObjectCrudUseCase, Depends(get_object_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


@router.patch("/objects/{item_id}")
async def update_object(
    item_id: UUID,
    payload: ObjectUpdateRequest,
    use_case: Annotated[ObjectCrudUseCase, Depends(get_object_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(item_id, payload)


@router.delete("/objects/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_object(
    item_id: UUID,
    use_case: Annotated[ObjectCrudUseCase, Depends(get_object_use_case)],
) -> Response:
    await use_case.delete(item_id)
    return _deleted_response()


@router.get("/doctors")
async def list_doctors(
    params: PaginationDependency,
    use_case: Annotated[DoctorCrudUseCase, Depends(get_doctor_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/doctors/{item_id}")
async def read_doctor(
    item_id: UUID,
    use_case: Annotated[DoctorCrudUseCase, Depends(get_doctor_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(item_id)


@router.post("/doctors", status_code=status.HTTP_201_CREATED)
async def create_doctor(
    payload: DoctorCreateRequest,
    use_case: Annotated[DoctorCrudUseCase, Depends(get_doctor_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


@router.patch("/doctors/{item_id}")
async def update_doctor(
    item_id: UUID,
    payload: DoctorUpdateRequest,
    use_case: Annotated[DoctorCrudUseCase, Depends(get_doctor_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(item_id, payload)


@router.delete("/doctors/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doctor(
    item_id: UUID,
    use_case: Annotated[DoctorCrudUseCase, Depends(get_doctor_use_case)],
) -> Response:
    await use_case.delete(item_id)
    return _deleted_response()


@router.get("/sample_types")
async def list_sample_types(
    params: PaginationDependency,
    use_case: Annotated[SampleTypeCrudUseCase, Depends(get_sample_type_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/sample_types/{item_id}")
async def read_sample_type(
    item_id: UUID,
    use_case: Annotated[SampleTypeCrudUseCase, Depends(get_sample_type_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(item_id)


@router.post("/sample_types", status_code=status.HTTP_201_CREATED)
async def create_sample_type(
    payload: SampleTypeCreateRequest,
    use_case: Annotated[SampleTypeCrudUseCase, Depends(get_sample_type_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


@router.patch("/sample_types/{item_id}")
async def update_sample_type(
    item_id: UUID,
    payload: SampleTypeUpdateRequest,
    use_case: Annotated[SampleTypeCrudUseCase, Depends(get_sample_type_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(item_id, payload)


@router.delete("/sample_types/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample_type(
    item_id: UUID,
    use_case: Annotated[SampleTypeCrudUseCase, Depends(get_sample_type_use_case)],
) -> Response:
    await use_case.delete(item_id)
    return _deleted_response()


@router.get("/research_goals")
async def list_research_goals(
    params: PaginationDependency,
    use_case: Annotated[ResearchGoalCrudUseCase, Depends(get_research_goal_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/research_goals/{item_id}")
async def read_research_goal(
    item_id: UUID,
    use_case: Annotated[ResearchGoalCrudUseCase, Depends(get_research_goal_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(item_id)


@router.post("/research_goals", status_code=status.HTTP_201_CREATED)
async def create_research_goal(
    payload: ResearchGoalCreateRequest,
    use_case: Annotated[ResearchGoalCrudUseCase, Depends(get_research_goal_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


@router.patch("/research_goals/{item_id}")
async def update_research_goal(
    item_id: UUID,
    payload: ResearchGoalUpdateRequest,
    use_case: Annotated[ResearchGoalCrudUseCase, Depends(get_research_goal_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(item_id, payload)


@router.delete("/research_goals/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_research_goal(
    item_id: UUID,
    use_case: Annotated[ResearchGoalCrudUseCase, Depends(get_research_goal_use_case)],
) -> Response:
    await use_case.delete(item_id)
    return _deleted_response()


@router.get("/indicators")
async def list_indicators(
    params: PaginationDependency,
    use_case: Annotated[IndicatorCrudUseCase, Depends(get_indicator_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/indicators/{item_id}")
async def read_indicator(
    item_id: UUID,
    use_case: Annotated[IndicatorCrudUseCase, Depends(get_indicator_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(item_id)


@router.post("/indicators", status_code=status.HTTP_201_CREATED)
async def create_indicator(
    payload: IndicatorCreateRequest,
    use_case: Annotated[IndicatorCrudUseCase, Depends(get_indicator_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


@router.patch("/indicators/{item_id}")
async def update_indicator(
    item_id: UUID,
    payload: IndicatorUpdateRequest,
    use_case: Annotated[IndicatorCrudUseCase, Depends(get_indicator_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(item_id, payload)


@router.delete("/indicators/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_indicator(
    item_id: UUID,
    use_case: Annotated[IndicatorCrudUseCase, Depends(get_indicator_use_case)],
) -> Response:
    await use_case.delete(item_id)
    return _deleted_response()


@router.get("/conclusions")
async def list_conclusions(
    params: PaginationDependency,
    use_case: Annotated[ConclusionCrudUseCase, Depends(get_conclusion_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/conclusions/{item_id}")
async def read_conclusion(
    item_id: UUID,
    use_case: Annotated[ConclusionCrudUseCase, Depends(get_conclusion_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(item_id)


@router.post("/conclusions", status_code=status.HTTP_201_CREATED)
async def create_conclusion(
    payload: ConclusionCreateRequest,
    use_case: Annotated[ConclusionCrudUseCase, Depends(get_conclusion_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


@router.patch("/conclusions/{item_id}")
async def update_conclusion(
    item_id: UUID,
    payload: ConclusionUpdateRequest,
    use_case: Annotated[ConclusionCrudUseCase, Depends(get_conclusion_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(item_id, payload)


@router.delete("/conclusions/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conclusion(
    item_id: UUID,
    use_case: Annotated[ConclusionCrudUseCase, Depends(get_conclusion_use_case)],
) -> Response:
    await use_case.delete(item_id)
    return _deleted_response()


@router.get("/protocol_types")
async def list_protocol_types(
    params: PaginationDependency,
    use_case: Annotated[ProtocolTypeCrudUseCase, Depends(get_protocol_type_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/protocol_types/{item_id}")
async def read_protocol_type(
    item_id: UUID,
    use_case: Annotated[ProtocolTypeCrudUseCase, Depends(get_protocol_type_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(item_id)


@router.post("/protocol_types", status_code=status.HTTP_201_CREATED)
async def create_protocol_type(
    payload: ProtocolTypeCreateRequest,
    use_case: Annotated[ProtocolTypeCrudUseCase, Depends(get_protocol_type_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


@router.patch("/protocol_types/{item_id}")
async def update_protocol_type(
    item_id: UUID,
    payload: ProtocolTypeUpdateRequest,
    use_case: Annotated[ProtocolTypeCrudUseCase, Depends(get_protocol_type_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(item_id, payload)


@router.delete("/protocol_types/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_protocol_type(
    item_id: UUID,
    use_case: Annotated[ProtocolTypeCrudUseCase, Depends(get_protocol_type_use_case)],
) -> Response:
    await use_case.delete(item_id)
    return _deleted_response()


@router.get("/direction_statuses")
async def list_direction_statuses(
    params: PaginationDependency,
    use_case: Annotated[DirectionStatusCrudUseCase, Depends(get_direction_status_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/direction_statuses/{item_id}")
async def read_direction_status(
    item_id: UUID,
    use_case: Annotated[DirectionStatusCrudUseCase, Depends(get_direction_status_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(item_id)


@router.post("/direction_statuses", status_code=status.HTTP_409_CONFLICT)
async def create_direction_status(
    use_case: Annotated[DirectionStatusCrudUseCase, Depends(get_direction_status_use_case)],
) -> None:
    use_case.reject_write()


@router.patch("/direction_statuses/{item_id}")
async def update_direction_status(
    item_id: UUID,
    payload: StatusUpdateRequest,
    use_case: Annotated[DirectionStatusCrudUseCase, Depends(get_direction_status_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(item_id, payload)


@router.delete("/direction_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def delete_direction_status(
    item_id: UUID,
    use_case: Annotated[DirectionStatusCrudUseCase, Depends(get_direction_status_use_case)],
) -> None:
    use_case.reject_write()


@router.get("/sample_statuses")
async def list_sample_statuses(
    params: PaginationDependency,
    use_case: Annotated[SampleStatusCrudUseCase, Depends(get_sample_status_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/sample_statuses/{item_id}")
async def read_sample_status(
    item_id: UUID,
    use_case: Annotated[SampleStatusCrudUseCase, Depends(get_sample_status_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(item_id)


@router.post("/sample_statuses", status_code=status.HTTP_409_CONFLICT)
async def create_sample_status(
    use_case: Annotated[SampleStatusCrudUseCase, Depends(get_sample_status_use_case)],
) -> None:
    use_case.reject_write()


@router.patch("/sample_statuses/{item_id}")
async def update_sample_status(
    item_id: UUID,
    payload: StatusUpdateRequest,
    use_case: Annotated[SampleStatusCrudUseCase, Depends(get_sample_status_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(item_id, payload)


@router.delete("/sample_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def delete_sample_status(
    item_id: UUID,
    use_case: Annotated[SampleStatusCrudUseCase, Depends(get_sample_status_use_case)],
) -> None:
    use_case.reject_write()


@router.get("/research_statuses")
async def list_research_statuses(
    params: PaginationDependency,
    use_case: Annotated[ResearchStatusCrudUseCase, Depends(get_research_status_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/research_statuses/{item_id}")
async def read_research_status(
    item_id: UUID,
    use_case: Annotated[ResearchStatusCrudUseCase, Depends(get_research_status_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(item_id)


@router.post("/research_statuses", status_code=status.HTTP_409_CONFLICT)
async def create_research_status(
    use_case: Annotated[ResearchStatusCrudUseCase, Depends(get_research_status_use_case)],
) -> None:
    use_case.reject_write()


@router.patch("/research_statuses/{item_id}")
async def update_research_status(
    item_id: UUID,
    payload: StatusUpdateRequest,
    use_case: Annotated[ResearchStatusCrudUseCase, Depends(get_research_status_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(item_id, payload)


@router.delete("/research_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def delete_research_status(
    item_id: UUID,
    use_case: Annotated[ResearchStatusCrudUseCase, Depends(get_research_status_use_case)],
) -> None:
    use_case.reject_write()


@router.get("/test_statuses")
async def list_test_statuses(
    params: PaginationDependency,
    use_case: Annotated[TestStatusCrudUseCase, Depends(get_test_status_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.get("/test_statuses/{item_id}")
async def read_test_status(
    item_id: UUID,
    use_case: Annotated[TestStatusCrudUseCase, Depends(get_test_status_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(item_id)


@router.post("/test_statuses", status_code=status.HTTP_409_CONFLICT)
async def create_test_status(
    use_case: Annotated[TestStatusCrudUseCase, Depends(get_test_status_use_case)],
) -> None:
    use_case.reject_write()


@router.patch("/test_statuses/{item_id}")
async def update_test_status(
    item_id: UUID,
    payload: StatusUpdateRequest,
    use_case: Annotated[TestStatusCrudUseCase, Depends(get_test_status_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(item_id, payload)


@router.delete("/test_statuses/{item_id}", status_code=status.HTTP_409_CONFLICT)
async def delete_test_status(
    item_id: UUID,
    use_case: Annotated[TestStatusCrudUseCase, Depends(get_test_status_use_case)],
) -> None:
    use_case.reject_write()
