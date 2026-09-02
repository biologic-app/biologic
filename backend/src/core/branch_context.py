from contextvars import ContextVar
from uuid import UUID

_current_branch_id: ContextVar[UUID | None] = ContextVar("current_branch_id", default=None)


def set_current_branch_id(branch_id: UUID | None) -> None:
    _current_branch_id.set(branch_id)


def get_current_branch_id() -> UUID | None:
    return _current_branch_id.get()
