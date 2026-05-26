from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.core.errors import BadRequestError


@dataclass(frozen=True)
class CursorState:
    sort_by: str
    sort_order: str
    sort_value: Any
    item_id: UUID


def encode_cursor(
    *,
    sort_by: str,
    sort_order: str,
    sort_value: Any,
    item_id: UUID,
) -> str:
    payload = {
        "sort_by": sort_by,
        "sort_order": sort_order,
        "sort_value": json_value(sort_value),
        "id": str(item_id),
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(value: str) -> CursorState:
    try:
        padded = value + "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError
        sort_by = payload["sort_by"]
        sort_order = payload["sort_order"]
        sort_value = payload["sort_value"]
        item_id = UUID(str(payload["id"]))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise BadRequestError("Pagination cursor is invalid.") from exc
    if not isinstance(sort_by, str) or sort_order not in {"asc", "desc"}:
        raise BadRequestError("Pagination cursor is invalid.")
    return CursorState(
        sort_by=sort_by,
        sort_order=sort_order,
        sort_value=sort_value,
        item_id=item_id,
    )


def json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, UUID):
        return str(value)
    return value
