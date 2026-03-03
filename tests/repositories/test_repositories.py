from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models.entities import Branch, ChangeLog, Role, RolePermission, User
from src.repositories.auth_repository import AuthRepository
from src.repositories.crud_repository import CRUDRepository, ListQuery
from src.repositories.role_permissions_repository import RolePermissionRepository
from src.repositories.sample_repository import SampleRepository


class _ScalarResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value


class _CountResult:
    def __init__(self, value: int) -> None:
        self._value = value

    def scalar_one(self) -> int:
        return self._value


class _ItemsResult:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def scalars(self) -> _ItemsResult:
        return self

    def all(self) -> list[object]:
        return self._items


class _Row:
    def __init__(self, mapping: dict[str, object]) -> None:
        self._mapping = mapping


class _RowsResult:
    def __init__(self, rows: list[_Row]) -> None:
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)


class _FirstResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def first(self) -> object | None:
        return self._value


def _make_session_mock() -> MagicMock:
    session = MagicMock()
    session.add = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


def test_legacy_sample_repository_init_smoke() -> None:
    repository = SampleRepository(session=object())
    assert repository is not None


def test_crud_repository_coerce_and_query_helpers() -> None:
    from src.models.entities import Direction

    repository = CRUDRepository(session=_make_session_mock(), model=Direction)

    assert repository._coerce_filter_value("is_done", "true") is True
    assert repository._coerce_filter_value("is_done", "0") is False
    assert repository._coerce_filter_value("year_no", "2025") == 2025
    assert repository._coerce_filter_value("id", str(uuid4()))
    assert repository._coerce_filter_value("sampled_at", "2025-01-01T00:00:00Z").tzinfo is not None
    assert repository._coerce_filter_value("is_done", "unknown") == "unknown"

    with pytest.raises(ValueError, match="Unknown field"):
        repository._column("missing")

    with pytest.raises(ValueError, match="Unsupported sort field"):
        repository._resolve_sort_column(ListQuery(sort_by="missing"), {"id"})


async def test_crud_repository_create_get_list_update_flow() -> None:
    session = _make_session_mock()
    repository = CRUDRepository(session=session, model=Branch)

    created = await repository.create({"code": "b-1", "name": "Branch 1"})
    assert isinstance(created, Branch)
    session.add.assert_called_once()
    session.commit.assert_awaited()
    session.refresh.assert_awaited()

    target_id = uuid4()
    branch = Branch(code="b-2", name="Branch 2")
    branch.id = target_id
    session.execute.return_value = _ScalarResult(branch)
    found = await repository.get(target_id)
    assert found is branch

    list_query = ListQuery(offset=0, limit=10, sort_by="created_at", sort_order="desc")
    session.execute.side_effect = [_CountResult(1), _ItemsResult([branch])]
    items, total = await repository.list(list_query, allowed_sort_fields={"created_at"})
    assert total == 1
    assert items == [branch]

    repository.get = AsyncMock(return_value=branch)
    updated = await repository.update(target_id, {"name": "Updated"})
    assert updated is branch
    assert branch.name == "Updated"


async def test_crud_repository_soft_delete_paths() -> None:
    session = _make_session_mock()

    soft_repo = CRUDRepository(session=session, model=Branch)
    soft_branch = Branch(code="b-3", name="Branch 3")
    soft_branch.id = uuid4()
    soft_repo.get = AsyncMock(return_value=soft_branch)
    deleted = await soft_repo.soft_delete_with_reason(soft_branch.id, reason="cleanup")

    assert deleted is True
    assert soft_branch.deleted_at is not None
    assert session.add.call_count >= 1

    session = _make_session_mock()
    hard_repo = CRUDRepository(session=session, model=Role)
    role = Role(key="user", name="User", scope_type="global")
    role.id = uuid4()
    hard_repo.get = AsyncMock(return_value=role)

    deleted = await hard_repo.soft_delete_with_reason(role.id, reason=None)
    assert deleted is True
    session.delete.assert_awaited_once_with(role)

    session = _make_session_mock()
    change_repo = CRUDRepository(session=session, model=ChangeLog)
    log = ChangeLog(entity_type="samples", entity_id=uuid4(), action="create")
    log.id = uuid4()
    change_repo.get = AsyncMock(return_value=log)

    deleted = await change_repo.soft_delete_with_reason(log.id, reason="ignored")
    assert deleted is True
    session.add.assert_not_called()


async def test_crud_repository_resolve_include_reference() -> None:
    session = _make_session_mock()
    repository = CRUDRepository(session=session, model=RolePermission)

    assert await repository.resolve_include_reference("role", None) is None
    assert await repository.resolve_include_reference("missing", uuid4()) is None

    role = Role(key="admin", name="Administrator", scope_type="global")
    role.id = uuid4()
    role.code = "ADMIN"
    session.execute.return_value = _RowsResult(
        rows=[
            _Row(
                {
                    "_ref_id": role.id,
                    "_ref_name": role.name,
                    "_ref_code": role.code,
                }
            )
        ]
    )

    ref = await repository.resolve_include_reference("role", role.id)
    assert ref is not None
    assert ref.id == role.id
    assert ref.name == "Administrator"

    user_repository = CRUDRepository(session=session, model=Branch)
    user_repository._include_targets = {"user": User}
    user = User(
        username="u",
        password_hash="hash",
        role_id=uuid4(),
    )
    user.id = uuid4()
    user.first_name = "John"
    user.last_name = "Doe"
    user.code = None
    session.execute.return_value = _RowsResult(
        rows=[
            _Row(
                {
                    "_ref_id": user.id,
                    "_ref_first_name": user.first_name,
                    "_ref_last_name": user.last_name,
                    "_ref_code": user.code,
                }
            )
        ]
    )

    ref = await user_repository.resolve_include_reference("user", user.id)
    assert ref is not None
    assert ref.name == "John Doe"


def test_role_permission_repository_init_smoke() -> None:
    session = _make_session_mock()
    repository = RolePermissionRepository(session=session)
    assert repository is not None


async def test_auth_repository_lookup_and_version_bump() -> None:
    session = _make_session_mock()
    repository = AuthRepository(session=session)

    role_id = uuid4()
    user = User(username="admin", password_hash="hash", role_id=role_id)
    user.id = uuid4()
    user.refresh_token_version = 1
    role = Role(key="admin", name="Administrator", scope_type="global")
    role.id = role_id

    session.execute.return_value = _FirstResult((user, role))
    by_username = await repository.get_user_with_role_by_username("admin")
    by_id = await repository.get_user_with_role_by_id(user.id)

    assert by_username == (user, role)
    assert by_id == (user, role)

    session.execute.return_value = _ScalarResult(2)
    next_version = await repository.bump_refresh_token_version(user.id)

    assert next_version == 2
    session.commit.assert_awaited()
