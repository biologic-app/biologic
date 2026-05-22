from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from src.core.config import get_settings

TEST_CODES = {
    "branch": "BR-TEST-001",
    "lab": "LAB-TEST-001",
    "object": "OBJ-TEST-001",
    "sample_type": "SAMPLE-TYPE-TEST-001",
    "research_goal": "RG-TEST-001",
    "indicator": "Indicator Test Seed 001",
    "direction_base_no": 900001,
    "sample": "Test Seed Sample 001",
}


async def seed_test_data(database_url: str | None = None) -> None:
    engine = create_async_engine(database_url or get_settings().database_url)
    async with engine.begin() as connection:
        await _seed_reference_rows(connection)
        await _seed_workflow_rows(connection)
        summary = await _summary(connection)
    await engine.dispose()

    print("Seeded local test data:")
    for line in summary:
        print(f"  {line}")


async def _seed_reference_rows(connection: AsyncConnection) -> None:
    await connection.execute(
        text(
            """
            INSERT INTO branches (code, name)
            SELECT :code, 'Test Branch'
            WHERE NOT EXISTS (SELECT 1 FROM branches WHERE code = :code)
            """
        ),
        {"code": TEST_CODES["branch"]},
    )
    await connection.execute(
        text(
            """
            INSERT INTO labs (code, name, full_name, branch_id)
            SELECT :code, 'Test Lab', 'Test Laboratory', b.id
            FROM branches b
            WHERE b.code = :branch_code
            ON CONFLICT (code) DO NOTHING
            """
        ),
        {"code": TEST_CODES["lab"], "branch_code": TEST_CODES["branch"]},
    )
    await connection.execute(
        text(
            """
            INSERT INTO objects (code, name, full_name, address, branch_id)
            SELECT :code, 'Test Object', 'Test Object Full', 'Test Address', b.id
            FROM branches b
            WHERE b.code = :branch_code
            ON CONFLICT (code) DO NOTHING
            """
        ),
        {"code": TEST_CODES["object"], "branch_code": TEST_CODES["branch"]},
    )
    await connection.execute(
        text(
            """
            INSERT INTO doctors (first_name, last_name, patronymic)
            SELECT 'Test', 'Doctor', 'Seed'
            WHERE NOT EXISTS (
                SELECT 1 FROM doctors
                WHERE first_name = 'Test'
                  AND last_name = 'Doctor'
                  AND patronymic = 'Seed'
            )
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO sample_types (code, name)
            VALUES (:code, 'Test Sample Type')
            ON CONFLICT (code) DO NOTHING
            """
        ),
        {"code": TEST_CODES["sample_type"]},
    )
    await connection.execute(
        text(
            """
            INSERT INTO research_goals (code, name, comment, lab_id)
            SELECT :code, 'Test Research Goal', 'Local test seed', l.id
            FROM labs l
            WHERE l.code = :lab_code
            ON CONFLICT (code) DO NOTHING
            """
        ),
        {"code": TEST_CODES["research_goal"], "lab_code": TEST_CODES["lab"]},
    )
    await connection.execute(
        text(
            """
            INSERT INTO indicators (name, unit, norm_text, research_goal_id, sample_type_id)
            SELECT :name, 'mg/L', '0-10', rg.id, st.id
            FROM research_goals rg
            CROSS JOIN sample_types st
            WHERE rg.code = :research_goal_code
              AND st.code = :sample_type_code
              AND NOT EXISTS (SELECT 1 FROM indicators WHERE name = :name)
            """
        ),
        {
            "name": TEST_CODES["indicator"],
            "research_goal_code": TEST_CODES["research_goal"],
            "sample_type_code": TEST_CODES["sample_type"],
        },
    )


async def _seed_workflow_rows(connection: AsyncConnection) -> None:
    await connection.execute(
        text(
            """
            WITH actor AS (
                SELECT id FROM users WHERE username = 'admin' LIMIT 1
            ),
            doctor AS (
                SELECT id FROM doctors
                WHERE first_name = 'Test' AND last_name = 'Doctor'
                LIMIT 1
            ),
            object_row AS (
                SELECT id FROM objects WHERE code = :object_code LIMIT 1
            ),
            status_row AS (
                SELECT id FROM direction_statuses WHERE code = 'draft' LIMIT 1
            )
            INSERT INTO directions (
                year_no,
                base_no,
                doctor_id,
                object_id,
                status_id,
                created_by,
                updated_by,
                sampled_at,
                received_at
            )
            SELECT
                EXTRACT(YEAR FROM CURRENT_DATE)::int,
                :base_no,
                doctor.id,
                object_row.id,
                status_row.id,
                actor.id,
                actor.id,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            FROM actor, doctor, object_row, status_row
            WHERE NOT EXISTS (
                SELECT 1 FROM directions WHERE base_no = :base_no
            )
            """
        ),
        {
            "object_code": TEST_CODES["object"],
            "base_no": TEST_CODES["direction_base_no"],
        },
    )
    await connection.execute(
        text(
            """
            WITH direction_row AS (
                SELECT id FROM directions WHERE base_no = :base_no LIMIT 1
            ),
            sample_type AS (
                SELECT id FROM sample_types WHERE code = :sample_type_code LIMIT 1
            ),
            status_row AS (
                SELECT id FROM sample_statuses WHERE code = 'pending' LIMIT 1
            ),
            actor AS (
                SELECT id FROM users WHERE username = 'admin' LIMIT 1
            )
            INSERT INTO samples (
                name,
                direction_id,
                sample_type_id,
                status_id,
                created_by,
                updated_by,
                sampled_at
            )
            SELECT
                :sample_name,
                direction_row.id,
                sample_type.id,
                status_row.id,
                actor.id,
                actor.id,
                CURRENT_TIMESTAMP
            FROM direction_row, sample_type, status_row, actor
            WHERE NOT EXISTS (SELECT 1 FROM samples WHERE name = :sample_name)
            """
        ),
        {
            "base_no": TEST_CODES["direction_base_no"],
            "sample_type_code": TEST_CODES["sample_type"],
            "sample_name": TEST_CODES["sample"],
        },
    )
    await connection.execute(
        text(
            """
            WITH sample_row AS (
                SELECT id FROM samples WHERE name = :sample_name LIMIT 1
            ),
            goal AS (
                SELECT id, lab_id FROM research_goals WHERE code = :research_goal_code LIMIT 1
            ),
            status_row AS (
                SELECT id FROM research_statuses WHERE code = 'draft' LIMIT 1
            ),
            actor AS (
                SELECT id FROM users WHERE username = 'admin' LIMIT 1
            )
            INSERT INTO research (
                sample_id,
                research_goal_id,
                lab_id,
                status_id,
                created_by,
                updated_by,
                comment
            )
            SELECT
                sample_row.id,
                goal.id,
                goal.lab_id,
                status_row.id,
                actor.id,
                actor.id,
                'Local test seed'
            FROM sample_row, goal, status_row, actor
            WHERE NOT EXISTS (
                SELECT 1
                FROM research r
                WHERE r.sample_id = sample_row.id
                  AND r.research_goal_id = goal.id
            )
            """
        ),
        {
            "sample_name": TEST_CODES["sample"],
            "research_goal_code": TEST_CODES["research_goal"],
        },
    )
    await connection.execute(
        text(
            """
            WITH research_row AS (
                SELECT r.id
                FROM research r
                JOIN samples s ON s.id = r.sample_id
                WHERE s.name = :sample_name
                LIMIT 1
            ),
            indicator AS (
                SELECT id FROM indicators WHERE name = :indicator_name LIMIT 1
            ),
            status_row AS (
                SELECT id FROM test_statuses WHERE code = 'queued' LIMIT 1
            ),
            actor AS (
                SELECT id FROM users WHERE username = 'admin' LIMIT 1
            )
            INSERT INTO tests (research_id, indicator_id, status_id, created_by, updated_by)
            SELECT research_row.id, indicator.id, status_row.id, actor.id, actor.id
            FROM research_row, indicator, status_row, actor
            WHERE NOT EXISTS (
                SELECT 1
                FROM tests t
                WHERE t.research_id = research_row.id
                  AND t.indicator_id = indicator.id
            )
            """
        ),
        {
            "sample_name": TEST_CODES["sample"],
            "indicator_name": TEST_CODES["indicator"],
        },
    )


async def _summary(connection: AsyncConnection) -> Sequence[str]:
    result = await connection.execute(
        text(
            """
            SELECT 'direction_id=' || d.id::text
            FROM directions d
            WHERE d.base_no = :base_no
            UNION ALL
            SELECT 'sample_id=' || s.id::text
            FROM samples s
            WHERE s.name = :sample_name
            UNION ALL
            SELECT 'admin_user=' || u.username
            FROM users u
            WHERE u.username = 'admin'
            """
        ),
        {
            "base_no": TEST_CODES["direction_base_no"],
            "sample_name": TEST_CODES["sample"],
        },
    )
    return [str(row[0]) for row in result.all()]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed local test data after Alembic migrations.")
    parser.add_argument(
        "--database-url",
        default=None,
        help="SQLAlchemy async database URL. Defaults to APP_DATABASE_URL from .env.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(seed_test_data(args.database_url))
