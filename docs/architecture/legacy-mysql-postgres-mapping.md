---
создал: 2026-08-27
tags:
  - biologic
  - migration
  - mysql
  - postgres
  - legacy
---
# Mapping legacy MySQL 5.1 → PostgreSQL

Зафиксированный контракт переноса дампа `uchet_mysql_dump` (MySQL `5.1.41`,
кодировка таблиц `cp1251`) в canonical-модель Biologic.

## Состояние источника

Дамп восстановлен без очистки исходного файла:

- MariaDB 5.5: `legacy_fast` в контейнере `legacy-mysql`;
- PostgreSQL staging: `biologic_legacy_stage`;
- рабочая PostgreSQL-БД `biologic` в переносе не участвует до отдельного запуска ETL.

Импорт в staging: 20 таблиц, 4 054 172 строки. Все исходные строки должны
оставаться доступными в staging даже если canonical-запись создать нельзя.

## Правила преобразования типов

| MySQL 5.1 | PostgreSQL canonical | Правило |
|---|---|---|
| `INT AUTO_INCREMENT` PK | `uuid` | Не переносить integer в PK. Генерировать детерминированный UUID из `(source_table, source_id)` и сохранять mapping. |
| `INT` FK | `uuid` FK | Разрешать через mapping соответствующей таблицы; отсутствующий parent → `NULL` или orphan-report. |
| `VARCHAR`, `TEXT` `cp1251` | `text` UTF-8 | Декодировать как `cp1251`, нормализовать только пробелы по краям. Исходное значение не перезаписывать в staging. |
| `TINYINT(1)` | `boolean` | `0 → false`, ненулевое значение → `true`. |
| `DATETIME` | `timestamptz` | Считать исходное значение UTC (дамп содержит `SET TIME_ZONE='+00:00'`). Нулевые/некорректные даты → `NULL` + warning. |
| `deleted TINYINT(1)` | `deleted_at` | `true` → `modified`, иначе `NULL`. Если timestamp отсутствует, использовать время запуска миграции и warning. |
| старые статусы `1/2/3` | status UUID | `1 → completed`, `2 → rejected`, `3 → in_progress` для результатов/тестов. Для направлений/образцов `simple_status=true → completed`, иначе `in_progress`. |
| `users.password` SHA-1 | `users.password_hash` bcrypt | SHA-1 не переносить. Пользователь создаётся/сопоставляется с `status='blocked'` и принудительным reset пароля. |

Все идентификаторы и связи должны проходить через таблицы mapping, а не через
совпадение порядковых номеров или имён.

## Табличный mapping

| Legacy | Canonical | Правило |
|---|---|---|
| `user_types` | `roles` | `2→admin`, `3→registrar`, `4→branch_chief`, `5→lab_chief`, `6→lab_assistant`, `7→observer` (новая обычная read-only роль). |
| `users` | `users` | Existing username не перезаписывать: связать через mapping. Остальных добавить с reset-паролем. `deleted=true` → blocked/deleted policy. |
| `podrs` | `labs` | Кодовая карта: `Х→TH`, `Б→BAK`, `Р→RV`, `ТБ→TB`, `ПЦР→PCR`. Неразрешённый код → orphan-report. |
| `sandoctors` | `doctors` | `name_full` разобрать на ФИО; неоднозначные строки сохранить в warning. |
| `resobjects` | `objects` | `code=LEGACY-RESOBJECT-{id}`, `name=name`, `full_name=name_full`, `address=adress`, `branch_id=NULL` если филиал не выводится однозначно. |
| `naprs` | `directions` | `year→year_no`, `id_year→base_no`, `sandoctor_id→doctor_id`, `resobject_id→object_id`, `time_otbor→sampled_at`, `time_in→received_at`, `time_out→completed_at`. `id_year/year` конфликтуют с существующим canonical unique key → report, не затирать. |
| `obr_types` | `sample_types` | Каждому legacy type создать стабильный код `LEGACY-OBR-TYPE-{id}`; исходное `name` сохранить. Сопоставление с существующим типом по точному нормализованному имени допускается только без дубля. |
| `obrs` | `samples` | `napr_id→direction_id`, `obr_type_id→sample_type_id`, `protocol_id→protocol_id`, `name`, `alt_name`, `mass`, `target`, `comment`, `section`, `postavka`, `nomencl_cod`, `part_cod`, `postavshik`, `urgent`, `time_in`, `time_out`. Missing protocol → `NULL` + report. |
| `targets` + `obrs.target` | `research_goals` | Каждая из 66 уникальных нормализованных строк `obrs.target` — отдельная legacy goal. Базовые 11 значений из `targets` используются для нормализации алиасов. Код: `LEGACY-TARGET-{sha256[:12]}`; оригинальная строка сохраняется в `comment`. |
| `poks` | `indicators` | `name`, `edizm→unit`, `norm→norm_text`, `norm_value`, `default_text`, `comment`; `obr_type_id→sample_type_id`. `podr_id` не имеет прямого поля в canonical `indicators`: сохранить в ETL mapping/comment, не приписывать показатель лаборатории без явного правила. |
| `results` | `research` | Одна legacy-строка результата → одно research: `obr_id→sample_id`, `podr_id→lab_id`, `comment`, `recommend→recommendation`, `time_in→received_at`, `time_out→completed_at`, status по таблице выше. Research goal берётся из нормализованного `obrs.target`; пустой target → `LEGACY-TARGET-UNSPECIFIED`. |
| `tests` | `tests` | `result_id→research_id`, `pok_id→indicator_id`, `active→is_active`, `value`, `comment`, `norm`, status по таблице выше, `verdict`: status `1→true`, `2→false`, `3→NULL`. |
| `protocol_types` | `protocol_types` | Stable code `LEGACY-PROTOCOL-TYPE-{id}`, исходное `name`. |
| `zakls` | `conclusions` | `code=LEGACY-ZAKL-{id}`, `name`, `text→text_singular/text_plural`. |
| `protocols` | `protocols` | `year→year_no`, `ex_num→copies`, `simple_status→is_signed`, `file_name→protocol_copy_name`, `file_vyp_name→excerpt_copy_name`, `zakl_id→conclusion_id`, `protocol_type_id→protocol_type_id`. |
| `obr_targets` | legacy audit / goal links | Использовать для проверки связей с `targets`; canonical link создавать только если sample и goal разрешены. Исходную строку всегда сохранять в staging. |
| `acos`, `aros`, `aros_acos` | не импортировать в RBAC | Старую ACL-модель не смешивать с canonical permissions. Доступ задаётся backend registry и текущими roles/permissions. |

## Split / join правила

### ФИО

`users.full_name` и `sandoctors.name_full` разделяются по токенам:

- 3 токена: `last_name`, `first_name`, `patronymic`;
- 2 токена: `last_name`, `first_name`, `patronymic=NULL`;
- инициалы/неоднозначность: не угадывать, сохранить исходную строку в import warning.

### Направление → образец → исследование → тест

Связи строятся только в таком порядке:

```text
naprs.id
  └─ obrs.napr_id       → directions → samples
       └─ results.obr_id → research
            └─ tests.result_id → tests
```

Для каждой созданной строки сохраняются `legacy_table` и `legacy_id` в ETL
mapping. Нельзя связывать строки по имени или по порядку загрузки.

### Лаборатории

`podrs` — старый справочник лабораторных подразделений, а не филиалы. Филиал
(`branches`) назначается только при наличии явного правила; иначе `branch_id=NULL`.

### Цели исследования

`obrs.target` — comma-separated список целей. Пробелы и регистр нормализуются,
алиасы приводятся к значениям `targets`, затем вся комбинация сохраняется как
отдельная research goal. Для 689 строк с пустым target создаётся дополнительная
цель `LEGACY-TARGET-UNSPECIFIED`. Это предотвращает потерю комбинаций вроде
`бак,т/х,т/б,РВ`.

## Orphan policy

Orphan — это строка с FK, для которой parent отсутствует в самом исходном
справочнике; это не удаление при миграции.

Зафиксированные случаи:

- `obrs.protocol_id`: 11 991 строк без protocol → sample импортировать с `protocol_id=NULL`;
- `results.obr_id=0`, `podr_id=0`: 242 строки без sample → оставить только в staging/report;
- `results.podr_id=8`: 28 строк без lab → research импортировать с `lab_id=NULL`;
- `obr_targets.obr_id=0,target_id=0`: 235 строк → оставить только в staging/report.

Canonical import не должен удалять или изменять эти строки в staging.

## Порядок ETL

Реализация контракта находится в `backend/scripts/import_legacy_mysql.py`.
Редактируемая конфигурация находится в
`backend/config/legacy_etl_mapping.json`; Python-код содержит только доменные
адаптеры split/join и преобразование связей.

### Изменение конфигурации

Проверить JSON без подключения к БД:

```bash
cd backend
./.venv/bin/python -m scripts.import_legacy_mysql \
  --mapping-file config/legacy_etl_mapping.json \
  --validate-mapping
```

Поддерживаются следующие изменения без правки Python:

- переименование source/target таблицы через `source_table` / `target_table`;
- переименование атрибута через `source_columns` / `target_columns`;
- удаление необязательного target-атрибута удалением ключа из `target_columns`;
- добавление прямого атрибута через `extra_columns`;
- отключение удалённой таблицы через `enabled: false` вместе с зависимыми сущностями;
- изменение role/status/lab/target dictionaries в `value_maps`;
- добавление простой плоской таблицы в `generic_entities`.

Пример дополнительного атрибута существующей сущности:

```json
{
  "extra_columns": [
    {
      "source": "legacy_external_code",
      "target": "external_code",
      "transform": "text"
    }
  ]
}
```

Допустимые transforms: `raw`, `text`, `int`, `bool`, `datetime_utc`.

Пример новой плоской таблицы:

```json
{
  "generic_entities": [
    {
      "key": "legacy_regions",
      "enabled": true,
      "source_table": "regions",
      "target_table": "regions",
      "source_pk": "id",
      "target_pk": "id",
      "id_strategy": "uuid5",
      "columns": [
        {"source": "name", "target": "name", "transform": "text"}
      ]
    }
  ]
}
```

`generic_entities` предназначены для плоских справочников. Новые таблицы с
FK-remapping, split/join или агрегацией требуют отдельного доменного адаптера.
Валидатор запрещает SQL-идентификаторы с пробелами/SQL-фрагментами и не позволяет
оставить включённую сущность при отключённых обязательных зависимостях.

По умолчанию скрипт выполняет только отчёт:

```bash
cd backend
./.venv/bin/python -m scripts.import_legacy_mysql
```

Запись в canonical-БД выполняется только явно:

```bash
./.venv/bin/python -m scripts.import_legacy_mysql --apply
```

Опционально источником и целью можно управлять через
`--source-database-url` и `--target-database-url`. Скрипт создаёт только
additive-таблицы `legacy_import.id_map` и `legacy_import.warning`; `DELETE`
из canonical-БД не выполняется.

1. Создать/проверить mapping и legacy goals.
2. Сопоставить роли, пользователей, labs, doctors, objects.
3. Загрузить conclusions и protocol types, затем protocols.
4. Загрузить directions.
5. Загрузить sample types, samples и sample-lab links.
6. Загрузить research goals, indicators и research.
7. Загрузить tests.
8. Применить status/deleted policy и сформировать orphan/warning report.
9. Проверить counts, FK, уникальности и выборочные записи через API/UI.

Каждый этап должен быть идемпотентным (`legacy_table + legacy_id`), пакетным и
без `DELETE` из canonical-БД.

## Acceptance checks

- исходные и загруженные counts сравниваются по каждой таблице;
- ни один canonical FK не указывает на отсутствующую строку;
- orphan counts совпадают с этим документом;
- 66 непустых legacy research goals плюс `LEGACY-TARGET-UNSPECIFIED` присутствуют и сохраняют исходные комбинации;
- существующие canonical users/roles не перезаписаны;
- все импортированные legacy users требуют reset пароля;
- staging и исходный дамп остаются доступными после ETL.
