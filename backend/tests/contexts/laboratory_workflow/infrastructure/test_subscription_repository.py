"""Integration coverage for the four-source subscriber derivation.

Gated on APP_TEST_DATABASE_URL like the other repository tests: it seeds a small
graph of roles, users, rules, a direction and its samples in a real Postgres and
asserts who list_for_entity / resolve_notification_targets derive as followers.
"""

from __future__ import annotations

from os import environ
from uuid import UUID

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.contexts.laboratory_workflow.infrastructure.crud_repositories import (
    SubscriptionCrudRepository,
)
from src.infrastructure.db.models import (
    Branch,
    Direction,
    Doctor,
    Lab,
    Object,
    Role,
    RoleSubscriptionRule,
    Sample,
    SampleLab,
    SampleStatus,
    User,
)

BRANCH_A = UUID("f0000000-0000-0000-0000-0000000000a1")
BRANCH_B = UUID("f0000000-0000-0000-0000-0000000000a2")
LAB_X = UUID("f0000000-0000-0000-0000-0000000000b1")
LAB_Y = UUID("f0000000-0000-0000-0000-0000000000b2")
OBJECT_A = UUID("f0000000-0000-0000-0000-0000000000c1")
OBJECT_B = UUID("f0000000-0000-0000-0000-0000000000c2")

ROLE_GLOBAL = UUID("f0000000-0000-0000-0000-0000000000d1")
ROLE_BRANCH = UUID("f0000000-0000-0000-0000-0000000000d2")
ROLE_LAB = UUID("f0000000-0000-0000-0000-0000000000d3")
ROLE_NONE = UUID("f0000000-0000-0000-0000-0000000000d4")
ROLE_STATUS = UUID("f0000000-0000-0000-0000-0000000000d5")

U_GLOBAL = UUID("f0000000-0000-0000-0000-0000000000e1")
U_BRANCH = UUID("f0000000-0000-0000-0000-0000000000e2")
U_LAB = UUID("f0000000-0000-0000-0000-0000000000e3")
U_OWNER = UUID("f0000000-0000-0000-0000-0000000000e4")
U_DOCTOR = UUID("f0000000-0000-0000-0000-0000000000e5")
U_STATUS = UUID("f0000000-0000-0000-0000-0000000000e6")

DOCTOR_ID = UUID("f0000000-0000-0000-0000-0000000000f1")
DIR_A = UUID("f0000000-0000-0000-0000-000000000101")
DIR_B = UUID("f0000000-0000-0000-0000-000000000102")
SAMPLE_LABX = UUID("f0000000-0000-0000-0000-000000000201")
SAMPLE_LABY = UUID("f0000000-0000-0000-0000-000000000202")
SAMPLE_REJECTED = UUID("f0000000-0000-0000-0000-000000000203")
SAMPLE_PENDING = UUID("f0000000-0000-0000-0000-000000000204")

RULE_IDS = [
    UUID("f0000000-0000-0000-0000-000000000301"),
    UUID("f0000000-0000-0000-0000-000000000302"),
    UUID("f0000000-0000-0000-0000-000000000303"),
    UUID("f0000000-0000-0000-0000-000000000304"),
    UUID("f0000000-0000-0000-0000-000000000305"),
    UUID("f0000000-0000-0000-0000-000000000306"),
]


def _database_url() -> str | None:
    return environ.get("APP_TEST_DATABASE_URL")


async def _seed(session: AsyncSession) -> None:
    # No ORM relationships are declared on these models, so SQLAlchemy cannot
    # topologically sort inter-table inserts; flush in dependency tiers instead.
    session.add_all(
        [
            Branch(id=BRANCH_A, code="BR-A", name="Branch A"),
            Branch(id=BRANCH_B, code="BR-B", name="Branch B"),
            Lab(id=LAB_X, code="LAB-X", name="Lab X"),
            Lab(id=LAB_Y, code="LAB-Y", name="Lab Y"),
            Role(id=ROLE_GLOBAL, key="sub_global", name="Global followers"),
            Role(id=ROLE_BRANCH, key="sub_branch", name="Branch followers"),
            Role(id=ROLE_LAB, key="sub_lab", name="Lab followers"),
            Role(id=ROLE_NONE, key="sub_none", name="No rule"),
            Role(id=ROLE_STATUS, key="sub_status", name="Rejected-only followers"),
        ]
    )
    await session.flush()
    rejected_status_id = (
        await session.execute(select(SampleStatus.id).where(SampleStatus.code == "rejected"))
    ).scalar_one()
    pending_status_id = (
        await session.execute(select(SampleStatus.id).where(SampleStatus.code == "pending"))
    ).scalar_one()
    session.add_all(
        [
            Object(id=OBJECT_A, code="OBJ-A", name="Object A", branch_id=BRANCH_A),
            Object(id=OBJECT_B, code="OBJ-B", name="Object B", branch_id=BRANCH_B),
            User(id=U_GLOBAL, username="u_global", password_hash="x", role_id=ROLE_GLOBAL),
            User(id=U_BRANCH, username="u_branch", password_hash="x", role_id=ROLE_BRANCH),
            User(id=U_LAB, username="u_lab", password_hash="x", role_id=ROLE_LAB),
            User(id=U_OWNER, username="u_owner", password_hash="x", role_id=ROLE_NONE),
            User(id=U_DOCTOR, username="u_doctor", password_hash="x", role_id=ROLE_NONE),
            User(id=U_STATUS, username="u_status", password_hash="x", role_id=ROLE_STATUS),
            RoleSubscriptionRule(id=RULE_IDS[0], role_id=ROLE_GLOBAL, entity_type="directions"),
            RoleSubscriptionRule(id=RULE_IDS[1], role_id=ROLE_GLOBAL, entity_type="samples"),
            RoleSubscriptionRule(
                id=RULE_IDS[2],
                role_id=ROLE_BRANCH,
                entity_type="directions",
                branch_id=BRANCH_A,
            ),
            RoleSubscriptionRule(
                id=RULE_IDS[3],
                role_id=ROLE_BRANCH,
                entity_type="samples",
                branch_id=BRANCH_A,
            ),
            RoleSubscriptionRule(
                id=RULE_IDS[4],
                role_id=ROLE_LAB,
                entity_type="samples",
                lab_id=LAB_X,
            ),
            RoleSubscriptionRule(
                id=RULE_IDS[5],
                role_id=ROLE_STATUS,
                entity_type="samples",
                status_code="rejected",
            ),
        ]
    )
    await session.flush()
    session.add(Doctor(id=DOCTOR_ID, first_name="Doc", user_id=U_DOCTOR))
    await session.flush()
    session.add_all(
        [
            Direction(
                id=DIR_A,
                year_no=2026,
                base_no=1,
                object_id=OBJECT_A,
                doctor_id=DOCTOR_ID,
                created_by=U_OWNER,
            ),
            Direction(
                id=DIR_B,
                year_no=2026,
                base_no=2,
                object_id=OBJECT_B,
                created_by=U_OWNER,
            ),
        ]
    )
    await session.flush()
    session.add_all(
        [
            Sample(id=SAMPLE_LABX, name="Sample X", direction_id=DIR_A),
            Sample(id=SAMPLE_LABY, name="Sample Y", direction_id=DIR_A),
            Sample(
                id=SAMPLE_REJECTED,
                name="Sample rejected",
                direction_id=DIR_A,
                status_id=rejected_status_id,
            ),
            Sample(
                id=SAMPLE_PENDING,
                name="Sample pending",
                direction_id=DIR_A,
                status_id=pending_status_id,
            ),
        ]
    )
    await session.flush()
    session.add_all(
        [
            SampleLab(sample_id=SAMPLE_LABX, lab_id=LAB_X),
            SampleLab(sample_id=SAMPLE_LABY, lab_id=LAB_Y),
        ]
    )
    await session.commit()


async def _cleanup(session: AsyncSession) -> None:
    await session.execute(
        delete(SampleLab).where(SampleLab.sample_id.in_([SAMPLE_LABX, SAMPLE_LABY]))
    )
    await session.execute(delete(RoleSubscriptionRule).where(RoleSubscriptionRule.id.in_(RULE_IDS)))
    sample_ids = [SAMPLE_LABX, SAMPLE_LABY, SAMPLE_REJECTED, SAMPLE_PENDING]
    await session.execute(delete(Sample).where(Sample.id.in_(sample_ids)))
    await session.execute(delete(Direction).where(Direction.id.in_([DIR_A, DIR_B])))
    await session.execute(delete(Doctor).where(Doctor.id == DOCTOR_ID))
    await session.execute(delete(Object).where(Object.id.in_([OBJECT_A, OBJECT_B])))
    await session.execute(
        delete(User).where(
            User.id.in_([U_GLOBAL, U_BRANCH, U_LAB, U_OWNER, U_DOCTOR, U_STATUS])
        )
    )
    await session.execute(
        delete(Role).where(
            Role.id.in_([ROLE_GLOBAL, ROLE_BRANCH, ROLE_LAB, ROLE_NONE, ROLE_STATUS])
        )
    )
    await session.execute(delete(Lab).where(Lab.id.in_([LAB_X, LAB_Y])))
    await session.execute(delete(Branch).where(Branch.id.in_([BRANCH_A, BRANCH_B])))
    await session.commit()


@pytest.mark.asyncio
async def test_subscription_derivation_role_scopes_and_doctor() -> None:
    database_url = _database_url()
    if database_url is None:
        pytest.skip("APP_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with session_factory() as session:
            await _cleanup(session)
            await _seed(session)

            repo = SubscriptionCrudRepository(session=session)

            # Direction in branch A: global + branch-A role rules, its owner and
            # its doctor. The lab rule is samples-only, so u_lab never matches.
            dir_a = await repo.list_for_entity("directions", DIR_A)
            source_by_user = {row["user_id"]: row["source"] for row in dir_a}
            assert source_by_user.get(U_GLOBAL) == "role"
            assert source_by_user.get(U_BRANCH) == "role"
            assert source_by_user.get(U_OWNER) == "owner"
            assert source_by_user.get(U_DOCTOR) == "doctor"
            assert U_LAB not in source_by_user

            # Direction in branch B: the branch-A rule must NOT match, only the
            # global rule and the owner (no doctor on this direction).
            dir_b_targets = await repo.resolve_notification_targets("directions", DIR_B)
            assert U_GLOBAL in dir_b_targets
            assert U_OWNER in dir_b_targets
            assert U_BRANCH not in dir_b_targets
            assert U_DOCTOR not in dir_b_targets

            # Sample assigned to lab X (branch A): global + branch + lab role
            # rules all match, plus the parent direction's owner and doctor.
            sample_x = await repo.resolve_notification_targets("samples", SAMPLE_LABX)
            assert {U_GLOBAL, U_BRANCH, U_LAB, U_OWNER, U_DOCTOR} <= sample_x

            # Sample assigned to lab Y: the lab-X rule must NOT match, but the
            # global and branch-A rules still do.
            sample_y = await repo.resolve_notification_targets("samples", SAMPLE_LABY)
            assert U_GLOBAL in sample_y
            assert U_BRANCH in sample_y
            assert U_LAB not in sample_y

            # Status-scoped rule: only the rejected sample gets the status
            # follower, a pending sibling in the same direction does not.
            rejected_targets = await repo.resolve_notification_targets(
                "samples", SAMPLE_REJECTED
            )
            assert U_STATUS in rejected_targets
            pending_targets = await repo.resolve_notification_targets("samples", SAMPLE_PENDING)
            assert U_STATUS not in pending_targets
    finally:
        async with session_factory() as session:
            await _cleanup(session)
        await engine.dispose()
