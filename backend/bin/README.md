# Bundled PostgreSQL client tools

`pg_dump`/`pg_restore` for the `custom` database-export engine
(`src/application/data_transfer.py`), checked in so a restore/export works
without asking an operator to install PostgreSQL client tools system-wide —
useful for the offline Windows deploy case in particular.

Both builds are PostgreSQL **15.13/15.14**, matching the `postgres:15-alpine`
server in `docker-compose.yaml`. Keep them on the same major version as the
server: a newer client can emit session-setup SQL (e.g. `transaction_timeout`,
added in PG17) that an older server rejects on restore.

## Layout

```
linux-x64/
  pg_dump, pg_restore     # x86_64 glibc build; needs libssl/libcrypto/libz/
                           # libgssapi_krb5 from the host (present on any
                           # modern glibc distro) plus the bundled libpq.
  lib/libpq.so.5           # loaded via LD_LIBRARY_PATH, set by _pg_env()
                           # in data_transfer.py — not baked into RPATH.
windows-x64/
  pg_dump.exe, pg_restore.exe, and every DLL they load transitively
  (libpq, libssl-3-x64, libcrypto-3-x64, libintl-9, libiconv-2,
  libwinpthread-1, zlib1) — everything else they import is a standard
  Windows system DLL, not bundled.
```

`src/application/data_transfer.py`'s `_bundled_tool()` resolves the right
binary for the running platform; both `pg_tools_available()` and the actual
`pg_dump`/`pg_restore` invocations go through it. Unsupported platforms
(arm64 Mac, aarch64 Linux, ...) fall back to whatever `pg_dump`/`pg_restore`
are on `PATH`, and if neither is found the `sql` engine (pure-Python,
asyncpg-based) takes over instead — see the module docstring.

## Provenance

- `linux-x64/` — `postgresql-15.13.0-x86_64-unknown-linux-gnu.tar.gz` from
  https://github.com/theseus-rs/postgresql-binaries (Apache-2.0 build
  tooling; PostgreSQL itself is under the PostgreSQL License).
- `windows-x64/` — extracted from EDB's official Windows binaries zip,
  `postgresql-15.14-1-windows-x64-binaries.zip` at
  https://www.enterprisedb.com/download-postgresql-binaries.

## Updating

Get a build for the *same* PostgreSQL major version as the server. Linux: a
`postgresql-<version>-x86_64-unknown-linux-gnu.tar.gz` release from
theseus-rs/postgresql-binaries — copy `bin/pg_dump`, `bin/pg_restore`, and
`lib/libpq.so.5.*` (rename the copy to plain `libpq.so.5`). Windows: EDB's
`postgresql-<version>-...-windows-x64-binaries.zip` — copy `pg_dump.exe`,
`pg_restore.exe`, and their DLL dependencies (check with `objdump -p
pg_dump.exe pg_restore.exe | grep 'DLL Name'`, recursively, since one of
those DLLs — currently `libpq.dll` — pulls in a few more of its own).
