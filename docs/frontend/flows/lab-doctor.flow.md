---
created: 2026-07-03
tags:
  - biologic
  - lab_doctor
  - e2e
  - flow
---

# Поток врача-лаборанта (ВЛ) (E2E flow spec)

> Источник: сквозной сценарий работы врача-лаборанта (ВЛ) в лабораторной
> системе, зафиксированный для написания Playwright e2e-тестов. Написан по
> аналогии с `docs/flows/registrator.flow.md` и
> `docs/flows/sanitary-doctor.flow.md` — теми же маршрутами, статус-кодами и
> селекторами UI.
>
> Стенд: backend `http://localhost:8080` (`/api/v1`), frontend
> `http://localhost:5177`. Демо-учётка: `doctor` / `doctor123`
> (роль `lab_doctor`, scope `own_lab`, см.
> `src/shared/config/role-credentials.ts` и
> `backend/migrations/versions/20260303_0009_seed_initial_rbac_users.py`).
>
> Видео: `docs/flows/videos/lab-doctor-flow.webm` — логин под doctor,
> подтверждение исследования, взятие в работу, испытания (взять в работу →
> внести результат → авто-completed исследования), брак образца со
> всплывающим SSE-уведомлением и запись в техническом аудите.
>
> E2E-спека: `tests/e2e/lab-doctor-lifecycle.spec.ts`.

## 0. Зона ответственности врача-лаборанта

Врач-лаборант (ВЛ) — центральная роль рабочего процесса лаборатории. К
моменту, когда образцы попадают к ВЛ, регистратор уже импортировал/создал
направление, зарегистрировал его (`directions.register`) и назначил образцам
исследования (`samples.assign-research`). ВЛ:

1. Подтверждает назначенные исследования и берёт их в работу.
2. Выполняет отдельные испытания (tests) внутри исследования: берёт в работу,
   вносит результат (значение/норма), при необходимости возвращает в очередь
   или отклоняет.
3. По завершении всех испытаний исследование **автоматически** переходит в
   `completed` (серверный каскад, не отдельная команда — см. §4).
4. Может забраковать образец (`samples.reject`) — например, если материал
   непригоден для исследования.
5. Может отклонить исследование (`research.reject`).

### Права роли (реальные, с бэкенда)

`GET /auth/login` для `doctor` возвращает набор прав `lab_doctor` из
`ROLE_PERMISSION_MATRIX["lab_doctor"]`
(`20260303_0009_seed_initial_rbac_users.py`). Ключевые командные права:

| resource | action | Команда UI |
|---|---|---|
| `research` (`results`) | `confirm` | research.confirm «Подтвердить исследование» |
| `research` (`results`) | `start` | research.start «Взять исследование в работу» |
| `research` (`results`) | `reject` | research.reject «Отклонить исследование» |
| `tests` | `start` | tests.start «Взять тест в работу» |
| `tests` | `result` | tests.complete «Внести результат теста» |
| `tests` | `requeue` | tests.requeue «Вернуть тест в очередь» |
| `tests` | `reject` | tests.reject «Отклонить тест» |
| `samples` | `reject` | samples.reject «Забраковать образец» |

Плюс read-права на `directions`, `samples`, `protocols`, `conclusions`,
`change_log`, `indicators` (create/update/delete), справочники. На фронте
бэкендовые `results.*` мапятся на ресурс `research` (`read → view`,
`result → complete`; см. `src/modules/auth/auth.api.ts::mapResource/mapAction`),
поэтому проверки `can("research", "confirm"|"start"|"reject")` и
`can("tests", "start"|"complete"|"requeue"|"reject")` истинны.

У ВЛ **нет** `directions.register`/`create`, `samples.create`,
`samples.close`, `protocols.create` — регистрация направлений и закрытие
образцов вне его зоны (закрытие — у НЛ, `lab_chief`).

## 1. Вход в систему

- Страница `/login` (`src/pages/LoginPage.vue`), форма (не быстрый вход по
  роли).
- Учётные данные: `doctor` / `doctor123`.
- `POST /api/v1/auth/login` → `{ data: { user, permissions, ... } }`,
  cookie-сессия. Редирект на `/dashboard`.
- Права сразу управляют видимостью пунктов меню — «Research» и «Tests» в
  сайдбаре активны (`canViewResearch`/`canViewTests` в
  `src/app/layouts/MainLayout.vue`), в отличие от санитарного врача, где они
  задизейблены замком.

## 2. Исследования — подтверждение и взятие в работу

- Страница `/research` (`src/pages/ResearchPage.vue`,
  `crudModules.research`), поиск `getByTestId('crud-search-input')`.
  Строку fixture-исследования удобно изолировать по значению поля
  «Комментарий» (`comment`, задаётся при `assign-research`) — оно входит в
  полнотекстовый поиск (`build_global_search_filter`, все str-колонки).
- Команды запускаются правым кликом по строке → пункт меню (по
  `label · title`, напр. `/CNF · Подтвердить исследование/`) или через
  выделение чекбоксов + `SelectionActionBar`. Механика —
  `getRowWorkflowActionItems`/`canRunCommandOnRow` в
  `src/modules/dictionaries/pages/DictionaryCrudContent.vue`.

### 2.1. Подтвердить исследование (draft → ordered)

- Правый клик по строке в статусе «Черновик» (`research_statuses.code=draft`)
  → «CNF · Подтвердить исследование» (`research.confirm`, без полей формы).
- `POST /api/v1/research/{id}/confirm` body `{ actor_id }` →
  `draft → ordered`. Тост «Исследования подтверждены».
- Бейдж статуса в таблице сразу меняется на «Запланировано»
  (`research_statuses.code=ordered`, name «Запланировано»).
- Карточка (правый клик → «Просмотр», `EntityDetailDialogBase.vue`,
  `businessKind="research"`) → вкладка «Технический аудит» →
  запись `research confirmed` (`change_log.action="research_confirmed"`,
  `GET /history?filters={entity_type:"research", entity_id}`).

### 2.2. Взять исследование в работу (ordered → in_progress)

- Правый клик → «STR · Взять исследование в работу» (`research.start`).
- `POST /api/v1/research/{id}/start` → `ordered → in_progress`. Тост
  «Исследования взяты в работу». Бейдж → «В работе».
- Серверный побочный эффект (`start_research` в `repositories.py`): если
  образец был в `registered`, он переходит в `in_progress` (`sample_started`),
  а направление из `registered` — в `in_progress` (`direction_started`).
- Технический аудит исследования: запись `research started`
  (`action="research_started"`).

## 3. Испытания (tests) — выполнение

- Страница `/tests` (`src/pages/TestsPage.vue`, `crudModules.tests`).
  У испытаний нет удобной текстовой колонки-идентификатора (у Research нет
  `name`), поэтому в e2e список сужается поиском по `research_id` (UUID-колонка
  `tests.research_id` кастуется в текст и входит в полнотекстовый поиск,
  `src/core/global_search.py`), а конкретная строка пиннится по уникальному
  имени показателя (`indicator.name`). Считать строки по `count` нельзя —
  таблица `/tests` рендерит дополнительный служебный пустой `<tr>`.
- При `assign-research` для каждого `indicator` цели исследования создаётся
  одна строка `tests` в статусе `queued` (`test_statuses.code=queued`, name
  «Запланировано»). Чтобы «последнее испытание завершает исследование» было
  детерминированно, в e2e создаётся отдельная цель с ровно одним индикатором.

### 3.1. Взять испытание в работу (queued → in_progress)

- Правый клик по строке «Запланировано» → «STR · Взять тест в работу»
  (`tests.start`). `POST /tests/{id}/start` → `queued → in_progress`. Тост
  «Тесты взяты в работу». Бейдж → «Выполняется» (`test_statuses.code=in_progress`).

### 3.2. Внести результат (in_progress → completed)

- Правый клик → «RES · Внести результат теста» (`tests.complete`) — командный
  диалог с полями «Значение» (`value`, обязательное) и «Норма» (`norm`),
  плюс «Комментарий».
- `POST /tests/{id}/complete` body `{ actor_id, value, norm, comment }` →
  `in_progress → completed`. Тост «Результаты тестов сохранены». Бейдж →
  «Выполнено».

### 3.3. Возврат в очередь и отклонение

- «REQ · Вернуть тест в очередь» (`tests.requeue`): `in_progress → queued`
  (без полей). Тост «Тесты возвращены в очередь», бейдж → «Запланировано».
- «REJ · Отклонить тест» (`tests.reject`): диалог с полем «Причина», статусы
  `queued`/`in_progress` → `rejected`. Тост «Тесты отклонены», бейдж →
  «Отклонено» (`test_statuses.code=rejected`).

## 4. Авто-завершение исследования (каскад)

- После `complete_test` (и `reject_test` — оба вызывают
  `_complete_parents_when_terminal`, `repositories.py`): если у исследования
  не осталось нетерминальных испытаний (все `completed`/`rejected`),
  исследование само переходит `in_progress → completed`
  (`action="research_completed"`), а если у образца не осталось
  нетерминальных исследований — образец переходит в `analyzed`
  (`sample_analyzed`).
- **Важно (предусловие каскада):** переход образца в `analyzed` валиден
  только из `in_progress`. То есть к моменту завершения последнего испытания
  образец уже должен быть зарегистрирован (`samples.register`,
  `pending → registered`) и переведён в работу (это делает `research.start`:
  `registered → in_progress`). Если завершать/отклонять последнее испытание
  на **незарегистрированном** образце (`pending`), каскад упирается в
  недопустимый переход `pending → analyzed` и вся команда
  `complete`/`reject` откатывается с `409 invalid_status_transition` — это
  корректное доменное поведение (нельзя «обработать» непринятый образец), а
  не баг. Поэтому в e2e образец предварительно регистрируется через API.
- В UI это видно так: после внесения результата последнего испытания на
  `/tests`, при возврате на `/research` бейдж исследования уже «Завершено»
  (`research_statuses.code=completed`), без отдельного действия ВЛ. В
  техническом аудите исследования — запись **«Исследование завершено»**
  (у `research_completed` есть отдельная русская метка в
  `src/shared/ui/technical-audit.ts::actionLabel`, а не generic-фолбэк
  `action.replace(/[._-]/g, ' ')`, как у остальных действий).

## 5. Брак образца (samples.reject) + SSE-уведомление

- Страница `/samples`, правый клик по строке → «REJ · Забраковать образец»
  (`samples.reject`) — диалог с обязательным полем «Причина».
- `POST /api/v1/samples/{id}/reject` body `{ actor_id, reason }`. Разрешённые
  исходные статусы: `pending`/`registered`/`in_progress` → `rejected`
  (`status_policy.py`). Тост «Образцы помечены как брак». Бейдж → «Брак».
- **SSE-уведомление** (пользователь требует это отслеживать; email/SMTP в
  системе нет — «уведомление на почту» = in-app alert через SSE):
  - При reject бэкенд эмитит доменное событие `SampleRejected`; через
    публикатор/подписчик (`EventPublisher` → `WorkflowNotificationSubscriber`,
    `src/contexts/notifications/application/subscribers.py`) создаётся alert
    `kind="workflow.sample_rejected"`, нацеленный на владельца направления
    (`Direction.created_by`, резолвится
    `resolve_notification_target`). Поэтому образец в e2e создаётся под
    сессией самого doctor — уведомление адресуется ему.
  - Фронт держит открытым `EventSource` на `GET /api/v1/alerts/stream`
    (`event: notification.created`,
    `src/shared/composables/useSystemNotifications.ts`) — подключение
    поднимается на `/dashboard` (`DashboardPage.vue`). Приходит тост +
    запись в NotificationsSlideover (`[data-tour="dashboard-notifications"]`,
    иконка колокольчика).
  - В тесте: после reject открыть колокольчик, найти текст причины во
    вкладке «Непрочитанные», нажать «Mark as read»
    (`POST /alerts/{id}/mark-read`), проверить переезд во вкладку
    «Прочитанные».
- Технический аудит образца (`businessKind="samples"`): запись
  `sample rejected` (`action="sample_rejected"`,
  `diff.status_code.{from,to}` + reason).

## 6. Отклонение исследования (research.reject)

- `/research`, правый клик → «REJ · Отклонить исследование»
  (`research.reject`) — диалог с полем «Причина», статусы `draft`/`ordered`
  → `rejected`. `POST /research/{id}/reject`. Тост «Исследования отклонены»,
  бейдж → «Отклонено». Технический аудит: `research rejected`
  (`action="research_rejected"`).

## 7. Дашборд ВЛ

- `/dashboard` (`DashboardPage.vue`) — общий для всех ролей.
  Блок KPI-карточек (`[data-tour="dashboard-stats"]`, `HomeStats.vue`) и
  график рабочего процесса (`[data-tour="dashboard-chart"]`,
  `HomeChart.vue`).
- Набор KPI сегодня **не зависит от роли**: бэкенд
  (`src/infrastructure/repositories/dashboard.py::_kpis`) отдаёт один и тот же
  фиксированный набор из 6 карточек для всех: «Поступило образцов»,
  «Выполнено тестов», «Просрочено», «Среднее время», «Брак»,
  «Исследования в работе». Отдельной роль-специфичной метрики «Ожидают
  подтверждения» на бэкенде нет (см. §8 «Известные ограничения»). В e2e
  проверяется наличие всех 6 карточек и графика.

## 8. Известные ограничения (не исправлялись — вне объёма этой сессии)

| # | Что могло бы ожидаться | Что реально сейчас |
|---|---|---|
| 1 | Роль-специфичный дашборд ВЛ («Ожидают подтверждения» / «В работе» / «Просрочено» / «Выполнено за период»). | `dashboard.py::_kpis` возвращает один фиксированный набор из 6 KPI для всех ролей; параметр роли в `GET /dashboard/summary` не участвует. Тест проверяет фактический набор, а не желаемый. |
| 2 | Скоуп `own_lab` — ВЛ видит только исследования/испытания своей лаборатории. | Автоматического скоупинга по лаборатории в списках нет (как и `own_objects` у санитарного врача — см. `sanitary-doctor.flow.md` §0). Любой залогиненный видит все записи; сузить можно только фильтром «Лаборатория». |
| 3 | RBAC на уровне API. | Эндпоинты `laboratory_workflow` не проверяют права запроса — авторизация на фронте. ВЛ физически может дёрнуть чужую команду напрямую через API. |

## 0'. Что было починено для этого потока

Багов продукта, блокирующих сценарий ВЛ, в этой сессии не обнаружено — весь
жизненный цикл (research confirm/start/reject, tests start/complete/requeue/
reject, авто-completed исследования, samples.reject + SSE-уведомление,
технический аудит) воспроизводится на реальном бэкенде без правок кода
приложения. Изменения этой сессии — только тестовая инфраструктура:
e2e-спека `tests/e2e/lab-doctor-lifecycle.spec.ts`, хелперы (`LAB_DOCTOR` /
`loginAsLabDoctor` в `support/auth.ts`, `goToResearch`/`goToTests` в
`support/nav.ts`, командные и reference-хелперы в `support/api.ts`), этот
flow-док и видео.

## Быстрая справка: статус-коды

```
RESEARCH:  in_progress → completed        (создаётся сразу in_progress)
           in_progress → rejected
TEST:      in_progress → completed        (создаётся сразу in_progress)
           in_progress → rejected
SAMPLE:    pending/registered/in_progress → rejected
           (in_progress → analyzed — авто, при завершении всех исследований)
```

## Быстрая справка: маршруты, использованные в потоке

| Действие | Метод/путь |
|---|---|
| Логин | `POST /auth/login` |
| Профиль/сессия | `GET /auth/me` |
| Список/карточка исследований | `GET /research`, `GET /research/{id}` |
| Подтвердить исследование | `POST /research/{id}/confirm` |
| Взять исследование в работу | `POST /research/{id}/start` |
| Отклонить исследование | `POST /research/{id}/reject` |
| Список/карточка испытаний | `GET /tests`, `GET /tests/{id}` |
| Взять испытание в работу | `POST /tests/{id}/start` |
| Внести результат испытания | `POST /tests/{id}/complete` |
| Вернуть испытание в очередь | `POST /tests/{id}/requeue` |
| Отклонить испытание | `POST /tests/{id}/reject` |
| Забраковать образец | `POST /samples/{id}/reject` |
| Назначить исследование (setup) | `POST /samples/{id}/assign-research` |
| Технический аудит | `GET /history?filters={entity_type,entity_id}` |
| Уведомления (список) | `GET /alerts?status=` |
| Уведомления (поток, SSE) | `GET /alerts/stream` |
| Отметить уведомление прочитанным | `POST /alerts/{id}/mark-read` |
| Дашборд | `GET /dashboard/summary` |
