# Единый мастер создания направлений (импорт + ручное) — план

Дата: 2026-07-13. Статус: согласован, в реализации.

## Цель

Объединить импорт направлений и ручное создание в один мастер, где оператор
создаёт направление и образцы в одном месте и может **добавлять/удалять образцы
до регистрации** черновика.

## Что уже есть (backend — менять не нужно)

Все нужные эндпоинты существуют в `laboratory_workflow/presentation/router.py`:

- `POST /directions` — создать черновик (обязателен `year_no: int`; `base_no` и
  прочее опционально). Backend проверяет уникальность пары `(year_no, base_no)`,
  но **не** присваивает `base_no` сам.
- `POST /directions/{id}/samples` — добавить образец (обязателен `name`).
- `PATCH /directions/{id}`, `PATCH /samples/{id}` — правка.
- `DELETE /samples/{id}`, `DELETE /directions/{id}` — удаление до регистрации.
- `POST /directions/{id}/register`, `assign-research`, `labs`, `research-goal-suggestions`.

Шаг «Дозаполнение» (`ImportFillStep`) уже фактически редактор «направление +
образцы» (поля направления, поля образца, лаборатории, цели). Не хватает только
добавления/удаления образцов и обёрток create/delete во фронтовом API.

## Решения (согласовано с оператором)

1. **Точка входа** — отдельный экран выбора режима: карточки «Импорт из файла» /
   «Создать вручную» (гейт по правам `import` / `create`).
2. **Нумерация** — авто на фронте: год = текущий, `base_no` = следующий за год;
   оба значения **редактируемы** оператором.
3. **Образцы** — добавление + удаление + правка в шаге дозаполнения.
4. **Реквизиты** (год/номер) — встроены в шаг Fill (не отдельный шаг). Черновик
   создаётся сразу при выборе «вручную»; год/номер редактируются в шапке Fill.
5. **Ренейм** — `DirectionImportWizard` → `DirectionWizard`,
   `useDirectionImport` → `useDirectionWizard`.

## Модель шагов

`ctx.step` переводится на строковые ключи; активный набор зависит от `mode`:

- `mode='import'`: `upload → review → fill → register`
- `mode='manual'`: `fill → register` (черновик создан заранее, реквизиты в Fill)
- `mode='draft'` (из строки таблицы): `fill → register`
- `mode='select'`: экран выбора (без степпера)

## Изменения по файлам (frontend)

| Файл | Изменение |
|---|---|
| `directions.api.ts` | +`createDirection`, `createSample`, `deleteSample`, `fetchNextBaseNo` |
| `useDirectionImport.ts` → `useDirectionWizard.ts` | `mode`, строковые шаги, `chooseImport`, `startManual`, `addSample`, `removeSample`; общий `hydrateFillStep` для manual/draft; `year_no`/`base_no` в `persistDirection` |
| `DirectionImportWizard.vue` → `DirectionWizard.vue` | экран выбора, mode-aware степпер и футер-навигация |
| `ModeSelectStep.vue` (new) | карточки выбора режима, гейт по правам |
| `ImportFillStep.vue` | редактируемая шапка год/номер, кнопка «+ образец», удаление образца с подтверждением |
| `DirectionsPage.vue` | одна кнопка «Создать направление» → режим `select`; действие строки «Дозаполнить» → режим `draft`; права `import`/`create` прокидываются в мастер |
| `tests/e2e/direction-lifecycle.spec.ts` | обновить шаги ручного создания под новый мастер (сейчас `test.fixme`) |

Backend и SDK не затрагиваются (нумерация — на фронте).

## Риски / крайние случаи

- **Гонка `base_no`**: одинаковый следующий номер у двух операторов → 409 на
  create; показываем ошибку, даём поменять номер. FE-автоинкремент — best-effort.
- Образец с пустым `name` в черновике допустим; регистрация блокируется
  валидацией (`direction_missing_sample_data` / `direction_missing_samples`).
- Права `create` и `import` разные — карточки гейтятся раздельно.
- Ренейм: импорты только в `DirectionsPage.vue` + 4 шаг-компонента.

## DoD

`cd frontend && bun run lint typecheck build` + `bun test tests/shared`; ручная
проверка трёх путей (импорт / вручную + образцы / draft из строки) и регистрации.
