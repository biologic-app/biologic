---
title: "Data Model"
category: reference
sources: []
created: 2026-04-29
updated: 2026-04-29
tags: [data-model, database, schema, entities]
aliases: [Модель данных, Сущности]
confidence: medium
volatility: warm
verified: 2026-04-29
summary: "Справочник сущностей лабораторной системы: доступ, структура, статусы, справочники, рабочие объекты, уведомления и аудит."
---

# Data Model

> Сводная модель данных лабораторной системы. Полный список включает 25 таблиц, сгруппированных по разделам.

## Access And Structure

### `branches`

Филиалы. Ключевые поля: `id`, `code`, `name`, `created_at`, `updated_at`, `deleted_at`.

### `labs`

Лаборатории внутри филиалов. Ключевые поля: `id`, `branch_id`, `code`, `name`, `full_name`, `created_by`, `updated_by`, timestamps, `deleted_at`.

### `objects`

Объекты-источники направлений. Ключевые поля: `id`, `branch_id`, `code`, `name`, `full_name`, `address`, audit timestamps.

### `users`

Пользователи системы. Ключевые поля: `id`, `username`, `password_hash`, `refresh_token_version`, `code`, ФИО, признаки `is_registrar`, `is_lab_head`, `is_branch_head`, `role_id`, `lab_id`, audit timestamps.

### `roles`

Роли. Ключевые поля: `id`, `key`, `name`, `scope_type`, timestamps. Допустимые `key`: `user_admin`, `branch_chief`, `lab_chief`, `registrar`, `lab_doctor`, `lab_assistant`, `sanitary_inspector`, `developer`.

### `permissions`

Каталог разрешений. Ключевые поля: `id`, `resource`, `action`. Ограничение: `UNIQUE (resource, action)`.

### `role_permissions`

Связь ролей и разрешений. Ключевые поля: `id`, `role_id`, `permission_id`. Ограничение: `UNIQUE (role_id, permission_id)`.

### `user_scopes`

Области видимости пользователя. Ключевые поля: `id`, `user_id`, `scope_id`. `scope_id` полиморфно ссылается на `branches.id`, `labs.id` или `objects.id` в зависимости от `roles.scope_type`. Рекомендуется partial unique индекс `UNIQUE (user_id) WHERE scope_id IS NULL`.

## Status Dictionaries

Таблицы `direction_statuses`, `sample_statuses`, `research_statuses`, `test_statuses` имеют общую форму: `id`, `code`, `name`, `created_at`, `updated_at`, `deleted_at`. Нормативные коды и переходы описаны в [[status-lifecycle|Lifecycle Statuses]] ([Lifecycle Statuses](status-lifecycle.md)).

## Reference Data

### `sample_types`

Типы проб. Ключевые поля: `id`, `code`, `name`, audit timestamps.

### `protocol_types`

Типы протоколов. Ключевые поля: `id`, `code`, `name`, timestamps.

### `research_goals`

Цели исследований. Ключевые поля: `id`, `code`, `name`, `comment`, `lab_id`, audit timestamps.

### `indicators`

Показатели. Ключевые поля: `id`, `name`, `unit`, `norm_text`, `norm_value`, `default_text`, `comment`, `research_goal_id`, `sample_type_id`, audit timestamps.

### `conclusions`

Заключения. Ключевые поля: `id`, `code`, `name`, `text_singular`, `text_plural`, `comment`, audit timestamps.

### `doctors`

Врачи. Ключевые поля: `id`, `first_name`, `last_name`, `patronymic`, audit timestamps.

## Working Objects

### `directions`

Направления. Ключевые поля: `id`, `year_no`, `base_no`, `is_done`, `is_urgent`, `doctor_id`, `object_id`, `status_id`, `sampled_at`, `received_at`, `completed_at`, audit timestamps.

### `samples`

Пробы / образцы. Ключевые поля: `id`, `month_no`, `name`, `alternate_name`, `mass`, `target_description`, `comment`, `section`, `delivery`, `nomenclature_code`, `batch_code`, `supplier`, `is_urgent`, `is_done`, `sample_type_id`, `status_id`, `direction_id`, `protocol_id`, `sampled_at`, `received_at`, `completed_at`, audit timestamps.

### `research`

Исследования. Ключевые поля: `id`, `sample_id`, `research_goal_id`, `status_id`, `comment`, `recommendation`, `received_at`, `completed_at`, audit timestamps.

### `tests`

Испытания. Ключевые поля: `id`, `value`, `comment`, `norm`, `is_active`, `research_id`, `indicator_id`, `status_id`, audit timestamps.

### `protocols`

Протоколы. Ключевые поля: `id`, `year_no`, `copies`, `is_signed`, `protocol_copy_name`, `excerpt_copy_name`, `conclusion_id`, `protocol_type_id`, `issued_at`, audit timestamps.

## Alerts

`alerts` создаются системой при бизнес-событиях. Ключевые поля: `id`, `user_id`, `branch_id`, `entity_type`, `entity_id`, `type`, `message`, `is_read`, `is_hidden`, `created_at`.

Нормативные `type`:

| type | Категория | Получатели |
|---|---|---|
| `sample_rejected` | Проблема | НЛ, НФ, РЕГ |
| `sample_deadline_overdue` | Проблема | ВЛ, НЛ, РЕГ |
| `direction_deadline_overdue` | Проблема | НФ, РЕГ, СВ |
| `verdict_non_compliant` | Проблема | НЛ, НФ |
| `sample_deadline_approaching` | Информация | ВЛ, НЛ, РЕГ |
| `direction_deadline_approaching` | Информация | НФ, СВ |
| `research_assigned` | Информация | ВЛ, НЛ |
| `sample_analyzed` | Информация | НЛ |
| `direction_registered` | Информация | СВ |
| `research_completed` | Успех | ВЛ, НЛ |
| `protocol_ready` | Успех | СВ |
| `direction_completed` | Успех | СВ, НФ |
| `protocol_formable` | Успех | РЕГ |

Уведомления не удаляются физически; пользователь управляет видимостью через `is_read` и `is_hidden`.

## Audit

`history` хранит журнал изменений и историю сущности. Ключевые поля: `id`, `branch_id`, `entity_type`, `entity_id`, `action`, `actor_id`, `actor_name`, `snapshot`, `diff`, `created_at`.

Типы `action`: `CREATE`, `UPDATE`, `DELETE`, `RESTORE`, `STATUS_TRANSITION`.

Формат `STATUS_TRANSITION` в `diff`:

```json
{
  "field": "status_id",
  "from_code": "ordered",
  "to_code": "in_progress",
  "entity_type": "research",
  "reason": "doctor_started",
  "triggered_by_role": "doctor"
}
```

Для каскадных переходов нужно сохранять `reason` или `cancellation_reason`, чтобы история была пригодна для расследований.

## See Also

- [[glossary|Glossary]] ([Glossary](glossary.md)) — термины предметной области.
- [[status-lifecycle|Lifecycle Statuses]] ([Lifecycle Statuses](status-lifecycle.md)) — нормативные статусы.
- [[access-matrix|Access Matrix]] ([Access Matrix](access-matrix.md)) — права на сущности.

## Sources

- User-provided domain specification in chat on 2026-04-29.
