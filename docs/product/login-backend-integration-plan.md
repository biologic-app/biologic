---
created: 2026-06-27
tags:
  - biologic
  - auth
  - plan
---

# План: привязка login-страницы и переключателя ролей к реальному бэкенду

> Цель: страница `/login` логинится через настоящий бэкенд (JWT в cookie),
> бэкенд отдаёт `resource.action.scope` для роли пользователя, фронтенд по этим
> правам меняет отображение UI (`can()`), виджет переключения ролей логинится
> под захардкоженными учётками, `logout` корректно чистит сессию.
> **Разграничение прав НА БЭКЕНДЕ не вводим** — бэкенд только аутентифицирует и
> возвращает права; фильтрация UI остаётся на фронтенде.

Инструкция написана пошагово, с готовыми блоками кода. Можно выполнять «сверху
вниз». Каждый шаг помечен файлом и действием.

---

## 0. Что уже есть и чего не хватает (контекст)

**Бэкенд (`/home/tminww/Projects/bio/backend`, FastAPI + DDD + единый UoW):**

- ❌ **Нет ни одного `/auth/*` эндпоинта.** Сейчас «актор» приходит заголовком
  `X-Actor-Id` (`src/presentation/http/access_control/dependencies.py::get_actor_id`).
- ✅ JWT-примитивы готовы, но **нигде не вызываются**: `src/core/security.py`
  (`hash_password`, `verify_password`, `encode_jwt_token`, `decode_jwt_token`,
  `token_subject`, `cookie_secure_flag`, `token_ttl_seconds`).
- ✅ Все настройки cookie/JWT есть в `src/core/config.py` (`Settings`).
- ✅ Сид-пользователи и bcrypt-хэши уже в БД (миграция
  `migrations/versions/20260303_0009_seed_initial_rbac_users.py`) — логины/пароли
  совпадают с `docs/role-access-matrix.md`.
- ✅ Роли (`admin/registrar/sanitary_inspector/lab_doctor/lab_assistant/lab_chief/
  branch_chief/developer`), права `(resource, action)` и связка `role_permissions`
  с колонкой `scope` (enum `access_scope_type`,
  `own|own_lab|all_labs|own_branch|all_branches|all`, DEFAULT `'all'`) уже
  заведены. **Сейчас у ВСЕХ строк `role_permissions.scope = 'all'`** — это и есть
  то, что надо проставить по матрице.
- ✅ Эндпоинт `GET /api/v1/user/me/permissions` уже отдаёт
  `{data:{permissions:[{id,resource,action,scope}]}}` по `X-Actor-Id`.

**Фронтенд (`/home/tminww/Projects/bio/frontend`, Vue 3 + Pinia):**

- ✅ `src/modules/auth/auth.api.ts` **уже** дёргает `/auth/login`, `/auth/logout`,
  `/auth/me` — но этих эндпоинтов на бэкенде нет (поэтому реальный логин не
  работает). Клиент шлёт cookie (`credentials: 'include'` в `client.api.ts`).
- ✅ `src/modules/auth/composables/useAuth.ts`: `can()` уже использует
  `effectivePermissions` — **если `permissions.length > 0`, берутся права с
  бэкенда**, иначе фронтовый пресет режима. То есть как только бэкенд начнёт
  отдавать права при логине, UI поедет от них автоматически.
- ⚠️ Виджет переключения ролей (`src/shared/ui/UserMenu.vue` → `auth.setMode`)
  **только меняет localStorage-пресет и только в DEV**, на бэкенд не ходит.
- ⚠️ `logout` чистит сессию, но **не редиректит** на `/login`; `onUnauthorized`
  (`src/app/index.ts`) тоже только чистит сессию.
- ⚠️ **Несовпадение словаря:** бэкенд называет сущность «исследование» ресурсом
  `results`, а фронтенд-навигация и пресеты — ресурсом `research`. `mapResource`
  в `auth.api.ts` НЕ переводит `results → research`, поэтому пункт меню
  «Исследования» (`research:view`) после реального логина пропадёт у всех. Чиним
  в шаге 2.1.

**Вывод:** бэкенду нужно добавить `/auth/login|logout|me` + проставить scope по
матрице; фронтенду — почти ничего, кроме правки словаря, виджета и редиректов.

---

## ЧАСТЬ A. БЭКЕНД

Рабочая папка: `/home/tminww/Projects/bio/backend`.

### A.1. Настройки `.env` (TTL и cookie)

Файл `.env` в корне `backend/` (скопировать из `.env.example`, если нет).
В `Settings` сейчас стоят отладочные TTL `access_token_ttl_seconds=40`,
`refresh_token_ttl_seconds=60` — для реального логина их надо поднять и задать
обязательные cookie-поля (`auth_cookie_secure`, `auth_cookie_domain` не имеют
значений по умолчанию).

Добавить/проверить строки (`APP_`-префикс обязателен):

```dotenv
APP_JWT_SECRET_KEY=dev-secret-change-me
APP_ACCESS_TOKEN_TTL_SECONDS=3600
APP_REFRESH_TOKEN_TTL_SECONDS=1209600
APP_AUTH_COOKIE_SAMESITE=lax
APP_AUTH_COOKIE_SECURE=false
APP_AUTH_COOKIE_DOMAIN=
APP_AUTH_COOKIE_PATH=/
```

> Для локалки `localhost:5173 → localhost:8080` — это «тот же сайт» (site = домен
> без учёта порта), поэтому `SameSite=lax` + `Secure=false` работают. Для прод
> (`bio.tminww.space`) выставить `APP_AUTH_COOKIE_SECURE=true` и при необходимости
> `APP_AUTH_COOKIE_DOMAIN`.

### A.2. Поиск пользователя по username — репозиторий + порт

**Файл `src/infrastructure/repositories/access_control.py`** — в класс
`UserRepository` (после метода `delete`, ~строка 63) добавить:

```python
    async def get_by_username(self, username: str) -> Any | None:
        result = await self.session.execute(
            select(User).where(
                User.username == username,
                User.deleted_at.is_(None),
            ),
        )
        return result.scalar_one_or_none()
```

(`select` и `User` уже импортированы в этом файле.)

**Файл `src/application/access_control/ports.py`** — добавить новый порт после
`AccessControlCrudRepository` (≈строка 23):

```python
class UserAuthRepository(AccessControlCrudRepository, Protocol):
    async def get_by_username(self, username: str) -> Any | None: ...
```

**Файл `src/domain/uow.py`** — поменять аннотацию `users` и импорт:

```python
# в импортах из src.application.access_control.ports добавить UserAuthRepository
from src.application.access_control.ports import (
    AccessControlCrudRepository,
    RolePermissionRepositoryPort,
    UserAuthRepository,
    UserPermissionOverrideRepositoryPort,
)
# ...
    # было: users: AccessControlCrudRepository
    users: UserAuthRepository
```

**Файл `src/infrastructure/uow.py`** — поменять аннотацию атрибута `users`
(≈строка 75) на `UserAuthRepository` и добавить его в импорт из
`src.application.access_control.ports`:

```python
from src.application.access_control.ports import (
    AccessControlCrudRepository,
    RolePermissionRepositoryPort,
    UserAuthRepository,
    UserPermissionOverrideRepositoryPort,
)
# ...
    users: UserAuthRepository  # было AccessControlCrudRepository
```

(Конкретный `UserRepository` уже реализует `list/read/create/update/delete` +
теперь `get_by_username`, значит структурно подходит под новый протокол.)

### A.3. Use case аутентификации

**Новый файл `src/application/access_control/use_cases/auth.py`:**

```python
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.access_control.use_cases._shared import (
    permission_sort_key,
    serialize_permission,
)
from src.core.errors import UnauthorizedError
from src.core.security import verify_password
from src.domain.uow import UnitOfWorkFactory


@dataclass(frozen=True)
class AuthSession:
    """Данные сессии, из которых роутер собирает ответ и токены."""

    user_id: UUID
    username: str
    role_key: str
    role_name: str
    first_name: str | None
    last_name: str | None
    patronymic: str | None
    refresh_token_version: int
    permissions: list[dict[str, object]]


class AuthUseCase:
    """Аутентификация по логину/паролю и сборка сессии по id."""

    def __init__(self, *, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def authenticate(self, username: str, password: str) -> AuthSession:
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_username(username)
            if user is None or not verify_password(password, user.password_hash):
                raise UnauthorizedError("Invalid username or password.")
            return await self._build_session(uow, user)

    async def session_for_user(self, user_id: UUID) -> AuthSession:
        async with self._uow_factory() as uow:
            user = await uow.users.read(user_id)  # NotFoundError если нет
            return await self._build_session(uow, user)

    async def _build_session(self, uow, user) -> AuthSession:
        role = await uow.roles.read(user.role_id)
        role_rows = await uow.role_permissions.list_for_role(user.role_id)
        override_rows = await uow.user_permission_overrides.list_for_user(user.id)

        effective: dict[object, dict[str, object]] = {
            permission.id: serialize_permission(permission, role_permission.scope)
            for role_permission, permission in role_rows
        }
        for override, permission in override_rows:
            if override.allowed:
                effective[permission.id] = serialize_permission(permission, override.scope)
            else:
                effective.pop(permission.id, None)

        return AuthSession(
            user_id=user.id,
            username=user.username,
            role_key=role.key,
            role_name=role.name,
            first_name=user.first_name,
            last_name=user.last_name,
            patronymic=user.patronymic,
            refresh_token_version=user.refresh_token_version,
            permissions=sorted(effective.values(), key=permission_sort_key),
        )
```

> Логика прав 1-в-1 повторяет существующий
> `UserPermissionSetUseCase.read_effective`, чтобы `/auth/*` и
> `/user/me/permissions` отдавали одинаковый набор.

### A.4. Pydantic-схема запроса логина

**Новый файл `src/presentation/http/access_control/auth_schemas.py`:**

```python
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
```

### A.5. Зависимость «текущий пользователь из cookie»

**Файл `src/presentation/http/access_control/dependencies.py`** — добавить
импорты и функции. Полный набор импортов сверху файла:

```python
from uuid import UUID

from fastapi import Header, Request

from src.application.access_control.use_cases.auth import AuthUseCase
from src.core.config import get_settings
from src.core.errors import UnauthorizedError
from src.core.security import decode_jwt_token, token_subject
from src.infrastructure.uow import build_uow_factory
# (остальные существующие импорты use case'ов оставить как есть)
```

Добавить в конец файла:

```python
async def get_auth_use_case() -> AuthUseCase:
    return AuthUseCase(uow_factory=build_uow_factory())


async def get_current_user_id(request: Request) -> UUID:
    settings = get_settings()
    token = request.cookies.get(settings.access_cookie_name)
    if not token:
        raise UnauthorizedError("Missing access token.")
    try:
        payload = decode_jwt_token(
            token,
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            expected_type="access",
        )
        return token_subject(payload)
    except Exception as exc:  # noqa: BLE001 — любой сбой декодирования = 401
        raise UnauthorizedError("Invalid or expired access token.") from exc
```

### A.6. Роутер `/auth`

**Новый файл `src/presentation/http/access_control/auth_router.py`:**

```python
from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from src.application.access_control.use_cases.auth import AuthSession, AuthUseCase
from src.core.config import Settings, get_settings
from src.core.responses import ResponseMeta, SingleResponse
from src.core.security import (
    cookie_secure_flag,
    encode_jwt_token,
    token_ttl_seconds,
)
from src.presentation.http.access_control.auth_schemas import LoginRequest
from src.presentation.http.access_control.dependencies import (
    get_auth_use_case,
    get_current_user_id,
)

router = APIRouter(tags=["auth"])

AuthUC = Annotated[AuthUseCase, Depends(get_auth_use_case)]


def _set_auth_cookies(response: Response, session: AuthSession, settings: Settings):
    access_delta = timedelta(seconds=settings.access_token_ttl_seconds)
    refresh_delta = timedelta(seconds=settings.refresh_token_ttl_seconds)

    access_token, access_exp = encode_jwt_token(
        subject=session.user_id,
        token_type="access",
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=access_delta,
    )
    refresh_token, refresh_exp = encode_jwt_token(
        subject=session.user_id,
        token_type="refresh",
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=refresh_delta,
        additional_claims={"rv": session.refresh_token_version},
    )

    common = {
        "httponly": True,
        "samesite": settings.auth_cookie_samesite,
        "secure": cookie_secure_flag(settings),
        "domain": settings.auth_cookie_domain or None,
        "path": settings.auth_cookie_path,
    }
    response.set_cookie(
        key=settings.access_cookie_name,
        value=access_token,
        max_age=token_ttl_seconds(access_delta),
        **common,
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        max_age=token_ttl_seconds(refresh_delta),
        **common,
    )
    return access_exp, refresh_exp


def _session_envelope(session: AuthSession, access_exp, refresh_exp, operation: str):
    return SingleResponse(
        data={
            "user": {
                "id": str(session.user_id),
                "username": session.username,
                "role_key": session.role_key,
                "role_name": session.role_name,
                "first_name": session.first_name,
                "last_name": session.last_name,
                "patronymic": session.patronymic,
            },
            "permissions": session.permissions,
            "access_expires_at": access_exp.isoformat(),
            "refresh_expires_at": refresh_exp.isoformat() if refresh_exp else None,
        },
        meta=ResponseMeta(operation=operation),
    )


@router.post("/auth/login")
async def login(payload: LoginRequest, response: Response, use_case: AuthUC):
    settings = get_settings()
    session = await use_case.authenticate(payload.username, payload.password)
    access_exp, refresh_exp = _set_auth_cookies(response, session, settings)
    return _session_envelope(session, access_exp, refresh_exp, "auth.login")


@router.get("/auth/me")
async def me(
    response: Response,
    use_case: AuthUC,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    settings = get_settings()
    session = await use_case.session_for_user(user_id)
    access_exp, refresh_exp = _set_auth_cookies(response, session, settings)
    return _session_envelope(session, access_exp, refresh_exp, "auth.me")


@router.post("/auth/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response):
    settings = get_settings()
    for name in (settings.access_cookie_name, settings.refresh_cookie_name):
        response.delete_cookie(
            key=name,
            domain=settings.auth_cookie_domain or None,
            path=settings.auth_cookie_path,
        )
    return SingleResponse(data={"ok": True}, meta=ResponseMeta(operation="auth.logout"))
```

> `/auth/me` заодно продлевает cookie (sliding session) — не обязательно, но
> удобно при коротком TTL.

### A.7. Подключить роутер

**Файл `src/api/v1/router.py`** — добавить импорт и `include_router`:

```python
from src.presentation.http.access_control.auth_router import router as auth_router
# ...
router.include_router(auth_router)
```

После этого появятся `POST /api/v1/auth/login`, `GET /api/v1/auth/me`,
`POST /api/v1/auth/logout`.

### A.8. Миграция: проставить `scope` по матрице ролей

Сейчас все `role_permissions.scope = 'all'`. Привязываем scope к роли по её
`scope_type` (это и есть «resource.action.scope для каждой роли»). Соответствие
enum'ов `role_scope_type → access_scope_type`:

| Роль (`scope_type`)            | `access_scope_type` |
| ------------------------------ | ------------------- |
| `global` (admin, developer)    | `all`               |
| `own_branch` (registrar, branch_chief) | `own_branch` |
| `own_lab` (lab_doctor/assistant/chief) | `own_lab`    |
| `own_objects` (sanitary_inspector)     | `own`        |

**Новый файл `migrations/versions/20260627_0015_role_permission_scopes.py`:**

```python
"""bind role_permission scopes to role scope_type

Revision ID: 20260627_0015
Revises: 20260608_0014
Create Date: 2026-06-27 00:00:00.000000
"""

from alembic import op

revision = "20260627_0015"
down_revision = "20260608_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE role_permissions rp
        SET scope = CASE r.scope_type
            WHEN 'global'      THEN 'all'::access_scope_type
            WHEN 'own_branch'  THEN 'own_branch'::access_scope_type
            WHEN 'own_lab'     THEN 'own_lab'::access_scope_type
            WHEN 'own_objects' THEN 'own'::access_scope_type
            ELSE 'all'::access_scope_type
        END
        FROM roles r
        WHERE rp.role_id = r.id;
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE role_permissions
        SET scope = 'all'::access_scope_type;
    """)
```

> ⚠️ Проверь, что `down_revision` указывает на **последнюю** существующую
> ревизию. На момент написания последняя — `20260608_0014_enable_pg_trgm`.
> Если появились новые — поправь `down_revision`.

> Замечание: фронтовый `can()` сейчас scope игнорирует (проверяет только
> resource+action). Поэтому эти scope — информационные «на вырост». При желании
> можно позже уточнить scope по сноскам матрицы (`$^1..$^7$`), но для текущей
> задачи достаточно уровня роли.

### A.9. Применить миграцию и поднять сервер

```bash
cd /home/tminww/Projects/bio/backend
uv run alembic upgrade head
make dev   # uvicorn на :8080
```

Проверка curl (cookie сохраняем в файл):

```bash
# логин
curl -i -c /tmp/bio.cookies -X POST http://localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"doctor","password":"doctor123"}'
# должно прийти 200 + data.user.role_key=="lab_doctor" + Set-Cookie: access_cookie/refresh_cookie

# me по cookie
curl -i -b /tmp/bio.cookies http://localhost:8080/api/v1/auth/me
# 200 + тот же user + permissions

# logout
curl -i -b /tmp/bio.cookies -X POST http://localhost:8080/api/v1/auth/logout
# 200 + Set-Cookie с истёкшим сроком

# неверный пароль
curl -i -X POST http://localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' -d '{"username":"doctor","password":"x"}'
# 401
```

---

## ЧАСТЬ B. ФРОНТЕНД

Рабочая папка: `/home/tminww/Projects/bio/frontend`.

### B.1. Починить словарь `results → research` (КРИТично для меню)

**Файл `src/modules/auth/auth.api.ts`**, функция `mapResource` (≈строка 54).
Бэкенд отдаёт ресурс `results`, а навигация/пресеты используют `research`.
Добавить перевод. Заменить тело `const mapped = ... ` так, чтобы был ещё кейс:

```ts
const mapResource = (resource: string): Resource | null => {
  const normalized = resource.trim().toLowerCase().replace(/_/g, "-");
  const mapped =
    normalized === "roles" || normalized === "role-permissions"
      ? "user-types"
      : normalized === "results"
        ? "research"
      : normalized === "direction-statuses" ||
          normalized === "sample-statuses" ||
          normalized === "research-statuses" ||
          normalized === "test-statuses" ||
          normalized === "conclusion-statuses"
        ? "statuses"
      : normalized;
  return knownResources.includes(mapped as Resource)
    ? (mapped as Resource)
    : null;
};
```

(Заодно добавлен `conclusion-statuses → statuses`, иначе он отбрасывается.)

Проверь `mapAction` (≈строка 70): бэкенд-действия исследований — `confirm`,
`start`, `reject`, `read`. `read→view` уже есть; `confirm/start/reject` проходят
как есть и присутствуют в `commandActions`. Менять не нужно.

### B.2. Карта учёток для виджета ролей

**Новый файл `src/shared/config/role-credentials.ts`:**

```ts
import type { UserModeId } from "@/shared/config/user-modes";

/**
 * Захардкоженные демо-учётки (см. docs/role-access-matrix.md и сид-миграцию
 * бэкенда 20260303_0009). Используются виджетом переключения ролей, чтобы
 * залогиниться под нужной ролью в обход страницы /login.
 */
export const roleCredentials: Record<UserModeId, { username: string; password: string }> = {
  developer:          { username: "tminww",       password: "tminww123" },
  user_admin:         { username: "admin",         password: "admin123" },
  registrar:          { username: "registrator",   password: "registrator123" },
  sanitary_inspector: { username: "sandoctor",     password: "sandoctor123" },
  lab_doctor:         { username: "doctor",        password: "doctor123" },
  lab_assistant:      { username: "laborant",      password: "laborant123" },
  lab_chief:          { username: "nachlab",       password: "nachlab123" },
  branch_chief:       { username: "nachfil",       password: "nachfil123" },
};
```

### B.3. `useAuth`: добавить `loginAs`, редирект при logout, обновить комментарий

**Файл `src/modules/auth/composables/useAuth.ts`.**

(a) Импортировать карту учёток и роутер (вверху файла):

```ts
import { roleCredentials } from "@/shared/config/role-credentials";
import { router } from "@/app/router";
```

(b) Обновить устаревший комментарий у `permissions` (строки 19–21) — теперь
права с бэкенда используются в `can()`:

```ts
  // Права роли с бэкенда (наполняются при логине/restoreSession).
  // Источник истины для can(): если массив непустой — берём его, иначе
  // фронтовый пресет активного режима (см. effectivePermissions ниже).
  const permissions = useStorage<Permission[]>("auth:permissions", []);
```

(c) Добавить экшен `loginAs` (после `login`, ≈строка 64):

```ts
  /** Логин под захардкоженной учёткой роли (для виджета переключения ролей). */
  const loginAs = async (modeId: UserModeId) => {
    const creds = roleCredentials[modeId];
    if (!creds) return;
    if (isUserModeId(modeId)) {
      activeModeId.value = modeId; // для подсветки активного пункта в меню
    }
    await login(creds.username, creds.password);
  };
```

(d) В `logout` (≈строка 66) после `clearSession()` добавить редирект на login:

```ts
  const logout = async () => {
    loading.value = true;
    try {
      await authApi.logout();
    } finally {
      clearSession();
      loading.value = false;
      await router.push({ name: "login" });
    }
  };
```

(e) В `return { ... }` добавить `loginAs`:

```ts
    login,
    loginAs,
    logout,
```

> `setMode` оставляем как есть (обратная совместимость); виджет переедет на
> `loginAs`.

### B.4. Виджет переключения ролей → реальный логин

**Файл `src/shared/ui/UserMenu.vue`.** В блоке пункта меню «mode» (≈строки
196–213) заменить `onSelect` так, чтобы он логинился под ролью:

```ts
    {
      label: t("userMenu.mode"),
      icon: "i-lucide-user-cog",
      children: userModeList.map((mode) => ({
        label: t(mode.labelKey),
        icon: mode.icon,
        type: "checkbox",
        checked: auth.activeModeId === mode.id,
        async onSelect(e: Event) {
          e.preventDefault();
          try {
            await auth.loginAs(mode.id);
            toast.add({
              title: t("modes.changed"),
              description: t("modes.changedTo", { mode: t(mode.labelKey) }),
              color: "success",
            });
          } catch {
            toast.add({
              title: t("login.errorTitle"),
              description: t("login.errorDescription"),
              color: "error",
            });
          }
        },
      })),
    },
```

### B.5. `logout` в шапке/сайдбаре → редирект на login

`useAuth.logout` уже редиректит (шаг B.3-d), поэтому обработчики в
`src/shared/ui/UserMenu.vue` (≈строка 219) и `src/app/layouts/MainLayout.vue`
(≈строка 144) менять не обязательно — они вызывают `await auth.logout()`.
Достаточно убедиться, что они его вызывают (уже так).

### B.6. Редирект на login при 401

**Файл `src/app/index.ts`** — в `setApiHooks` дополнить `onUnauthorized`
редиректом (после `logoutLocal`):

```ts
import { router } from "./router";
// ...
setApiHooks({
  onUnauthorized: () => {
    const auth = useAuth();
    auth.logoutLocal();
    if (router.currentRoute.value.name !== "login") {
      void router.push({ name: "login" });
    }
  },
});
```

> Важно при коротком TTL access-токена: протух токен → любой запрос вернёт 401 →
> пользователя выкинет на login. С TTL=3600 (шаг A.1) это редко.

### B.7. (Опционально) Упростить `me()`

В `src/modules/auth/auth.api.ts` функция `me()` после `/auth/me` ещё раз
дёргает `/user/me/permissions` с `X-Actor-Id`. Теперь `/auth/me` уже отдаёт
права, поэтому второй запрос можно удалить (оставить только `return session;`).
Не обязательно — лишний запрос безвреден, но это минус один round-trip.

---

## ЧАСТЬ C. ПРОВЕРКА (acceptance)

1. **Бэкенд поднят, миграции применены** (`alembic upgrade head` без ошибок).
2. **Реальный логин:** открыть `http://localhost:5173/login`, ввести
   `doctor` / `doctor123` → редирект на `/dashboard`, в DevTools → Application →
   Cookies видны `access_cookie` и `refresh_cookie`; в Network у `/auth/login`
   статус 200.
3. **UI меняется от прав:** под `doctor` (lab_doctor) в меню видны
   «Исследования» (research), «Тесты», «Образцы», но НЕТ «Доступ» (users/roles).
   Под `nachfil` (branch_chief) — нет «Тестов»/«Исследований», но есть обзорные
   разделы. (Сверить с `docs/role-access-matrix.md`.)
4. **Виджет ролей:** UserMenu → «Режим» → выбрать другую роль → тост «режим
   изменён», меню перестраивается под новую роль, в Network есть `/auth/login`.
5. **Перезагрузка страницы (F5):** сессия сохраняется (сработал `restoreSession`
   → `/auth/me` по cookie), меню остаётся под текущей ролью.
6. **Logout:** UserMenu → «Выйти» → редирект на `/login`, cookie удалены, повтор
   перехода на `/dashboard` снова кидает на `/login` (router guard).
7. **Неверный пароль на /login:** тост с ошибкой, остаёмся на login.

---

## ЧАСТЬ D. РИСКИ И ЗАМЕТКИ

- **Короткий TTL.** В дефолтном `config.py` TTL = 40/60 сек — для демо мало,
  обязательно поднять в `.env` (шаг A.1), иначе пользователя будет постоянно
  выкидывать по 401.
- **CORS/cookie.** `app_factory.py` уже отдаёт `allow_credentials=True` и список
  dev-origin'ов (включая `:5173`). Если фронт на другом порту — добавить origin
  в этот список, иначе cookie не установятся.
- **Словарь `results`/`research`.** Без правки B.1 раздел «Исследования»
  пропадёт у всех ролей после реального логина — это главный «тихий» баг.
- **scope — информационный.** Фронтовый `can()` (`modeAllows` в `user-modes.ts`)
  scope не учитывает. Бэкенд scope не применяет (по условию задачи). Значения
  scope нужны «на будущее» и для отображения в админке прав.
- **Дев-гейт `setMode`.** Старый `setMode` работал только в DEV. Новый `loginAs`
  ходит на бэкенд и работает в любом окружении — если виджет должен быть только
  для демо, можно обернуть пункт «Режим» в `v-if="isDev"` в `UserMenu.vue`.
- **Базовая линия lint/test красная** (см. проектную память): прогоняй проверку
  точечно по изменённым файлам, не полагайся на общий зелёный `make lint`/`make
  test`.

---

## Чек-лист файлов

**Бэкенд (создать):**
- `src/application/access_control/use_cases/auth.py`
- `src/presentation/http/access_control/auth_schemas.py`
- `src/presentation/http/access_control/auth_router.py`
- `migrations/versions/20260627_0015_role_permission_scopes.py`

**Бэкенд (изменить):**
- `src/infrastructure/repositories/access_control.py` (+`get_by_username`)
- `src/application/access_control/ports.py` (+`UserAuthRepository`)
- `src/domain/uow.py` (тип `users`)
- `src/infrastructure/uow.py` (тип `users`)
- `src/presentation/http/access_control/dependencies.py` (+2 зависимости)
- `src/api/v1/router.py` (+`auth_router`)
- `.env` (TTL/cookie)

**Фронтенд (создать):**
- `src/shared/config/role-credentials.ts`

**Фронтенд (изменить):**
- `src/modules/auth/auth.api.ts` (`mapResource`; опц. `me()`)
- `src/modules/auth/composables/useAuth.ts` (`loginAs`, logout-редирект, коммент)
- `src/shared/ui/UserMenu.vue` (виджет ролей → `loginAs`)
- `src/app/index.ts` (`onUnauthorized` → редирект на login)
