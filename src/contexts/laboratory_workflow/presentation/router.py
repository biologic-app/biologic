from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.laboratory_workflow.application.commands import WorkflowCommandService
from src.contexts.laboratory_workflow.application.crud import WorkflowCrudUseCase
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
from src.contexts.laboratory_workflow.infrastructure.crud_repositories import (
    DirectionCrudRepository,
    ProtocolCrudRepository,
    ResearchCrudRepository,
    SampleCrudRepository,
    TestCrudRepository,
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
from src.contexts.notifications.application.service import NotificationService
from src.contexts.notifications.infrastructure.repositories import SqlAlchemyNotificationRepository
from src.core.database import get_db_session
from src.core.pagination import PaginationDependency
from src.core.responses import ListResponse, ResponseMeta, SingleResponse

router = APIRouter(tags=["workflow"])


async def get_workflow_command_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkflowCommandService:
    return WorkflowCommandService(
        repository=SqlAlchemyWorkflowRepository(session=session),
        notification_service=NotificationService(
            repository=SqlAlchemyNotificationRepository(session=session),
        ),
    )


async def get_workflow_crud_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkflowCrudUseCase:
    return WorkflowCrudUseCase(
        directions=DirectionCrudRepository(session=session),
        samples=SampleCrudRepository(session=session),
        research=ResearchCrudRepository(session=session),
        tests=TestCrudRepository(session=session),
        protocols=ProtocolCrudRepository(session=session),
    )


def _deleted_response() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/directions")
async def list_directions(
    params: PaginationDependency,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_directions(params)


@router.get("/directions/{direction_id}")
async def read_direction(
    direction_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_direction(direction_id)


@router.post("/directions", status_code=status.HTTP_201_CREATED)
async def create_direction(
    payload: DirectionCreateRequest,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_direction(payload)


@router.patch("/directions/{direction_id}")
async def update_direction(
    direction_id: UUID,
    payload: DirectionUpdateRequest,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_direction(direction_id, payload)


@router.delete("/directions/{direction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_direction(
    direction_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> Response:
    await use_case.delete_direction(direction_id)
    return _deleted_response()


@router.get("/samples")
async def list_samples(
    params: PaginationDependency,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_samples(params)


@router.get("/samples/{sample_id}")
async def read_sample(
    sample_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_sample(sample_id)


@router.post("/samples", status_code=status.HTTP_201_CREATED)
async def create_sample(
    payload: SampleCreateRequest,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_sample(payload)


@router.patch("/samples/{sample_id}")
async def update_sample(
    sample_id: UUID,
    payload: SampleUpdateRequest,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_sample(sample_id, payload)


@router.delete("/samples/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample(
    sample_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> Response:
    await use_case.delete_sample(sample_id)
    return _deleted_response()


@router.get("/research")
async def list_research(
    params: PaginationDependency,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_research(params)


@router.get("/research/{research_id}")
async def read_research(
    research_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_research(research_id)


@router.post("/research", status_code=status.HTTP_201_CREATED)
async def create_research(
    payload: ResearchCreateRequest,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_research(payload)


@router.patch("/research/{research_id}")
async def update_research(
    research_id: UUID,
    payload: ResearchUpdateRequest,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_research(research_id, payload)


@router.delete("/research/{research_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_research(
    research_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> Response:
    await use_case.delete_research(research_id)
    return _deleted_response()


@router.get("/tests")
async def list_tests(
    params: PaginationDependency,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_tests(params)


@router.get("/tests/{test_id}")
async def read_test(
    test_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_test(test_id)


@router.post("/tests", status_code=status.HTTP_409_CONFLICT)
async def create_test(
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> None:
    use_case.reject_test_create()


@router.patch("/tests/{test_id}")
async def update_test(
    test_id: UUID,
    payload: TestUpdateRequest,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_test(test_id, payload)


@router.delete("/tests/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test(
    test_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> Response:
    await use_case.delete_test(test_id)
    return _deleted_response()


@router.get("/protocols")
async def list_protocols(
    params: PaginationDependency,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_protocols(params)


@router.get("/protocols/{protocol_id}")
async def read_protocol(
    protocol_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read_protocol(protocol_id)


@router.delete("/protocols/{protocol_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_protocol(
    protocol_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> Response:
    await use_case.delete_protocol(protocol_id)
    return _deleted_response()


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
