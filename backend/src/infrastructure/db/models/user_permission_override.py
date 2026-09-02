from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.uuid7 import new_uuid7
from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.enums import AccessScopeType
from src.infrastructure.db.models.mixins import TenantMixin


class UserPermissionOverride(TenantMixin, Base):
    __tablename__ = "user_permission_overrides"
    __table_args__ = (
        Index(
            "user_permission_overrides_user_id_permission_id",
            "user_id",
            "permission_id",
            unique=True,
        ),
        Index("user_permission_overrides_permission_id", "permission_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=new_uuid7,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_user_permission_overrides_user_id_users_id"),
        nullable=False,
    )
    permission_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "permissions.id",
            name="fk_user_permission_overrides_permission_id_permissions_id",
        ),
        nullable=False,
    )
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    scope: Mapped[AccessScopeType | None] = mapped_column(
        SQLEnum(
            AccessScopeType,
            name="access_scope_type",
            values_callable=lambda enum: [item.value for item in enum],
        ),
    )
