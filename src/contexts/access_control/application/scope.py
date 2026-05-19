from uuid import UUID

from src.contexts.access_control.domain.scope_policy import (
    ActorScope,
    ScopeFilter,
    entity_id_scope,
    global_scope,
    own_alerts_scope,
    own_branch_scope,
    own_lab_scope,
    own_objects_scope,
)


def build_scope_filter(
    scope_type: str,
    actor: ActorScope,
    *,
    entity_id: UUID | None = None,
) -> ScopeFilter:
    if scope_type == "global":
        return global_scope(actor)
    if scope_type == "own_branch":
        return own_branch_scope(actor)
    if scope_type == "own_lab":
        return own_lab_scope(actor)
    if scope_type == "own_objects":
        return own_objects_scope(actor)
    if scope_type == "own_alerts":
        return own_alerts_scope(actor)
    if scope_type == "entity_id" and entity_id is not None:
        return entity_id_scope(entity_id)
    return ScopeFilter(field=None)
