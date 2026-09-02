from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Text,
    text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.uuid7 import new_uuid7
from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.enums import RoleScopeType
from src.infrastructure.db.models.mixins import TenantMixin


class Role(TenantMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (
        Index("roles_roles_key", "key", unique=True),
        Index("roles_roles_scope_type", "scope_type"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=new_uuid7,
    )
    key: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    scope_type: Mapped[RoleScopeType] = mapped_column(
        SQLEnum(
            RoleScopeType,
            name="role_scope_type",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        server_default=text("'global'::role_scope_type"),
    )
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
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
