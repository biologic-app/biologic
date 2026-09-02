from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase, Session

from src.core.branch_context import get_current_branch_id


class Base(DeclarativeBase):
    """Base class for SQLAlchemy declarative models."""


@event.listens_for(Session, "before_flush")
def apply_current_branch_to_new_rows(
    session: Session, _flush_context: object, _instances: object
) -> None:
    """Stamp every new branch-aware row with the authenticated branch."""
    branch_id = get_current_branch_id()
    if branch_id is None:
        return
    for row in session.new:
        if hasattr(row, "branch_id"):
            row.branch_id = branch_id
