"""seed reference data

Revision ID: 20260219_0002
Revises: 20260218_0001
Create Date: 2026-02-19 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260219_0002"
down_revision = "20260218_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO roles (key, name, scope_type)
        VALUES
            ('admin', 'Administrator', 'global'),
            ('registrar', 'Registrar', 'own_branch'),
            ('branch_chief', 'Branch Chief', 'own_branch'),
            ('lab_chief', 'Laboratory Chief', 'own_lab'),
            ('lab_doctor', 'Laboratory Doctor', 'own_lab'),
            ('laborant', 'Laborant', 'own_lab'),
            ('sanitary_inspector', 'Sanitary Inspector', 'own_objects')
        ON CONFLICT (key) DO UPDATE
        SET
            name = EXCLUDED.name,
            scope_type = EXCLUDED.scope_type,
            updated_at = CURRENT_TIMESTAMP;
        """)

    op.execute("""
        INSERT INTO statuses (code, name)
        SELECT
            'ST-' || LPAD(gs::text, 3, '0'),
            'Status ' || gs::text
        FROM generate_series(1, 100) AS gs
        ON CONFLICT (code) DO NOTHING;
        """)

    op.execute("""
        INSERT INTO conclusion_statuses (code, name)
        SELECT
            'CSTAT-' || LPAD(gs::text, 3, '0'),
            'Conclusion Status ' || gs::text
        FROM generate_series(1, 100) AS gs
        ON CONFLICT (code) DO NOTHING;
        """)

    op.execute("""
        INSERT INTO sample_types (code, name)
        SELECT
            'SAMPLE-TYPE-' || LPAD(gs::text, 3, '0'),
            'Sample Type ' || gs::text
        FROM generate_series(1, 100) AS gs
        ON CONFLICT (code) DO NOTHING;
        """)

    op.execute("""
        INSERT INTO protocol_types (code, name)
        SELECT
            'PROTO-' || LPAD(gs::text, 3, '0'),
            'Protocol Type ' || gs::text
        FROM generate_series(1, 100) AS gs
        ON CONFLICT (code) DO NOTHING;
        """)

    op.execute("""
        INSERT INTO branches (code, name)
        SELECT src.code, src.name
        FROM (
            SELECT
                'BR-' || LPAD(gs::text, 3, '0') AS code,
                'Branch ' || gs::text AS name
            FROM generate_series(1, 100) AS gs
        ) AS src
        WHERE NOT EXISTS (
            SELECT 1
            FROM branches b
            WHERE b.code = src.code
        );
        """)

    op.execute("""
        WITH branch_pool AS (
            SELECT
                id,
                row_number() OVER (ORDER BY code, id) AS rn
            FROM branches
            WHERE code LIKE 'BR-%'
        ),
        src AS (
            SELECT
                gs,
                'LAB-' || LPAD(gs::text, 3, '0') AS code,
                'Lab ' || gs::text AS name,
                ((gs - 1) % 100) + 1 AS branch_rn
            FROM generate_series(1, 100) AS gs
        )
        INSERT INTO labs (code, name, full_name, branch_id)
        SELECT
            src.code,
            src.name,
            src.name || ' Full',
            bp.id
        FROM src
        LEFT JOIN branch_pool bp ON bp.rn = src.branch_rn
        ON CONFLICT (code) DO NOTHING;
        """)

    op.execute("""
        WITH branch_pool AS (
            SELECT
                id,
                row_number() OVER (ORDER BY code, id) AS rn
            FROM branches
            WHERE code LIKE 'BR-%'
        ),
        src AS (
            SELECT
                gs,
                'OBJ-' || LPAD(gs::text, 3, '0') AS code,
                'Object ' || gs::text AS name,
                ((gs - 1) % 100) + 1 AS branch_rn
            FROM generate_series(1, 100) AS gs
        )
        INSERT INTO objects (code, name, full_name, address, branch_id)
        SELECT
            src.code,
            src.name,
            src.name || ' Full',
            'Address ' || src.gs::text,
            bp.id
        FROM src
        LEFT JOIN branch_pool bp ON bp.rn = src.branch_rn
        ON CONFLICT (code) DO NOTHING;
        """)

    op.execute("""
        INSERT INTO doctors (first_name, last_name, patronymic)
        SELECT
            'Doctor ' || gs::text,
            'Surname ' || gs::text,
            'Patronymic ' || gs::text
        FROM generate_series(1, 100) AS gs
        WHERE NOT EXISTS (
            SELECT 1
            FROM doctors d
            WHERE d.first_name = 'Doctor ' || gs::text
              AND d.last_name = 'Surname ' || gs::text
        );
        """)

    op.execute("""
        WITH lab_pool AS (
            SELECT
                id,
                row_number() OVER (ORDER BY code, id) AS rn
            FROM labs
            WHERE code LIKE 'LAB-%'
        ),
        src AS (
            SELECT
                gs,
                'RG-' || LPAD(gs::text, 3, '0') AS code,
                'Research Goal ' || gs::text AS name,
                ((gs - 1) % 100) + 1 AS lab_rn
            FROM generate_series(1, 100) AS gs
        )
        INSERT INTO research_goals (code, name, comment, lab_id)
        SELECT
            src.code,
            src.name,
            'Auto-seeded reference goal',
            lp.id
        FROM src
        LEFT JOIN lab_pool lp ON lp.rn = src.lab_rn
        ON CONFLICT (code) DO NOTHING;
        """)

    op.execute("""
        WITH lab_pool AS (
            SELECT
                id,
                row_number() OVER (ORDER BY code, id) AS rn
            FROM labs
            WHERE code LIKE 'LAB-%'
        ),
        sample_type_pool AS (
            SELECT
                id,
                row_number() OVER (ORDER BY code, id) AS rn
            FROM sample_types
            WHERE code LIKE 'SAMPLE-TYPE-%'
        ),
        src AS (
            SELECT
                gs,
                'Indicator ' || gs::text AS name,
                ((gs - 1) % 100) + 1 AS lab_rn,
                ((gs - 1) % 100) + 1 AS sample_type_rn
            FROM generate_series(1, 100) AS gs
        )
        INSERT INTO indicators (
            name,
            unit,
            norm_text,
            norm_value,
            default_text,
            comment,
            lab_id,
            sample_type_id
        )
        SELECT
            src.name,
            'mg/L',
            'Normal range',
            (src.gs::text || '.0'),
            'N/A',
            'Auto-seeded reference indicator',
            lp.id,
            stp.id
        FROM src
        LEFT JOIN lab_pool lp ON lp.rn = src.lab_rn
        LEFT JOIN sample_type_pool stp ON stp.rn = src.sample_type_rn
        WHERE NOT EXISTS (
            SELECT 1
            FROM indicators i
            WHERE i.name = src.name
        );
        """)

    op.execute("""
        WITH role_pool AS (
            SELECT
                id,
                row_number() OVER (ORDER BY key, id) AS rn
            FROM roles
        ),
        role_meta AS (
            SELECT COUNT(*)::int AS cnt FROM role_pool
        ),
        lab_pool AS (
            SELECT
                id,
                row_number() OVER (ORDER BY code, id) AS rn
            FROM labs
            WHERE code LIKE 'LAB-%'
        ),
        lab_meta AS (
            SELECT COUNT(*)::int AS cnt FROM lab_pool
        ),
        src AS (
            SELECT
                gs,
                'user_' || LPAD(gs::text, 3, '0') AS username,
                ((gs - 1) % GREATEST((SELECT cnt FROM role_meta), 1)) + 1 AS role_rn,
                CASE
                    WHEN (SELECT cnt FROM lab_meta) = 0 THEN NULL
                    ELSE ((gs - 1) % (SELECT cnt FROM lab_meta)) + 1
                END AS lab_rn
            FROM generate_series(1, 100) AS gs
        )
        INSERT INTO users (
            username,
            password_hash,
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
            src.username,
            'seed_password_hash',
            'USR-' || LPAD(src.gs::text, 3, '0'),
            'User ' || src.gs::text,
            'Seeded',
            'Autogen',
            (src.gs % 5 = 0),
            (src.gs % 7 = 0),
            (src.gs % 9 = 0),
            rp.id,
            lp.id
        FROM src
        JOIN role_pool rp ON rp.rn = src.role_rn
        LEFT JOIN lab_pool lp ON lp.rn = src.lab_rn
        ON CONFLICT (username) DO NOTHING;
        """)

    op.execute("""
        WITH resources (resource) AS (
            VALUES
                ('branches'),
                ('labs'),
                ('objects'),
                ('doctors'),
                ('research_goals'),
                ('indicators'),
                ('directions'),
                ('samples'),
                ('results'),
                ('tests')
        ),
        actions (action) AS (
            VALUES
                ('read'),
                ('create'),
                ('update'),
                ('delete')
        ),
        permissions_seed AS (
            INSERT INTO permissions (resource, action)
            SELECT res.resource, act.action
            FROM resources res
            CROSS JOIN actions act
            ON CONFLICT (resource, action) DO NOTHING
            RETURNING id, resource, action
        ),
        permission_map AS (
            SELECT id, resource, action FROM permissions_seed
            UNION ALL
            SELECT p.id, p.resource, p.action
            FROM permissions p
            JOIN resources res ON res.resource = p.resource
            JOIN actions act ON act.action = p.action
        )
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT DISTINCT r.id, pm.id
        FROM roles r
        JOIN permission_map pm ON r.key = 'admin' OR pm.action = 'read'
        ON CONFLICT (role_id, permission_id) DO NOTHING;
        """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions rp
        USING roles r, permissions p
        WHERE rp.role_id = r.id
          AND rp.permission_id = p.id
          AND r.key IN (
              'admin',
              'registrar',
              'branch_chief',
              'lab_chief',
              'lab_doctor',
              'laborant',
              'sanitary_inspector'
          )
          AND p.resource IN (
              'branches',
              'labs',
              'objects',
              'doctors',
              'research_goals',
              'indicators',
              'directions',
              'samples',
              'results',
              'tests'
          )
          AND p.action IN ('read', 'create', 'update', 'delete');
        """)

    op.execute("""
        DELETE FROM permissions p
        WHERE p.resource IN (
            'branches',
            'labs',
            'objects',
            'doctors',
            'research_goals',
            'indicators',
            'directions',
            'samples',
            'results',
            'tests'
        )
        AND p.action IN ('read', 'create', 'update', 'delete')
        AND NOT EXISTS (
            SELECT 1
            FROM role_permissions rp
            WHERE rp.permission_id = p.id
        );
        """)

    op.execute("DELETE FROM users WHERE username LIKE 'user_%';")
    op.execute("DELETE FROM indicators WHERE name LIKE 'Indicator %';")
    op.execute("DELETE FROM research_goals WHERE code LIKE 'RG-%';")
    op.execute("DELETE FROM doctors WHERE first_name LIKE 'Doctor %';")
    op.execute("DELETE FROM objects WHERE code LIKE 'OBJ-%';")
    op.execute("DELETE FROM labs WHERE code LIKE 'LAB-%';")
    op.execute("DELETE FROM branches WHERE code LIKE 'BR-%';")
    op.execute("DELETE FROM sample_types WHERE code LIKE 'SAMPLE-TYPE-%';")
    op.execute("DELETE FROM protocol_types WHERE code LIKE 'PROTO-%';")
    op.execute("DELETE FROM conclusion_statuses WHERE code LIKE 'CSTAT-%';")
    op.execute("DELETE FROM statuses WHERE code LIKE 'ST-%';")
    op.execute("""
        DELETE FROM roles
        WHERE key IN (
            'admin',
            'registrar',
            'branch_chief',
            'lab_chief',
            'lab_doctor',
            'laborant',
            'sanitary_inspector'
        );
        """)
