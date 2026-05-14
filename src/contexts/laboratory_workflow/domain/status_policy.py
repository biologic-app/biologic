from dataclasses import dataclass


@dataclass(frozen=True)
class InvalidStatusTransition(Exception):
    resource: str
    from_code: str
    to_code: str
    code: str = "invalid_status_transition"


ALLOWED_TRANSITIONS: dict[str, set[tuple[str, str]]] = {
    "directions": {
        ("draft", "registered"),
        ("registered", "in_progress"),
        ("in_progress", "partially_completed"),
        ("in_progress", "completed"),
        ("partially_completed", "in_progress"),
        ("partially_completed", "completed"),
    },
    "samples": {
        ("pending", "registered"),
        ("pending", "rejected"),
        ("registered", "in_progress"),
        ("in_progress", "analyzed"),
        ("analyzed", "in_progress"),
        ("analyzed", "completed"),
    },
    "research": {
        ("draft", "ordered"),
        ("draft", "rejected"),
        ("ordered", "in_progress"),
        ("ordered", "rejected"),
        ("in_progress", "completed"),
        ("completed", "in_progress"),
    },
    "tests": {
        ("queued", "in_progress"),
        ("queued", "rejected"),
        ("in_progress", "completed"),
        ("in_progress", "queued"),
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
