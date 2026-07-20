from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class InvalidStatusTransition(Exception):
    resource: str
    from_code: str
    to_code: str
    code: str = "invalid_status_transition"


class SampleDeadlinePolicy:
    def calculate(self, received_at: datetime) -> datetime:
        return received_at + timedelta(days=2)


ALLOWED_TRANSITIONS: dict[str, set[tuple[str, str]]] = {
    "directions": {
        ("draft", "registered"),
        ("registered", "in_progress"),
        ("in_progress", "partially_completed"),
        ("in_progress", "completed"),
        ("partially_completed", "completed"),
    },
    "samples": {
        ("pending", "registered"),
        ("registered", "in_progress"),
        ("registered", "rejected"),
        ("in_progress", "analyzed"),
        ("in_progress", "rejected"),
        ("analyzed", "in_progress"),
        ("analyzed", "completed"),
    },
    "research": {
        ("in_progress", "completed"),
        ("in_progress", "rejected"),
    },
    "tests": {
        ("in_progress", "completed"),
        ("in_progress", "rejected"),
    },
}


def ensure_allowed_transition(resource: str, from_code: str, to_code: str) -> None:
    if (from_code, to_code) not in ALLOWED_TRANSITIONS.get(resource, set()):
        raise InvalidStatusTransition(
            resource=resource,
            from_code=from_code,
            to_code=to_code,
        )


def allowed_transitions_map() -> dict[str, list[tuple[str, str]]]:
    """Serializable snapshot of ALLOWED_TRANSITIONS — единый источник правды для
    UI-схемы статусов. Пары отсортированы для стабильного ответа API."""
    return {resource: sorted(pairs) for resource, pairs in ALLOWED_TRANSITIONS.items()}
