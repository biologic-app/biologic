from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.models.base import Base


class UserScope(Base):
    __tablename__ = "user_scopes"
    __table_args__ = (
        Index("user_scopes_user_scopes_user_id_scope_id", "user_id", "scope_id", unique=True),
        Index("user_scopes_user_scopes_scope_id", "scope_id"),
        Index(
            "user_scopes_user_scopes_user_id_null_scope_id",
            "user_id",
            unique=True,
            postgresql_where=text("scope_id IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuidv7()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_user_scopes_user_id_users_id"),
        nullable=False,
    )
    scope_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    scope_kind: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'object'"))
