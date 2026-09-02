from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from src.core.uuid7 import new_uuid7
from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.branch import Branch
from src.infrastructure.db.models.mixins import LabMixin, SoftDeleteMixin, TenantMixin


class User(TenantMixin, LabMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("users_users_username", "username", unique=True),
        Index("users_users_role_id", "role_id"),
        Index("users_users_lab_id", "lab_id"),
        Index("users_users_deleted_at", "deleted_at"),
    )

    branch: Mapped[Branch | None] = relationship(
        Branch,
        primaryjoin=lambda: foreign(User.branch_id) == Branch.id,
        viewonly=True,
        lazy="selectin",
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=new_uuid7,
    )
    username: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    code: Mapped[str | None] = mapped_column(Text)
    first_name: Mapped[str | None] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    patronymic: Mapped[str | None] = mapped_column(Text)
    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", name="fk_users_role_id_roles_id"),
        nullable=False,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_users_created_by_users_id"),
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_users_updated_by_users_id"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    @property
    def branch_name(self) -> str | None:
        return self.branch.name if self.branch is not None else None
