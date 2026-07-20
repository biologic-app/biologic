"""Design-system-neutral color names for lifecycle status catalogs.

The values here are generic color-name strings (not Nuxt UI tokens, not hex).
The FRONTEND owns the color vocabulary and is the single source of truth: it
maps these names onto its own design system (``shared/domain/status-color.ts``)
and falls back to a neutral color for any name it does not recognise. The
backend only assigns and stores a name per status; it does not constrain the
vocabulary. Each per-entity mapping below is keyed by the stable status
``code`` strings defined in :mod:`src.core.status_codes`.
"""

from src.core.status_codes import (
    DIRECTION_COMPLETED,
    DIRECTION_DRAFT,
    DIRECTION_IN_PROGRESS,
    DIRECTION_PARTIALLY_COMPLETED,
    DIRECTION_REGISTERED,
    RESEARCH_COMPLETED,
    RESEARCH_IN_PROGRESS,
    RESEARCH_REJECTED,
    SAMPLE_ANALYZED,
    SAMPLE_COMPLETED,
    SAMPLE_IN_PROGRESS,
    SAMPLE_PENDING,
    SAMPLE_REGISTERED,
    SAMPLE_REJECTED,
    TEST_COMPLETED,
    TEST_IN_PROGRESS,
    TEST_REJECTED,
)

DIRECTION_STATUS_COLORS: dict[str, str] = {
    DIRECTION_DRAFT: "gray",
    DIRECTION_REGISTERED: "indigo",
    DIRECTION_IN_PROGRESS: "blue",
    DIRECTION_PARTIALLY_COMPLETED: "lime",
    DIRECTION_COMPLETED: "green",
}

SAMPLE_STATUS_COLORS: dict[str, str] = {
    SAMPLE_PENDING: "amber",
    SAMPLE_REGISTERED: "indigo",
    SAMPLE_IN_PROGRESS: "blue",
    SAMPLE_ANALYZED: "violet",
    SAMPLE_COMPLETED: "green",
    SAMPLE_REJECTED: "red",
}

RESEARCH_STATUS_COLORS: dict[str, str] = {
    RESEARCH_IN_PROGRESS: "blue",
    RESEARCH_COMPLETED: "green",
    RESEARCH_REJECTED: "red",
}

TEST_STATUS_COLORS: dict[str, str] = {
    TEST_IN_PROGRESS: "blue",
    TEST_COMPLETED: "green",
    TEST_REJECTED: "red",
}
