---
created: 2026-07-01
tags:
  - biologic
  - registrar
  - e2e
  - flow
---

# Поток регистратора (E2E flow spec)

> Источник: сквозной сценарий работы регистратора в лабораторной системе,
> зафиксированный для написания Playwright e2e-тестов. Дополняет
> `docs/work-processes-by-roles.md` и `docs/role-access-matrix.md` —
> конкретными маршрутами, статус-кодами и селекторами UI.
>
> Стенд: backend `http://localhost:8080` (`/api/v1`), frontend
> `http://localhost:5177`. Демо-учётка: `registrator` / `registrator123`
> (роль `registrar`, см. `src/shared/config/role-credentials.ts`).

## 0. Что было починено для этого потока

На момент постановки задачи часть шагов ниже физически не работала на
реальном (не мок) бэкенде. Список того, что было исправлено в этой сессии,
чтобы весь сценарий стал воспроизводим:

| # | Проблема | Исправление |
|---|----------|-------------|
| 1 | На бэкенде не было ни одного `/auth/*` эндпоинта — логин со страницы `/login` не работал против реального API (фронт уже дёргал `/auth/login`). | Добавлены `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` + `UserAuthRepository.get_by_username`, JWT-cookie сессия. См. `backend/docs/…` план `frontend/docs/login-backend-integration-plan.md`, реализовано 1:1. |
| 2 | `POST /directions` и `POST /samples` никогда не проставляли `status_id` — новые записи оставались с `status_id = NULL` навсегда, что ломает весь lifecycle. | `DirectionCrudRepository.create` / `SampleCrudRepository.create` теперь проставляют дефолтный статус (`draft` / `pending`) через `_default_status_id`, если он не передан явно. |
| 3 | Импорт направлений существовал только в CSV и создавал **только** направления, без образцов. | Добавлены `POST /directions/import-excel` и `POST /directions/import-json` — оба создают направление **и** вложенные образцы (см. §2). |
| 4 | `samples.reject` разрешался только из `pending` — нельзя было забраковать образец «в работе». | В `status_policy.py` разрешены переходы `registered → rejected` и `in_progress → rejected`; во фронтовом `workflow-commands.ts` статусы команды `samples.reject` расширены до `["pending", "registered", "in_progress"]`. |
| 5 | Страница «Образцы» позволяла регистратору создавать образец напрямую (минуя направление). | `entity-rules.ts`: `samples.createDisabled = true` (как у `tests`); `SamplesPage.vue` больше не рендерит кнопку «Создать». |
| 6 | Не было способа добавить образец в существующее направление из его карточки — только через общую форму `/samples`, которая теперь отключена. | В карточке направления (вкладка «Связанные») добавлена кнопка «Добавить образец» (только для `status.code === 'draft'` и права `samples:create`), открывающая форму создания образца с предзаполненным `direction_id`. |

Всё остальное в сценарии ниже уже было реализовано и осталось без изменений.

## 1. Вход в систему

- Страница: `/login` (`src/pages/LoginPage.vue`).
- Регистратор вводит логин/пароль вручную (без использования виджета
  «быстрый вход под ролью» — тот вызывает `auth.loginAs`, минуя форму).
- Учётные данные: `registrator` / `registrator123`.
- `POST /api/v1/auth/login` → `{ data: { user, permissions, access_expires_at, refresh_expires_at } }`,
  `Set-Cookie: access_cookie`, `refresh_cookie` (httpOnly, `SameSite=Lax`).
- После успешного логина — редирект на `/dashboard`.
- Неверный пароль → 401, тост с ошибкой, остаёмся на `/login`.
- Права возвращаются бэкендом и **сразу** управляют видимостью пунктов меню
  через `useAuth().can(resource, action)` (см. `src/modules/auth/composables/useAuth.ts`).

## 2. Импорт направления

- Страница `/directions` (`src/pages/DirectionsPage.vue`), кнопка «Создать» →
  выпадающее меню (`data-testid="direction-import-menu-trigger"`):
  - **«Импортировать Excel»** (основной способ) — `input[data-testid="import-excel-input"]`,
    принимает `.xlsx` → `POST /api/v1/directions/import-excel`.
  - **«Импортировать JSON (резервный способ)»** — `input[data-testid="import-json-input"]`,
    принимает `.json` → `POST /api/v1/directions/import-json`.
- Оба эндпоинта на бэкенде (`src/contexts/laboratory_workflow/application/direction_sample_import.py`)
  принимают одну и ту же построчную форму данных: одна строка = один образец,
  поля направления повторяются в каждой строке своего направления. Строки
  группируются по паре `(year_no, base_no)` — первая строка с новым ключом
  создаёт направление, каждая строка этого ключа добавляет образец.
  - Обязательные поля строки: `year_no`, `sample_name`.
  - Поля направления: `year_no`, `base_no`, `is_urgent`, `doctor_id`,
    `object_id`, `sampled_at`, `received_at`, `completed_at`.
  - Поля образца: `sample_name` → `name`, `sample_type_id`, `mass`,
    `alternate_name`, `nomenclature_code`, `batch_code`, `supplier`,
    `sample_is_urgent` (иначе наследует `is_urgent` направления), `month_no`.
  - Excel: первый лист книги, первая строка — заголовки (как имена полей выше).
  - JSON: `{"rows": [ {...}, ... ]}` либо просто массив таких объектов.
  - Ответ: `WorkflowImportSummary` — `{ filename, rows_processed,
    directions_created, samples_created, skipped_rows, errors[], warnings[] }`.
- Устаревший `POST /directions/import` (CSV, создаёт только направления без
  образцов) оставлен для обратной совместимости, но в UI больше не используется.
- После импорта направление появляется в статусе `draft` (код `direction_statuses.code`),
  каждый образец — в статусе `pending` (код `sample_statuses.code`).

## 3. Редактирование импортированного направления, «нельзя частично в работу»

- Открыть карточку направления или образца в статусе `draft` / `pending` →
  редактируется инлайн (кнопка «Редактировать» в карточке, `EntityDetailDialogBase.vue`).
- Редактирование полей разрешено **только пока сущность в статусе
  draft/pending** — на уровне бэкенда `PATCH` не позволяет менять `status_id`
  напрямую (`_reject_status_update`), переход статуса — только через
  командные эндпоинты (`POST /{resource}/{id}/{action}`).
- **Нет команды «зарегистрировать один образец в работу»** — единственная
  команда уровня направления — `POST /directions/{id}/register`
  (`workflowCommands["directions.register"]`, статус-триггер `draft`).
  Перевести можно только направление целиком; перед этим бэкенд проверяет
  (`_ensure_direction_ready_for_registration` в
  `infrastructure/repositories.py`):
  1. в направлении есть хотя бы один образец;
  2. у каждого образца заполнены `name` и `sample_type_id`;
  3. каждому образцу назначено хотя бы одно исследование (`assign-research`).
  Если хоть один образец не готов — `409 direction_missing_sample_data` /
  `direction_missing_research_assignments`.
- Забраковать при этом можно отдельные образцы независимо от готовности
  направления (см. §5) — это единственная операция уровня образца, доступная
  до регистрации направления.

## 4. Проверка и выпуск направления

- Регистратор назначает образцам тип (`sample_type_id`) и исследования
  (`POST /samples/{id}/assign-research`), затем выделяет направление в
  таблице и выполняет массовую команду **«Зарегистрировать»**
  (`directions.register`, `SelectionActionBar`, статус `draft`).
- `POST /api/v1/directions/{id}/register` → статус направления `draft → registered`.
- Бизнес-статус в карточке (степпер «История переходов статуса», правая
  колонка вкладки «Карточка») сразу отражает переход.

## 5. Брак образца (draft / в работе)

- Пометить как брак можно:
  - через карточку образца (открыть `/samples`, карточка образца, действие
    «Забраковать» — командный диалог с обязательным полем «Причина»);
  - через выделение строк в таблице `/samples` и кнопку «Брак» на панели
    массовых действий (`SelectionActionBar`, команда `samples.reject`).
- `POST /api/v1/samples/{id}/reject` body `{ actor_id, reason }`.
- Разрешённые исходные статусы образца (после исправления в этой сессии):
  `pending`, `registered`, `in_progress` → `rejected`
  (`status_policy.py::ALLOWED_TRANSITIONS["samples"]`).
- При отклонении создаётся уведомление (`workflow.sample_rejected`, см. §15)
  и все привязанные исследования образца автоматически переводятся в `rejected`.

## 6. Ручное создание направления + добавление образцов

- Кнопка «Создать» на `/directions` (не «Импортировать») открывает форму
  создания направления (`year_no`, `base_no`, `doctor_id`, `object_id`,
  даты, `is_urgent`). `POST /directions` → создаётся в статусе `draft`.
- Открыть карточку нового направления → вкладка «Связанные» → кнопка
  **«Добавить образец»** (`data-testid="add-sample-to-direction"`, видна
  только когда статус направления — `draft` и есть право `samples:create`).
  Открывает форму создания образца (без поля «Направление» — оно
  подставляется автоматически из карточки), `POST /samples` с
  `direction_id` текущего направления → образец создаётся в `pending`.
- Далее — тот же процесс, что и для импортированного направления (§3–5).

## 7. Повтор процесса

- Требования §3–6 идентичны и для импортированного, и для вручную
  созданного направления — конкретный источник создания не влияет на
  дальнейший жизненный цикл (registration/reject/audit).

## 8. Фильтры и поиск по датам/полям

- Кнопка «Фильтры» в тулбаре (`CrudFilterControls.vue`) открывает модальное
  окно с полями из `crudModules.directions.filterFields` /
  `crudModules.samples.filterFields`: диапазоны дат (`sampled_at`,
  `received_at`, `completed_at`, `deadline`), select-фильтры (`status_id`,
  `object_id`, `doctor_id`, `sample_type_id`, …), текстовые фильтры, boolean
  (`is_urgent`, `is_done`).
- Фильтры сериализуются в JSON и передаются как query-параметр `filters` на
  `GET /directions` / `GET /samples` (`src/core/pagination.py`).

## 9. Полнотекстовый поиск по направлениям

- Поле поиска в тулбаре (`CrudSearchControl.vue`) передаёт значение как
  query-параметр `search` на `GET /directions`.
- На бэкенде — `build_global_search_filter` (`src/core/global_search.py`),
  использует `pg_trgm` (миграция `20260608_0014_enable_pg_trgm`) для
  нечёткого поиска по нескольким колонкам, включая связанные (doctor/object).

## 10. Карточка направления: редактирование, технический аудит, бизнес-статус

- Открыть строку таблицы `/directions` → модалка `BusinessEntityDetailModal`
  → `EntityDetailDialogBase.vue`, три вкладки:
  - **«Карточка»** — поля + инлайн-редактирование (кнопка «Редактировать»,
    доступна всегда в UI, но `PATCH` бэкенд не даёт менять `status_id`); в
    правой колонке — степпер бизнес-статуса (`История переходов статуса`,
    построен из `statusHistory` — `created → received/registered → completed`).
  - **«Технический аудит»** — сырые записи `change_log`, `GET /api/v1/history?filters={entity_type,entity_id}`
    (см. `loadAuditHistory` в `EntityDetailDialogBase.vue`). Каждая запись:
    `{ action, actor_name, diff, snapshot, created_at }`.
  - **«Связанные»** — образцы направления (и, для направления, кнопка
    «Добавить образец», см. §6).
- После перехода статуса (`register`) — степпер бизнес-статуса сразу
  показывает новый шаг, а вкладка «Технический аудит» — новую запись
  `change_log` (`action="direction_registered"`, `diff.status_code.{from,to}`).
- Редактирование полей физически возможно из UI в любом статусе (кнопка не
  скрывается), но реально применяется только пока направление в `draft` —
  дальнейшие сценарии редактирования не предусмотрены бизнес-процессом и не
  тестируются в этом потоке за пределами `draft`.

## 11. Просмотр образцов

- Страница `/samples` — список всех образцов (без кнопки «Создать», см. §0/§12).
- Открыть карточку — та же трёхвкладочная модалка, `businessKind="samples"`.

## 12. Регистратор не создаёт образцы на странице образцов

- `entity-rules.ts`: `samples.createDisabled = true`. Кнопка «Создать» на
  `/samples` отсутствует (страница отрендерена без слота `navbar-right`,
  как `/tests`). Единственный путь создания образца вручную — из карточки
  направления (§6); массово — импорт (§2).

## 13. Карточка образца: брак через карточку и через выделение

- Из карточки образца: командное действие «Забраковать» (аналогично §5),
  диалог с полем «Причина».
- Через выделение строк в таблице `/samples`: чекбоксы → `SelectionActionBar`
  → кнопка «Брак» (цвет `warning`, команда `samples.reject`) — можно
  забраковать несколько образцов одним действием.

## 14. Технический и бизнес-аудит образца

- Аналогично §10, но `businessKind="samples"`:
  - Бизнес-статус степпер: `created → registered → closed`.
  - Технический аудит: `GET /history?filters={entity_type:"samples", entity_id}`.
- После «Брак» степпер сразу показывает переход, технический аудит —
  запись `action="sample_rejected"` с `diff.status_code.{from,to}` и `reason`.

## 15. Уведомление о браке по SSE

- При `POST /samples/{id}/reject` бэкенд эмитит доменное событие
  `SampleRejected` → `NotificationService.create_from_events` создаёт alert
  `kind="workflow.sample_rejected"` в одной транзакции с командой
  (`src/contexts/notifications/`).
- Фронтенд: `useSystemNotifications.ts` держит открытым
  `EventSource` на `GET /api/v1/alerts/stream` (`event: notification.created`),
  автопереподключение через 3с при обрыве.
- Панель уведомлений — `NotificationsSlideover.vue` (открывается из шапки),
  вкладки «Непрочитанные»/«Прочитанные», получает список через
  `GET /alerts?status=unread|read`.
- Отметить прочитанным: `POST /alerts/{id}/mark-read` (кнопка в панели) →
  `read_at` проставляется, элемент переезжает во вкладку «Прочитанные».

## Быстрая справка: статус-коды

```
DIRECTION: draft → registered → in_progress → partially_completed → completed
SAMPLE:    pending → registered → in_progress → analyzed → completed
           pending/registered/in_progress → rejected
           analyzed → in_progress (reopen)
```

## Быстрая справка: маршруты, использованные в потоке

| Действие | Метод/путь |
|---|---|
| Логин | `POST /auth/login` |
| Профиль/сессия | `GET /auth/me` |
| Выход | `POST /auth/logout` |
| Импорт направлений (Excel) | `POST /directions/import-excel` |
| Импорт направлений (JSON, резерв) | `POST /directions/import-json` |
| Список/карточка направлений | `GET /directions`, `GET /directions/{id}` |
| Создать направление вручную | `POST /directions` |
| Изменить направление (только draft) | `PATCH /directions/{id}` |
| Зарегистрировать направление | `POST /directions/{id}/register` |
| Список/карточка образцов | `GET /samples`, `GET /samples/{id}` |
| Создать образец (в направлении) | `POST /samples` |
| Зарегистрировать образец | `POST /samples/{id}/register` |
| Забраковать образец | `POST /samples/{id}/reject` |
| Назначить исследование образцу | `POST /samples/{id}/assign-research` |
| Технический аудит | `GET /history?filters={entity_type,entity_id}` |
| Уведомления (список) | `GET /alerts?status=` |
| Уведомления (поток) | `GET /alerts/stream` (SSE) |
| Отметить уведомление прочитанным | `POST /alerts/{id}/mark-read` |
