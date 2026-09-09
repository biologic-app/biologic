# Нормативная структура frontend

## Статус документа

Документ задаёт целевую структуру frontend-проекта Biologic. Он является нормативным: новые файлы и каталоги должны соответствовать этим правилам, а существующие исключения должны быть явно перечислены в разделе «Исключения» или в allowlist соответствующего автоматического правила.

Корневой каталог frontend: `biologic/frontend/`.

Правила, отмеченные именем Python-скрипта, должны проверяться из корня репозитория. Скрипты находятся в `scripts/rule/structure/`. Если скрипт ещё не реализован, указанное имя является нормативным именем проверки, которую необходимо реализовать до включения правила в обязательный quality gate.

## 1. Назначение структуры

Структура должна:

- отделять запуск приложения от предметных модулей;
- направлять зависимости от UI к предметной логике и инфраструктуре, но не наоборот;
- делать границы feature-модулей видимыми по файловой системе;
- локализовать API, state, domain rules и UI конкретной функции;
- не превращать `shared` в свалку feature-кода;
- позволять проверять структуру, naming и зависимости AST/CST-анализом;
- сохранять предсказуемое размещение тестов, generated-кода и технических файлов.

Главное правило декомпозиции: если в одном смысловом каталоге становится больше 7 исходных файлов, они должны быть сгруппированы в подкаталоги по назначению. Правило применяется к исходным `.ts`, `.tsx`, `.vue`, `.js`, `.jsx` и `.css`, но не применяется механически к generated/vendor/build/node_modules и другим техническим каталогам.

## 2. Эталонное дерево каталогов

```text
frontend/
├── public/                         # статические публичные ресурсы
├── src/
│   ├── app/                        # composition root приложения
│   │   ├── layouts/
│   │   ├── router/
│   │   ├── store/                  # только создание/подключение store-системы
│   │   └── styles/
│   ├── pages/                      # route entry points
│   ├── modules/                    # предметные feature-модули
│   │   └── <feature>/
│   │       ├── api/
│   │       ├── components/
│   │       ├── composables/
│   │       ├── domain/
│   │       ├── pages/
│   │       ├── services/
│   │       ├── stores/
│   │       ├── types/
│   │       └── data/                # только декларативные demo/seed данные
│   ├── shared/
│   │   ├── api/                     # общий transport/API client
│   │   ├── components/              # действительно feature-neutral UI
│   │   ├── composables/             # действительно переиспользуемые composables
│   │   ├── config/
│   │   ├── constants/
│   │   ├── domain/                  # общие domain primitives
│   │   ├── i18n/
│   │   ├── services/               # общие application services
│   │   ├── stores/                  # только shared stores
│   │   ├── types/
│   │   └── utils/
│   ├── main.ts
│   └── sw.ts
├── tests/
│   ├── shared/
│   └── e2e/
├── scripts/                        # только frontend-local tooling, если нужно
└── [tooling/config files]
```

Текущий `src/shared/ui/` следует считать переходным именем. Новые универсальные Vue-компоненты размещаются в `src/shared/components/`; существующий `shared/ui` допускается до миграции по allowlist.

## 3. Ответственность каталогов

### `src/app`

Содержит сборку приложения: bootstrap, layouts, router, router guards, регистрацию plugins, глобальные стили и подключение Pinia. Здесь не размещается бизнес-логика feature-модулей.

### `src/pages`

Содержит только route-level entry points. Страница может собирать компоненты и composables модуля, но не должна содержать повторяемую domain/API-логику.

### `src/modules/<feature>`

Изолированный предметный модуль. Модуль владеет своей страницей, UI, API-адаптерами, domain-правилами, composables, stores и типами. Модуль не должен импортировать внутренности другого модуля; общий контракт выносится в `shared` или в явно разрешённый публичный entry point.

### `api`

API-адаптеры и запросы конкретного модуля. Здесь преобразуются transport DTO в модель, используемую feature-кодом. Компоненты не вызывают `fetch` напрямую.

### `components`

Vue-компоненты конкретного модуля. Компонент отвечает за представление и локальное взаимодействие, а не за общий API transport.

### `composables`

Reactive/application logic конкретного модуля, оформленная как `useXxx`. Composable может обращаться к API, store и domain этого же модуля.

### `domain`

Чистые правила предметной области, преобразования и проверки. Domain-код не импортирует Vue-компоненты, router, `window`, `document` и UI-библиотеки.

### `pages` внутри модуля

Допускается для feature-owned route pages. Такие страницы подключаются из router через публичный entry point модуля либо напрямую только по установленному правилу проекта. Нельзя одновременно бессистемно размещать одинаковый тип страниц в корне и внутри модулей.

### `services`

Долгоживущие application/infrastructure services: realtime, telemetry, storage, browser integration и т. п. Service не является Vue-компонентом и не должен маскироваться под composable.

### `stores`

Pinia stores конкретного модуля. Store содержит состояние и state transitions, но не markup. Shared store размещается в `src/shared/stores`, app store setup — в `src/app/store`.

### `shared`

Только код, который не знает о конкретном feature-модуле. `shared` не импортирует `modules`, `pages` или feature-specific код. Общие API-клиенты могут быть инфраструктурой, но feature endpoint adapters остаются в модуле.

### `tests`

`tests/shared` содержит unit/integration-тесты с зеркальной группировкой по слоям. `tests/e2e` содержит сценарии браузера, fixtures и Playwright support-код.

### Generated/vendor/build

Сгенерированные SDK, vendor-код, `node_modules`, `dist`, кэши и отчёты являются техническими каталогами. Они не подлежат механической декомпозиции и не должны редактироваться вручную.

## 4. Правила размещения файлов

1. Route entry point размещается в `src/pages` или в `<feature>/pages` согласно единой модели feature. Для нового кода предпочтительна feature-owned страница.
2. Компонент размещается рядом с потребляющим feature; в `shared/components` — только при наличии минимум двух независимых потребителей или заранее определённого framework-level назначения.
3. API конкретной функции размещается в `<feature>/api`; общий HTTP client — в `shared/api`.
4. Pinia store размещается в `<feature>/stores` или `shared/stores`, а не в `composables`.
5. Domain rules не размещаются в `.vue`-файлах.
6. Декларативные типы публичного feature-контракта размещаются в `<feature>/types`; общие типы — в `shared/types`.
7. Вспомогательная функция получает каталог по смыслу, а не по форме: форматирование — `utils`, бизнес-правило — `domain`, UI helper — рядом с UI-подсистемой.
8. Нельзя добавлять новый файл в перегруженный смысловой каталог без создания подкаталога либо записи об исключении.

Проверка: `scripts/rule/structure/check_file_placement.py`.

## 5. Правила декомпозиции каталогов

Для каждого смыслового каталога считается количество исходных файлов непосредственно в нём. При количестве больше 7 обязательна группировка по назначению: например, `components/form`, `components/table`, `components/navigation` или `api/generated`.

Дополнительные ограничения:

- generated/vendor/build/node_modules и явно перечисленные технические каталоги исключаются;
- каталог не следует дробить, если подкаталоги не выражают устойчивые смысловые границы;
- один подкаталог не должен быть создан только ради одного файла, кроме публичного entry point или специального технического файла;
- крупный компонент не превращается в набор случайных файлов: декомпозиция должна следовать ответственности и dependency direction;
- файлы размером более 500 строк или 30 KB требуют архитектурного обоснования либо декомпозиции.

Проверки:

- `scripts/rule/structure/check_directory_threshold.py`
- `scripts/rule/structure/check_file_size.py`

## 6. Правила именования файлов

- Vue-компоненты: `PascalCase.vue`.
- Route pages: `PascalCasePage.vue`.
- Composables: `useCamelCase.ts`.
- Stores: `useCamelCase.store.ts` или `useCamelCase.ts` внутри `stores/`; формат выбирается один раз для проекта.
- API-адаптеры: `kebab-case.api.ts`.
- Services: `kebab-case.service.ts`.
- Types: `kebab-case.ts` или `types.ts` для небольшого локального набора.
- Utilities/domain/config/constants: `kebab-case.ts`.
- Тесты: `*.test.ts` для unit/integration, `*.spec.ts` для E2E.
- Generated: только в `generated/`, с суффиксом `.gen.ts`.
- Barrel-файлы называются `index.ts` и не должны скрывать циклические или запрещённые зависимости.

Проверка: `scripts/rule/structure/check_file_naming.py`.

## 7. Правила именования компонентов

- Имя файла и имя компонента — PascalCase и совпадают по смыслу.
- Компонент должен иметь минимум два слова, кроме общепринятых framework/application names (`App`, `RouterView`, `Suspense` и т. п.).
- Суффиксы отражают роль: `Page`, `Layout`, `Modal`, `Dialog`, `Drawer`, `Panel`, `Table`, `Form`, `Card`, `Badge`, `Icon`, `Node`.
- Feature-компонент не получает имя `Shared*`, если он не является shared.
- Не допускаются generic-имена `Component`, `Thing`, `Helper`, `Common` без предметного уточнения.

Проверка: `scripts/rule/structure/check_component_naming.py`.

## 8. Правила именования функций

- Функции и переменные используют `camelCase`.
- Обработчики событий начинаются с `on`: `onSubmit`, `onNodeDrop`.
- Предикаты начинаются с `is`, `has`, `can`, `should`.
- Создатели объектов/конфигураций — `create` или `build`.
- Преобразования — `to`, `from`, `map`, `normalize`, `resolve`.
- Форматтеры — `format`.
- Async-функция называется по действию, а не по технической реализации.
- Нельзя называть composable-функцию без префикса `use`.

Проверка: `scripts/rule/structure/check_symbol_naming.py`.

## 9. Classes, types, interfaces, enums

- `class`, `type`, `interface`, `enum` используют PascalCase.
- Интерфейсы не получают обязательный префикс `I`.
- Типы-массивы, DTO, props и state получают предметные имена: `UserRow`, `JournalSchema`, `LoginFormState`.
- Суффиксы допускаются по роли: `Props`, `Emits`, `State`, `Options`, `Config`, `Params`, `Result`, `Response`, `Dto`.
- Enum должен описывать устойчивый закрытый набор. Для локальных discriminated unions предпочтителен `type` с literal values.
- Публичные типы feature не объявляются внутри большого компонента, если они используются более чем в одном файле.

Проверка: `scripts/rule/structure/check_type_naming.py`.

## 10. Hooks, composables, stores, services

### Composables

- Именуются `useXxx`.
- Возвращают объект с согласованными именами состояния и действий.
- Не содержат markup.
- Shared composable не импортирует feature-модули.
- Browser side effects должны быть локализованы и явно названы.

### Stores

- Объявляются только через `defineStore` в `stores/`.
- Store id уникален и соответствует имени store.
- Store не импортирует компоненты.
- API вызовы выполняются через API/service слой, а не через произвольный `fetch` в store.

### Services

- Именуются `xxx.service.ts`.
- Не используют `defineStore` и не притворяются composables.
- Не содержат template/UI-кода.
- Должны иметь ясный жизненный цикл и область ответственности.

Проверки:

- `scripts/rule/structure/check_composable_store_service.py`
- `scripts/rule/structure/check_direct_side_effects.py`

## 11. Допустимые зависимости между слоями

Допустимое направление:

```text
app -> pages -> modules -> shared
app -> shared
modules -> собственные api/domain/services/stores/types/components/composables
shared/components -> shared/composables, shared/types, shared/utils, shared/domain
shared/api -> shared/types, shared/config
domain -> types, pure utils
```

Запрещено:

- `shared -> modules`;
- `shared -> pages`;
- `shared -> app`;
- `domain -> Vue/UI/router/browser APIs`;
- компонент -> прямой `fetch`, если запрос не является специально разрешённым browser download;
- модуль -> внутренности другого модуля;
- циклические зависимости между модулями;
- импорт generated SDK из произвольного UI-кода при наличии feature API-адаптера.

Разрешённые исключения должны быть заданы allowlist с объяснением и владельцем.

Проверка: `scripts/rule/structure/check_dependency_layers.py`.

## 12. Исключения

1. `src/shared/api/generated/**` — generated OpenAPI-код; исключён из naming, size и decomposition checks, но проверяется расположение и отсутствие ручного редактирования.
2. `node_modules`, `dist`, `dev-dist`, `dist-ssr`, build-кэши и Playwright artifacts — технические каталоги; не анализируются как исходники.
3. `src/sw.ts` — service worker entry point; может использовать browser/service-worker API и не обязан следовать правилам Vue-компонентов.
4. `src/app/main.ts` — bootstrap entry point; допускает прямую сборку приложения.
5. `src/shared/ui/**` — существующий переходный каталог. Новые feature-specific компоненты туда не добавляются; существующие перечисляются в allowlist миграции.
6. `src/modules/*/pages/**` и `src/pages/**` — обе модели временно поддерживаются. Для нового route-level кода применяется выбранная проектом feature-owned модель.
7. Сгенерированные типы и большие translation dictionaries могут превышать лимиты размера, если находятся в предусмотренном technical/generated каталоге.
8. Browser storage, downloads и telemetry могут использовать `localStorage`, `fetch`, `window` или `document` только в разрешённых service/API/composable-файлах, перечисленных в allowlist.

Проверка исключений: `scripts/rule/structure/check_allowlist.py`.

## 13. Реестр автоматических правил

| Python-скрипт | Правило | Объект проверки |
|---|---|---|
| `scripts/rule/structure/check_file_placement.py` | размещение файлов по слоям и назначению | пути файлов, AST импортов |
| `scripts/rule/structure/check_directory_threshold.py` | не более 7 исходных файлов в смысловом каталоге | дерево каталогов |
| `scripts/rule/structure/check_file_size.py` | лимиты размера и строк | `.ts`, `.vue`, `.tsx`, `.js`, `.css` |
| `scripts/rule/structure/check_file_naming.py` | соглашения имён файлов | все frontend source files |
| `scripts/rule/structure/check_component_naming.py` | имена Vue-компонентов | Vue SFC AST |
| `scripts/rule/structure/check_symbol_naming.py` | имена функций, переменных и обработчиков | TypeScript/Vue AST |
| `scripts/rule/structure/check_type_naming.py` | имена classes/types/interfaces/enums | TypeScript AST |
| `scripts/rule/structure/check_composable_store_service.py` | различение composables, stores и services | imports, exports, `defineStore`, AST |
| `scripts/rule/structure/check_direct_side_effects.py` | запрет прямых `fetch`, storage и browser effects в UI | TypeScript/Vue AST |
| `scripts/rule/structure/check_dependency_layers.py` | допустимые направления импортов и отсутствие циклов | AST import graph |
| `scripts/rule/structure/check_allowlist.py` | корректность и актуальность исключений | allowlist + filesystem |

Проверки TypeScript/Vue должны использовать CST/AST-парсинг: Vue SFC parser для `.vue`, TypeScript AST для `.ts`/`.tsx` и отдельный анализ `script`/template-блоков. Regex допускается только для простых проверок пути, расширения и имени файла; он не является достаточным способом проверки символов, импортов, вызовов или структуры исходного кода.
