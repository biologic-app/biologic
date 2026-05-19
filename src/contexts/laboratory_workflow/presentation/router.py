from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
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
    IssueProtocolRequest,
    RegisterDirectionRequest,
    RegisterSampleRequest,
    RejectSampleRequest,
    RejectTestRequest,
    UpdateProtocolRequest,
)
from src.core.database import get_db_session
from src.core.responses import ResponseMeta, SingleResponse

router = APIRouter(tags=["workflow"])


async def get_workflow_command_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkflowCommandService:
    return WorkflowCommandService(repository=SqlAlchemyWorkflowRepository(session=session))


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
