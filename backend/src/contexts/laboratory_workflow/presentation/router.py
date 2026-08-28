from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
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
from src.contexts.laboratory_workflow.domain.status_policy import allowed_transitions_map
from src.contexts.laboratory_workflow.infrastructure.crud_repositories import (
    DirectionCrudRepository,
    ProtocolCrudRepository,
    ResearchCrudRepository,
    SampleCrudRepository,
    SampleLabCrudRepository,
    SubscriptionCrudRepository,
    TestCrudRepository,
)
from src.contexts.laboratory_workflow.infrastructure.protocol_report_repository import (
    ProtocolReportRepository,
)
from src.contexts.laboratory_workflow.presentation.schemas import (
    AssignResearchRequest,
    CloseSampleRequest,
    CompleteTestRequest,
    CreateProtocolRequest,
    DirectionCreateRequest,
    DirectionUpdateRequest,
    IssueProtocolRequest,
    RegisterDirectionRequest,
    RegisterSampleRequest,
    RejectResearchRequest,
    RejectSampleRequest,
    RejectTestRequest,
    ResearchUpdateRequest,
    SampleCreateRequest,
    SampleLabsUpdateRequest,
    SampleUpdateRequest,
    StatusTransition,
    StatusTransitionsResponse,
    SubscriptionRequest,
    TestUpdateRequest,
    UpdateProtocolRequest,
)
from src.core.database import get_db_session
from src.core.errors import BadRequestError
from src.core.pagination import PaginationDependency
from src.core.responses import ListResponse, ResponseMeta, SingleResponse
from src.infrastructure.repositories.catalogs import DoctorRepository, ObjectRepository
from src.infrastructure.uow import build_uow_factory
from src.presentation.http.access_control.dependencies import (
    get_current_user_id,
    get_current_user_id_optional,
    require_permission,
)

router = APIRouter(tags=["workflow"])
ActorId = Annotated[UUID, Depends(get_current_user_id)]


async def get_workflow_command_service() -> WorkflowCommandService:
    return WorkflowCommandService(
        uow_factory=build_uow_factory(),
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
        sample_labs=SampleLabCrudRepository(session=session),
        subscriptions=SubscriptionCrudRepository(session=session),
        doctors=DoctorRepository(session=session),
        objects=ObjectRepository(session=session),
        protocol_reports=ProtocolReportRepository(session=session),
    )


def _deleted_response() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx_response(filename: str, content: bytes) -> Response:
    return Response(
        content=content,
        media_type=_XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/status-transitions")
async def get_status_transitions() -> StatusTransitionsResponse:
    # Единый источник правды для UI-схемы статусов: разрешённые переходы из
    # доменной политики. Фронтенд строит FSM по этому ответу, чтобы схема и
    # серверная валидация не расходились.
    return StatusTransitionsResponse(
        data={
            resource: [
                StatusTransition(from_code=from_code, to_code=to_code)
                for from_code, to_code in pairs
            ]
            for resource, pairs in allowed_transitions_map().items()
        },
    )


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
    actor_id: Annotated[UUID | None, Depends(get_current_user_id_optional)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_direction(payload, actor_id=actor_id)


@router.post("/directions/import")
async def import_directions(
    file: Annotated[UploadFile, File()],
    type: Annotated[str, Form()],
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
    actor_id: Annotated[UUID | None, Depends(get_current_user_id_optional)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.import_directions(
        file.filename or "", await file.read(), type_=type, actor_id=actor_id
    )


@router.post("/directions/{direction_id}/samples", status_code=status.HTTP_201_CREATED)
async def add_direction_sample(
    direction_id: UUID,
    payload: SampleCreateRequest,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
    actor_id: Annotated[UUID | None, Depends(get_current_user_id_optional)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.add_direction_sample(direction_id, payload, actor_id=actor_id)


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


@router.get("/samples/{sample_id}/labs")
async def list_sample_labs(
    sample_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_sample_labs(sample_id)


def _resolve_subscriber(
    payload: SubscriptionRequest, actor_id: UUID | None
) -> UUID:
    user_id = payload.user_id or actor_id
    if user_id is None:
        raise BadRequestError("user_id is required when there is no authenticated user.")
    return user_id


@router.get("/directions/{direction_id}/subscriptions")
async def list_direction_subscriptions(
    direction_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_subscriptions("directions", direction_id)


@router.post("/directions/{direction_id}/subscribe")
async def subscribe_direction(
    direction_id: UUID,
    payload: SubscriptionRequest,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
    actor_id: Annotated[UUID | None, Depends(get_current_user_id_optional)],
) -> ListResponse[dict[str, object]]:
    return await use_case.subscribe(
        "directions", direction_id, _resolve_subscriber(payload, actor_id)
    )


@router.post("/directions/{direction_id}/unsubscribe")
async def unsubscribe_direction(
    direction_id: UUID,
    payload: SubscriptionRequest,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
    actor_id: Annotated[UUID | None, Depends(get_current_user_id_optional)],
) -> ListResponse[dict[str, object]]:
    return await use_case.unsubscribe(
        "directions", direction_id, _resolve_subscriber(payload, actor_id)
    )


@router.get("/samples/{sample_id}/subscriptions")
async def list_sample_subscriptions(
    sample_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_subscriptions("samples", sample_id)


@router.post("/samples/{sample_id}/subscribe")
async def subscribe_sample(
    sample_id: UUID,
    payload: SubscriptionRequest,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
    actor_id: Annotated[UUID | None, Depends(get_current_user_id_optional)],
) -> ListResponse[dict[str, object]]:
    return await use_case.subscribe(
        "samples", sample_id, _resolve_subscriber(payload, actor_id)
    )


@router.post("/samples/{sample_id}/unsubscribe")
async def unsubscribe_sample(
    sample_id: UUID,
    payload: SubscriptionRequest,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
    actor_id: Annotated[UUID | None, Depends(get_current_user_id_optional)],
) -> ListResponse[dict[str, object]]:
    return await use_case.unsubscribe(
        "samples", sample_id, _resolve_subscriber(payload, actor_id)
    )


# «Мои подписки» для колонки-пина: id направлений/образцов, на которые текущий
# пользователь подписан вручную. Литеральный сегмент "subscriptions/mine" не
# конфликтует с "/{id}/subscriptions" (третий сегмент — "mine", не "subscriptions").
@router.get("/directions/subscriptions/mine")
async def list_my_direction_subscriptions(
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
    actor_id: Annotated[UUID | None, Depends(get_current_user_id_optional)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_user_subscriptions("directions", actor_id)


@router.get("/samples/subscriptions/mine")
async def list_my_sample_subscriptions(
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
    actor_id: Annotated[UUID | None, Depends(get_current_user_id_optional)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list_user_subscriptions("samples", actor_id)


@router.put("/samples/{sample_id}/labs")
async def set_sample_labs(
    sample_id: UUID,
    payload: SampleLabsUpdateRequest,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.set_sample_labs(sample_id, payload.lab_ids)


@router.get("/samples/{sample_id}/research-goal-suggestions")
async def suggest_sample_research_goals(
    sample_id: UUID,
    sample_type_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.suggest_research_goals(sample_id, sample_type_id)


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


@router.get("/protocols/{protocol_id}/document")
async def protocol_document(
    protocol_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> Response:
    filename, content = await use_case.protocol_document(protocol_id)
    return _xlsx_response(filename, content)


@router.get("/protocols/{protocol_id}/excerpt")
async def protocol_excerpt(
    protocol_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> Response:
    filename, content = await use_case.protocol_excerpt(protocol_id)
    return _xlsx_response(filename, content)


@router.delete("/protocols/{protocol_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_protocol(
    protocol_id: UUID,
    use_case: Annotated[WorkflowCrudUseCase, Depends(get_workflow_crud_use_case)],
) -> Response:
    await use_case.delete_protocol(protocol_id)
    return _deleted_response()


@router.post(
    "/directions/{direction_id}/register",
    dependencies=[Depends(require_permission("directions.register"))],
)
async def register_direction(
    direction_id: UUID,
    request: RegisterDirectionRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
    actor_id: ActorId,
) -> SingleResponse[CommandResult]:
    result = await service.register_direction(
        RegisterDirectionInput(
            direction_id=direction_id,
            actor_id=actor_id,
            comment=request.comment,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="directions.register"))


@router.post(
    "/samples/{sample_id}/register",
    dependencies=[Depends(require_permission("samples.register"))],
)
async def register_sample(
    sample_id: UUID,
    request: RegisterSampleRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
    actor_id: ActorId,
) -> SingleResponse[CommandResult]:
    result = await service.register_sample(
        RegisterSampleInput(
            sample_id=sample_id,
            actor_id=actor_id,
            received_at=request.received_at,
            deadline=request.deadline,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="samples.register"))


@router.post(
    "/samples/{sample_id}/reject",
    dependencies=[Depends(require_permission("samples.reject"))],
)
async def reject_sample(
    sample_id: UUID,
    request: RejectSampleRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
    actor_id: ActorId,
) -> SingleResponse[CommandResult]:
    result = await service.reject_sample(
        RejectSampleInput(
            sample_id=sample_id,
            actor_id=actor_id,
            reason=request.reason,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="samples.reject"))


@router.post(
    "/samples/{sample_id}/assign-research",
    dependencies=[Depends(require_permission("research.create"))],
)
async def assign_research(
    sample_id: UUID,
    request: AssignResearchRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
    actor_id: ActorId,
) -> SingleResponse[CommandResult]:
    result = await service.assign_research(
        AssignResearchInput(
            sample_id=sample_id,
            actor_id=actor_id,
            research_goal_id=request.research_goal_id,
            comment=request.comment,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="samples.assign_research"))


@router.post(
    "/samples/{sample_id}/close",
    dependencies=[Depends(require_permission("samples.close"))],
)
async def close_sample(
    sample_id: UUID,
    request: CloseSampleRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
    actor_id: ActorId,
) -> SingleResponse[CommandResult]:
    result = await service.close_sample(
        CloseSampleInput(
            sample_id=sample_id,
            actor_id=actor_id,
            verdict=request.verdict,
            comment=request.comment,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="samples.close"))


@router.post(
    "/research/{research_id}/reject",
    dependencies=[Depends(require_permission("research.reject"))],
)
async def reject_research(
    research_id: UUID,
    request: RejectResearchRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
    actor_id: ActorId,
) -> SingleResponse[CommandResult]:
    result = await service.reject_research(
        ResearchCommandInput(
            research_id=research_id,
            actor_id=actor_id,
            reason=request.reason,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="research.reject"))


@router.post(
    "/tests/{test_id}/complete",
    dependencies=[Depends(require_permission("tests.complete"))],
)
async def complete_test(
    test_id: UUID,
    request: CompleteTestRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
    actor_id: ActorId,
) -> SingleResponse[CommandResult]:
    result = await service.complete_test(
        CompleteTestInput(
            test_id=test_id,
            actor_id=actor_id,
            value=request.value,
            norm=request.norm,
            comment=request.comment,
            verdict=request.verdict,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="tests.complete"))


@router.post(
    "/tests/{test_id}/reject",
    dependencies=[Depends(require_permission("tests.reject"))],
)
async def reject_test(
    test_id: UUID,
    request: RejectTestRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
    actor_id: ActorId,
) -> SingleResponse[CommandResult]:
    result = await service.reject_test(
        TestCommandInput(test_id=test_id, actor_id=actor_id, reason=request.reason),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="tests.reject"))


@router.post(
    "/protocols",
    dependencies=[Depends(require_permission("protocols.create"))],
)
async def create_protocol(
    request: CreateProtocolRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
    actor_id: ActorId,
) -> SingleResponse[CommandResult]:
    result = await service.create_protocol(
        CreateProtocolInput(
            actor_id=actor_id,
            sample_ids=request.sample_ids,
            protocol_type_id=request.protocol_type_id,
            conclusion_id=request.conclusion_id,
            copies=request.copies,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="protocols.create"))


@router.patch(
    "/protocols/{protocol_id}",
    dependencies=[Depends(require_permission("protocols.update"))],
)
async def update_protocol(
    protocol_id: UUID,
    request: UpdateProtocolRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
    actor_id: ActorId,
) -> SingleResponse[CommandResult]:
    result = await service.update_protocol(
        UpdateProtocolInput(
            protocol_id=protocol_id,
            actor_id=actor_id,
            protocol_type_id=request.protocol_type_id,
            conclusion_id=request.conclusion_id,
            copies=request.copies,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="protocols.update"))


@router.post(
    "/protocols/{protocol_id}/issue",
    dependencies=[Depends(require_permission("protocols.issue"))],
)
async def issue_protocol(
    protocol_id: UUID,
    request: IssueProtocolRequest,
    service: Annotated[WorkflowCommandService, Depends(get_workflow_command_service)],
    actor_id: ActorId,
) -> SingleResponse[CommandResult]:
    result = await service.issue_protocol(
        IssueProtocolInput(
            protocol_id=protocol_id,
            actor_id=actor_id,
            issued_at=request.issued_at,
        ),
    )
    return SingleResponse(data=result, meta=ResponseMeta(operation="protocols.issue"))
