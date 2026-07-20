from __future__ import annotations

from typing import Any, Protocol

from src.core.responses import ResponseMeta, SingleResponse


class ReleasedSamplesRepository(Protocol):
    async def released_by_direction(self) -> list[dict[str, Any]]: ...


class ReleasedSamplesUseCase:
    def __init__(self, *, repository: ReleasedSamplesRepository) -> None:
        self.repository = repository

    async def released_by_direction(self) -> SingleResponse[list[dict[str, Any]]]:
        data = await self.repository.released_by_direction()
        return SingleResponse(
            data=data,
            meta=ResponseMeta(operation="directions.released_samples"),
        )
