# ruff: noqa: RUF001

from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass

import asyncpg  # type: ignore[import-untyped]

REFERENCE_MAX = 100
HIGHLOAD_MAX = 1_000_000
AUX_TABLE_MAX_MULTIPLIER = 20

SEEDED_TABLES: tuple[str, ...] = (
    "roles",
    "direction_statuses",
    "sample_statuses",
    "research_statuses",
    "test_statuses",
    "sample_types",
    "protocol_types",
    "branches",
    "labs",
    "objects",
    "doctors",
    "research_goals",
    "indicators",
    "users",
    "permissions",
    "role_permissions",
    "user_scopes",
    "directions",
    "samples",
    "research",
    "tests",
    "conclusions",
    "protocols",
    "change_log",
)

PROFILE_DEFAULTS: dict[str, dict[str, int]] = {
    "tiny": {
        "reference_count": 5,
        "directions": 100,
        "samples": 100,
        "research": 100,
        "tests": 100,
    },
    "dev": {
        "reference_count": 100,
        "directions": 10_000,
        "samples": 10_000,
        "research": 10_000,
        "tests": 10_000,
    },
    "perf-lite": {
        "reference_count": 100,
        "directions": 100_000,
        "samples": 100_000,
        "research": 100_000,
        "tests": 100_000,
    },
}


@dataclass(slots=True)
class SeedPlan:
    database_url: str
    reference_count: int
    directions: int
    samples: int
    research: int
    tests: int
    truncate: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deterministic seed data by schema. "
            "Reference entities are capped at 100 records; "
            "high-load entities are capped at 1,000,000 records."
        )
    )
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_DEFAULTS.keys()),
        default="dev",
        help="Base preset for seed volumes.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database DSN. Falls back to APP_ALEMBIC_DATABASE_URL/APP_DATABASE_URL.",
    )
    parser.add_argument(
        "--reference-count",
        type=int,
        default=None,
        help="Rows for each reference entity (0-100).",
    )
    parser.add_argument(
        "--directions",
        type=int,
        default=None,
        help="Rows for directions (0-1000000).",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=None,
        help="Rows for samples (0-1000000).",
    )
    parser.add_argument(
        "--research",
        type=int,
        default=None,
        help="Rows for research (0-1000000).",
    )
    parser.add_argument(
        "--tests",
        type=int,
        default=None,
        help="Rows for tests (0-1000000).",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate seeded tables before generation.",
    )
    return parser.parse_args()


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url.split("://", 1)[1]
    return url


def resolve_database_url(cli_url: str | None) -> str:
    if cli_url:
        return normalize_database_url(cli_url)

    env_url = os.getenv("APP_ALEMBIC_DATABASE_URL") or os.getenv("APP_DATABASE_URL")
    if env_url:
        return normalize_database_url(env_url)

    return "postgresql://postgres:postgres@127.0.0.1:5432/biologic"


def enforce_bounds(name: str, value: int, minimum: int, maximum: int) -> None:
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be in range [{minimum}, {maximum}], got {value}")


def derive_aux_table_count(primary: int, reference_count: int) -> int:
    baseline = primary if primary > 0 else reference_count
    if baseline <= 0:
        return 1

    cap = max(reference_count, 1) * AUX_TABLE_MAX_MULTIPLIER
    return min(baseline, cap)


def build_plan(args: argparse.Namespace) -> SeedPlan:
    defaults = PROFILE_DEFAULTS[args.profile]

    reference_count = (
        defaults["reference_count"] if args.reference_count is None else args.reference_count
    )
    directions = defaults["directions"] if args.directions is None else args.directions
    samples = defaults["samples"] if args.samples is None else args.samples
    research = defaults["research"] if args.research is None else args.research
    tests = defaults["tests"] if args.tests is None else args.tests

    enforce_bounds("reference_count", reference_count, 0, REFERENCE_MAX)
    enforce_bounds("directions", directions, 0, HIGHLOAD_MAX)
    enforce_bounds("samples", samples, 0, HIGHLOAD_MAX)
    enforce_bounds("research", research, 0, HIGHLOAD_MAX)
    enforce_bounds("tests", tests, 0, HIGHLOAD_MAX)

    return SeedPlan(
        database_url=resolve_database_url(args.database_url),
        reference_count=reference_count,
        directions=directions,
        samples=samples,
        research=research,
        tests=tests,
        truncate=args.truncate,
    )


async def table_count(conn: asyncpg.Connection, table_name: str) -> int:
    query = f"SELECT COUNT(*)::bigint FROM {table_name}"
    return int(await conn.fetchval(query))


async def truncate_seeded_tables(conn: asyncpg.Connection) -> None:
    await conn.execute("""
        TRUNCATE TABLE
            tests,
            research,
            samples,
            directions,
            protocols,
            conclusions,
            change_log,
            indicators,
            research_goals,
            objects,
            doctors,
            role_permissions,
            user_scopes,
            permissions,
            users,
            labs,
            branches,
            sample_types,
            protocol_types,
            test_statuses,
            research_statuses,
            sample_statuses,
            direction_statuses,
            roles
        CASCADE;
        """)


async def seed_reference_entities(conn: asyncpg.Connection, count: int) -> None:
    if count == 0:
        return

    await conn.execute("""
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

    await conn.execute("""
        INSERT INTO direction_statuses (code, name)
        VALUES
            ('draft', 'Черновик'),
            ('registered', 'Зарегистрировано'),
            ('in_progress', 'В работе'),
            ('partially_completed', 'Частично выполнено'),
            ('completed', 'Выполнено')
        ON CONFLICT (code) DO NOTHING;
        """)

    await conn.execute("""
        INSERT INTO sample_statuses (code, name)
        VALUES
            ('pending', 'На регистрации'),
            ('registered', 'Зарегистрирован'),
            ('rejected', 'Брак'),
            ('in_progress', 'На исследовании'),
            ('analyzed', 'Обработан'),
            ('completed', 'Закрыт')
        ON CONFLICT (code) DO NOTHING;
        """)

    await conn.execute("""
        INSERT INTO research_statuses (code, name)
        VALUES
            ('draft', 'Черновик'),
            ('ordered', 'Запланировано'),
            ('in_progress', 'В работе'),
            ('completed', 'Завершено'),
            ('rejected', 'Отклонено')
        ON CONFLICT (code) DO NOTHING;
        """)

    await conn.execute("""
        INSERT INTO test_statuses (code, name)
        VALUES
            ('queued', 'Запланировано'),
            ('in_progress', 'Выполняется'),
            ('completed', 'Выполнено'),
            ('rejected', 'Отклонено')
        ON CONFLICT (code) DO NOTHING;
        """)

    await conn.execute(
        """
        INSERT INTO sample_types (code, name)
        SELECT
            'SAMPLE-TYPE-' || LPAD(gs::text, 3, '0'),
            'Sample Type ' || gs::text
        FROM generate_series(1, $1::int) AS gs
        ON CONFLICT (code) DO NOTHING;
        """,
        count,
    )

    await conn.execute(
        """
        INSERT INTO protocol_types (code, name)
        SELECT
            'PROTO-' || LPAD(gs::text, 3, '0'),
            'Protocol Type ' || gs::text
        FROM generate_series(1, $1::int) AS gs
        ON CONFLICT (code) DO NOTHING;
        """,
        count,
    )

    await conn.execute(
        """
        INSERT INTO branches (code, name)
        SELECT src.code, src.name
        FROM (
            SELECT
                'BR-' || LPAD(gs::text, 3, '0') AS code,
                'Branch ' || gs::text AS name
            FROM generate_series(1, $1::int) AS gs
        ) AS src
        WHERE NOT EXISTS (
            SELECT 1
            FROM branches b
            WHERE b.code = src.code
        );
        """,
        count,
    )

    await conn.execute(
        """
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
                ((gs - 1) % $1::int) + 1 AS branch_rn
            FROM generate_series(1, $1::int) AS gs
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
        """,
        count,
    )

    await conn.execute(
        """
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
                ((gs - 1) % $1::int) + 1 AS branch_rn
            FROM generate_series(1, $1::int) AS gs
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
        """,
        count,
    )

    await conn.execute(
        """
        INSERT INTO doctors (first_name, last_name, patronymic)
        SELECT
            'Doctor ' || gs::text,
            'Surname ' || gs::text,
            'Patronymic ' || gs::text
        FROM generate_series(1, $1::int) AS gs
        WHERE NOT EXISTS (
            SELECT 1
            FROM doctors d
            WHERE d.first_name = 'Doctor ' || gs::text
              AND d.last_name = 'Surname ' || gs::text
        );
        """,
        count,
    )

    await conn.execute(
        """
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
                ((gs - 1) % $1::int) + 1 AS lab_rn
            FROM generate_series(1, $1::int) AS gs
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
        """,
        count,
    )

    await conn.execute(
        """
        WITH research_goal_pool AS (
            SELECT
                id,
                row_number() OVER (ORDER BY code, id) AS rn
            FROM research_goals
            WHERE code LIKE 'RG-%'
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
                ((gs - 1) % $1::int) + 1 AS research_goal_rn,
                ((gs - 1) % $1::int) + 1 AS sample_type_rn
            FROM generate_series(1, $1::int) AS gs
        )
        INSERT INTO indicators (
            name,
            unit,
            norm_text,
            norm_value,
            default_text,
            comment,
            research_goal_id,
            sample_type_id
        )
        SELECT
            src.name,
            'mg/L',
            'Normal range',
            (src.gs::text || '.0'),
            'N/A',
            'Auto-seeded reference indicator',
            rgp.id,
            stp.id
        FROM src
        LEFT JOIN research_goal_pool rgp ON rgp.rn = src.research_goal_rn
        LEFT JOIN sample_type_pool stp ON stp.rn = src.sample_type_rn
        WHERE NOT EXISTS (
            SELECT 1
            FROM indicators i
            WHERE i.name = src.name
        );
        """,
        count,
    )

    await conn.execute(
        """
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
            FROM generate_series(1, $1::int) AS gs
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
        """,
        count,
    )

    await conn.execute("""
        WITH resources (resource) AS (
            VALUES
                ('branches'),
                ('labs'),
                ('objects'),
                ('doctors'),
                ('research_goals'),
                ('indicators'),
                ('direction_statuses'),
                ('sample_statuses'),
                ('research_statuses'),
                ('test_statuses'),
                ('directions'),
                ('samples'),
                ('research'),
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


async def insert_directions(conn: asyncpg.Connection, count: int) -> None:
    if count == 0:
        return

    await conn.execute(
        """
        WITH doctor_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM doctors
            WHERE deleted_at IS NULL
        ),
        doctor_meta AS (SELECT COUNT(*)::int AS cnt FROM doctor_pool),
        object_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM objects
            WHERE deleted_at IS NULL
        ),
        object_meta AS (SELECT COUNT(*)::int AS cnt FROM object_pool),
        status_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM direction_statuses
            WHERE deleted_at IS NULL
        ),
        status_meta AS (SELECT COUNT(*)::int AS cnt FROM status_pool),
        base_offset AS (
            SELECT COALESCE(MAX(base_no), 0) AS max_base FROM directions
        ),
        src AS (
            SELECT
                gs,
                ((gs - 1) % GREATEST((SELECT cnt FROM doctor_meta), 1)) + 1 AS doctor_rn,
                ((gs - 1) % GREATEST((SELECT cnt FROM object_meta), 1)) + 1 AS object_rn,
                ((gs - 1) % GREATEST((SELECT cnt FROM status_meta), 1)) + 1 AS status_rn
            FROM generate_series(1, $1::int) AS gs
        )
        INSERT INTO directions (
            year_no,
            base_no,
            is_done,
            is_urgent,
            doctor_id,
            object_id,
            status_id,
            sampled_at,
            received_at,
            completed_at
        )
        SELECT
            EXTRACT(YEAR FROM CURRENT_TIMESTAMP)::int,
            bo.max_base + src.gs,
            (src.gs % 3 = 0),
            (src.gs % 10 = 0),
            dp.id,
            op.id,
            sp.id,
            CURRENT_TIMESTAMP - ((src.gs % 30) || ' days')::interval,
            CURRENT_TIMESTAMP - ((src.gs % 20) || ' days')::interval,
            CASE
                WHEN src.gs % 3 = 0
                THEN CURRENT_TIMESTAMP - ((src.gs % 7) || ' days')::interval
                ELSE NULL
            END
        FROM src
        CROSS JOIN base_offset bo
        LEFT JOIN doctor_pool dp ON dp.rn = src.doctor_rn
        LEFT JOIN object_pool op ON op.rn = src.object_rn
        LEFT JOIN status_pool sp ON sp.rn = src.status_rn;
        """,
        count,
    )


async def insert_samples(conn: asyncpg.Connection, count: int) -> None:
    if count == 0:
        return

    await conn.execute(
        """
        WITH direction_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM directions
            WHERE deleted_at IS NULL
        ),
        direction_meta AS (SELECT COUNT(*)::int AS cnt FROM direction_pool),
        sample_type_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM sample_types
            WHERE deleted_at IS NULL
        ),
        sample_type_meta AS (SELECT COUNT(*)::int AS cnt FROM sample_type_pool),
        status_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM sample_statuses
            WHERE deleted_at IS NULL
        ),
        status_meta AS (SELECT COUNT(*)::int AS cnt FROM status_pool),
        src AS (
            SELECT
                gs,
                ((gs - 1) % GREATEST((SELECT cnt FROM direction_meta), 1)) + 1 AS direction_rn,
                ((gs - 1) % GREATEST((SELECT cnt FROM sample_type_meta), 1)) + 1 AS sample_type_rn,
                ((gs - 1) % GREATEST((SELECT cnt FROM status_meta), 1)) + 1 AS status_rn
            FROM generate_series(1, $1::int) AS gs
        )
        INSERT INTO samples (
            month_no,
            name,
            alternate_name,
            mass,
            target_description,
            comment,
            section,
            delivery,
            nomenclature_code,
            batch_code,
            supplier,
            is_urgent,
            is_done,
            sample_type_id,
            status_id,
            direction_id,
            sampled_at,
            received_at,
            completed_at
        )
        SELECT
            ((src.gs - 1) % 12) + 1,
            'Sample ' || src.gs::text,
            'Alt Sample ' || src.gs::text,
            ((src.gs % 200) + 1)::text || ' g',
            'Target ' || src.gs::text,
            'Auto-generated sample',
            'Section ' || ((src.gs % 5) + 1)::text,
            'Delivery ' || ((src.gs % 3) + 1)::text,
            'NM-' || LPAD(src.gs::text, 8, '0'),
            'BATCH-' || LPAD((src.gs % 1000)::text, 4, '0'),
            'Supplier ' || ((src.gs % 20) + 1)::text,
            (src.gs % 10 = 0),
            (src.gs % 3 = 0),
            stp.id,
            sp.id,
            dp.id,
            CURRENT_TIMESTAMP - ((src.gs % 30) || ' days')::interval,
            CURRENT_TIMESTAMP - ((src.gs % 20) || ' days')::interval,
            CASE
                WHEN src.gs % 3 = 0
                THEN CURRENT_TIMESTAMP - ((src.gs % 7) || ' days')::interval
                ELSE NULL
            END
        FROM src
        LEFT JOIN direction_pool dp ON dp.rn = src.direction_rn
        LEFT JOIN sample_type_pool stp ON stp.rn = src.sample_type_rn
        LEFT JOIN status_pool sp ON sp.rn = src.status_rn;
        """,
        count,
    )


async def insert_research(conn: asyncpg.Connection, count: int) -> None:
    if count == 0:
        return

    sample_total = await table_count(conn, "samples")
    if sample_total == 0:
        raise RuntimeError("Cannot generate research: samples table is empty.")

    research_goal_total = await table_count(conn, "research_goals")
    if research_goal_total == 0:
        raise RuntimeError("Cannot generate research: research_goals table is empty.")

    await conn.execute(
        """
        WITH sample_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM samples
            WHERE deleted_at IS NULL
        ),
        sample_meta AS (SELECT COUNT(*)::int AS cnt FROM sample_pool),
        research_goal_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM research_goals
            WHERE deleted_at IS NULL
        ),
        research_goal_meta AS (SELECT COUNT(*)::int AS cnt FROM research_goal_pool),
        status_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM research_statuses
            WHERE deleted_at IS NULL
        ),
        status_meta AS (SELECT COUNT(*)::int AS cnt FROM status_pool),
        src AS (
            SELECT
                gs,
                ((gs - 1) % GREATEST((SELECT cnt FROM sample_meta), 1)) + 1 AS sample_rn,
                (
                    (gs - 1) % GREATEST((SELECT cnt FROM research_goal_meta), 1)
                ) + 1 AS research_goal_rn,
                ((gs - 1) % GREATEST((SELECT cnt FROM status_meta), 1)) + 1 AS status_rn
            FROM generate_series(1, $1::int) AS gs
        )
        INSERT INTO research (
            sample_id,
            research_goal_id,
            status_id,
            comment,
            recommendation,
            received_at,
            completed_at
        )
        SELECT
            sp.id,
            rgp.id,
            stp.id,
            'Research comment ' || src.gs::text,
            'Recommendation ' || ((src.gs % 7) + 1)::text,
            CURRENT_TIMESTAMP - ((src.gs % 15) || ' days')::interval,
            CASE
                WHEN src.gs % 3 = 0
                THEN CURRENT_TIMESTAMP - ((src.gs % 5) || ' days')::interval
                ELSE NULL
            END
        FROM src
        JOIN sample_pool sp ON sp.rn = src.sample_rn
        JOIN research_goal_pool rgp ON rgp.rn = src.research_goal_rn
        LEFT JOIN status_pool stp ON stp.rn = src.status_rn;
        """,
        count,
    )


async def insert_tests(conn: asyncpg.Connection, count: int) -> None:
    if count == 0:
        return

    research_total = await table_count(conn, "research")
    if research_total == 0:
        raise RuntimeError("Cannot generate tests: research table is empty.")

    await conn.execute(
        """
        WITH research_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM research
            WHERE deleted_at IS NULL
        ),
        research_meta AS (SELECT COUNT(*)::int AS cnt FROM research_pool),
        indicator_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM indicators
            WHERE deleted_at IS NULL
        ),
        indicator_meta AS (SELECT COUNT(*)::int AS cnt FROM indicator_pool),
        status_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM test_statuses
            WHERE deleted_at IS NULL
        ),
        status_meta AS (SELECT COUNT(*)::int AS cnt FROM status_pool),
        src AS (
            SELECT
                gs,
                ((gs - 1) % GREATEST((SELECT cnt FROM research_meta), 1)) + 1 AS research_rn,
                ((gs - 1) % GREATEST((SELECT cnt FROM indicator_meta), 1)) + 1 AS indicator_rn,
                ((gs - 1) % GREATEST((SELECT cnt FROM status_meta), 1)) + 1 AS status_rn
            FROM generate_series(1, $1::int) AS gs
        )
        INSERT INTO tests (
            value,
            comment,
            norm,
            is_active,
            research_id,
            indicator_id,
            status_id
        )
        SELECT
            ((src.gs % 500)::numeric / 10.0)::text,
            'Test comment ' || src.gs::text,
            '0.0-50.0',
            (src.gs % 20 <> 0),
            rp.id,
            ip.id,
            sp.id
        FROM src
        JOIN research_pool rp ON rp.rn = src.research_rn
        LEFT JOIN indicator_pool ip ON ip.rn = src.indicator_rn
        LEFT JOIN status_pool sp ON sp.rn = src.status_rn;
        """,
        count,
    )


async def insert_conclusions(conn: asyncpg.Connection, count: int) -> None:
    if count == 0:
        return

    await conn.execute(
        """
        WITH src AS (
            SELECT gs
            FROM generate_series(1, $1::int) AS gs
        )
        INSERT INTO conclusions (code, name, text_singular, text_plural, comment)
        SELECT
            'CONCLUSION-' || LPAD(src.gs::text, 6, '0'),
            'Conclusion ' || src.gs::text,
            'Заключение для образца ' || src.gs::text,
            'Заключения для образцов ' || src.gs::text,
            'Conclusion ' || src.gs::text,
        FROM src;
        """,
        count,
    )


async def insert_protocols(conn: asyncpg.Connection, count: int) -> None:
    if count == 0:
        return

    protocol_type_total = await table_count(conn, "protocol_types")
    if protocol_type_total == 0:
        raise RuntimeError("Cannot generate protocols: protocol_types table is empty.")

    await conn.execute(
        """
        WITH protocol_type_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM protocol_types
            WHERE deleted_at IS NULL
        ),
        protocol_type_meta AS (SELECT COUNT(*)::int AS cnt FROM protocol_type_pool),
        conclusion_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM conclusions
            WHERE deleted_at IS NULL
        ),
        conclusion_meta AS (SELECT COUNT(*)::int AS cnt FROM conclusion_pool),
        src AS (
            SELECT
                gs,
                (
                    (gs - 1) % GREATEST((SELECT cnt FROM protocol_type_meta), 1)
                ) + 1 AS protocol_type_rn,
                CASE
                    WHEN (SELECT cnt FROM conclusion_meta) = 0 THEN NULL
                    ELSE ((gs - 1) % (SELECT cnt FROM conclusion_meta)) + 1
                END AS conclusion_rn
            FROM generate_series(1, $1::int) AS gs
        )
        INSERT INTO protocols (
            year_no,
            copies,
            is_signed,
            protocol_copy_name,
            excerpt_copy_name,
            conclusion_id,
            protocol_type_id,
            issued_at
        )
        SELECT
            EXTRACT(YEAR FROM CURRENT_TIMESTAMP)::int,
            ((src.gs - 1) % 3) + 1,
            (src.gs % 2 = 0),
            'protocol-copy-' || LPAD(src.gs::text, 6, '0') || '.pdf',
            'excerpt-copy-' || LPAD(src.gs::text, 6, '0') || '.pdf',
            cp.id,
            ptp.id,
            CURRENT_TIMESTAMP - ((src.gs % 30) || ' days')::interval
        FROM src
        JOIN protocol_type_pool ptp ON ptp.rn = src.protocol_type_rn
        LEFT JOIN conclusion_pool cp ON cp.rn = src.conclusion_rn;
        """,
        count,
    )

    # Link seeded protocols to samples so protocol_id also participates in seeded relations.
    await conn.execute("""
        WITH sample_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM samples
            WHERE deleted_at IS NULL
              AND protocol_id IS NULL
        ),
        protocol_pool AS (
            SELECT id, row_number() OVER (ORDER BY issued_at NULLS LAST, id) AS rn
            FROM protocols
            WHERE deleted_at IS NULL
        ),
        protocol_meta AS (SELECT COUNT(*)::int AS cnt FROM protocol_pool),
        mapping AS (
            SELECT
                sp.id AS sample_id,
                ((sp.rn - 1) % GREATEST((SELECT cnt FROM protocol_meta), 1)) + 1 AS protocol_rn
            FROM sample_pool sp
        )
        UPDATE samples s
        SET
            protocol_id = pp.id,
            updated_at = CURRENT_TIMESTAMP
        FROM mapping mp
        JOIN protocol_pool pp ON pp.rn = mp.protocol_rn
        WHERE s.id = mp.sample_id;
        """)


async def insert_change_log(conn: asyncpg.Connection, count: int) -> None:
    if count == 0:
        return

    sample_total = await table_count(conn, "samples")
    if sample_total == 0:
        raise RuntimeError("Cannot generate change_log: samples table is empty.")

    await conn.execute(
        """
        WITH sample_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM samples
            WHERE deleted_at IS NULL
        ),
        sample_meta AS (SELECT COUNT(*)::int AS cnt FROM sample_pool),
        branch_pool AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM branches
            WHERE deleted_at IS NULL
        ),
        branch_meta AS (SELECT COUNT(*)::int AS cnt FROM branch_pool),
        actor_pool AS (
            SELECT
                id,
                username,
                row_number() OVER (ORDER BY id) AS rn
            FROM users
            WHERE deleted_at IS NULL
        ),
        actor_meta AS (SELECT COUNT(*)::int AS cnt FROM actor_pool),
        src AS (
            SELECT
                gs,
                ((gs - 1) % GREATEST((SELECT cnt FROM sample_meta), 1)) + 1 AS sample_rn,
                CASE
                    WHEN (SELECT cnt FROM branch_meta) = 0 THEN NULL
                    ELSE ((gs - 1) % (SELECT cnt FROM branch_meta)) + 1
                END AS branch_rn,
                CASE
                    WHEN (SELECT cnt FROM actor_meta) = 0 THEN NULL
                    ELSE ((gs - 1) % (SELECT cnt FROM actor_meta)) + 1
                END AS actor_rn
            FROM generate_series(1, $1::int) AS gs
        )
        INSERT INTO change_log (
            branch_id,
            entity_type,
            entity_id,
            action,
            actor_id,
            actor_name,
            snapshot,
            diff,
            created_at
        )
        SELECT
            bp.id,
            'samples',
            sp.id,
            CASE
                WHEN src.gs % 3 = 0 THEN 'update'
                WHEN src.gs % 5 = 0 THEN 'delete'
                ELSE 'create'
            END,
            ap.id,
            COALESCE(ap.username, 'seed-system'),
            jsonb_build_object(
                'source', 'seed_data',
                'entity', 'samples',
                'entity_id', sp.id::text
            ),
            jsonb_build_object(
                'seq', src.gs,
                'note', 'auto generated'
            ),
            CURRENT_TIMESTAMP - ((src.gs % 15) || ' days')::interval
        FROM src
        JOIN sample_pool sp ON sp.rn = src.sample_rn
        LEFT JOIN branch_pool bp ON bp.rn = src.branch_rn
        LEFT JOIN actor_pool ap ON ap.rn = src.actor_rn;
        """,
        count,
    )


async def collect_table_counts(conn: asyncpg.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in SEEDED_TABLES:
        counts[table] = await table_count(conn, table)
    return counts


def assert_non_empty_seeded_tables(counts: dict[str, int]) -> None:
    empty_tables = [table for table, value in counts.items() if value == 0]
    if empty_tables:
        raise RuntimeError(
            "Seed generation finished with empty tables: " + ", ".join(sorted(empty_tables))
        )


async def run_seed(plan: SeedPlan) -> None:
    conn = await asyncpg.connect(plan.database_url)
    try:
        if plan.truncate:
            print("Truncating seeded tables...")
            await truncate_seeded_tables(conn)

        print(f"Seeding reference entities (up to {plan.reference_count} rows each)...")
        await seed_reference_entities(conn, plan.reference_count)

        print(f"Generating directions: {plan.directions}")
        await insert_directions(conn, plan.directions)

        print(f"Generating samples: {plan.samples}")
        await insert_samples(conn, plan.samples)

        print(f"Generating research: {plan.research}")
        await insert_research(conn, plan.research)

        print(f"Generating tests: {plan.tests}")
        await insert_tests(conn, plan.tests)

        conclusions_count = derive_aux_table_count(plan.research, plan.reference_count)
        print(f"Generating conclusions: {conclusions_count}")
        await insert_conclusions(conn, conclusions_count)

        protocols_count = derive_aux_table_count(plan.samples, plan.reference_count)
        print(f"Generating protocols: {protocols_count}")
        await insert_protocols(conn, protocols_count)

        change_log_count = derive_aux_table_count(plan.tests, plan.reference_count)
        print(f"Generating change_log: {change_log_count}")
        await insert_change_log(conn, change_log_count)

        counts = await collect_table_counts(conn)
        assert_non_empty_seeded_tables(counts)

        print("Seed generation completed.")
        print("Counts:", counts)
    finally:
        await conn.close()


def main() -> None:
    args = parse_args()
    plan = build_plan(args)
    asyncio.run(run_seed(plan))


if __name__ == "__main__":
    main()
