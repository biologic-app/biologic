from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.laboratory_workflow.application.commands import WorkflowCommandService
from src.contexts.laboratory_workflow.application.dto import (
    CommandResult,
    RegisterDirectionInput,
)
from src.contexts.laboratory_workflow.infrastructure.repositories import (
    SqlAlchemyWorkflowRepository,
)
from src.contexts.laboratory_workflow.presentation.schemas import RegisterDirectionRequest
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
