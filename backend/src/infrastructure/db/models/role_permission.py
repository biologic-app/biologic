from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy import (
    ForeignKey,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.enums import AccessScopeType


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        Index(
            "role_permissions_role_permissions_role_id_permission_id",
            "role_id",
            "permission_id",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuidv7()"),
    )
    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", name="fk_role_permissions_role_id_roles_id"),
        nullable=False,
    )
    permission_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("permissions.id", name="fk_role_permissions_permission_id_permissions_id"),
        nullable=False,
    )
    scope: Mapped[AccessScopeType] = mapped_column(
        SQLEnum(
            AccessScopeType,
            name="access_scope_type",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        server_default=text("'all'::access_scope_type"),
    )
