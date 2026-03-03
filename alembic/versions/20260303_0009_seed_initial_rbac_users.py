"""seed initial users and role permission matrix

Revision ID: 20260303_0009
Revises: 20260303_0008
Create Date: 2026-03-03 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Iterable

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260303_0009"
down_revision = "20260303_0008"
branch_labels = None
depends_on = None


ROLE_DEFINITIONS: dict[str, dict[str, str]] = {
    "admin": {"name": "Administrator", "scope_type": "global"},
    "registrar": {"name": "Registrar", "scope_type": "own_branch"},
    "sanitary_inspector": {"name": "Sanitary Inspector", "scope_type": "own_objects"},
    "lab_doctor": {"name": "Lab Doctor", "scope_type": "own_lab"},
    "lab_assistant": {"name": "Lab Assistant", "scope_type": "own_lab"},
    "lab_chief": {"name": "Lab Chief", "scope_type": "own_lab"},
    "branch_chief": {"name": "Branch Chief", "scope_type": "own_branch"},
    "developer": {"name": "Developer", "scope_type": "global"},
}

PERMISSION_CATALOG: tuple[tuple[str, str], ...] = (
    ("branches", "read"),
    ("change_log", "read"),
    ("conclusion_statuses", "read"),
    ("conclusions", "create"),
    ("conclusions", "read"),
    ("conclusions", "update"),
    ("directions", "create"),
    ("directions", "import"),
    ("directions", "read"),
    ("directions", "register"),
    ("directions", "update"),
    ("doctors", "create"),
    ("doctors", "delete"),
    ("doctors", "read"),
    ("doctors", "update"),
    ("indicators", "create"),
    ("indicators", "delete"),
    ("indicators", "read"),
    ("indicators", "update"),
    ("labs", "read"),
    ("objects", "read"),
    ("protocol_types", "read"),
    ("protocols", "create"),
    ("protocols", "read"),
    ("protocols", "update"),
    ("research_goals", "read"),
    ("results", "confirm"),
    ("results", "read"),
    ("results", "reject"),
    ("results", "start"),
    ("role_permissions", "create"),
    ("role_permissions", "delete"),
    ("role_permissions", "read"),
    ("role_permissions", "update"),
    ("roles", "create"),
    ("roles", "delete"),
    ("roles", "read"),
    ("roles", "update"),
    ("sample_targets", "read"),
    ("sample_types", "read"),
    ("samples", "close"),
    ("samples", "create"),
    ("samples", "read"),
    ("samples", "register"),
    ("samples", "reject"),
    ("samples", "update"),
    ("statuses", "read"),
    ("tests", "read"),
    ("tests", "reject"),
    ("tests", "requeue"),
    ("tests", "result"),
    ("tests", "start"),
    ("user_roles", "create"),
    ("user_roles", "delete"),
    ("user_roles", "read"),
    ("user_roles", "update"),
    ("users", "create"),
    ("users", "delete"),
    ("users", "read"),
    ("users", "update"),
)

ROLE_PERMISSION_MATRIX: dict[str, tuple[tuple[str, str], ...]] = {
    "admin": (
        ("roles", "create"),
        ("roles", "read"),
        ("roles", "update"),
        ("roles", "delete"),
        ("role_permissions", "create"),
        ("role_permissions", "read"),
        ("role_permissions", "update"),
        ("role_permissions", "delete"),
        ("users", "create"),
        ("users", "read"),
        ("users", "update"),
        ("users", "delete"),
        ("user_roles", "create"),
        ("user_roles", "read"),
        ("user_roles", "update"),
        ("user_roles", "delete"),
        ("directions", "read"),
        ("samples", "read"),
        ("results", "read"),
        ("tests", "read"),
        ("protocols", "read"),
        ("conclusions", "read"),
        ("change_log", "read"),
    ),
    "registrar": (
        ("branches", "read"),
        ("labs", "read"),
        ("objects", "read"),
        ("sample_types", "read"),
        ("sample_targets", "read"),
        ("research_goals", "read"),
        ("indicators", "read"),
        ("protocol_types", "read"),
        ("statuses", "read"),
        ("directions", "create"),
        ("directions", "read"),
        ("directions", "update"),
        ("directions", "import"),
        ("directions", "register"),
        ("samples", "create"),
        ("samples", "read"),
        ("samples", "update"),
        ("samples", "register"),
        ("samples", "reject"),
        ("results", "read"),
        ("results", "reject"),
        ("tests", "read"),
        ("protocols", "create"),
        ("protocols", "read"),
        ("protocols", "update"),
        ("conclusions", "create"),
        ("conclusions", "read"),
        ("conclusions", "update"),
    ),
    "sanitary_inspector": (
        ("directions", "read"),
        ("samples", "read"),
        ("protocols", "read"),
        ("conclusions", "read"),
        ("change_log", "read"),
    ),
    "lab_doctor": (
        ("sample_types", "read"),
        ("sample_targets", "read"),
        ("research_goals", "read"),
        ("indicators", "create"),
        ("indicators", "read"),
        ("indicators", "update"),
        ("indicators", "delete"),
        ("statuses", "read"),
        ("directions", "read"),
        ("samples", "read"),
        ("samples", "reject"),
        ("results", "read"),
        ("results", "confirm"),
        ("results", "start"),
        ("results", "reject"),
        ("tests", "read"),
        ("tests", "start"),
        ("tests", "result"),
        ("tests", "requeue"),
        ("tests", "reject"),
        ("protocols", "read"),
        ("conclusions", "read"),
        ("change_log", "read"),
    ),
    "lab_assistant": (
        ("labs", "read"),
        ("sample_types", "read"),
        ("sample_targets", "read"),
        ("research_goals", "read"),
        ("indicators", "read"),
        ("statuses", "read"),
        ("directions", "read"),
        ("samples", "read"),
        ("results", "read"),
        ("tests", "read"),
        ("protocols", "read"),
        ("conclusions", "read"),
        ("change_log", "read"),
    ),
    "lab_chief": (
        ("branches", "read"),
        ("labs", "read"),
        ("sample_types", "read"),
        ("sample_targets", "read"),
        ("research_goals", "read"),
        ("indicators", "read"),
        ("indicators", "update"),
        ("protocol_types", "read"),
        ("statuses", "read"),
        ("conclusion_statuses", "read"),
        ("directions", "read"),
        ("samples", "read"),
        ("samples", "close"),
        ("results", "read"),
        ("results", "confirm"),
        ("results", "start"),
        ("results", "reject"),
        ("tests", "read"),
        ("tests", "start"),
        ("tests", "result"),
        ("tests", "requeue"),
        ("tests", "reject"),
        ("protocols", "read"),
        ("conclusions", "read"),
        ("change_log", "read"),
    ),
    "branch_chief": (
        ("branches", "read"),
        ("labs", "read"),
        ("objects", "read"),
        ("statuses", "read"),
        ("directions", "read"),
        ("samples", "read"),
        ("results", "read"),
        ("tests", "read"),
        ("protocols", "read"),
        ("conclusions", "read"),
        ("change_log", "read"),
    ),
}

SEED_USERS: tuple[dict[str, object], ...] = (
    {
        "username": "admin",
        "password_hash": "$2b$12$31.eOAY8FTBiLBeFDln1aukR6ulC9N3QPHpSaHb4K03w8oSirMMXO",
        "role_key": "admin",
        "code": "ADM-001",
        "first_name": "System",
        "last_name": "Administrator",
        "is_registrar": False,
        "is_lab_head": False,
        "is_branch_head": False,
    },
    {
        "username": "registrator",
        "password_hash": "$2b$12$2P2Th3MrtGkwfPY8RlpASeU4BrFDKLuTuaTYL1iJJ5k.UgceEmoDG",
        "role_key": "registrar",
        "code": "REG-001",
        "first_name": "Main",
        "last_name": "Registrar",
        "is_registrar": True,
        "is_lab_head": False,
        "is_branch_head": False,
    },
    {
        "username": "sandoctor",
        "password_hash": "$2b$12$hnKaA3krUf/OcLNbT2h0cODuytiz5ZBoFO59KPGoNwUxQaYBH5sgq",
        "role_key": "sanitary_inspector",
        "code": "SAN-001",
        "first_name": "Sanitary",
        "last_name": "Inspector",
        "is_registrar": False,
        "is_lab_head": False,
        "is_branch_head": False,
    },
    {
        "username": "doctor",
        "password_hash": "$2b$12$HEI0Om0Yj3dN23iuNOQv5.o7LxfO3lvH/8UZDYY1QMq13w6XlAYKS",
        "role_key": "lab_doctor",
        "code": "DOC-001",
        "first_name": "Lab",
        "last_name": "Doctor",
        "is_registrar": False,
        "is_lab_head": False,
        "is_branch_head": False,
    },
    {
        "username": "laborant",
        "password_hash": "$2b$12$8KWv04UbCAHys4zsydg7o.P4PovTzkemvne.9FOPzilpzR8k20Drq",
        "role_key": "lab_assistant",
        "code": "LAB-001",
        "first_name": "Lab",
        "last_name": "Assistant",
        "is_registrar": False,
        "is_lab_head": False,
        "is_branch_head": False,
    },
    {
        "username": "nachlab",
        "password_hash": "$2b$12$xSeCXbFqxLyz5Bz8oDmBEud3N9zVxV5u470fjvMS2sjlTnSxR1Dg2",
        "role_key": "lab_chief",
        "code": "LCH-001",
        "first_name": "Lab",
        "last_name": "Chief",
        "is_registrar": False,
        "is_lab_head": True,
        "is_branch_head": False,
    },
    {
        "username": "nachfil",
        "password_hash": "$2b$12$Z/cYiesQmpPPbH6Sfov0Xe.Rd0167R.p2B.lz757Sq6hmi1hnlKfO",
        "role_key": "branch_chief",
        "code": "BCH-001",
        "first_name": "Branch",
        "last_name": "Chief",
        "is_registrar": False,
        "is_lab_head": False,
        "is_branch_head": True,
    },
    {
        "username": "tminww",
        "password_hash": "$2b$12$YCNo9bFWrwCFeHXVf69nsOEQVB5yxtP2LMT6Rbenuw0kFOsI4GgaW",
        "role_key": "developer",
        "code": "DEV-001",
        "first_name": "Tminww",
        "last_name": "Developer",
        "is_registrar": False,
        "is_lab_head": False,
        "is_branch_head": False,
    },
)


def _delete_role_permissions_for_roles(conn: sa.Connection, role_keys: Iterable[str]) -> None:
    stmt = sa.text(
        """
        DELETE FROM role_permissions
        WHERE role_id IN (
            SELECT id
            FROM roles
            WHERE key IN :role_keys
        )
        """
    ).bindparams(sa.bindparam("role_keys", expanding=True))
    conn.execute(stmt, {"role_keys": list(role_keys)})


def upgrade() -> None:
    conn = op.get_bind()

    upsert_role = sa.text(
        """
        INSERT INTO roles (key, name, scope_type)
        VALUES (:key, :name, CAST(:scope_type AS role_scope_type))
        ON CONFLICT (key) DO UPDATE
        SET
            name = EXCLUDED.name,
            scope_type = EXCLUDED.scope_type,
            updated_at = CURRENT_TIMESTAMP
        """
    )
    for role_key, payload in ROLE_DEFINITIONS.items():
        conn.execute(
            upsert_role,
            {
                "key": role_key,
                "name": payload["name"],
                "scope_type": payload["scope_type"],
            },
        )

    insert_permission = sa.text(
        """
        INSERT INTO permissions (resource, action)
        VALUES (:resource, :action)
        ON CONFLICT (resource, action) DO NOTHING
        """
    )
    for resource, action in PERMISSION_CATALOG:
        conn.execute(insert_permission, {"resource": resource, "action": action})

    _delete_role_permissions_for_roles(conn, ROLE_DEFINITIONS.keys())

    insert_role_permission = sa.text(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p
          ON p.resource = :resource
         AND p.action = :action
        WHERE r.key = :role_key
        ON CONFLICT (role_id, permission_id) DO NOTHING
        """
    )
    for role_key, pairs in ROLE_PERMISSION_MATRIX.items():
        for resource, action in pairs:
            conn.execute(
                insert_role_permission,
                {
                    "role_key": role_key,
                    "resource": resource,
                    "action": action,
                },
            )

    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.key = 'developer'
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        )
    )

    upsert_user = sa.text(
        """
        INSERT INTO users (
            username,
            password_hash,
            refresh_token_version,
            code,
            first_name,
            last_name,
            patronymic,
            is_registrar,
            is_lab_head,
            is_branch_head,
            role_id,
            lab_id
        )
        SELECT
            :username,
            :password_hash,
            0,
            :code,
            :first_name,
            :last_name,
            NULL,
            :is_registrar,
            :is_lab_head,
            :is_branch_head,
            r.id,
            NULL
        FROM roles r
        WHERE r.key = :role_key
        ON CONFLICT (username) DO UPDATE
        SET
            password_hash = EXCLUDED.password_hash,
            refresh_token_version = 0,
            code = EXCLUDED.code,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            patronymic = EXCLUDED.patronymic,
            is_registrar = EXCLUDED.is_registrar,
            is_lab_head = EXCLUDED.is_lab_head,
            is_branch_head = EXCLUDED.is_branch_head,
            role_id = EXCLUDED.role_id,
            lab_id = EXCLUDED.lab_id,
            deleted_at = NULL,
            updated_at = CURRENT_TIMESTAMP
        """
    )
    for user in SEED_USERS:
        conn.execute(upsert_user, user)


def downgrade() -> None:
    conn = op.get_bind()

    delete_users = sa.text(
        """
        DELETE FROM users
        WHERE username IN :usernames
        """
    ).bindparams(sa.bindparam("usernames", expanding=True))
    conn.execute(delete_users, {"usernames": [item["username"] for item in SEED_USERS]})

    _delete_role_permissions_for_roles(conn, ROLE_DEFINITIONS.keys())

    conn.execute(
        sa.text(
            """
            DELETE FROM roles
            WHERE key IN ('developer', 'lab_assistant')
              AND NOT EXISTS (
                  SELECT 1
                  FROM users u
                  WHERE u.role_id = roles.id
              )
            """
        )
    )
