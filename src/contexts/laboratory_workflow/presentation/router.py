from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.laboratory_workflow.application.commands import WorkflowCommandService
from src.contexts.laboratory_workflow.application.dto import (
    AssignResearchInput,
    CloseSampleInput,
    CommandResult,
    CompleteTestInput,
    CreateProtocolInput,
    IssueProtocolInput,
    RegisterDirectionInput,
    RegisterSampleInput,
    RejectSampleInput,
    ResearchCommandInput,
    TestCommandInput,
    UpdateProtocolInput,
)
from src.contexts.laboratory_workflow.infrastructure.repositories import (
    SqlAlchemyWorkflowRepository,
)
from src.contexts.laboratory_workflow.presentation.schemas import (
    ActorRequest,
    AssignResearchRequest,
    CloseSampleRequest,
    CompleteTestRequest,
    CreateProtocolRequest,
    DirectionCreateRequest,
    DirectionUpdateRequest,
    IssueProtocolRequest,
    RegisterDirectionRequest,
    RegisterSampleRequest,
    RejectSampleRequest,
    RejectTestRequest,
    ResearchCreateRequest,
    ResearchUpdateRequest,
    SampleCreateRequest,
    SampleUpdateRequest,
    TestUpdateRequest,
    UpdateProtocolRequest,
)
from src.core.database import get_db_session
from src.core.errors import DomainConflictError, NotFoundError
from src.core.pagination import PageMeta, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse

router = APIRouter(tags=["workflow"])


async def get_workflow_command_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkflowCommandService:
    return WorkflowCommandService(repository=SqlAlchemyWorkflowRepository(session=session))


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
    data = _payload(payload)
    if "status_id" in data:
        raise DomainConflictError(
            code="invalid_status_transition",
            detail=f"{resource} lifecycle status must be changed through commands.",
        )
    return SingleResponse(
        data={"id": str(item_id), **data},
        meta=ResponseMeta(operation=f"{resource}.update"),
    )


def _deleted() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/directions")
async def list_directions(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params, allowed=("status", "doctor", "object"))


@router.get("/directions/{direction_id}")
async def read_direction(direction_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("directions", direction_id)


@router.post("/directions", status_code=status.HTTP_201_CREATED)
async def create_direction(
    payload: DirectionCreateRequest,
) -> SingleResponse[dict[str, object]]:
    return _created("directions", payload)


@router.patch("/directions/{direction_id}")
async def update_direction(
    direction_id: UUID,
    payload: DirectionUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("directions", direction_id, payload)


@router.delete("/directions/{direction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_direction(direction_id: UUID) -> Response:
    return _deleted()


@router.get("/samples")
async def list_samples(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params, allowed=("status", "direction", "sample_type", "protocol"))


@router.get("/samples/{sample_id}")
async def read_sample(sample_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("samples", sample_id)


@router.post("/samples", status_code=status.HTTP_201_CREATED)
async def create_sample(payload: SampleCreateRequest) -> SingleResponse[dict[str, object]]:
    return _created("samples", payload)


@router.patch("/samples/{sample_id}")
async def update_sample(
    sample_id: UUID,
    payload: SampleUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("samples", sample_id, payload)


@router.delete("/samples/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample(sample_id: UUID) -> Response:
    return _deleted()


@router.get("/research")
async def list_research(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params, allowed=("status", "sample", "research_goal", "lab"))


@router.get("/research/{research_id}")
async def read_research(research_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("research", research_id)


@router.post("/research", status_code=status.HTTP_201_CREATED)
async def create_research(payload: ResearchCreateRequest) -> SingleResponse[dict[str, object]]:
    return _created("research", payload)


@router.patch("/research/{research_id}")
async def update_research(
    research_id: UUID,
    payload: ResearchUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("research", research_id, payload)


@router.delete("/research/{research_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_research(research_id: UUID) -> Response:
    return _deleted()


@router.get("/tests")
async def list_tests(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params, allowed=("status", "research", "indicator"))


@router.get("/tests/{test_id}")
async def read_test(test_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("tests", test_id)


@router.post("/tests", status_code=status.HTTP_409_CONFLICT)
async def create_test() -> None:
    raise DomainConflictError(
        code="resource_read_only",
        detail="tests cannot be created through generic CRUD.",
    )


@router.patch("/tests/{test_id}")
async def update_test(
    test_id: UUID,
    payload: TestUpdateRequest,
) -> SingleResponse[dict[str, object]]:
    return _updated("tests", test_id, payload)


@router.delete("/tests/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test(test_id: UUID) -> Response:
    return _deleted()


@router.get("/protocols")
async def list_protocols(
    params: Annotated[PaginationParams, Depends()],
) -> ListResponse[dict[str, object]]:
    return _list_response(params, allowed=("conclusion", "protocol_type"))


@router.get("/protocols/{protocol_id}")
async def read_protocol(protocol_id: UUID) -> SingleResponse[dict[str, object]]:
    return _read_missing("protocols", protocol_id)


@router.delete("/protocols/{protocol_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_protocol(protocol_id: UUID) -> Response:
    return _deleted()


@router.post("/directions/{direction_id}/register")
async def register_direction(
    direction_id: UUID,
    request: RegisterDirectionRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
) -> SingleResponse[CommandResult]:
    result = await service.register_direction(
        RegisterDirectionInput(
            direction_id=direction_id,
            actor_id=request.actor_id,
            comment=request.comment,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="directions.register"))


@router.post("/samples/{sample_id}/register")
async def register_sample(
    sample_id: UUID,
    request: RegisterSampleRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
) -> SingleResponse[CommandResult]:
    result = await service.register_sample(
        RegisterSampleInput(
            sample_id=sample_id,
            actor_id=request.actor_id,
            received_at=request.received_at,
            deadline=request.deadline,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="samples.register"))


@router.post("/samples/{sample_id}/reject")
async def reject_sample(
    sample_id: UUID,
    request: RejectSampleRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
) -> SingleResponse[CommandResult]:
    result = await service.reject_sample(
        RejectSampleInput(
            sample_id=sample_id,
            actor_id=request.actor_id,
            reason=request.reason,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="samples.reject"))


@router.post("/samples/{sample_id}/assign-research")
async def assign_research(
    sample_id: UUID,
    request: AssignResearchRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
) -> SingleResponse[CommandResult]:
    result = await service.assign_research(
        AssignResearchInput(
            sample_id=sample_id,
            actor_id=request.actor_id,
            research_goal_id=request.research_goal_id,
            comment=request.comment,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="samples.assign_research"))


@router.post("/samples/{sample_id}/close")
async def close_sample(
    sample_id: UUID,
    request: CloseSampleRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
) -> SingleResponse[CommandResult]:
    result = await service.close_sample(
        CloseSampleInput(
            sample_id=sample_id,
            actor_id=request.actor_id,
            verdict=request.verdict,
            comment=request.comment,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="samples.close"))


@router.post("/research/{research_id}/confirm")
async def confirm_research(
    research_id: UUID,
    request: ActorRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
) -> SingleResponse[CommandResult]:
    result = await service.confirm_research(
        ResearchCommandInput(research_id=research_id, actor_id=request.actor_id),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="research.confirm"))


@router.post("/research/{research_id}/start")
async def start_research(
    research_id: UUID,
    request: ActorRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
) -> SingleResponse[CommandResult]:
    result = await service.start_research(
        ResearchCommandInput(research_id=research_id, actor_id=request.actor_id),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="research.start"))


@router.post("/tests/{test_id}/start")
async def start_test(
    test_id: UUID,
    request: ActorRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
) -> SingleResponse[CommandResult]:
    result = await service.start_test(TestCommandInput(test_id=test_id, actor_id=request.actor_id))
    return SingleResponse(data=result, meta=ResponseMeta(operation="tests.start"))


@router.post("/tests/{test_id}/complete")
async def complete_test(
    test_id: UUID,
    request: CompleteTestRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
) -> SingleResponse[CommandResult]:
    result = await service.complete_test(
        CompleteTestInput(
            test_id=test_id,
            actor_id=request.actor_id,
            value=request.value,
            norm=request.norm,
            comment=request.comment,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="tests.complete"))


@router.post("/tests/{test_id}/requeue")
async def requeue_test(
    test_id: UUID,
    request: ActorRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
) -> SingleResponse[CommandResult]:
    result = await service.requeue_test(
        TestCommandInput(test_id=test_id, actor_id=request.actor_id),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="tests.requeue"))


@router.post("/tests/{test_id}/reject")
async def reject_test(
    test_id: UUID,
    request: RejectTestRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
) -> SingleResponse[CommandResult]:
    result = await service.reject_test(
        TestCommandInput(test_id=test_id, actor_id=request.actor_id, reason=request.reason),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="tests.reject"))


@router.post("/protocols")
async def create_protocol(
    request: CreateProtocolRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
) -> SingleResponse[CommandResult]:
    result = await service.create_protocol(
        CreateProtocolInput(
            actor_id=request.actor_id,
            sample_ids=request.sample_ids,
            protocol_type_id=request.protocol_type_id,
            conclusion_id=request.conclusion_id,
            copies=request.copies,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="protocols.create"))


@router.patch("/protocols/{protocol_id}")
async def update_protocol(
    protocol_id: UUID,
    request: UpdateProtocolRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
) -> SingleResponse[CommandResult]:
    result = await service.update_protocol(
        UpdateProtocolInput(
            protocol_id=protocol_id,
            actor_id=request.actor_id,
            protocol_type_id=request.protocol_type_id,
            conclusion_id=request.conclusion_id,
            copies=request.copies,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="protocols.update"))


@router.post("/protocols/{protocol_id}/issue")
async def issue_protocol(
    protocol_id: UUID,
    request: IssueProtocolRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
) -> SingleResponse[CommandResult]:
    result = await service.issue_protocol(
        IssueProtocolInput(
            protocol_id=protocol_id,
            actor_id=request.actor_id,
            issued_at=request.issued_at,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="protocols.issue"))
