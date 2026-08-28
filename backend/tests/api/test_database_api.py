from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.application import data_transfer
from src.core.config import get_settings
from src.presentation.http.access_control.dependencies import get_current_user_id
from src.presentation.http.database import router as database_router

ACTOR_ID = UUID("00000000-0000-0000-0000-0000000000a1")


def _configure(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    monkeypatch.setenv("APP_DATABASE_BACKUP_DIR", str(tmp_path / "backups"))
    get_settings.cache_clear()


class _Row:
    """Stand-in for the DatabaseBackup ORM row."""

    def __init__(self, **values: Any) -> None:
        self.id = uuid4()
        self.filename = ""
        self.file_path = ""
        self.format = "sql"
        self.origin = "export"
        self.status = "in_progress"
        self.size_bytes = 0
        self.duration_ms = None
        self.error = None
        self.created_by = None
        self.created_at = datetime.now(UTC)
        self.completed_at = None
        self.restored_at = None
        for key, value in values.items():
            setattr(self, key, value)


class _FakeRepository:
    def __init__(self) -> None:
        self.rows: list[_Row] = []
        self.deleted: list[UUID] = []

    async def list(self, *, limit: int) -> tuple[list[_Row], int]:
        return self.rows[:limit], len(self.rows)

    async def read(self, backup_id: UUID) -> _Row:
        return next(row for row in self.rows if row.id == backup_id)

    async def add(self, **values: Any) -> _Row:
        row = _Row(**values)
        self.rows.append(row)
        return row

    async def update(self, backup: _Row, **values: Any) -> _Row:
        for key, value in values.items():
            setattr(backup, key, value)
        return backup

    async def delete(self, backup_id: UUID) -> None:
        self.deleted.append(backup_id)
        self.rows = [row for row in self.rows if row.id != backup_id]


def _seed_completed_backup(repository: _FakeRepository, tmp_path: Path) -> _Row:
    """Seed the fake registry with one completed dump present on disk."""
    path = tmp_path / "seeded.sql"
    path.write_text("-- dump --\n", encoding="utf-8")
    row = _Row(
        filename=path.name,
        file_path=str(path),
        format="sql",
        status="completed",
        size_bytes=path.stat().st_size,
        completed_at=datetime.now(UTC),
    )
    repository.rows.append(row)
    return row


def _client(repository: _FakeRepository) -> TestClient:
    app = create_app()
    app.dependency_overrides[database_router.get_backup_repository] = lambda: repository
    app.dependency_overrides[get_current_user_id] = lambda: ACTOR_ID
    return TestClient(app)


def test_create_backup_writes_a_file_and_records_its_path(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    _configure(monkeypatch, tmp_path)
    repository = _FakeRepository()

    async def fake_create_dump(path: Path, *, fmt: str | None = None) -> str:
        path.write_text("-- dump --\n", encoding="utf-8")
        return "sql"

    monkeypatch.setattr(database_router, "create_dump", fake_create_dump)
    monkeypatch.setattr(database_router, "preferred_format", lambda: "sql")

    response = _client(repository).post("/api/v1/database/backups")

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "completed"
    assert data["origin"] == "export"
    assert data["size_bytes"] == len("-- dump --\n")
    # The dump lives on disk; the row only points at it.
    assert Path(data["file_path"]).read_text(encoding="utf-8") == "-- dump --\n"
    assert data["file_exists"] is True


def test_failed_export_keeps_an_honest_record_and_no_stray_file(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    _configure(monkeypatch, tmp_path)
    repository = _FakeRepository()

    async def failing_dump(path: Path, *, fmt: str | None = None) -> str:
        path.write_text("partial", encoding="utf-8")
        raise data_transfer.DatabaseTransferError("pg_dump exploded")

    monkeypatch.setattr(database_router, "create_dump", failing_dump)
    monkeypatch.setattr(database_router, "preferred_format", lambda: "sql")

    response = _client(repository).post("/api/v1/database/backups")

    assert response.status_code == 400
    assert "pg_dump exploded" in response.json()["detail"]
    assert repository.rows[0].status == "failed"
    assert repository.rows[0].error == "pg_dump exploded"
    assert not Path(repository.rows[0].file_path).exists()


def test_upload_stores_the_file_and_classifies_its_format(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    _configure(monkeypatch, tmp_path)
    repository = _FakeRepository()

    response = _client(repository).post(
        "/api/v1/database/backups/upload",
        files={"file": ("legacy.dump", b"PGDMP\x00binary-archive", "application/octet-stream")},
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["format"] == "custom"
    assert data["origin"] == "upload"
    assert Path(data["file_path"]).read_bytes() == b"PGDMP\x00binary-archive"


def test_upload_rejects_a_dump_over_the_configured_limit(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    _configure(monkeypatch, tmp_path)
    monkeypatch.setenv("APP_DATABASE_BACKUP_MAX_MB", "0")
    get_settings.cache_clear()
    repository = _FakeRepository()

    response = _client(repository).post(
        "/api/v1/database/backups/upload",
        files={"file": ("big.sql", b"INSERT INTO t VALUES (1);", "application/sql")},
    )

    assert response.status_code == 400
    assert repository.rows == []
    assert list((tmp_path / "backups").iterdir()) == []


def test_restore_requires_the_literal_confirmation(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    _configure(monkeypatch, tmp_path)
    repository = _FakeRepository()
    row = _seed_completed_backup(repository, tmp_path)

    client = _client(repository)
    assert client.post(f"/api/v1/database/backups/{row.id}/restore").status_code == 400

    restored: list[tuple[Path, str]] = []

    async def fake_restore(path: Path, fmt: str) -> None:
        restored.append((path, fmt))

    monkeypatch.setattr(database_router, "restore_dump", fake_restore)
    response = client.post(
        f"/api/v1/database/backups/{row.id}/restore",
        params={"confirmation": database_router.RESTORE_CONFIRMATION},
    )

    assert response.status_code == 200
    assert restored == [(Path(row.file_path), "sql")]
    assert response.json()["data"]["restored_at"] is not None


def test_delete_removes_the_file_alongside_the_record(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    _configure(monkeypatch, tmp_path)
    repository = _FakeRepository()
    row = _seed_completed_backup(repository, tmp_path)

    response = _client(repository).delete(f"/api/v1/database/backups/{row.id}")

    assert response.status_code == 204
    assert repository.deleted == [row.id]
    assert not Path(row.file_path).exists()


def test_detect_format_reads_the_pg_dump_magic() -> None:
    assert data_transfer.detect_format(b"PGDMP\x01") == data_transfer.CUSTOM_FORMAT
    assert data_transfer.detect_format(b"-- Bio") == data_transfer.SQL_FORMAT


def test_build_filename_matches_the_engine_extension() -> None:
    assert data_transfer.build_filename(data_transfer.CUSTOM_FORMAT).endswith(".dump")
    assert data_transfer.build_filename(data_transfer.SQL_FORMAT, prefix="uploaded").startswith(
        "uploaded-"
    )
