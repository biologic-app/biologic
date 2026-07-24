# Сравнительный отчёт: schema-driven UI движки для рабочих процессов

- Дата: 2026-07-22. Данные сверены через npm registry API, GitHub Releases API и raw
  LICENSE-файлы (не по маркетинговым страницам).
- Цель: решить adopt-vs-build по **трём слоям** (рендер полей / layout экрана / визуальный
  редактор) для движка рабочих процессов LIMS.
- Ограничения стека: Vue 3.5, `@nuxt/ui` v4, strict TS, только явные импорты, bun; лицензии —
  коммерчески безопасные; минимум тяжёлых зависимостей.
- Решение по итогам отчёта — в `docs/architecture/2026-07-22-workflow-engine-adopt-vs-build.md`.

## 1. Критерии сравнения

| # | Критерий | Почему важен |
|---|---|---|
| C1 | Лицензия ядра **и** редактора отдельно | Редакторы SurveyJS/Vueform часто коммерческие при MIT-ядре |
| C2 | Нативность Vue 3 | React/vanilla-ядра тянут второй рантайм или чёрный ящик |
| C3 | Полностью кастомные рендереры под Nuxt UI | Обязательное условие — наш дизайн-язык Nuxt UI |
| C4 | Layout в схеме (грид/колонки) | У нас свой грид 12 колонок — оцениваем, стоит ли брать |
| C5 | Визуальный редактор (и его лицензия) | Слой 3 |
| C6 | Вес / зависимости / tree-shaking под strict TS | Bundle и трение сборки |
| C7 | Активность поддержки | Риск заброшенности |

## 2. Кандидаты (факты)

### JSON Forms (`@jsonforms/vue`)
- **C1:** MIT везде (core, vue, vue-vanilla, vue-vuetify). Редактора нет (experimental заброшен).
- **C2:** нативный официальный Vue 3 пакет + рендер-сеты vanilla/vuetify. Nuxt UI-сета нет.
- **C3:** полная замена рендереров через `JsonFormsRendererRegistryEntry {renderer, tester}` +
  `rankWith()` — общий механизм, а не спецкейс (так устроены сами vanilla/vuetify).
- **C4:** слабый — HorizontalLayout (равные доли, без span), Vertical, Group, Categorization
  (табы). Грид/произвольные колонки «из коробки» отсутствуют.
- **C5:** нет.
- **C6:** ~92KB gzip рабочий минимум (`vue` 9 + `core` 68 + `vue-vanilla` 15); чистый TS/ESM,
  strict-friendly.
- **C7:** скромная (2 релиза/год + патчи); MIT/Eclipse Foundation. Версия 3.8.0 (2026-06-16).

### FormKit (`@formkit/vue`)
- **C1:** core MIT; **Pro** (repeater, datepicker, autocomplete…) — платный license key
  (бесплатно на dev, платно в prod). Классического билдера нет (Kickstart — платный AI, не то).
- **C2:** Vue 3 only, framework-first.
- **C3:** через API секций (`outer/wrapper/inner/…`) + `$cmp`/`library` — подмена любой части
  маркапа своими компонентами.
- **C4:** нет грида в схеме; компоновка через `$el` + свой Tailwind (ложится на Nuxt UI, но не
  «из коробки»).
- **C6:** 33KB gzip, 9 зависимостей; strict-friendly, явные импорты ок.
- **C7:** 4 релиза/год. Версия 2.1.0 (2026-06-10).
- **Оговорка:** `repeater` (наш `table`) — в **Pro** (платно).

### Vueform (`@vueform/vueform`)
- **C1:** ядро MIT (сверено по raw LICENSE). **Builder** (визуальный конструктор) — коммерческий
  SaaS (~$82/мес).
- **C2:** нативный Vue-only.
- **C3:** override/регистрация кастомных elements (component-override, не registry+tester).
- **C4:** **лучший из Vue-нативных** — `columns`/`size` per-элемент (responsive spans) из коробки.
- **C6:** 241KB gzip (895KB raw), 15 зависимостей, unpacked 17.5MB; хуже tree-shaking (монолит).
- **C7:** активно (1.13.13, 2026-06-22).

### form-create (`@form-create/*`)
- **C1:** MIT везде, включая `@form-create/designer` (drag-drop редактор).
- **C2:** Vue 3 есть, но **жёсткая привязка к UI-китам** (Element Plus / Ant / Naive / Vant /
  Varlet); headless-ядра нет → для Nuxt UI нужен свой renderer-пакет (`formCreate.component()`).
- **C4:** через row/col примитивы конкретного кита.
- **C5:** `@form-create/designer` — MIT, drag-drop (обновлялся ноя 2025).
- **C7:** умеренная, по сути один мейнтейнер, доки/комьюнити на китайском. Naive-линия живее
  (3.3.1, июнь 2026).
- **Внимание:** старый `form-create` (Vue 2) заброшен с 2019 — не использовать.

### SurveyJS
- **C1:** рендер `survey-core`/`survey-vue3-ui` — MIT; **Creator** (редактор) — коммерческий
  (лицензия на разработчика, ~$557–1998/dev).
- **C2:** обёртка `survey-vue3-ui` над MobX-агностик-ядром (не Vue-first).
- **C3:** `Serializer.addClass()` + composite question API + документированная интеграция своих
  Vue 3 компонентов как question types.
- **C4:** нативный грид (`columns` + `gridLayoutEnabled`), pages/panels.
- **C5:** Survey Creator — самый зрелый редактор из всех, но коммерческий.
- **C6:** тяжёлый — `survey-core` 289KB gzip + `vue3-ui` +53KB → ~340KB+; MobX + обёртка = трение
  под strict TS.
- **C7:** очень активен (48 релизов/год; 2.5.35 2026-07-21; v3.0 вышел параллельно).

### Form.io (`@formio/js`)
- **C1:** клиентский рендерер+**встроенный билдер** — MIT (сервер `formio` OSL-3.0 — нам не нужен,
  у нас свой FastAPI). Билдер бесплатен.
- **C2:** **нет нативного Vue 3** — vanilla JS/ES6 чёрный ящик; `@formio/vue` монтирует свой DOM,
  не Vue-реактивность.
- **C3:** OOP class-extension (`Components.baseComponent`) на чистом JS — борьба с собственным
  DOM-менеджментом при попытке своих Vue-компонентов.
- **C4:** богатый (Columns/Panel/Table/Tabs/Well/FieldSet/HTML).
- **C6:** unpacked 23.7MB; собственный DOM, наследие jQuery-эры — худшая посадка под strict TS /
  идиоматичный Vue.
- **C7:** активен (`@formio/js` 5.4.3, 2026-07-21); легаси `formiojs` заброшен.

### amis (`baidu/amis`)
- **C1:** ядро Apache-2.0, `amis-editor` ISC.
- **C2:** **нет Vue 3** — React+MobX (peerDeps react/react-dom); Vue-обёртки встраивают React-
  рантайм (микрофронтенд). Для нашего стека = второй UI-рантайм в бандле.
- **C4:** богатейший layout (grid/flex/panel/tabs).
- **C5:** amis-editor — полноценный low-code page builder (ISC), но React.
- **C6:** `amis` unpacked 77.3MB, `amis-core` 7.8MB — на порядок тяжелее всех.
- **C7:** **устарел** — ~11 мес без публикации в npm (6.13.0, 2025-08-12), хотя коммиты шли до
  марта 2026. Тревожный сигнал.

### Новые игроки (июль 2026)
Зрелых альтернатив нет. shadcn-vue AutoForm / FormCN — тонкие Zod→форма генераторы (без layout-
системы и редактора). У Nuxt UI встроенного schema→form нет (nuxt/ui issue #786 открыт). Внутри
form-create растут рендер-пакеты под новые киты — рост игрока, не новый конкурент.

## 3. Сводная матрица

| Кандидат | C1 ядро/редактор | C2 Vue3 | C3 Nuxt UI рендер | C4 layout | C5 редактор | C6 вес gzip | C7 |
|---|---|---|---|---|---|---|---|
| JSON Forms | MIT / — | нативный | registry+tester (чисто) | слабый | нет | ~92KB | скромн. |
| FormKit | MIT / Pro платно | нативный | секции/$cmp | нет | нет | 33KB | средн. |
| Vueform | MIT / Builder платн. | нативный | override | **лучший** | платный | 241KB | активн. |
| form-create | MIT / MIT | привязан к китам | свой пакет нужен | через кит | MIT designer | ~core | 1 мейнт. |
| SurveyJS | MIT / Creator платн. | обёртка/MobX | addClass API | нативный | зрелый, платн. | ~340KB | оч.активн. |
| Form.io | MIT / MIT | нет (vanilla) | OOP JS, чужой DOM | богатый | MIT встроен | 23.7MB unp. | активн. |
| amis | Apache/ISC | **нет (React)** | React registry | богатейший | React | 77MB unp. | устарел |

## 4. Итог по слоям

### Слой 1 — рендер полей: **BUILD** (Option A подтверждён)
Реальные кандидаты на adopt — только JSON Forms и FormKit (MIT-ядро, Vue3-нативность, кастомные
рендереры, приемлемый вес). Остальные отпадают по C2/C6/C1 (Form.io и amis — не Vue-нативны и
тяжелы; Vueform — тяжёл и монолитен; SurveyJS — тяжёл, MobX-обёртка; form-create — привязан к
чужим китам).

Но центральное обещание Option B — «adopt испаряет Фазу 4» — **фактами не подтверждается**:
1. **Кастомные Nuxt UI-рендереры всё равно писать** — ни JSON Forms, ни FormKit не дают
   Nuxt UI-контролов; их «из коробки» рендереры — под другие киты (vanilla/vuetify/собственный).
   C3 у обоих есть, но это работа, а не бесплатная выгода.
2. **Дифференцирующие типы полей проектно-специфичны и не идут «из коробки» нигде:**
   `dictionary` (данные из catalogs-эндпоинтов LIMS через SDK), `computed` (json-logic поверх
   answers нашего движка), `table` с доменной привязкой к `execute-step`. Их пришлось бы
   реализовывать поверх любой библиотеки.
3. **`table`/repeater у FormKit — в Pro (платно)**; у JSON Forms массивы есть, но с тем же
   объёмом кастомного рендера под Nuxt UI.
4. **Layout мы строим сами** (слой 2, ниже) — сильная сторона Vueform/SurveyJS (C4) для нас
   нерелевантна.
5. **Второй слой абстракции** (наша схема ↔ схема библиотеки) + риск конфликта со strict TS /
   явными импортами — чистая издержка.

Итог: adopt слоя полей не даёт заявленной экономии; 6 примитивов уже рендерятся нативным Nuxt UI
(эволюция `JournalRunner.vue:325-352`), а тяжёлая часть MVP-библиотеки (dictionary/computed/table)
одинаково кастомна при любом выборе. Решение — **build**. Это не sunk-cost: центральный тезис
Option B опровергнут фактами, а не отклонён из привязанности к прототипу.

### Слой 2 — layout экрана: **BUILD**
Наша модель `Screen → Row → Block{span}` (schema-doc §3) рендерится CSS-грид + Nuxt UI (~150
строк). Adopt (Vueform/SurveyJS-грид) требует чужой системы вёрстки поверх Tailwind/Nuxt UI —
трения больше, чем экономии.

### Слой 3 — визуальный редактор: **BUILD**
Ни один кандидат не даёт graph-first редактора (наша модель — граф с условиями/циклами). Билдеры
form-центричны: SurveyJS Creator и Vueform Builder — коммерческие; Form.io Builder и amis-editor —
чужой рантайм (vanilla/React); `@form-create/designer` MIT, но привязан к чужому киту. Граф-
редактор уже есть на VueFlow; грид-редактор экрана строим на HTML5 DnD + CSS Grid.

## 5. Заимствуемые идеи (даже при build)
- **JSON Forms registry+tester** — образец чистой архитектуры для нашего маппинга `field.type →
  компонент` (расширяемость новыми типами без ветвлений).
- **Vueform `columns/size`** — валидирует наш выбор span-модели грида.
- **SurveyJS `gridLayoutEnabled` / composite questions** — образец для `table`-блока.
- **form-create designer (MIT)** — референс UX drag-and-drop для нашего ScreenEditor.

## Приложение. Оговорки по данным
- Веса gzip части тяжёлых пакетов (Form.io, amis) недоступны через bundlephobia (таймаут по
  размеру) — приведён unpacked-размер как нижняя граница оценки.
- Границы «бесплатно/платно» у SurveyJS Creator и Vueform Builder — по вендорским прайсам июля
  2026; уточнение стоимости на команду — при необходимости отдельным запросом.
