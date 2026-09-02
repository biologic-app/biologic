from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
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
from src.infrastructure.db.models.mixins import LabMixin, SoftDeleteMixin, TenantMixin


class RoleSubscriptionRule(TenantMixin, LabMixin, SoftDeleteMixin, Base):
    """Mandatory, admin-configured subscription rule keyed on a role.

    Everyone holding ``role_id`` implicitly follows entities of ``entity_type``,
    optionally narrowed to a single ``branch_id`` and/or ``lab_id``, and/or a
    single lifecycle ``status_code`` (e.g. only rejected samples). A NULL scope
    column means "any" on that axis. Lab-scoped rules only ever match samples
    (directions have no direct lab), enforced by a CHECK constraint; likewise
    ``status_code`` is checked against the status set of the matching
    ``entity_type`` (see src/core/status_codes.py — the stable code string is
    stored here rather than a status row id, since a single column would
    otherwise have to reference either direction_statuses or sample_statuses
    depending on entity_type). These rules are never stored per-entity;
    followers are derived at read time — see SubscriptionCrudRepository.
    """

    __tablename__ = "role_subscription_rules"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('directions', 'samples')",
            name="role_subscription_rules_entity_type_check",
        ),
        CheckConstraint(
            "lab_id IS NULL OR entity_type = 'samples'",
            name="role_subscription_rules_lab_scope_check",
        ),
        CheckConstraint(
            "status_code IS NULL"
            " OR (entity_type = 'directions' AND status_code IN"
            " ('draft', 'registered', 'in_progress', 'partially_completed', 'completed'))"
            " OR (entity_type = 'samples' AND status_code IN"
            " ('pending', 'registered', 'in_progress', 'analyzed', 'completed', 'rejected'))",
            name="role_subscription_rules_status_code_check",
        ),
        Index(
            "role_subscription_rules_unique_rule",
            "role_id",
            "entity_type",
            text("COALESCE(branch_id, '00000000-0000-0000-0000-000000000000')"),
            text("COALESCE(lab_id, '00000000-0000-0000-0000-000000000000')"),
            text("COALESCE(status_code, '')"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("role_subscription_rules_role_id", "role_id"),
        Index("role_subscription_rules_deleted_at", "deleted_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=new_uuid7,
    )
    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", name="fk_role_subscription_rules_role_id_roles_id"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[str | None] = mapped_column(Text)
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
