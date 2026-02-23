from __future__ import annotations

import inspect

import pytest
from pydantic import BaseModel

import src.schemas as contracts
from src.models.base import Base
from src.models.entities import (
    Branch,
    ChangeLog,
    Conclusion,
    ConclusionStatus,
    Direction,
    Doctor,
    Indicator,
    Lab,
    Object,
    Protocol,
    ProtocolType,
    ResearchGoal,
    Result,
    Role,
    RolePermission,
    Sample,
    SampleTarget,
    SampleType,
    Status,
    User,
    UserRole,
)
from src.models.entities import Test as DbRow
from tests._helpers import build_model_instance

ALL_ENTITIES = [
    ResearchGoal,
    Lab,
    Indicator,
    User,
    Role,
    DbRow,
    Status,
    ConclusionStatus,
    Conclusion,
    UserRole,
    Object,
    Doctor,
    Direction,
    SampleTarget,
    Protocol,
    Branch,
    RolePermission,
    Sample,
    ChangeLog,
    ProtocolType,
    Result,
    SampleType,
]


CONTRACT_MODELS = [
    model
    for name, model in inspect.getmembers(contracts, inspect.isclass)
    if issubclass(model, BaseModel) and name.endswith("DTO")
]


@pytest.mark.parametrize("model_cls", CONTRACT_MODELS)
def test_contract_models_can_be_built(model_cls: type[BaseModel]) -> None:
    instance = build_model_instance(model_cls)
    assert isinstance(instance, model_cls)


def test_all_entities_registered_in_mapper_registry() -> None:
    mapped_tables = {mapper.persist_selectable.name for mapper in Base.registry.mappers}
    expected_tables = {entity.__tablename__ for entity in ALL_ENTITIES}
    assert expected_tables.issubset(mapped_tables)
