import dataclasses
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ActorScope:
    actor_id: UUID
    role_key: str
    branch_ids: frozenset[UUID] = dataclasses.field(default_factory=frozenset)
    lab_ids: frozenset[UUID] = dataclasses.field(default_factory=frozenset)
    object_ids: frozenset[UUID] = dataclasses.field(default_factory=frozenset)


@dataclass(frozen=True)
class ScopeFilter:
    field: str | None
    values: frozenset[UUID] = dataclasses.field(default_factory=frozenset)
    unrestricted: bool = False

    def contains(self, value: UUID | None) -> bool:
        return self.unrestricted or (value is not None and value in self.values)


def global_scope(actor: ActorScope) -> ScopeFilter:
    return ScopeFilter(field=None, unrestricted=True)


def own_branch_scope(actor: ActorScope) -> ScopeFilter:
    return ScopeFilter(field="branch_id", values=actor.branch_ids)


def own_lab_scope(actor: ActorScope) -> ScopeFilter:
    return ScopeFilter(field="lab_id", values=actor.lab_ids)


def own_objects_scope(actor: ActorScope) -> ScopeFilter:
    return ScopeFilter(field="object_id", values=actor.object_ids)


def own_alerts_scope(actor: ActorScope) -> ScopeFilter:
    return ScopeFilter(field="user_id", values=frozenset({actor.actor_id}))


def entity_id_scope(entity_id: UUID) -> ScopeFilter:
    return ScopeFilter(field="entity_id", values=frozenset({entity_id}))
