from __future__ import annotations

import argparse
import random
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from src.core.config import get_settings

# ---------------------------------------------------------------------------
# Backfills `samples` with historical rows for dashboard/timeline testing.
#
# Every row shares the same sample_type/actor/urgency and is otherwise blank
# (no direction, no comment, ...) — the only fields that vary per row are
# `status_id`, `sampled_at` (collection date) and `received_at` (registration
# date); `is_done` follows from `status_id` since it is not an independent
# axis in the domain. For each calendar day in [--start-date, --end-date] a
# random count of samples (--min-per-day .. --max-per-day) is inserted, with
# status drawn from a distribution that skews "completed" for older days and
# "still in the pipeline" for days near --end-date, so a timeline chart over
# the range looks like a real intake funnel rather than uniform noise.
# ---------------------------------------------------------------------------

DEFAULT_NAME_PREFIX = "History Seed Sample "
DEFAULT_ACTOR_USERNAME = "admin"
DEFAULT_SAMPLE_TYPE_CODE = "ST-WATER-DRINK"
DEFAULT_MIN_PER_DAY = 200
DEFAULT_MAX_PER_DAY = 500
INSERT_CHUNK_SIZE = 5_000

STATUS_CODES: tuple[str, ...] = (
    "pending",
    "registered",
    "in_progress",
    "analyzed",
    "completed",
    "rejected",
)
DONE_STATUS_CODES = frozenset({"completed", "rejected"})

# Status weights at the oldest day of the range vs. the newest day; each
# day's weights are linearly interpolated between the two by its position.
EARLY_STATUS_WEIGHTS: dict[str, float] = {
    "pending": 1,
    "registered": 2,
    "in_progress": 4,
    "analyzed": 8,
    "completed": 80,
    "rejected": 5,
}
LATE_STATUS_WEIGHTS: dict[str, float] = {
    "pending": 20,
    "registered": 20,
    "in_progress": 25,
    "analyzed": 15,
    "completed": 15,
    "rejected": 5,
}


def _day_status_weights(fraction: float) -> list[float]:
    return [
        EARLY_STATUS_WEIGHTS[code]
        + (LATE_STATUS_WEIGHTS[code] - EARLY_STATUS_WEIGHTS[code]) * fraction
        for code in STATUS_CODES
    ]


def _random_time_of_day(day: date, rng: random.Random) -> datetime:
    return datetime(
        day.year,
        day.month,
        day.day,
        hour=rng.randint(7, 19),
        minute=rng.randint(0, 59),
        second=rng.randint(0, 59),
        tzinfo=UTC,
    )


def _iter_days(start_date: date, end_date: date) -> Sequence[date]:
    total_days = (end_date - start_date).days
    return [start_date + timedelta(days=offset) for offset in range(total_days + 1)]


def _generate_rows(
    *,
    start_date: date,
    end_date: date,
    min_per_day: int,
    max_per_day: int,
    name_prefix: str,
    rng: random.Random,
    now: datetime,
) -> list[dict[str, object]]:
    days = _iter_days(start_date, end_date)
    span_days = max((end_date - start_date).days, 1)
    rows: list[dict[str, object]] = []
    running_index = 0

    for day in days:
        fraction = (day - start_date).days / span_days
        weights = _day_status_weights(fraction)
        count = rng.randint(min_per_day, max_per_day)

        for _ in range(count):
            running_index += 1
            status_code = rng.choices(STATUS_CODES, weights=weights, k=1)[0]
            sampled_at = _random_time_of_day(day, rng)
            received_at = min(
                sampled_at + timedelta(hours=rng.uniform(0, 36)),
                now,
            )
            rows.append(
                {
                    "name": f"{name_prefix}{day.isoformat()}-{running_index:06d}",
                    "month_no": day.month,
                    "status_code": status_code,
                    "sampled_at": sampled_at,
                    "received_at": received_at,
                    "is_done": status_code in DONE_STATUS_CODES,
                }
            )

    return rows


async def _resolve_actor_id(connection: AsyncConnection, *, username: str) -> str:
    actor_id = await connection.scalar(
        text("SELECT id FROM users WHERE username = :username LIMIT 1"),
        {"username": username},
    )
    if actor_id is None:
        raise SystemExit(
            f"No user with username={username!r}. Run seed_test_data.py first to bootstrap users."
        )
    return str(actor_id)


async def _resolve_sample_type_id(connection: AsyncConnection, *, code: str) -> str:
    sample_type_id = await connection.scalar(
        text("SELECT id FROM sample_types WHERE code = :code LIMIT 1"),
        {"code": code},
    )
    if sample_type_id is None:
        raise SystemExit(
            f"No sample type with code={code!r}. Run seed_test_data.py first to bootstrap "
            "reference data."
        )
    return str(sample_type_id)


async def _resolve_status_ids(connection: AsyncConnection) -> dict[str, str]:
    result = await connection.execute(
        text("SELECT code, id FROM sample_statuses WHERE code = ANY(:codes)"),
        {"codes": list(STATUS_CODES)},
    )
    status_ids = {code: str(status_id) for code, status_id in result.all()}
    missing = set(STATUS_CODES) - status_ids.keys()
    if missing:
        raise SystemExit(
            f"Missing sample_statuses rows for codes={sorted(missing)}. Run seed_test_data.py "
            "first to bootstrap status tables."
        )
    return status_ids


async def _truncate_generated(connection: AsyncConnection, *, name_prefix: str) -> None:
    await connection.execute(
        text("DELETE FROM samples WHERE name LIKE :pattern"),
        {"pattern": f"{name_prefix}%"},
    )


async def _insert_rows(
    connection: AsyncConnection,
    *,
    rows: list[dict[str, object]],
    status_ids: dict[str, str],
    sample_type_id: str,
    actor_id: str,
) -> None:
    for chunk_start in range(0, len(rows), INSERT_CHUNK_SIZE):
        chunk = rows[chunk_start : chunk_start + INSERT_CHUNK_SIZE]
        await connection.execute(
            text(
                """
                INSERT INTO samples (
                    month_no, name, sample_type_id, status_id,
                    created_by, updated_by, sampled_at, received_at,
                    created_at, updated_at, is_urgent, is_done
                )
                SELECT
                    src.month_no, src.name, :sample_type_id, src.status_id,
                    :actor_id, :actor_id, src.sampled_at, src.received_at,
                    src.received_at, src.received_at, false, src.is_done
                FROM unnest(
                    CAST(:month_no AS int[]),
                    CAST(:name AS text[]),
                    CAST(:status_id AS uuid[]),
                    CAST(:sampled_at AS timestamptz[]),
                    CAST(:received_at AS timestamptz[]),
                    CAST(:is_done AS boolean[])
                ) AS src(month_no, name, status_id, sampled_at, received_at, is_done)
                """
            ),
            {
                "sample_type_id": sample_type_id,
                "actor_id": actor_id,
                "month_no": [row["month_no"] for row in chunk],
                "name": [row["name"] for row in chunk],
                "status_id": [status_ids[str(row["status_code"])] for row in chunk],
                "sampled_at": [row["sampled_at"] for row in chunk],
                "received_at": [row["received_at"] for row in chunk],
                "is_done": [row["is_done"] for row in chunk],
            },
        )


async def seed_sample_history(
    database_url: str | None,
    *,
    start_date: date,
    end_date: date,
    min_per_day: int,
    max_per_day: int,
    name_prefix: str,
    actor_username: str,
    sample_type_code: str,
    truncate_generated: bool,
    seed: int | None,
) -> None:
    if end_date < start_date:
        raise SystemExit("--end-date must not be before --start-date")
    if min_per_day > max_per_day:
        raise SystemExit("--min-per-day must not be greater than --max-per-day")

    rng = random.Random(seed)
    now = datetime.now(UTC)

    engine = create_async_engine(database_url or get_settings().database_url)
    async with engine.begin() as connection:
        actor_id = await _resolve_actor_id(connection, username=actor_username)
        sample_type_id = await _resolve_sample_type_id(connection, code=sample_type_code)
        status_ids = await _resolve_status_ids(connection)

        if truncate_generated:
            await _truncate_generated(connection, name_prefix=name_prefix)

        rows = _generate_rows(
            start_date=start_date,
            end_date=end_date,
            min_per_day=min_per_day,
            max_per_day=max_per_day,
            name_prefix=name_prefix,
            rng=rng,
            now=now,
        )
        await _insert_rows(
            connection,
            rows=rows,
            status_ids=status_ids,
            sample_type_id=sample_type_id,
            actor_id=actor_id,
        )

    await engine.dispose()

    status_counts: dict[str, int] = {code: 0 for code in STATUS_CODES}
    for row in rows:
        status_counts[str(row["status_code"])] += 1

    print(
        f"Seeded {len(rows)} samples across "
        f"{(end_date - start_date).days + 1} days ({start_date} .. {end_date}):"
    )
    for code in STATUS_CODES:
        print(f"  {code}={status_counts[code]}")


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid date {value!r}, expected YYYY-MM-DD") from exc


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be greater than or equal to 1")
    return parsed


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill samples with a per-day random count, varying only status/dates, "
            "for dashboard timeline testing."
        )
    )
    parser.add_argument(
        "--start-date",
        type=_date,
        required=True,
        help="First day to seed (YYYY-MM-DD, in the past).",
    )
    parser.add_argument(
        "--end-date",
        type=_date,
        default=None,
        help="Last day to seed (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--min-per-day",
        type=_positive_int,
        default=DEFAULT_MIN_PER_DAY,
        help=f"Minimum samples per day. Defaults to {DEFAULT_MIN_PER_DAY}.",
    )
    parser.add_argument(
        "--max-per-day",
        type=_positive_int,
        default=DEFAULT_MAX_PER_DAY,
        help=f"Maximum samples per day. Defaults to {DEFAULT_MAX_PER_DAY}.",
    )
    parser.add_argument(
        "--sample-type",
        default=DEFAULT_SAMPLE_TYPE_CODE,
        help=f"sample_types.code shared by every generated row. Defaults to "
        f"{DEFAULT_SAMPLE_TYPE_CODE!r}.",
    )
    parser.add_argument(
        "--actor-username",
        default=DEFAULT_ACTOR_USERNAME,
        help=f"users.username used as created_by/updated_by. Defaults to "
        f"{DEFAULT_ACTOR_USERNAME!r}.",
    )
    parser.add_argument(
        "--name-prefix",
        default=DEFAULT_NAME_PREFIX,
        help="Prefix for generated sample names (also used by --truncate to find them).",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Delete previously generated rows (matching --name-prefix) before seeding.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible output. Omit for non-deterministic data.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="SQLAlchemy async database URL. Defaults to APP_DATABASE_URL from .env.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    import asyncio

    args = _parse_args()
    asyncio.run(
        seed_sample_history(
            args.database_url,
            start_date=args.start_date,
            end_date=args.end_date or date.today(),
            min_per_day=args.min_per_day,
            max_per_day=args.max_per_day,
            name_prefix=args.name_prefix,
            actor_username=args.actor_username,
            sample_type_code=args.sample_type,
            truncate_generated=args.truncate,
            seed=args.seed,
        )
    )
