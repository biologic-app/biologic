from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.uuid7 import new_uuid7
from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.mixins import SoftDeleteMixin, TenantMixin


class Subscription(TenantMixin, SoftDeleteMixin, Base):
    """Explicit user subscription to a direction or a sample.

    Implicit followers (registrars, direction owner) are derived at read
    time and never stored — see SubscriptionCrudRepository.
    """

    __tablename__ = "subscriptions"
    __table_args__ = (
        Index(
            "subscriptions_unique_triple",
            "user_id",
            "entity_type",
            "entity_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("subscriptions_entity", "entity_type", "entity_id"),
        Index("subscriptions_subscriptions_deleted_at", "deleted_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=new_uuid7,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_subscriptions_user_id_users_id"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
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
