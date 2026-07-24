from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.workflows.use_cases._shared import (
    ATTACHMENT_FIELDS,
    serialize,
    single_response,
)
from src.core.errors import BadRequestError
from src.core.responses import SingleResponse
from src.domain.uow import UnitOfWorkFactory


@dataclass(frozen=True)
class AttachmentBinary:
    data: bytes
    content_type: str | None
    filename: str


class WorkflowAttachmentUseCase:
    def __init__(self, *, uow_factory: UnitOfWorkFactory, max_mb: int) -> None:
        self._uow_factory = uow_factory
        self._max_mb = max_mb
        self._max_bytes = max_mb * 1024 * 1024

    async def create(
        self,
        run_id: UUID,
        field_id: str,
        filename: str,
        content_type: str | None,
        data: bytes,
    ) -> SingleResponse[dict[str, object]]:
        if len(data) > self._max_bytes:
            raise BadRequestError(
                f"Attachment exceeds the {self._max_mb} MB limit."
            )
        async with self._uow_factory() as uow:
            await uow.workflows.get_run(run_id)
            attachment = await uow.workflows.create_attachment(
                run_id=run_id,
                field_id=field_id,
                filename=filename,
                content_type=content_type,
                size_bytes=len(data),
                data=data,
            )
            await uow.commit()
            return single_response(
                serialize(attachment, ATTACHMENT_FIELDS),
                operation="workflows.attachments.create",
            )

    async def read_binary(self, attachment_id: UUID) -> AttachmentBinary:
        async with self._uow_factory() as uow:
            attachment = await uow.workflows.get_attachment(attachment_id)
            return AttachmentBinary(
                data=attachment.data,
                content_type=attachment.content_type,
                filename=attachment.filename,
            )
