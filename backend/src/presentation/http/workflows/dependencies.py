from src.application.workflows.use_cases.attachments import WorkflowAttachmentUseCase
from src.application.workflows.use_cases.execute_step import ExecuteStepUseCase
from src.application.workflows.use_cases.import_templates import WorkflowImportUseCase
from src.application.workflows.use_cases.run_crud import WorkflowRunUseCase
from src.application.workflows.use_cases.template_crud import WorkflowTemplateUseCase
from src.core.config import get_settings
from src.infrastructure.uow import build_uow_factory


async def get_template_use_case() -> WorkflowTemplateUseCase:
    return WorkflowTemplateUseCase(uow_factory=build_uow_factory())


async def get_run_use_case() -> WorkflowRunUseCase:
    return WorkflowRunUseCase(uow_factory=build_uow_factory())


async def get_execute_step_use_case() -> ExecuteStepUseCase:
    return ExecuteStepUseCase(uow_factory=build_uow_factory())


async def get_import_use_case() -> WorkflowImportUseCase:
    return WorkflowImportUseCase(uow_factory=build_uow_factory())


async def get_attachment_use_case() -> WorkflowAttachmentUseCase:
    return WorkflowAttachmentUseCase(
        uow_factory=build_uow_factory(),
        max_mb=get_settings().workflow_attachment_max_mb,
    )
