from __future__ import annotations

import argparse
import asyncio
from collections.abc import Iterator, Sequence
from typing import Any

from sqlalchemy import BindParameter, bindparam, text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from src.core.config import get_settings

# ---------------------------------------------------------------------------
# Realistic dev reference dataset.
#
# This script is the sole seed source for local/dev/test databases — including
# a brand-new one. All data-seeding migrations were reduced to pure schema
# (0002, 0009, 0016, 0022, 0024): a fresh ``alembic upgrade head`` produces
# empty tables only, and this script is what makes the app usable (roles,
# permissions, status tables, named accounts, branches, protocol types,
# conclusions, mandatory subscription rules, then the realistic reference/
# workflow rows below). Run it once after every ``alembic upgrade head``.
#
# It wipes all operational data plus the previously-synthetic reference rows
# (what used to be ~100-of-everything placeholders from migration 0002, and
# the placeholder lab goals from 0022) and inserts a small realistic set
# instead (5 labs, 9 sample types, 5 doctors, 6 objects, 18 research goals,
# ~90 indicators). Auth (users/roles/permissions), user_scopes, status
# tables, branches and protocol_types are bootstrapped once by
# ``_seed_bootstrap_data`` and otherwise preserved/upserted by code, not reset
# per run.
#
# The 5 real laboratories are kept by ``code`` (BAK/TH/TB/RV/PCR). Users that
# pointed at a synthetic lab have ``users.lab_id`` reset to NULL before the
# synthetic labs are deleted (the FK is ON DELETE NO ACTION), so no user is
# ever cascade-deleted and no FK is violated. ``labs.branch_id`` is left as-is
# for the real labs; branches are never deleted.
# ---------------------------------------------------------------------------

# --- RBAC / cross-environment bootstrap data (moved from migrations 0002, ---
# --- 0009, 0016, 0022, 0024 — see _seed_bootstrap_data). ---------------------

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

# 8 named accounts used for local dev / manual QA / e2e login flows.
# Password hashes are bcrypt of "<username>123" (e.g. "admin123").
SEED_USERS: tuple[dict[str, object], ...] = (
    {
        "username": "admin",
        "password_hash": "$2b$12$31.eOAY8FTBiLBeFDln1aukR6ulC9N3QPHpSaHb4K03w8oSirMMXO",
        "role_key": "admin",
        "code": "ADM-001",
        "first_name": "Даниил",
        "last_name": "Третьяков",
    },
    {
        "username": "registrator",
        "password_hash": "$2b$12$2P2Th3MrtGkwfPY8RlpASeU4BrFDKLuTuaTYL1iJJ5k.UgceEmoDG",
        "role_key": "registrar",
        "code": "REG-001",
        "first_name": "Владимир",
        "last_name": "Алексиков",
    },
    {
        "username": "sandoctor",
        "password_hash": "$2b$12$hnKaA3krUf/OcLNbT2h0cODuytiz5ZBoFO59KPGoNwUxQaYBH5sgq",
        "role_key": "sanitary_inspector",
        "code": "SAN-001",
        "first_name": "Владислав",
        "last_name": "Морозов",
    },
    {
        "username": "doctor",
        "password_hash": "$2b$12$HEI0Om0Yj3dN23iuNOQv5.o7LxfO3lvH/8UZDYY1QMq13w6XlAYKS",
        "role_key": "lab_doctor",
        "code": "DOC-001",
        "first_name": "Алексей",
        "last_name": "Афанасьев",
    },
    {
        "username": "laborant",
        "password_hash": "$2b$12$8KWv04UbCAHys4zsydg7o.P4PovTzkemvne.9FOPzilpzR8k20Drq",
        "role_key": "lab_assistant",
        "code": "LAB-001",
        "first_name": "Тыла",
        "last_name": "Труженник",
    },
    {
        "username": "nachlab",
        "password_hash": "$2b$12$xSeCXbFqxLyz5Bz8oDmBEud3N9zVxV5u470fjvMS2sjlTnSxR1Dg2",
        "role_key": "lab_chief",
        "code": "LCH-001",
        "first_name": "Станислав",
        "last_name": "Прокофьев",
    },
    {
        "username": "nachfil",
        "password_hash": "$2b$12$Z/cYiesQmpPPbH6Sfov0Xe.Rd0167R.p2B.lz757Sq6hmi1hnlKfO",
        "role_key": "branch_chief",
        "code": "BCH-001",
        "first_name": "Олег",
        "last_name": "Иванов",
    },
    {
        "username": "tminww",
        "password_hash": "$2b$12$YCNo9bFWrwCFeHXVf69nsOEQVB5yxtP2LMT6Rbenuw0kFOsI4GgaW",
        "role_key": "developer",
        "code": "DEV-001",
        "first_name": "Серафим",
        "last_name": "Олейник",
    },
)

# Status seed rows: (code, color). The stable `code` is the sole status
# identity; the frontend translates labels via i18n. Colors are design-system-
# neutral names (see src.core.status_colors); the frontend owns the color
# vocabulary and maps each name onto its design system.
DIRECTION_STATUSES: tuple[tuple[str, str], ...] = (
    ("draft", "gray"),
    ("registered", "indigo"),
    ("in_progress", "blue"),
    ("partially_completed", "lime"),
    ("completed", "green"),
)

SAMPLE_STATUSES: tuple[tuple[str, str], ...] = (
    ("pending", "amber"),
    ("registered", "indigo"),
    ("rejected", "red"),
    ("in_progress", "blue"),
    ("analyzed", "violet"),
    ("completed", "green"),
)

RESEARCH_STATUSES: tuple[tuple[str, str], ...] = (
    ("in_progress", "blue"),
    ("completed", "green"),
    ("rejected", "red"),
)

TEST_STATUSES: tuple[tuple[str, str], ...] = (
    ("in_progress", "blue"),
    ("completed", "green"),
    ("rejected", "red"),
)

# Realistic branches/protocol types. Previously ~100 synthetic placeholder
# rows each (migration 0002); a small realistic set is enough for dev.
BRANCHES: tuple[tuple[str, str], ...] = (
    ("BR-CENTRAL", "Центральный филиал"),
    ("BR-NORTH", "Северный филиал"),
)

PROTOCOL_TYPES: tuple[tuple[str, str], ...] = (
    ("PROTO-LAB", "Протокол лабораторных испытаний"),
    ("PROTO-SANITARY", "Протокол санитарно-эпидемиологической экспертизы"),
    ("PROTO-RADIATION", "Протокол радиационного контроля"),
)

# 5 typical conclusions: (code, name, text_singular, text_plural, comment).
CONCLUSIONS: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "CONFORMS",
        "Соответствует требованиям",
        "Проба соответствует требованиям нормативной документации.",
        "Пробы соответствуют требованиям нормативной документации.",
        "Типовое заключение: показатели в пределах нормы.",
    ),
    (
        "NOT_CONFORMS",
        "Не соответствует требованиям",
        "Проба не соответствует требованиям нормативной документации.",
        "Пробы не соответствуют требованиям нормативной документации.",
        "Типовое заключение: обнаружено несоответствие нормативным требованиям.",
    ),
    (
        "CONFORMS_WITH_REMARKS",
        "Соответствует с замечаниями",
        "Проба соответствует требованиям нормативной документации с замечаниями.",
        "Пробы соответствуют требованиям нормативной документации с замечаниями.",
        "Типовое заключение: соответствие подтверждено, есть замечания по "
        "оформлению или маркировке.",
    ),
    (
        "RETEST_REQUIRED",
        "Требуется повторное исследование",
        "По пробе требуется повторное лабораторное исследование.",
        "По пробам требуется повторное лабораторное исследование.",
        "Типовое заключение: результат неоднозначен, назначается повтор.",
    ),
    (
        "EXCEEDS_LIMITS",
        "Превышение допустимых норм",
        "В пробе обнаружено превышение допустимых норм по одному или нескольким показателям.",
        "В пробах обнаружено превышение допустимых норм по одному или нескольким показателям.",
        "Типовое заключение: зафиксировано превышение ПДК/норматива.",
    ),
)

# Mandatory role-based subscription rules: (role_key, entity_type), global/unscoped.
ROLE_SUBSCRIPTION_RULES: tuple[tuple[str, str], ...] = (
    ("registrar", "directions"),
    ("registrar", "samples"),
)

# The 5 real laboratories, kept by code. names/full_name upserted for idempotency.
REAL_LABS: tuple[tuple[str, str, str], ...] = (
    ("BAK", "Бактериологическая", "Бактериологическая лаборатория"),
    ("TH", "Химическая", "Химическая лаборатория"),
    ("TB", "Токсико-биологическая", "Токсико-биологическая лаборатория"),
    ("RV", "Радиационная", "Радиационная лаборатория"),
    ("PCR", "ПЦР", "Лаборатория ПЦР-диагностики"),
)

# 9 sample types (code, name).
SAMPLE_TYPES: tuple[tuple[str, str], ...] = (
    ("ST-WATER-DRINK", "Вода питьевая"),
    ("ST-WATER-WASTE", "Вода сточная"),
    ("ST-MILK", "Молоко и молочная продукция"),
    ("ST-MEAT", "Мясо и мясопродукты"),
    ("ST-FISH", "Рыба и рыбопродукты"),
    ("ST-VEG", "Овощи и фрукты"),
    ("ST-SOIL", "Почва"),
    ("ST-SWAB", "Смывы с поверхностей"),
    ("ST-AIR", "Воздух"),
)

# 5 sanitary doctors (last_name, first_name, patronymic).
DOCTORS: tuple[tuple[str, str, str], ...] = (
    ("Иванов", "Иван", "Иванович"),
    ("Петрова", "Анна", "Сергеевна"),
    ("Сидоров", "Владимир", "Петрович"),
    ("Кузнецова", "Елена", "Александровна"),
    ("Смирнов", "Дмитрий", "Николаевич"),
)

# 6 objects (code, name, address).
OBJECTS: tuple[tuple[str, str, str], ...] = (
    ("OBJ-MOLKOM", "ООО Молочный комбинат", "ул. Заводская, 1"),
    ("OBJ-MYASO", "АО Мясокомбинат Восток", "ул. Промышленная, 12"),
    ("OBJ-SCHOOL5", "Школа №5 (пищеблок)", "ул. Школьная, 5"),
    ("OBJ-REST", "Ресторан Нептун", "пр. Морской, 30"),
    ("OBJ-VODOKANAL", "МУП Водоканал", "ул. Насосная, 7"),
    ("OBJ-RYNOK", "Рынок Центральный", "пл. Торговая, 2"),
)

# 18 research goals (lab_code, goal_code, goal_name).
RESEARCH_GOALS: tuple[tuple[str, str, str], ...] = (
    ("BAK", "RG-BAK-KMAFANM", "КМАФАнМ (ОМЧ)"),
    ("BAK", "RG-BAK-BGKP", "БГКП (колиформы)"),
    ("BAK", "RG-BAK-PATOGEN", "Патогенные, в т.ч. сальмонеллы"),
    ("BAK", "RG-BAK-LISTERIA", "Listeria monocytogenes"),
    ("BAK", "RG-BAK-SAUREUS", "S. aureus"),
    ("TH", "RG-TH-METALS", "Тяжёлые металлы (Pb, Cd, Hg, As)"),
    ("TH", "RG-TH-NITRAT", "Нитраты"),
    ("TH", "RG-TH-NITRIT", "Нитриты"),
    ("TH", "RG-TH-PEST", "Пестициды (ГХЦГ, ДДТ)"),
    ("TB", "RG-TB-MICOTOX", "Микотоксины (афлатоксин B1)"),
    ("TB", "RG-TB-ANTIBIO", "Антибиотики"),
    ("TB", "RG-TB-HISTAMIN", "Гистамин"),
    ("RV", "RG-RV-CS137", "Цезий-137"),
    ("RV", "RG-RV-SR90", "Стронций-90"),
    ("RV", "RG-RV-ACTIVITY", "Удельная эффективная активность"),
    ("PCR", "RG-PCR-SALM", "ДНК Salmonella"),
    ("PCR", "RG-PCR-LIST", "ДНК Listeria monocytogenes"),
    ("PCR", "RG-PCR-GMO", "ГМО"),
)

# Indicators: goal_code -> list of sample_type codes. The (goal, sample type)
# pair is what makes the "(sample type + lab) -> goals" derivation non-empty.
_FOOD = ("ST-MILK", "ST-MEAT", "ST-FISH", "ST-VEG")
_ALL_FOOD_WATER_SOIL = (
    "ST-MILK",
    "ST-MEAT",
    "ST-FISH",
    "ST-VEG",
    "ST-WATER-DRINK",
    "ST-WATER-WASTE",
    "ST-SOIL",
)
GOAL_SAMPLE_TYPES: dict[str, tuple[str, ...]] = {
    # BAK -> milk, meat, fish, drinking water, swabs, veg
    "RG-BAK-KMAFANM": ("ST-MILK", "ST-MEAT", "ST-FISH", "ST-WATER-DRINK", "ST-SWAB", "ST-VEG"),
    "RG-BAK-BGKP": ("ST-MILK", "ST-MEAT", "ST-FISH", "ST-WATER-DRINK", "ST-SWAB", "ST-VEG"),
    "RG-BAK-PATOGEN": ("ST-MILK", "ST-MEAT", "ST-FISH", "ST-WATER-DRINK", "ST-SWAB", "ST-VEG"),
    "RG-BAK-LISTERIA": ("ST-MILK", "ST-MEAT", "ST-FISH", "ST-WATER-DRINK", "ST-SWAB", "ST-VEG"),
    "RG-BAK-SAUREUS": ("ST-MILK", "ST-MEAT", "ST-FISH", "ST-WATER-DRINK", "ST-SWAB", "ST-VEG"),
    # TH (metals/nitrates/nitrites/pesticides) -> all food + water + soil
    "RG-TH-METALS": _ALL_FOOD_WATER_SOIL,
    "RG-TH-NITRAT": _ALL_FOOD_WATER_SOIL,
    "RG-TH-NITRIT": _ALL_FOOD_WATER_SOIL,
    "RG-TH-PEST": _ALL_FOOD_WATER_SOIL,
    # TB
    "RG-TB-MICOTOX": ("ST-MILK", "ST-MEAT", "ST-VEG"),
    "RG-TB-ANTIBIO": ("ST-MILK", "ST-MEAT", "ST-FISH"),
    "RG-TB-HISTAMIN": ("ST-FISH",),
    # RV -> all food + water + soil
    "RG-RV-CS137": _ALL_FOOD_WATER_SOIL,
    "RG-RV-SR90": _ALL_FOOD_WATER_SOIL,
    "RG-RV-ACTIVITY": _ALL_FOOD_WATER_SOIL,
    # PCR
    "RG-PCR-SALM": ("ST-MEAT", "ST-MILK", "ST-FISH"),
    "RG-PCR-LIST": ("ST-MEAT", "ST-MILK", "ST-FISH"),
    "RG-PCR-GMO": ("ST-VEG", "ST-MEAT"),
}

_ = _FOOD  # documented food shorthand; kept for readability of the mapping above

# Single realistic workflow row (used by the default, non-bulk seed path) plus
# codes reused by the bulk (--count) generator. All point at real reference data.
TEST_CODES: dict[str, object] = {
    "object": "OBJ-MOLKOM",
    "sample_type": "ST-MILK",
    "research_goal": "RG-BAK-KMAFANM",
    "indicator": "RG-BAK-KMAFANM / ST-MILK",
    "direction_base_no": 900001,
    "sample": "Образец мясной продукции 900001",
}

# Doctor used as sampling doctor for generated/single directions.
WORKFLOW_DOCTOR_LAST = "Иванов"
# Sample type / labs / goal / indicator for the single realistic workflow row.
WORKFLOW_OBJECT = "OBJ-MYASO"
WORKFLOW_SAMPLE_TYPE = "ST-MEAT"
WORKFLOW_SAMPLE_LABS = ("BAK", "TB")
WORKFLOW_GOAL = "RG-BAK-PATOGEN"
WORKFLOW_INDICATOR = "RG-BAK-PATOGEN / ST-MEAT"

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
        await _seed_bootstrap_data(connection)
        await _reset_operational_data(connection)
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


async def _seed_bootstrap_data(connection: AsyncConnection) -> None:
    """RBAC + cross-environment reference data, idempotent (safe to re-run).

    Roles, status tables, branches and protocol types must exist before
    anything below reads them (users need role_id, directions need
    status_id, objects need a branch to fall back to, ...), so this runs
    first, before the operational-data reset.
    """
    for role_key, payload in ROLE_DEFINITIONS.items():
        await connection.execute(
            text(
                """
                INSERT INTO roles (key, name, scope_type)
                VALUES (:key, :name, CAST(:scope_type AS role_scope_type))
                ON CONFLICT (key) DO UPDATE
                SET name = EXCLUDED.name,
                    scope_type = EXCLUDED.scope_type,
                    updated_at = CURRENT_TIMESTAMP
                """
            ),
            {"key": role_key, "name": payload["name"], "scope_type": payload["scope_type"]},
        )

    for table, status_rows in (
        ("direction_statuses", DIRECTION_STATUSES),
        ("sample_statuses", SAMPLE_STATUSES),
        ("research_statuses", RESEARCH_STATUSES),
        ("test_statuses", TEST_STATUSES),
    ):
        await connection.execute(
            text(
                f"""
                INSERT INTO {table} (code, color)
                SELECT * FROM unnest(
                    CAST(:code AS text[]), CAST(:color AS text[])
                )
                ON CONFLICT (code) DO UPDATE
                SET color = EXCLUDED.color
                """  # noqa: S608 (table is one of 4 fixed literals above, not user input)
            ),
            {
                "code": [code for code, _ in status_rows],
                "color": [color for _, color in status_rows],
            },
        )

    await connection.execute(
        text(
            """
            INSERT INTO protocol_types (code, name)
            SELECT * FROM unnest(CAST(:code AS text[]), CAST(:name AS text[]))
            ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
            """
        ),
        {
            "code": [code for code, _ in PROTOCOL_TYPES],
            "name": [name for _, name in PROTOCOL_TYPES],
        },
    )

    # branches.code has no unique/exclusion constraint (unlike the tables
    # above), so ON CONFLICT cannot target it — guard with NOT EXISTS instead.
    await connection.execute(
        text(
            """
            INSERT INTO branches (code, name)
            SELECT src.code, src.name
            FROM unnest(CAST(:code AS text[]), CAST(:name AS text[])) AS src(code, name)
            WHERE NOT EXISTS (SELECT 1 FROM branches b WHERE b.code = src.code)
            """
        ),
        {"code": [code for code, _ in BRANCHES], "name": [name for _, name in BRANCHES]},
    )

    await connection.execute(
        text(
            """
            INSERT INTO permissions (resource, action)
            SELECT * FROM unnest(CAST(:resource AS text[]), CAST(:action AS text[]))
            ON CONFLICT (resource, action) DO NOTHING
            """
        ),
        {
            "resource": [resource for resource, _ in PERMISSION_CATALOG],
            "action": [action for _, action in PERMISSION_CATALOG],
        },
    )

    # Full replace per role: delete then reinsert, so a matrix edit here is
    # reflected exactly (not just additively merged) on the next run.
    await connection.execute(
        text(
            """
            DELETE FROM role_permissions
            WHERE role_id IN (
                SELECT id FROM roles WHERE key = ANY(CAST(:role_keys AS text[]))
            )
            """
        ),
        {"role_keys": list(ROLE_DEFINITIONS.keys())},
    )
    for role_key, pairs in ROLE_PERMISSION_MATRIX.items():
        await connection.execute(
            text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, p.id
                FROM unnest(
                    CAST(:resource AS text[]), CAST(:action AS text[])
                ) AS m(resource, action)
                JOIN permissions p ON p.resource = m.resource AND p.action = m.action
                CROSS JOIN (SELECT id FROM roles WHERE key = :role_key) r
                ON CONFLICT (role_id, permission_id) DO NOTHING
                """
            ),
            {
                "role_key": role_key,
                "resource": [resource for resource, _ in pairs],
                "action": [action for _, action in pairs],
            },
        )
    # developer gets every permission, not just the matrix above.
    await connection.execute(
        text(
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

    await connection.execute(
        text(
            """
            INSERT INTO conclusions (code, name, text_singular, text_plural, comment)
            SELECT * FROM unnest(
                CAST(:code AS text[]),
                CAST(:name AS text[]),
                CAST(:text_singular AS text[]),
                CAST(:text_plural AS text[]),
                CAST(:comment AS text[])
            )
            ON CONFLICT (code) DO NOTHING
            """
        ),
        {
            "code": [row[0] for row in CONCLUSIONS],
            "name": [row[1] for row in CONCLUSIONS],
            "text_singular": [row[2] for row in CONCLUSIONS],
            "text_plural": [row[3] for row in CONCLUSIONS],
            "comment": [row[4] for row in CONCLUSIONS],
        },
    )

    # 8 named accounts (0 rows of synthetic bulk "user_NNN" filler — dropped,
    # nobody logs in as those; the realistic named set is what dev/QA uses).
    for user in SEED_USERS:
        await connection.execute(
            text(
                """
                INSERT INTO users (
                    username, password_hash, refresh_token_version, code,
                    first_name, last_name, patronymic, role_id, lab_id
                )
                SELECT
                    :username, :password_hash, 0, :code,
                    :first_name, :last_name, NULL, r.id, NULL
                FROM roles r
                WHERE r.key = :role_key
                ON CONFLICT (username) DO UPDATE
                SET password_hash = EXCLUDED.password_hash,
                    refresh_token_version = 0,
                    code = EXCLUDED.code,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    patronymic = EXCLUDED.patronymic,
                    role_id = EXCLUDED.role_id,
                    lab_id = EXCLUDED.lab_id,
                    deleted_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                """
            ),
            user,
        )

    for role_key, entity_type in ROLE_SUBSCRIPTION_RULES:
        await connection.execute(
            text(
                """
                INSERT INTO role_subscription_rules (role_id, entity_type)
                SELECT id, :entity_type FROM roles WHERE key = :role_key
                ON CONFLICT DO NOTHING
                """
            ),
            {"role_key": role_key, "entity_type": entity_type},
        )


async def _reset_operational_data(connection: AsyncConnection) -> None:
    """Delete all operational + synthetic reference rows, FK-children first.

    Auth (users/roles/permissions), user_scopes, user_permission_overrides,
    status tables, branches, protocol_types and conclusions (all bootstrapped
    once by ``_seed_bootstrap_data``) are preserved. ``users.lab_id`` is reset
    to NULL for any user pointing at a lab that is about to be deleted so no
    user is cascade-deleted and the (NO ACTION) FK is not violated.
    """
    # 1. Operational workflow data, children before parents.
    for table in (
        "tests",
        "research",
        "sample_labs",
        "samples",
        "protocols",
        "directions",
        "notifications",
        "change_log",
        "ui_events",
    ):
        await connection.execute(text(f"DELETE FROM {table}"))

    # Reset denormalized active counters (repopulated by triggers on insert).
    await connection.execute(
        text("UPDATE entity_active_counts SET active_total = 0, updated_at = CURRENT_TIMESTAMP")
    )

    # 2. Detach users from synthetic labs before deleting those labs.
    await connection.execute(
        text(
            """
            UPDATE users
            SET lab_id = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE lab_id IN (
                SELECT id FROM labs WHERE code NOT IN :real_lab_codes
            )
            """
        ).bindparams(_expanding("real_lab_codes")),
        {"real_lab_codes": [code for code, _, _ in REAL_LABS]},
    )

    # 3. Synthetic reference data. indicators/research_goals wiped entirely and
    #    reinserted; sample_types/doctors/objects/labs pruned to the real set.
    await connection.execute(text("DELETE FROM indicators"))
    await connection.execute(text("DELETE FROM research_goals"))
    await connection.execute(text("DELETE FROM sample_types"))
    await connection.execute(
        text(
            """
            DELETE FROM doctors
            WHERE (last_name, first_name, patronymic) NOT IN (
                SELECT * FROM unnest(
                    CAST(:last AS text[]),
                    CAST(:first AS text[]),
                    CAST(:patronymic AS text[])
                )
            )
            """
        ),
        {
            "last": [last for last, _, _ in DOCTORS],
            "first": [first for _, first, _ in DOCTORS],
            "patronymic": [patronymic for _, _, patronymic in DOCTORS],
        },
    )
    await connection.execute(
        text("DELETE FROM objects WHERE code NOT IN :object_codes").bindparams(
            _expanding("object_codes")
        ),
        {"object_codes": [code for code, _, _ in OBJECTS]},
    )
    await connection.execute(
        text("DELETE FROM labs WHERE code NOT IN :real_lab_codes").bindparams(
            _expanding("real_lab_codes")
        ),
        {"real_lab_codes": [code for code, _, _ in REAL_LABS]},
    )


async def _seed_reference_rows(connection: AsyncConnection) -> None:
    """Insert the realistic reference dataset (idempotent, upsert by code)."""
    await connection.execute(
        text(
            """
            INSERT INTO labs (code, name, full_name)
            SELECT * FROM unnest(
                CAST(:code AS text[]), CAST(:name AS text[]), CAST(:full_name AS text[])
            )
            ON CONFLICT (code) DO UPDATE
            SET name = EXCLUDED.name,
                full_name = EXCLUDED.full_name,
                updated_at = CURRENT_TIMESTAMP
            """
        ),
        {
            "code": [code for code, _, _ in REAL_LABS],
            "name": [name for _, name, _ in REAL_LABS],
            "full_name": [full for _, _, full in REAL_LABS],
        },
    )

    await connection.execute(
        text(
            """
            INSERT INTO sample_types (code, name)
            SELECT * FROM unnest(CAST(:code AS text[]), CAST(:name AS text[]))
            ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
            """
        ),
        {
            "code": [code for code, _ in SAMPLE_TYPES],
            "name": [name for _, name in SAMPLE_TYPES],
        },
    )

    await connection.execute(
        text(
            """
            INSERT INTO doctors (last_name, first_name, patronymic)
            SELECT src.last_name, src.first_name, src.patronymic
            FROM unnest(
                CAST(:last AS text[]), CAST(:first AS text[]), CAST(:patronymic AS text[])
            ) AS src(last_name, first_name, patronymic)
            WHERE NOT EXISTS (
                SELECT 1 FROM doctors d
                WHERE d.last_name = src.last_name
                  AND d.first_name = src.first_name
                  AND d.patronymic = src.patronymic
            )
            """
        ),
        {
            "last": [last for last, _, _ in DOCTORS],
            "first": [first for _, first, _ in DOCTORS],
            "patronymic": [patronymic for _, _, patronymic in DOCTORS],
        },
    )

    await connection.execute(
        text(
            """
            INSERT INTO objects (code, name, full_name, address, branch_id)
            SELECT
                src.code,
                src.name,
                src.name,
                src.address,
                COALESCE(
                    (SELECT branch_id FROM labs WHERE code = 'BAK' AND branch_id IS NOT NULL),
                    (SELECT id FROM branches ORDER BY code, id LIMIT 1)
                )
            FROM unnest(
                CAST(:code AS text[]), CAST(:name AS text[]), CAST(:address AS text[])
            ) AS src(code, name, address)
            ON CONFLICT (code) DO UPDATE
            SET name = EXCLUDED.name,
                full_name = EXCLUDED.full_name,
                address = EXCLUDED.address,
                updated_at = CURRENT_TIMESTAMP
            """
        ),
        {
            "code": [code for code, _, _ in OBJECTS],
            "name": [name for _, name, _ in OBJECTS],
            "address": [address for _, _, address in OBJECTS],
        },
    )

    await connection.execute(
        text(
            """
            INSERT INTO research_goals (code, name, comment, lab_id)
            SELECT src.goal_code, src.goal_name, 'Realistic dev seed goal', l.id
            FROM unnest(
                CAST(:lab_code AS text[]),
                CAST(:goal_code AS text[]),
                CAST(:goal_name AS text[])
            ) AS src(lab_code, goal_code, goal_name)
            JOIN labs l ON l.code = src.lab_code
            ON CONFLICT (code) DO UPDATE
            SET name = EXCLUDED.name,
                lab_id = EXCLUDED.lab_id,
                updated_at = CURRENT_TIMESTAMP
            """
        ),
        {
            "lab_code": [lab for lab, _, _ in RESEARCH_GOALS],
            "goal_code": [code for _, code, _ in RESEARCH_GOALS],
            "goal_name": [name for _, _, name in RESEARCH_GOALS],
        },
    )

    goal_codes: list[str] = []
    sample_type_codes: list[str] = []
    for goal_code, st_codes in GOAL_SAMPLE_TYPES.items():
        for st_code in st_codes:
            goal_codes.append(goal_code)
            sample_type_codes.append(st_code)
    await connection.execute(
        text(
            """
            INSERT INTO indicators (
                name, unit, norm_text, comment, research_goal_id, sample_type_id
            )
            SELECT
                rg.code || ' / ' || st.code,
                'ед.',
                'в пределах нормы',
                'Realistic dev seed indicator',
                rg.id,
                st.id
            FROM unnest(CAST(:goal_code AS text[]), CAST(:st_code AS text[]))
                AS m(goal_code, st_code)
            JOIN research_goals rg ON rg.code = m.goal_code
            JOIN sample_types st ON st.code = m.st_code
            WHERE NOT EXISTS (
                SELECT 1 FROM indicators i WHERE i.name = rg.code || ' / ' || st.code
            )
            """
        ),
        {"goal_code": goal_codes, "st_code": sample_type_codes},
    )


async def _seed_workflow_rows(connection: AsyncConnection) -> None:
    """Create one realistic direction/sample/research/test with attached labs.

    Gives the ``(sample type + lab) -> research goals`` derivation a real sample
    to exercise: the sample is of type ST-MEAT and attached to labs BAK + TB.
    """
    await connection.execute(
        text(
            """
            WITH actor AS (
                SELECT id FROM users WHERE username = 'admin' LIMIT 1
            ),
            doctor AS (
                SELECT id FROM doctors WHERE last_name = :doctor_last LIMIT 1
            ),
            object_row AS (
                SELECT id FROM objects WHERE code = :object_code LIMIT 1
            ),
            status_row AS (
                SELECT id FROM direction_statuses WHERE code = 'draft' LIMIT 1
            )
            INSERT INTO directions (
                year_no, base_no, doctor_id, object_id, status_id,
                created_by, updated_by, sampled_at, received_at
            )
            SELECT
                EXTRACT(YEAR FROM CURRENT_DATE)::int,
                :base_no, doctor.id, object_row.id, status_row.id,
                actor.id, actor.id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM actor, doctor, object_row, status_row
            WHERE NOT EXISTS (SELECT 1 FROM directions WHERE base_no = :base_no)
            """
        ),
        {
            "doctor_last": WORKFLOW_DOCTOR_LAST,
            "object_code": WORKFLOW_OBJECT,
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
                name, direction_id, sample_type_id, status_id,
                created_by, updated_by, sampled_at
            )
            SELECT
                :sample_name, direction_row.id, sample_type.id, status_row.id,
                actor.id, actor.id, CURRENT_TIMESTAMP
            FROM direction_row, sample_type, status_row, actor
            WHERE NOT EXISTS (SELECT 1 FROM samples WHERE name = :sample_name)
            """
        ),
        {
            "base_no": TEST_CODES["direction_base_no"],
            "sample_type_code": WORKFLOW_SAMPLE_TYPE,
            "sample_name": TEST_CODES["sample"],
        },
    )
    await connection.execute(
        text(
            """
            INSERT INTO sample_labs (sample_id, lab_id)
            SELECT s.id, l.id
            FROM samples s
            JOIN labs l ON l.code = ANY(CAST(:lab_codes AS text[]))
            WHERE s.name = :sample_name
              AND NOT EXISTS (
                  SELECT 1 FROM sample_labs sl
                  WHERE sl.sample_id = s.id AND sl.lab_id = l.id
              )
            """
        ),
        {
            "sample_name": TEST_CODES["sample"],
            "lab_codes": list(WORKFLOW_SAMPLE_LABS),
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
                SELECT id FROM research_statuses WHERE code = 'in_progress' LIMIT 1
            ),
            actor AS (
                SELECT id FROM users WHERE username = 'admin' LIMIT 1
            )
            INSERT INTO research (
                sample_id, research_goal_id, lab_id, status_id,
                created_by, updated_by, comment
            )
            SELECT
                sample_row.id, goal.id, goal.lab_id, status_row.id,
                actor.id, actor.id, 'Realistic dev seed'
            FROM sample_row, goal, status_row, actor
            WHERE NOT EXISTS (
                SELECT 1 FROM research r
                WHERE r.sample_id = sample_row.id AND r.research_goal_id = goal.id
            )
            """
        ),
        {
            "sample_name": TEST_CODES["sample"],
            "research_goal_code": WORKFLOW_GOAL,
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
                SELECT id FROM test_statuses WHERE code = 'in_progress' LIMIT 1
            ),
            actor AS (
                SELECT id FROM users WHERE username = 'admin' LIMIT 1
            )
            INSERT INTO tests (research_id, indicator_id, status_id, created_by, updated_by)
            SELECT research_row.id, indicator.id, status_row.id, actor.id, actor.id
            FROM research_row, indicator, status_row, actor
            WHERE NOT EXISTS (
                SELECT 1 FROM tests t
                WHERE t.research_id = research_row.id AND t.indicator_id = indicator.id
            )
            """
        ),
        {
            "sample_name": TEST_CODES["sample"],
            "indicator_name": WORKFLOW_INDICATOR,
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
                    SELECT id FROM doctors WHERE last_name = :doctor_last LIMIT 1
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
                    SELECT id FROM research_statuses WHERE code = 'in_progress' LIMIT 1
                ),
                indicator AS (
                    SELECT id FROM indicators WHERE name = :indicator_name LIMIT 1
                ),
                test_status AS (
                    SELECT id FROM test_statuses WHERE code = 'in_progress' LIMIT 1
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
                "doctor_last": WORKFLOW_DOCTOR_LAST,
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
                SELECT id FROM doctors WHERE last_name = :doctor_last LIMIT 1
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
            "doctor_last": WORKFLOW_DOCTOR_LAST,
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
            SELECT 'labs=' || count(*)::text FROM labs WHERE deleted_at IS NULL
            UNION ALL
            SELECT 'sample_types=' || count(*)::text FROM sample_types WHERE deleted_at IS NULL
            UNION ALL
            SELECT 'doctors=' || count(*)::text FROM doctors WHERE deleted_at IS NULL
            UNION ALL
            SELECT 'objects=' || count(*)::text FROM objects WHERE deleted_at IS NULL
            UNION ALL
            SELECT 'research_goals=' || count(*)::text FROM research_goals WHERE deleted_at IS NULL
            UNION ALL
            SELECT 'indicators=' || count(*)::text FROM indicators WHERE deleted_at IS NULL
            """
        )
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


def _expanding(name: str) -> BindParameter[Any]:
    return bindparam(name, expanding=True)


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
            "and tests. If omitted, creates the single realistic workflow row."
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
