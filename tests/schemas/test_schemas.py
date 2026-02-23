from __future__ import annotations

from src.schemas.base import ListMetaDTO
from src.schemas.health import HealthResponse
from src.schemas.sample import (
    SampleCreateDTO,
    SampleListEnvelopeDTO,
    SampleReadDTO,
    SampleUpdateDTO,
)
from tests._helpers import build_model_instance


def test_health_schema_smoke() -> None:
    schema = HealthResponse(status="ok")
    assert schema.status == "ok"


def test_sample_dto_schema_smoke() -> None:
    create_payload = build_model_instance(SampleCreateDTO)
    patch_payload = build_model_instance(SampleUpdateDTO)

    assert isinstance(create_payload.name, str)
    assert patch_payload is not None


def test_sample_read_and_list_schema_smoke() -> None:
    read_model = build_model_instance(SampleReadDTO)
    list_model = SampleListEnvelopeDTO(
        items=[read_model],
        meta=ListMetaDTO(total=1, offset=0, limit=15),
    )

    assert list_model.meta.total == 1
    assert len(list_model.items) == 1
