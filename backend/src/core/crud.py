from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CrudResource:
    name: str
    model: type[Any]
    allowed_includes: tuple[str, ...] = ()
    read_only: bool = False
    forbidden_patch_fields: tuple[str, ...] = ()
