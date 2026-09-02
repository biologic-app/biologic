"""Full-database export/import engine.

Dumps are files on disk; PostgreSQL only stores the path (see
``DatabaseBackup``). Two interchangeable engines are picked at runtime, and
both now carry schema *and* data, so a restore never needs a pre-migrated
target — an empty database is a valid restore target for either:

* ``custom`` — ``pg_dump --format=custom`` / ``pg_restore``. Preferred, and
  available almost everywhere: Linux x86_64 and Windows x86_64 both ship the
  client binaries in ``backend/bin/`` (see ``backend/bin/README.md``), so
  this needs nothing installed on the host; PATH is only a fallback for
  platforms that aren't bundled (arm64 Mac, aarch64 servers, ...).
* ``sql`` — a plain SQL script generated through asyncpg (DDL via
  ``pg_get_*def()`` introspection, data via generated ``INSERT``s), the
  fallback for those unbundled platforms when PATH has nothing either. Every
  DDL statement is written idempotently (``IF NOT EXISTS``, ``CREATE OR
  REPLACE``, a ``DO`` block for constraints) so the same script is also safe
  to run against an already-migrated database — restoring is then just "make
  it match this snapshot", not "start from empty".

Both engines skip ``database_backups``: a restore must never wipe the registry
that points at the file being restored. ``alembic_version`` travels with
everything else now, so the restored database reports the migration state
the dump was actually taken at.
"""

from __future__ import annotations

import asyncio
import gzip
import os
import shutil
import subprocess
import sys
import zlib
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import asyncpg
from sqlalchemy.engine import URL, make_url

from src.core.config import get_settings

# gzip's own magic bytes — every dump this module writes is gzip-compressed,
# storage and transfer alike, so this is what tells a stored/uploaded file
# apart from a stray uncompressed one (kept readable for backward compat).
_GZIP_MAGIC = b"\x1f\x8b"

# `backend/bin/<platform>/` — pg_dump/pg_restore checked into the repo so the
# ``custom`` engine works without asking an operator to install PostgreSQL
# client tools system-wide. Only Linux and Windows x86_64 are bundled; every
# other platform (arm64 Mac, aarch64 servers, ...) falls back to PATH.
_BIN_DIR = Path(__file__).resolve().parents[2] / "bin"


@lru_cache
def _bundled_tool(name: str) -> Path | None:
    """Path to a bundled ``pg_dump``/``pg_restore``, or ``None`` if not bundled."""
    if sys.platform == "win32":
        candidate = _BIN_DIR / "windows-x64" / f"{name}.exe"
    elif sys.platform.startswith("linux") and os.uname().machine in ("x86_64", "amd64"):
        candidate = _BIN_DIR / "linux-x64" / name
    else:
        return None
    return candidate if candidate.is_file() else None

# The dump registry can never travel inside its own dump: a restore must not
# overwrite the row that points at the file currently being restored.
EXCLUDED_TABLES = ("database_backups",)

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
    if _bundled_tool("pg_dump") is not None and sys.platform.startswith("linux"):
        # The bundled pg_dump/pg_restore link against a private libpq shipped
        # alongside them, not whatever (if anything) the system provides.
        lib_dir = str(_BIN_DIR / "linux-x64" / "lib")
        existing = environment.get("LD_LIBRARY_PATH")
        environment["LD_LIBRARY_PATH"] = f"{lib_dir}:{existing}" if existing else lib_dir
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


def _tool_path(name: str) -> str:
    """Resolved ``pg_dump``/``pg_restore`` invocation: bundled binary, else PATH."""
    bundled = _bundled_tool(name)
    return str(bundled) if bundled is not None else name


def pg_tools_available() -> bool:
    """True when both client binaries the ``custom`` engine needs are reachable."""
    return bool(
        (_bundled_tool("pg_dump") or shutil.which("pg_dump"))
        and (_bundled_tool("pg_restore") or shutil.which("pg_restore"))
    )


def preferred_format() -> str:
    return CUSTOM_FORMAT if pg_tools_available() else SQL_FORMAT


def _sniff_gzip_member(head: bytes, want: int) -> bytes:
    """Decompress as much as ``head`` (a prefix of a gzip stream) yields.

    A partial gzip member has no valid end-of-stream marker, so a plain
    ``decompress()`` raises; ``decompressobj`` tolerates that and just hands
    back whatever bytes it managed to inflate before running out of input.
    """
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        return decompressor.decompress(head, want)
    except zlib.error:
        return b""


def detect_format(head: bytes) -> str:
    """Classify a dump archive by the first bytes of its *decompressed* content."""
    decompressed = _sniff_gzip_member(head, len(_CUSTOM_MAGIC))
    return CUSTOM_FORMAT if decompressed.startswith(_CUSTOM_MAGIC) else SQL_FORMAT


def is_gzip(head: bytes) -> bool:
    return head.startswith(_GZIP_MAGIC)


def backup_dir() -> Path:
    directory = Path(get_settings().database_backup_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def build_filename(fmt: str, *, prefix: str = "biologic") -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    suffix = "dump" if fmt == CUSTOM_FORMAT else "sql"
    return f"{prefix}-{stamp}.{suffix}.gz"


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
    """Write a pg_dump custom archive, then gzip it in place at ``path``.

    pg_dump has no "compress to this exact file" option that also lets us
    pick the container format, so it writes an uncompressed archive to a
    sibling temp file first — that temp file is what carries progress while
    the dump runs (see the router's progress poller), not ``path`` itself.
    """
    url = _database_url()
    tmp = path.with_name(path.name + ".tmp")
    try:
        _run(
            [
                _tool_path("pg_dump"),
                "--format=custom",
                "--no-owner",
                "--no-acl",
                "--exclude-table=public.database_backups",
                *_connection_args(url),
                "--file",
                str(tmp),
            ]
        )
        with tmp.open("rb") as source, gzip.open(path, "wb") as dest:
            shutil.copyfileobj(source, dest)
    finally:
        tmp.unlink(missing_ok=True)


def _custom_restore(path: Path) -> None:
    url = _database_url()
    with path.open("rb") as source:
        compressed = is_gzip(source.read(len(_GZIP_MAGIC)))
    restore_path = path
    tmp: Path | None = None
    if compressed:
        tmp = path.with_name(path.name + ".tmp")
        with gzip.open(path, "rb") as source, tmp.open("wb") as dest:
            shutil.copyfileobj(source, dest)
        restore_path = tmp
    try:
        _run(
            [
                _tool_path("pg_restore"),
                "--clean",
                "--if-exists",
                "--no-owner",
                "--exit-on-error",
                "--single-transaction",
                *_connection_args(url),
                str(restore_path),
            ],
            lock_timeout=_lock_timeout(),
        )
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


# --- Schema introspection (SQL engine) ---------------------------------------
#
# No pg_dump binary here, so DDL is reconstructed from the catalog using
# Postgres's own pg_get_*def() functions — the same building blocks pg_dump
# itself uses internally, rather than hand-assembling CREATE TABLE from
# information_schema. Every statement is written idempotently so the script
# is safe to replay against a database that already has this exact schema.


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


async def _schema_extensions(conn: asyncpg.Connection) -> list[str]:
    rows = await conn.fetch("SELECT extname FROM pg_extension WHERE extname <> 'plpgsql'")
    return [f"CREATE EXTENSION IF NOT EXISTS {_quote_ident(row['extname'])};" for row in rows]


async def _schema_enums(conn: asyncpg.Connection) -> list[str]:
    rows = await conn.fetch(
        """
        SELECT t.typname, array_agg(e.enumlabel ORDER BY e.enumsortorder) AS labels
        FROM pg_type t
        JOIN pg_enum e ON e.enumtypid = t.oid
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'public'
        GROUP BY t.typname
        ORDER BY t.typname
        """
    )
    statements = []
    for row in rows:
        labels = ", ".join(_quote_literal(label) for label in row["labels"])
        name = _quote_ident(row["typname"])
        statements.append(
            f"DO $ddl$ BEGIN\n"
            f"  CREATE TYPE {name} AS ENUM ({labels});\n"
            f"EXCEPTION WHEN duplicate_object THEN NULL;\n"
            f"END $ddl$;"
        )
    return statements


async def _schema_functions(conn: asyncpg.Connection) -> list[str]:
    rows = await conn.fetch(
        """
        SELECT pg_get_functiondef(p.oid) AS def
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND NOT EXISTS (
            SELECT 1 FROM pg_depend d WHERE d.objid = p.oid AND d.deptype = 'e'
          )
        ORDER BY p.proname
        """
    )
    # pg_get_functiondef() always renders "CREATE OR REPLACE FUNCTION ..." —
    # idempotent by construction, no extra wrapping needed.
    return [f"{row['def']};" for row in rows]


async def _schema_sequences(conn: asyncpg.Connection) -> list[str]:
    """Sequences not auto-created by an identity column's own DDL."""
    rows = await conn.fetch(
        """
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'S' AND n.nspname = 'public'
          AND c.relname NOT IN (SELECT unnest($1::text[]))
          AND NOT EXISTS (
            SELECT 1 FROM pg_depend d WHERE d.objid = c.oid AND d.deptype = 'i'
          )
        ORDER BY c.relname
        """,
        list(EXCLUDED_TABLES),
    )
    return [f"CREATE SEQUENCE IF NOT EXISTS {_quote_ident(row['relname'])};" for row in rows]


async def _schema_tables(conn: asyncpg.Connection) -> list[str]:
    tables = await conn.fetch(
        """
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'r' AND n.nspname = 'public'
          AND c.relname NOT IN (SELECT unnest($1::text[]))
        ORDER BY c.relname
        """,
        list(EXCLUDED_TABLES),
    )
    statements = []
    for table_row in tables:
        table = table_row["relname"]
        columns = await conn.fetch(
            """
            SELECT a.attname,
                   format_type(a.atttypid, a.atttypmod) AS data_type,
                   a.attnotnull,
                   a.attidentity,
                   pg_get_expr(ad.adbin, ad.adrelid) AS default_expr
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_attrdef ad ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
            WHERE n.nspname = 'public' AND c.relname = $1
              AND a.attnum > 0 AND NOT a.attisdropped
            ORDER BY a.attnum
            """,
            table,
        )
        column_lines = []
        for col in columns:
            line = f"{_quote_ident(col['attname'])} {col['data_type']}"
            if col["attidentity"] == "a":
                line += " GENERATED ALWAYS AS IDENTITY"
            elif col["attidentity"] == "d":
                line += " GENERATED BY DEFAULT AS IDENTITY"
            elif col["default_expr"] is not None:
                line += f" DEFAULT {col['default_expr']}"
            if col["attnotnull"]:
                line += " NOT NULL"
            column_lines.append(line)

        constraints = await conn.fetch(
            """
            SELECT pg_get_constraintdef(con.oid) AS def
            FROM pg_constraint con
            JOIN pg_class c ON c.oid = con.conrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relname = $1 AND con.contype IN ('p', 'u', 'c')
            ORDER BY con.contype, con.conname
            """,
            table,
        )
        for con in constraints:
            column_lines.append(con["def"])

        body = ",\n  ".join(column_lines)
        statements.append(f"CREATE TABLE IF NOT EXISTS {_quote_ident(table)} (\n  {body}\n);")
    return statements


async def _schema_foreign_keys(conn: asyncpg.Connection) -> list[str]:
    rows = await conn.fetch(
        """
        SELECT c.relname AS table_name, con.conname, pg_get_constraintdef(con.oid) AS def
        FROM pg_constraint con
        JOIN pg_class c ON c.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND con.contype = 'f'
          AND c.relname NOT IN (SELECT unnest($1::text[]))
        ORDER BY c.relname, con.conname
        """,
        list(EXCLUDED_TABLES),
    )
    statements = []
    for row in rows:
        table = _quote_ident(row["table_name"])
        name = _quote_ident(row["conname"])
        statements.append(
            f"DO $ddl$ BEGIN\n"
            f"  ALTER TABLE {table} ADD CONSTRAINT {name} {row['def']};\n"
            f"EXCEPTION WHEN duplicate_object THEN NULL;\n"
            f"END $ddl$;"
        )
    return statements


async def _schema_indexes(conn: asyncpg.Connection) -> list[str]:
    """Plain indexes — those backing a PK/UNIQUE constraint are already covered."""
    rows = await conn.fetch(
        """
        SELECT c.relname AS index_name, pg_get_indexdef(c.oid) AS def
        FROM pg_index i
        JOIN pg_class c ON c.oid = i.indexrelid
        JOIN pg_class t ON t.oid = i.indrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND t.relname NOT IN (SELECT unnest($1::text[]))
          AND NOT EXISTS (SELECT 1 FROM pg_constraint con WHERE con.conindid = c.oid)
        ORDER BY c.relname
        """,
        list(EXCLUDED_TABLES),
    )
    statements = []
    for row in rows:
        # pg_get_indexdef() renders "CREATE [UNIQUE] INDEX name ON ..." — the
        # single " INDEX " token appears exactly once, right before the name.
        statements.append(f"{row['def'].replace(' INDEX ', ' INDEX IF NOT EXISTS ', 1)};")
    return statements


async def _schema_views(conn: asyncpg.Connection) -> tuple[list[str], list[str]]:
    """Regular + materialized views. Returns (ddl statements, matview names).

    Materialized views are created ``WITH NO DATA``: the tables they select
    from are still empty at this point in the dump (schema is written before
    data), so populating them now would just capture zero rows. The caller
    refreshes them once the data section has run.
    """
    rows = await conn.fetch(
        """
        SELECT c.relname, c.relkind, pg_get_viewdef(c.oid, true) AS def
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('v', 'm')
        ORDER BY c.relkind, c.relname
        """
    )
    statements = []
    matviews = []
    for row in rows:
        name = _quote_ident(row["relname"])
        body = row["def"].rstrip().removesuffix(";")
        if row["relkind"] == "v":
            statements.append(f"CREATE OR REPLACE VIEW {name} AS\n{body};")
        else:
            matviews.append(row["relname"])
            statements.append(
                f"CREATE MATERIALIZED VIEW IF NOT EXISTS {name} AS\n{body}\nWITH NO DATA;"
            )
    return statements, matviews


async def _schema_triggers(conn: asyncpg.Connection) -> list[str]:
    rows = await conn.fetch(
        """
        SELECT c.relname AS table_name, t.tgname, pg_get_triggerdef(t.oid) AS def
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE NOT t.tgisinternal AND n.nspname = 'public'
          AND c.relname NOT IN (SELECT unnest($1::text[]))
        ORDER BY c.relname, t.tgname
        """,
        list(EXCLUDED_TABLES),
    )
    statements = []
    for row in rows:
        table = _quote_ident(row["table_name"])
        name = _quote_ident(row["tgname"])
        statements.append(f"DROP TRIGGER IF EXISTS {name} ON {table};\n{row['def']};")
    return statements


async def _write_schema(conn: asyncpg.Connection, out: Any) -> list[str]:
    """Write full schema DDL to ``out``; return matview names still to refresh."""
    view_statements, matviews = await _schema_views(conn)
    sections = [
        ("Extensions", await _schema_extensions(conn)),
        ("Enum types", await _schema_enums(conn)),
        ("Functions", await _schema_functions(conn)),
        ("Sequences", await _schema_sequences(conn)),
        ("Tables", await _schema_tables(conn)),
        ("Foreign keys", await _schema_foreign_keys(conn)),
        # Views (including matviews) must exist before indexes that target them.
        ("Views", view_statements),
        ("Indexes", await _schema_indexes(conn)),
        ("Triggers", await _schema_triggers(conn)),
    ]

    for title, statements in sections:
        if not statements:
            continue
        out.write(f"-- {title}\n")
        for statement in statements:
            out.write(statement)
            out.write("\n")
        out.write("\n")
    return matviews


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
        with gzip.open(path, "wt", encoding="utf-8") as out:
            out.write("-- Biologic full dump: schema (idempotent DDL) + data.\n")
            out.write("-- Safe to run against an empty database or an already-migrated one.\n\n")
            matviews = await _write_schema(conn, out)

            tables = await _data_tables(conn)
            out.write("-- Data\n")
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

            if matviews:
                out.write("\n-- Materialized views were created empty; populate them now.\n")
                for name in matviews:
                    out.write(f"REFRESH MATERIALIZED VIEW {_quote_ident(name)};\n")
    except asyncpg.PostgresError as exc:
        raise DatabaseTransferError(str(exc)) from exc
    finally:
        await conn.close()


def _read_text_maybe_gzip(path: Path) -> str:
    with path.open("rb") as source:
        compressed = is_gzip(source.read(len(_GZIP_MAGIC)))
    if compressed:
        with gzip.open(path, "rt", encoding="utf-8") as source:
            return source.read()
    return path.read_text(encoding="utf-8")


async def _sql_restore(path: Path) -> None:
    script = await asyncio.to_thread(_read_text_maybe_gzip, path)
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


async def _custom_restore_with_excluded_dependants_handled(path: Path) -> None:
    """Run ``_custom_restore``, working around pg_restore's own ``--clean`` bug.

    ``database_backups`` is excluded from every dump (see ``EXCLUDED_TABLES``),
    but its ``id`` column still defaults to ``uuidv7()`` in the *live* target
    database. pg_restore's ``--clean`` phase always does a plain
    ``DROP FUNCTION IF EXISTS public.uuidv7()`` (no ``CASCADE``) before
    recreating it — which fails outright, because the dump has no idea that
    row default outside its own tables exists. Dropping that one default
    first and restoring it after is cheaper and safer than teaching pg_dump's
    --clean about a table it was never supposed to know about.
    """
    conn = await asyncpg.connect(_dsn())
    try:
        await conn.execute(
            'ALTER TABLE IF EXISTS "database_backups" ALTER COLUMN "id" DROP DEFAULT'
        )
    except asyncpg.PostgresError as exc:
        raise DatabaseTransferError(str(exc)) from exc
    finally:
        await conn.close()

    try:
        await asyncio.to_thread(_custom_restore, path)
    finally:
        conn = await asyncpg.connect(_dsn())
        try:
            await conn.execute(
                'ALTER TABLE IF EXISTS "database_backups" '
                'ALTER COLUMN "id" SET DEFAULT uuidv7()'
            )
        except asyncpg.PostgresError:
            pass  # The restore's own error already takes priority if it failed too.
        finally:
            await conn.close()


async def restore_dump(path: Path, fmt: str) -> None:
    """Restore ``path`` into the configured database."""
    if not path.exists():
        raise DatabaseTransferError("Dump file is missing on the server filesystem.")
    if fmt == CUSTOM_FORMAT:
        if not pg_tools_available():
            raise DatabaseTransferError(
                "This dump needs pg_restore, which is not installed on the server."
            )
        await _custom_restore_with_excluded_dependants_handled(path)
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
