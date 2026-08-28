"""Full-database export/import engine.

Dumps are files on disk; PostgreSQL only stores the path (see
``DatabaseBackup``). Two interchangeable engines are picked at runtime:

* ``custom`` — ``pg_dump --format=custom`` / ``pg_restore``. Preferred: it
  carries schema *and* data, and it is the artefact a DBA expects to receive.
* ``sql`` — a plain ``INSERT`` script generated through asyncpg, used when the
  PostgreSQL client binaries are absent (a bare `uv run` dev box, an offline
  Windows deploy). It is data-only: the schema belongs to Alembic, so a restore
  targets an already-migrated database.

Both engines skip ``database_backups``: a restore must never wipe the registry
that points at the file being restored. ``alembic_version`` is skipped by the
SQL engine for the same reason — the running code owns the schema revision.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import asyncpg
from sqlalchemy.engine import URL, make_url

from src.core.config import get_settings

# Rows the application owns as *infrastructure* state, never as data to move.
EXCLUDED_TABLES = ("database_backups", "alembic_version")

CUSTOM_FORMAT = "custom"
SQL_FORMAT = "sql"

# Every pg_dump custom archive starts with this magic string.
_CUSTOM_MAGIC = b"PGDMP"

# Rows per generated INSERT statement — large enough to keep the script small,
# small enough that a single statement stays readable and parseable.
_INSERT_CHUNK = 500


class DatabaseTransferError(RuntimeError):
    """Raised when PostgreSQL cannot create or restore a database dump."""


# --- Connection plumbing -----------------------------------------------------


def _database_url() -> URL:
    """The configured URL with the async driver suffix stripped."""
    url = make_url(get_settings().database_url)
    if "+" in url.drivername:
        url = url.set(drivername=url.drivername.split("+", 1)[0])
    return url


def _dsn() -> str:
    return _database_url().render_as_string(hide_password=False)


def _pg_env(url: URL) -> dict[str, str]:
    environment = os.environ.copy()
    if url.password is not None:
        environment["PGPASSWORD"] = url.password
    return environment


def _lock_timeout() -> str:
    return f"{get_settings().database_restore_lock_timeout_seconds}s"


def _lock_error(exc: asyncpg.PostgresError) -> DatabaseTransferError:
    """Turn a lock timeout into something an operator can act on."""
    if isinstance(exc, asyncpg.LockNotAvailableError):
        return DatabaseTransferError(
            "Restore could not lock the application tables: another session is "
            "still using the database. Stop the other clients and try again."
        )
    return DatabaseTransferError(str(exc))


def _connection_args(url: URL) -> list[str]:
    args: list[str] = []
    if url.host:
        args.extend(["--host", url.host])
    if url.port:
        args.extend(["--port", str(url.port)])
    if url.username:
        args.extend(["--username", url.username])
    if url.database:
        args.extend(["--dbname", url.database])
    return args


def pg_tools_available() -> bool:
    """True when both client binaries the ``custom`` engine needs are on PATH."""
    return bool(shutil.which("pg_dump") and shutil.which("pg_restore"))


def preferred_format() -> str:
    return CUSTOM_FORMAT if pg_tools_available() else SQL_FORMAT


def detect_format(head: bytes) -> str:
    """Classify an uploaded dump by its first bytes."""
    return CUSTOM_FORMAT if head.startswith(_CUSTOM_MAGIC) else SQL_FORMAT


def backup_dir() -> Path:
    directory = Path(get_settings().database_backup_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def build_filename(fmt: str, *, prefix: str = "biologic") -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    suffix = "dump" if fmt == CUSTOM_FORMAT else "sql"
    return f"{prefix}-{stamp}.{suffix}"


# --- Engine: pg_dump / pg_restore -------------------------------------------


def _run(command: list[str], *, lock_timeout: str | None = None) -> None:
    environment = _pg_env(_database_url())
    if lock_timeout is not None:
        environment["PGOPTIONS"] = f"-c lock_timeout={lock_timeout}"
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            env=environment,
        )
    except FileNotFoundError as exc:
        raise DatabaseTransferError(
            "PostgreSQL client tools are not installed (pg_dump/pg_restore required)."
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip()
        raise DatabaseTransferError(detail or "PostgreSQL database transfer failed.") from exc


def _custom_dump(path: Path) -> None:
    url = _database_url()
    _run(
        [
            "pg_dump",
            "--format=custom",
            "--no-owner",
            "--no-acl",
            "--exclude-table=public.database_backups",
            *_connection_args(url),
            "--file",
            str(path),
        ]
    )


def _custom_restore(path: Path) -> None:
    url = _database_url()
    _run(
        [
            "pg_restore",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--exit-on-error",
            "--single-transaction",
            *_connection_args(url),
            str(path),
        ],
        lock_timeout=_lock_timeout(),
    )


# --- Engine: plain SQL via asyncpg ------------------------------------------


async def _data_tables(conn: asyncpg.Connection) -> list[str]:
    rows = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    )
    return [row["tablename"] for row in rows if row["tablename"] not in EXCLUDED_TABLES]


async def _insertable_columns(conn: asyncpg.Connection, table: str) -> list[str]:
    """Columns a restore may write: generated and identity-always ones cannot."""
    rows = await conn.fetch(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = $1
          AND is_generated = 'NEVER'
          AND COALESCE(identity_generation, '') <> 'ALWAYS'
        ORDER BY ordinal_position
        """,
        table,
    )
    return [row["column_name"] for row in rows]


def _tuple_expression(columns: list[str]) -> str:
    """SQL that makes PostgreSQL itself render one row as a VALUES tuple.

    Quoting is delegated to ``quote_nullable`` so escaping is never done in
    Python, and every value is emitted as an untyped literal — INSERT coerces
    those to the target column type, which works for uuid, jsonb, bytea and
    arrays alike.
    """
    parts = ", ".join(f'quote_nullable("{column}"::text)' for column in columns)
    return f"'(' || array_to_string(ARRAY[{parts}], ', ') || ')'"


async def _write_table(conn: asyncpg.Connection, out: Any, table: str) -> None:
    columns = await _insertable_columns(conn, table)
    if not columns:
        return
    column_list = ", ".join(f'"{column}"' for column in columns)
    query = f'SELECT {_tuple_expression(columns)} AS tuple FROM "{table}"'
    chunk: list[str] = []

    def flush() -> None:
        if not chunk:
            return
        out.write(f'INSERT INTO "{table}" ({column_list}) VALUES\n')
        out.write(",\n".join(chunk))
        out.write(";\n")
        chunk.clear()

    async with conn.transaction():
        async for record in conn.cursor(query):
            chunk.append(record["tuple"])
            if len(chunk) >= _INSERT_CHUNK:
                flush()
    flush()


async def _sequences(conn: asyncpg.Connection) -> list[asyncpg.Record]:
    """Sequences whose position must travel with the data.

    Sequences owned by an excluded table are left out: their ``setval`` would
    fail on a database where that table does not exist yet.
    """
    rows = await conn.fetch(
        """
        SELECT s.sequencename, s.last_value, owner.relname AS owner_table
        FROM pg_sequences s
        JOIN pg_class c ON c.relname = s.sequencename AND c.relkind = 'S'
        JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = s.schemaname
        LEFT JOIN pg_depend d ON d.objid = c.oid AND d.deptype IN ('a', 'i')
        LEFT JOIN pg_class owner ON owner.oid = d.refobjid AND owner.relkind IN ('r', 'p')
        WHERE s.schemaname = 'public'
        """
    )
    return [row for row in rows if row["owner_table"] not in EXCLUDED_TABLES]


async def _sql_dump(path: Path) -> None:
    conn = await asyncpg.connect(_dsn())
    try:
        tables = await _data_tables(conn)
        with path.open("w", encoding="utf-8") as out:
            out.write("-- Biologic data dump. Schema is owned by Alembic; this file\n")
            out.write("-- replaces the contents of every application table.\n")
            # Triggers off: foreign keys must not fight the truncate/insert order.
            out.write("SET session_replication_role = replica;\n")
            for table in tables:
                out.write(f'TRUNCATE TABLE "{table}" CASCADE;\n')
            for table in tables:
                await _write_table(conn, out, table)
            for row in await _sequences(conn):
                if row["last_value"] is None:
                    continue
                out.write(
                    f"SELECT setval('public.\"{row['sequencename']}\"', "
                    f"{row['last_value']}, true);\n"
                )
            out.write("SET session_replication_role = DEFAULT;\n")
    except asyncpg.PostgresError as exc:
        raise DatabaseTransferError(str(exc)) from exc
    finally:
        await conn.close()


async def _sql_restore(path: Path) -> None:
    script = path.read_text(encoding="utf-8")
    conn = await asyncpg.connect(_dsn())
    try:
        await conn.execute(f"SET lock_timeout = '{_lock_timeout()}'")
        # asyncpg's simple query protocol runs the whole script as one implicit
        # transaction, so semicolons inside literals need no statement splitter
        # and a failure halfway through leaves the database untouched.
        await conn.execute(script)
    except asyncpg.PostgresError as exc:
        raise _lock_error(exc) from exc
    finally:
        await conn.close()


# --- Public API --------------------------------------------------------------


async def create_dump(path: Path, *, fmt: str | None = None) -> str:
    """Write a dump of the configured database to ``path``; return its format."""
    chosen = fmt or preferred_format()
    if chosen == CUSTOM_FORMAT:
        await asyncio.to_thread(_custom_dump, path)
    else:
        await _sql_dump(path)
    return chosen


async def restore_dump(path: Path, fmt: str) -> None:
    """Restore ``path`` into the configured database."""
    if not path.exists():
        raise DatabaseTransferError("Dump file is missing on the server filesystem.")
    if fmt == CUSTOM_FORMAT:
        if not pg_tools_available():
            raise DatabaseTransferError(
                "This dump needs pg_restore, which is not installed on the server."
            )
        await asyncio.to_thread(_custom_restore, path)
    else:
        await _sql_restore(path)


async def database_overview() -> dict[str, Any]:
    """Live facts about the target database, for the operations page header."""
    url = _database_url()
    conn = await asyncpg.connect(_dsn())
    try:
        row = await conn.fetchrow(
            """
            SELECT current_database() AS name,
                   current_setting('server_version') AS server_version,
                   pg_database_size(current_database()) AS size_bytes,
                   (SELECT count(*) FROM pg_tables WHERE schemaname = 'public') AS table_count
            """
        )
    except asyncpg.PostgresError as exc:
        raise DatabaseTransferError(str(exc)) from exc
    finally:
        await conn.close()
    return {
        "name": row["name"],
        "host": url.host,
        "port": url.port,
        "server_version": row["server_version"],
        "size_bytes": int(row["size_bytes"]),
        "table_count": int(row["table_count"]),
    }
