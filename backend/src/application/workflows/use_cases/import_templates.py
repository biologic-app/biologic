from __future__ import annotations

from src.application.workflows.dto import ImportTemplateInput
from src.application.workflows.use_cases._shared import single_response
from src.core.responses import SingleResponse
from src.domain.uow import UnitOfWorkFactory
from src.domain.workflows.schema import validate_workflow_schema


class WorkflowImportUseCase:
    """Bulk import of templates, their immutable versions, runs and run events.

    v1→v2 conversion happens on the frontend; the backend validates every
    incoming schema version and lays the bundle out across the tables in one
    transaction.
    """

    def __init__(self, *, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def import_bundle(
        self,
        templates: list[ImportTemplateInput],
    ) -> SingleResponse[dict[str, object]]:
        # Validate all version schemas up front so a bad schema aborts before
        # any row is written.
        for template in templates:
            for version in template.versions:
                validate_workflow_schema(version.schema)

        counts = {"templates": 0, "versions": 0, "runs": 0, "events": 0}
        async with self._uow_factory() as uow:
            for template in templates:
                created = await uow.workflows.create_template(
                    {"title": template.title, "current_version": template.current_version}
                )
                counts["templates"] += 1
                for version in template.versions:
                    await uow.workflows.create_version(
                        created.id,
                        version.version,
                        version.schema,
                    )
                    counts["versions"] += 1
                for run in template.runs:
                    created_run = await uow.workflows.create_run(
                        {
                            "template_id": created.id,
                            "schema_version": run.schema_version,
                            "title": run.title,
                            "status": run.status,
                            "scope_kind": run.scope_kind,
                            "scope_id": run.scope_id,
                            "answers": run.answers,
                            "loops": run.loops,
                            "history": run.history,
                            "current_node_id": run.current_node_id,
                            "created_by": run.created_by,
                        }
                    )
                    counts["runs"] += 1
                    for event in run.events:
                        await uow.workflows.append_event(
                            run_id=created_run.id,
                            kind=event.kind,
                            node_id=event.node_id,
                            payload=event.payload,
                            author=event.author,
                        )
                        counts["events"] += 1
            await uow.commit()

        return single_response(dict(counts), operation="workflows.templates.import")
