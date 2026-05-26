from __future__ import annotations

import argparse
import asyncio
from collections.abc import Iterator, Sequence

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

GENERATED_DIRECTION_BASE_NO_START = 1_000_000
GENERATED_SAMPLE_NAME_PREFIX = "Generated Seed Sample "
GENERATED_RESEARCH_COMMENT_PREFIX = "Generated local seed"
DEFAULT_BATCH_SIZE = 10_000


async def seed_test_data(
    database_url: str | None = None,
    *,
    count: int | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    truncate_generated: bool = False,
) -> None:
    engine = create_async_engine(database_url or get_settings().database_url)
    async with engine.begin() as connection:
        await _seed_reference_rows(connection)
        if truncate_generated:
            await _truncate_generated_rows(connection)
        if count is None:
            await _seed_workflow_rows(connection)
        else:
            await _seed_generated_workflow_rows(connection, count=count, batch_size=batch_size)
        summary = await _summary(connection, generated_count=count)
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


def _iter_seed_batches(total_count: int, batch_size: int) -> Iterator[tuple[int, int]]:
    for start_index in range(1, total_count + 1, batch_size):
        yield start_index, min(start_index + batch_size - 1, total_count)


async def _seed_generated_workflow_rows(
    connection: AsyncConnection,
    *,
    count: int,
    batch_size: int,
) -> None:
    for start_index, end_index in _iter_seed_batches(total_count=count, batch_size=batch_size):
        await connection.execute(
            text(
                """
                WITH generated AS (
                    SELECT generated_index
                    FROM generate_series(
                        CAST(:start_index AS integer),
                        CAST(:end_index AS integer)
                    ) AS series(generated_index)
                ),
                actor AS (
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
                direction_status AS (
                    SELECT id FROM direction_statuses WHERE code = 'draft' LIMIT 1
                ),
                sample_type AS (
                    SELECT id FROM sample_types WHERE code = :sample_type_code LIMIT 1
                ),
                sample_status AS (
                    SELECT id FROM sample_statuses WHERE code = 'pending' LIMIT 1
                ),
                goal AS (
                    SELECT id, lab_id
                    FROM research_goals
                    WHERE code = :research_goal_code
                    LIMIT 1
                ),
                research_status AS (
                    SELECT id FROM research_statuses WHERE code = 'draft' LIMIT 1
                ),
                indicator AS (
                    SELECT id FROM indicators WHERE name = :indicator_name LIMIT 1
                ),
                test_status AS (
                    SELECT id FROM test_statuses WHERE code = 'queued' LIMIT 1
                ),
                inserted_directions AS (
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
                        :base_no_start + generated.generated_index,
                        doctor.id,
                        object_row.id,
                        direction_status.id,
                        actor.id,
                        actor.id,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    FROM generated
                    CROSS JOIN actor
                    CROSS JOIN doctor
                    CROSS JOIN object_row
                    CROSS JOIN direction_status
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM directions existing
                        WHERE existing.base_no = :base_no_start + generated.generated_index
                    )
                    RETURNING id, base_no
                ),
                all_directions AS (
                    SELECT id, base_no FROM inserted_directions
                    UNION ALL
                    SELECT directions.id, directions.base_no
                    FROM directions
                    JOIN generated
                        ON directions.base_no = :base_no_start + generated.generated_index
                ),
                inserted_samples AS (
                    INSERT INTO samples (
                        month_no,
                        name,
                        direction_id,
                        sample_type_id,
                        status_id,
                        created_by,
                        updated_by,
                        sampled_at,
                        received_at
                    )
                    SELECT
                        EXTRACT(MONTH FROM CURRENT_DATE)::int,
                        :sample_name_prefix
                            || lpad(
                                (all_directions.base_no - :base_no_start)::text,
                                7,
                                '0'
                            ),
                        all_directions.id,
                        sample_type.id,
                        sample_status.id,
                        actor.id,
                        actor.id,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    FROM all_directions
                    CROSS JOIN sample_type
                    CROSS JOIN sample_status
                    CROSS JOIN actor
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM samples existing
                        WHERE existing.name = :sample_name_prefix
                            || lpad(
                                (all_directions.base_no - :base_no_start)::text,
                                7,
                                '0'
                            )
                    )
                    RETURNING id, name, direction_id
                ),
                all_samples AS (
                    SELECT id, name, direction_id FROM inserted_samples
                    UNION ALL
                    SELECT samples.id, samples.name, samples.direction_id
                    FROM samples
                    JOIN all_directions ON all_directions.id = samples.direction_id
                    WHERE samples.name = :sample_name_prefix
                        || lpad(
                            (all_directions.base_no - :base_no_start)::text,
                            7,
                            '0'
                        )
                ),
                inserted_research AS (
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
                        all_samples.id,
                        goal.id,
                        goal.lab_id,
                        research_status.id,
                        actor.id,
                        actor.id,
                        :research_comment_prefix || ' ' || right(all_samples.name, 7)
                    FROM all_samples
                    CROSS JOIN goal
                    CROSS JOIN research_status
                    CROSS JOIN actor
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM research existing
                        WHERE existing.sample_id = all_samples.id
                          AND existing.research_goal_id = goal.id
                    )
                    RETURNING id, sample_id
                ),
                all_research AS (
                    SELECT id, sample_id FROM inserted_research
                    UNION ALL
                    SELECT research.id, research.sample_id
                    FROM research
                    JOIN all_samples ON all_samples.id = research.sample_id
                    CROSS JOIN goal
                    WHERE research.research_goal_id = goal.id
                ),
                inserted_tests AS (
                    INSERT INTO tests (
                        research_id,
                        indicator_id,
                        status_id,
                        created_by,
                        updated_by
                    )
                    SELECT
                        all_research.id,
                        indicator.id,
                        test_status.id,
                        actor.id,
                        actor.id
                    FROM all_research
                    CROSS JOIN indicator
                    CROSS JOIN test_status
                    CROSS JOIN actor
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM tests existing
                        WHERE existing.research_id = all_research.id
                          AND existing.indicator_id = indicator.id
                    )
                    RETURNING id
                )
                SELECT
                    (SELECT count(*) FROM inserted_directions) AS inserted_directions,
                    (SELECT count(*) FROM inserted_samples) AS inserted_samples,
                    (SELECT count(*) FROM inserted_research) AS inserted_research,
                    (SELECT count(*) FROM inserted_tests) AS inserted_tests
                """
            ),
            {
                "start_index": start_index,
                "end_index": end_index,
                "base_no_start": GENERATED_DIRECTION_BASE_NO_START,
                "object_code": TEST_CODES["object"],
                "sample_type_code": TEST_CODES["sample_type"],
                "research_goal_code": TEST_CODES["research_goal"],
                "indicator_name": TEST_CODES["indicator"],
                "sample_name_prefix": GENERATED_SAMPLE_NAME_PREFIX,
                "research_comment_prefix": GENERATED_RESEARCH_COMMENT_PREFIX,
            },
        )


async def _truncate_generated_rows(connection: AsyncConnection) -> None:
    await connection.execute(
        text(
            """
            DELETE FROM tests
            USING research, samples
            WHERE tests.research_id = research.id
              AND research.sample_id = samples.id
              AND samples.name LIKE :sample_name_pattern
            """
        ),
        {"sample_name_pattern": f"{GENERATED_SAMPLE_NAME_PREFIX}%"},
    )
    await connection.execute(
        text(
            """
            DELETE FROM research
            USING samples
            WHERE research.sample_id = samples.id
              AND samples.name LIKE :sample_name_pattern
            """
        ),
        {"sample_name_pattern": f"{GENERATED_SAMPLE_NAME_PREFIX}%"},
    )
    await connection.execute(
        text(
            """
            DELETE FROM samples
            WHERE name LIKE :sample_name_pattern
            """
        ),
        {"sample_name_pattern": f"{GENERATED_SAMPLE_NAME_PREFIX}%"},
    )
    await connection.execute(
        text(
            """
            WITH doctor AS (
                SELECT id FROM doctors
                WHERE first_name = 'Test' AND last_name = 'Doctor'
                LIMIT 1
            ),
            object_row AS (
                SELECT id FROM objects WHERE code = :object_code LIMIT 1
            )
            DELETE FROM directions
            USING doctor, object_row
            WHERE directions.base_no > :base_no_start
              AND directions.doctor_id = doctor.id
              AND directions.object_id = object_row.id
            """
        ),
        {
            "base_no_start": GENERATED_DIRECTION_BASE_NO_START,
            "object_code": TEST_CODES["object"],
        },
    )


async def _summary(
    connection: AsyncConnection,
    *,
    generated_count: int | None,
) -> Sequence[str]:
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
    summary = [str(row[0]) for row in result.all()]
    if generated_count is not None:
        generated_result = await connection.execute(
            text(
                """
                SELECT 'generated_research_count=' || count(*)::text
                FROM research
                JOIN samples ON samples.id = research.sample_id
                WHERE samples.name LIKE :sample_name_pattern
                """
            ),
            {"sample_name_pattern": f"{GENERATED_SAMPLE_NAME_PREFIX}%"},
        )
        summary.extend(str(row[0]) for row in generated_result.all())
        summary.append(f"generated_research_target={generated_count}")
    return summary


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be greater than or equal to 1")
    return parsed


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed local test data after Alembic migrations.")
    parser.add_argument(
        "--database-url",
        default=None,
        help="SQLAlchemy async database URL. Defaults to APP_DATABASE_URL from .env.",
    )
    parser.add_argument(
        "--count",
        type=_positive_int,
        default=None,
        help=(
            "Create this many generated research rows with related directions, samples, "
            "and tests. If omitted, creates the original single local workflow row."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=_positive_int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Generated row batch size. Defaults to {DEFAULT_BATCH_SIZE}.",
    )
    parser.add_argument(
        "--truncate-generated",
        action="store_true",
        help="Delete previously generated bulk workflow rows before seeding.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(
        seed_test_data(
            args.database_url,
            count=args.count,
            batch_size=args.batch_size,
            truncate_generated=args.truncate_generated,
        )
    )
