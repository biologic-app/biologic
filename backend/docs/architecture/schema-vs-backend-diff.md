---
создал: 2026-07-03
tags:
  - biologic
  - postgres
  - backend
  - diff
---
# Дифф: справочная модель данных ↔ ORM-модели бэкенда

Сопоставление документа «Модель данных» (25 таблиц) с фактическими SQLAlchemy-моделями
в `backend/src/infrastructure/db/models/`.

> **TL;DR.** Все 25 сущностей схемы в бэкенде присутствуют. Две таблицы **переименованы**
> (`alerts → notifications`, `history → change_log`), причём `notifications` **существенно
> перепроектирована**. 4 рабочие таблицы имеют **лишние поля** (расширения RBAC / импорт /
> дедлайны). Есть **одна таблица сверх схемы** — `user_permission_overrides`. Плюс во всём
> RBAC добавлено измерение `scope` (enum `access_scope_type`), которого в схеме нет.

---

## Сводка соответствия таблиц

| Раздел | Таблица (схема) | Таблица (бэкенд) | Статус |
|---|---|---|---|
| Доступ | `branches` | `branches` | ✅ идентично |
| Доступ | `labs` | `labs` | ✅ идентично |
| Доступ | `objects` | `objects` | ✅ идентично |
| Доступ | `users` | `users` | ✅ идентично |
| Доступ | `roles` | `roles` | ✅ идентично |
| Доступ | `permissions` | `permissions` | ✅ идентично |
| Доступ | `role_permissions` | `role_permissions` | ⚠️ +поле `scope` |
| Доступ | `user_scopes` | `user_scopes` | ✅ идентично* |
| Доступ | — | `user_permission_overrides` | ➕ **таблица сверх схемы** |
| Статусы | `direction_statuses` | `direction_statuses` | ✅ идентично |
| Статусы | `sample_statuses` | `sample_statuses` | ✅ идентично |
| Статусы | `research_statuses` | `research_statuses` | ✅ идентично |
| Статусы | `test_statuses` | `test_statuses` | ✅ идентично |
| Справочники | `sample_types` | `sample_types` | ✅ идентично |
| Справочники | `protocol_types` | `protocol_types` | ✅ идентично |
| Справочники | `research_goals` | `research_goals` | ✅ идентично |
| Справочники | `indicators` | `indicators` | ✅ идентично |
| Справочники | `conclusions` | `conclusions` | ✅ идентично |
| Справочники | `doctors` | `doctors` | ✅ идентично |
| Рабочие | `directions` | `directions` | ⚠️ +поле `import_warnings` |
| Рабочие | `samples` | `samples` | ⚠️ +поля `deadline`, `verdict` |
| Рабочие | `research` | `research` | ⚠️ +поле `lab_id` |
| Рабочие | `tests` | `tests` | ✅ идентично |
| Рабочие | `protocols` | `protocols` | ✅ идентично |
| Уведомления | `alerts` | `notifications` | 🔴 **переименована + перепроектирована** |
| Аудит | `history` | `change_log` | 🟡 переименована (поля идентичны)** |

\* `user_scopes`: поля совпадают, есть `UNIQUE (user_id, scope_id)`, но **не реализован** рекомендованный
партиал-индекс `UNIQUE (user_id) WHERE scope_id IS NULL`.

\** Сам документ схемы внутренне противоречив: заголовок и текст называют таблицу `history`,
а SQL-пример в том же разделе обращается к `change_log`. Бэкенд использует `change_log` —
совпадает с примером, а не с заголовком.

**Итог:** совпадают полностью — **20**; расходятся по полям — **4**; переименованы — **2**
(из них 1 переработана); лишних таблиц в бэкенде — **1**.

---

## Детальные расхождения

### 🔴 `alerts` (схема) → `notifications` (бэкенд) — принципиальная переработка

Таблица переименована **и** имеет другую структуру. Это не косметика, а иная модель адресации
и полезной нагрузки уведомлений.

| Поле схемы (`alerts`) | Поле бэкенда (`notifications`) | Комментарий |
|---|---|---|
| `user_id` `uuid` **NOT NULL** | `target_user_id` `uuid` **NULL** (FK users) | Ослаблена обязательность: адресат-пользователь опционален |
| — | `target_role_key` `text` **NULL** | ➕ Новая адресация: уведомление на **роль**, а не только на пользователя |
| `type` `text` NOT NULL | `kind` `text` NOT NULL | Переименовано |
| — | `source_event_type` `text` NOT NULL | ➕ Отдельно хранится тип породившего события |
| — | `title` `text` NOT NULL | ➕ Заголовок уведомления |
| `message` `text` NOT NULL | `message` `text` NOT NULL | ✅ совпадает |
| — | `payload` `jsonb` NOT NULL DEFAULT `'{}'` | ➕ Структурированная нагрузка |
| `entity_type` `text` **NULL** | `entity_type` `text` **NOT NULL** | Ужесточена обязательность |
| `entity_id` `uuid` **NULL** | `entity_id` `uuid` **NOT NULL** | Ужесточена обязательность |
| `branch_id` `uuid` NULL | — | ➖ В бэкенде **нет** привязки к филиалу |
| `is_read` `bool` DEFAULT false | `read_at` `timestamptz` NULL | Модель «прочитано» через **отметку времени**, а не флаг |
| `is_hidden` `bool` DEFAULT false | — | ➖ **Нет** механизма скрытия (`is_hidden`) |
| `created_at` `timestamptz` | `created_at` `timestamptz` | ✅ совпадает |

**Следствия для UI / выборок из схемы:**
- Запрос из схемы `WHERE user_id = :uid AND is_hidden = false` **не работает** — нет ни `user_id`
  (есть `target_user_id`), ни `is_hidden`.
- Признак прочтения: в бэкенде это `read_at IS NULL` (не прочитано) вместо `is_read = false`.
- Адресация «по роли» (`target_role_key`) в схеме не предусмотрена вовсе.

---

### 🟡 `history` (схема) → `change_log` (бэкенд) — только имя

Набор полей совпадает: `id, branch_id, entity_type, entity_id, action, actor_id, actor_name,
snapshot (jsonb), diff (jsonb), created_at`. Отличается лишь имя таблицы (см. сноску выше про
противоречие в самом документе). Индексы в бэкенде: по `(entity_type, entity_id)`, `actor_id`,
`branch_id`, `created_at`.

---

### ⚠️ `role_permissions` — +`scope`

| | Тип | Ограничения | Примечание |
|---|---|---|---|
| ➕ `scope` | `enum access_scope_type` | NOT NULL, DEFAULT `'all'` | Отсутствует в схеме |

Значения enum `access_scope_type`: `own`, `own_lab`, `all_labs`, `own_branch`, `all_branches`, `all`.
Бэкенд моделирует **более гранулярный RBAC**, чем схема: право роли несёт собственную область
видимости. В схеме область видимости жёстко привязана к `roles.scope_type` (4 значения:
`global/own_branch/own_lab/own_objects`), т.е. это две разные модели scope.

---

### ⚠️ `directions` — +`import_warnings`

| | Тип | Ограничения | Примечание |
|---|---|---|---|
| ➕ `import_warnings` | `jsonb` | NULL | Отсутствует в схеме. Похоже на буфер предупреждений при импорте направлений |

Все поля схемы присутствуют. Уникальность: `UNIQUE (year_no, base_no) WHERE deleted_at IS NULL`.

---

### ⚠️ `samples` — +`deadline`, +`verdict`

| | Тип | Ограничения | Примечание |
|---|---|---|---|
| ➕ `deadline` | `timestamptz` | NULL | Отсутствует в схеме. Дедлайн по образцу (согласуется с уведомлениями `sample_deadline_*`) |
| ➕ `verdict` | `text` | NULL | Отсутствует в схеме. Согласуется с `verdict_non_compliant` в типах уведомлений |

Примечательно: типы уведомлений в схеме (`sample_deadline_overdue`, `verdict_non_compliant`)
**опираются** на эти два поля, но в разделе таблицы `samples` схемы они не описаны — то есть
бэкенд здесь полнее самой схемы.

---

### ⚠️ `research` — +`lab_id`

| | Тип | Ограничения | Примечание |
|---|---|---|---|
| ➕ `lab_id` | `uuid` | NULL (FK `labs.id`) | Отсутствует в схеме. Прямая привязка исследования к лаборатории |

Все поля схемы присутствуют. Индекс по `lab_id` есть. Вероятно, денормализация для scope-фильтрации
(`own_lab`) без джойна через `sample → direction`.

---

### ➕ `user_permission_overrides` — таблица целиком сверх схемы

Персональные исключения прав поверх ролевых — точечная выдача/отзыв разрешения конкретному
пользователю. В документе «Модель данных» такой таблицы нет.

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | `uuid` | PK, DEFAULT `uuidv7()` |
| `user_id` | `uuid` | NOT NULL, FK `users.id` |
| `permission_id` | `uuid` | NOT NULL, FK `permissions.id` |
| `allowed` | `boolean` | NOT NULL (`true` — выдать, `false` — отозвать) |
| `scope` | `enum access_scope_type` | NULL |
| — | | `UNIQUE (user_id, permission_id)` |

---

## Замечания по RBAC (схема vs бэкенд)

Модель доступа — главная точка расхождения помимо `notifications`:

1. Схема: область видимости роли задаётся одним полем `roles.scope_type`
   (`global/own_branch/own_lab/own_objects`), полиморфно через `user_scopes.scope_id`.
2. Бэкенд: **та же** `roles.scope_type` (enum `role_scope_type`, значения совпадают) **плюс**
   отдельное, более детальное измерение `access_scope_type` на уровне **каждого права**
   (`role_permissions.scope`) и персональные оверрайды (`user_permission_overrides`).

То есть фактическая RBAC-модель бэкенда — надмножество описанной в схеме.

---

## Что стоит решить

- **`alerts` vs `notifications`.** Наибольший риск рассинхрона: имя таблицы, набор полей и
  модель адресации/прочтения расходятся. Нужно привести один из артефактов в соответствие
  (скорее — обновить документ схемы под реализацию, т.к. бэкенд функционально богаче).
- **`history` vs `change_log`.** Договориться об одном имени и починить внутреннее противоречие
  в документе (заголовок `history` vs SQL `change_log`).
- **RBAC-расширения** (`scope` в `role_permissions`, `user_permission_overrides`) — задокументировать
  в схеме или явно пометить как «намеренно вне справочной модели».
- **Доп. поля** `directions.import_warnings`, `samples.deadline/verdict`, `research.lab_id` —
  дописать в схему (особенно `samples.deadline/verdict`, на которые уже ссылаются типы уведомлений).
