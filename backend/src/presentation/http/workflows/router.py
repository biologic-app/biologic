from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status

from src.application.workflows.dto import (
    ExecuteStepInput,
    ImportEventInput,
    ImportRunInput,
    ImportTemplateInput,
    ImportVersionInput,
    StepActionInput,
)
from src.application.workflows.use_cases.attachments import WorkflowAttachmentUseCase
from src.application.workflows.use_cases.execute_step import ExecuteStepUseCase
from src.application.workflows.use_cases.import_templates import WorkflowImportUseCase
from src.application.workflows.use_cases.run_crud import WorkflowRunUseCase
from src.application.workflows.use_cases.template_crud import WorkflowTemplateUseCase
from src.core.pagination import PaginationDependency
from src.core.responses import ListResponse, SingleResponse
from src.presentation.http.access_control.dependencies import (
    CurrentPrincipal,
    get_current_principal,
)
from src.presentation.http.workflows.dependencies import (
    get_attachment_use_case,
    get_execute_step_use_case,
    get_import_use_case,
    get_run_use_case,
    get_template_use_case,
)
from src.presentation.http.workflows.schemas import (
    AddCommentRequest,
    ExecuteStepRequest,
    ImportRequest,
    RunCreateRequest,
    RunUpdateRequest,
    TemplateCreateRequest,
    TemplateUpdateRequest,
)

router = APIRouter(tags=["workflows"])


def _deleted_response() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Templates ---------------------------------------------------------------


@router.get("/workflow-templates")
async def list_templates(
    params: PaginationDependency,
    use_case: Annotated[WorkflowTemplateUseCase, Depends(get_template_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.post("/workflow-templates", status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: TemplateCreateRequest,
    use_case: Annotated[WorkflowTemplateUseCase, Depends(get_template_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


# Registered before `/workflow-templates/{template_id}` so the literal `import`
# path is matched ahead of the UUID-typed parameter.
@router.post("/workflow-templates/import")
async def import_templates(
    payload: ImportRequest,
    use_case: Annotated[WorkflowImportUseCase, Depends(get_import_use_case)],
) -> SingleResponse[dict[str, object]]:
    templates = [
        ImportTemplateInput(
            title=template.title,
            current_version=template.current_version,
            versions=[
                ImportVersionInput(version=v.version, schema=v.schema_body)
                for v in template.versions
            ],
            runs=[
                ImportRunInput(
                    schema_version=run.schema_version,
                    title=run.title,
                    status=run.status,
                    scope_kind=run.scope_kind,
                    scope_id=run.scope_id,
                    answers=run.answers,
                    loops=run.loops,
                    history=run.history,
                    current_node_id=run.current_node_id,
                    created_by=run.created_by,
                    events=[
                        ImportEventInput(
                            kind=e.kind,
                            node_id=e.node_id,
                            payload=e.payload,
                            author=e.author,
                        )
                        for e in run.events
                    ],
                )
                for run in template.runs
            ],
        )
        for template in payload.templates
    ]
    return await use_case.import_bundle(templates)


@router.get("/workflow-templates/{template_id}")
async def read_template(
    template_id: UUID,
    params: PaginationDependency,
    use_case: Annotated[WorkflowTemplateUseCase, Depends(get_template_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(template_id, includes=params.includes_requested)


@router.patch("/workflow-templates/{template_id}")
async def update_template(
    template_id: UUID,
    payload: TemplateUpdateRequest,
    use_case: Annotated[WorkflowTemplateUseCase, Depends(get_template_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(template_id, payload)


@router.delete("/workflow-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    use_case: Annotated[WorkflowTemplateUseCase, Depends(get_template_use_case)],
) -> Response:
    await use_case.delete(template_id)
    return _deleted_response()


@router.post("/workflow-templates/{template_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_template_version(
    template_id: UUID,
    schema: dict[str, Any],
    use_case: Annotated[WorkflowTemplateUseCase, Depends(get_template_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create_version(template_id, schema)


# --- Runs --------------------------------------------------------------------


@router.get("/workflow-runs")
async def list_runs(
    params: PaginationDependency,
    use_case: Annotated[WorkflowRunUseCase, Depends(get_run_use_case)],
) -> ListResponse[dict[str, object]]:
    return await use_case.list(params)


@router.post("/workflow-runs", status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: RunCreateRequest,
    use_case: Annotated[WorkflowRunUseCase, Depends(get_run_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(payload)


@router.get("/workflow-runs/{run_id}")
async def read_run(
    run_id: UUID,
    params: PaginationDependency,
    use_case: Annotated[WorkflowRunUseCase, Depends(get_run_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.read(run_id, includes=params.includes_requested)


@router.patch("/workflow-runs/{run_id}")
async def update_run(
    run_id: UUID,
    payload: RunUpdateRequest,
    use_case: Annotated[WorkflowRunUseCase, Depends(get_run_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update(run_id, payload)


@router.delete("/workflow-runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_run(
    run_id: UUID,
    use_case: Annotated[WorkflowRunUseCase, Depends(get_run_use_case)],
) -> Response:
    await use_case.delete(run_id)
    return _deleted_response()


@router.post("/workflow-runs/{run_id}/complete")
async def complete_run(
    run_id: UUID,
    use_case: Annotated[WorkflowRunUseCase, Depends(get_run_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.complete(run_id)


@router.post("/workflow-runs/{run_id}/archive")
async def archive_run(
    run_id: UUID,
    use_case: Annotated[WorkflowRunUseCase, Depends(get_run_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.archive(run_id)


@router.post("/workflow-runs/{run_id}/comments", status_code=status.HTTP_201_CREATED)
async def add_run_comment(
    run_id: UUID,
    payload: AddCommentRequest,
    use_case: Annotated[WorkflowRunUseCase, Depends(get_run_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.add_comment(
        run_id,
        payload.text,
        node_id=payload.node_id,
        author=payload.author,
    )


@router.post("/workflow-runs/{run_id}/execute-step")
async def execute_step(
    run_id: UUID,
    payload: ExecuteStepRequest,
    use_case: Annotated[ExecuteStepUseCase, Depends(get_execute_step_use_case)],
    principal: Annotated[CurrentPrincipal, Depends(get_current_principal)],
) -> SingleResponse[dict[str, object]]:
    command = ExecuteStepInput(
        run_id=run_id,
        node_id=payload.node_id,
        attempt=payload.attempt,
        actions=[
            StepActionInput(
                action_id=action.action_id,
                command=action.command,
                resolved_args=action.resolved_args,
            )
            for action in payload.actions
        ],
        actor_id=principal.user_id,
        author=payload.author,
    )
    return await use_case.execute(command)


@router.post("/workflow-runs/{run_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    run_id: UUID,
    file: Annotated[UploadFile, File()],
    field_id: Annotated[str, Form()],
    use_case: Annotated[WorkflowAttachmentUseCase, Depends(get_attachment_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.create(
        run_id=run_id,
        field_id=field_id,
        filename=file.filename or "attachment",
        content_type=file.content_type,
        data=await file.read(),
    )


# --- Attachments -------------------------------------------------------------


@router.get("/workflow-attachments/{attachment_id}")
async def download_attachment(
    attachment_id: UUID,
    use_case: Annotated[WorkflowAttachmentUseCase, Depends(get_attachment_use_case)],
) -> Response:
    binary = await use_case.read_binary(attachment_id)
    return Response(
        content=binary.data,
        media_type=binary.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{binary.filename}"'},
    )
