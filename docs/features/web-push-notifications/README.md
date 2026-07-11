# Web Push + PWA в notifications context

Доставка push-уведомлений на уровень ОС (Windows / Linux) поверх существующего
in-app-канала (SSE `/alerts/stream`). Пользователь получает нативный тост, даже
когда вкладка приложения не в фокусе, а установленная PWA — когда окно свёрнуто
(пока жив фоновый процесс браузера).

> Трекер работ — чеклист ниже. Отмечайте `- [x]` по мере выполнения.

## Цель и границы

- **В scope:** Web Push (VAPID) + оформление фронта как PWA, хранение подписок,
  рассылка из notifications context, отписка/чистка протухших подписок.
- **Вне scope:** нативные десктоп-агенты (Electron/Tauri/tray) — отклонены
  (условие «только браузер»); гарантированная доставка через outbox — вынесена в
  «Дальнейшее усиление».
- **Планка доставки:** best-effort, пока у пользователя запущен браузер (в т.ч. в
  фоне). Полностью выключенный браузер веб-push в реальном времени не доставит —
  это ограничение технологии, не бага.

## Архитектурные решения

1. **Push — дополнительный канал, не замена.** SSE + непрочитанные в БД остаются
   источником истины; при заходе в приложение пользователь видит всё пропущенное.
2. **Отправка строго после `uow.commit()`.** `WorkflowNotificationSubscriber`
   вызывается до коммита (`create_many` делает только `flush`). Subscriber
   накапливает созданные `NotificationRecord` в push-outbox, а
   `WorkflowCommandService._publish_events` после `uow.commit()` передаёт их
   диспетчеру. Иначе можно отправить push по откатившейся транзакции.
3. **Рассылка не блокирует ответ API.** Запросы к push-сервисам уходят в фон
   (`asyncio.create_task`); задачи трекаются и дренируются в `lifespan` —
   переиспользуем graceful-shutdown-инфраструктуру (`app.state.shutdown_event`).

---

## Фаза 0 — Подготовка (VAPID + зависимости)

- [ ] Сгенерировать VAPID-пару (`openssl` / `vapid --gen`): `public` (base64url) и `private`
- [ ] `backend/pyproject.toml` → `[project].dependencies`: добавить `pywebpush>=2.0.0` (тянет `py-vapid` + `http-ece`); `cryptography` уже присутствует
- [ ] `backend/src/core/config.py` (`Settings`): поля `vapid_public_key: str`, `vapid_private_key: str`, `vapid_subject: str = "mailto:afims568@gmail.com"` (читаются как `APP_VAPID_*`)
- [ ] `backend/.env.example`: добавить `APP_VAPID_PUBLIC_KEY=`, `APP_VAPID_PRIVATE_KEY=`, `APP_VAPID_SUBJECT=`
- [ ] Реальный `.env` заполнить ключами локально (не коммитить)

## Фаза 1 — Backend: хранилище подписок

- [ ] Модель `backend/src/infrastructure/db/models/push_subscription.py` (таблица `push_subscriptions`), по образцу `subscription.py`:
  - [ ] `id` UUID PK, `server_default uuidv7()`
  - [ ] `user_id` UUID, FK `users.id` `ON DELETE CASCADE` (`fk_push_subscriptions_user_id_users_id`)
  - [ ] `endpoint` Text, **UNIQUE**, not null
  - [ ] `p256dh` Text not null, `auth` Text not null
  - [ ] `user_agent` Text nullable (для UI «мои устройства»)
  - [ ] `created_at` TIMESTAMPTZ `DEFAULT CURRENT_TIMESTAMP`
- [ ] Зарегистрировать модель в `backend/src/infrastructure/db/models/__init__.py` (импорт + `__all__`)
- [ ] Миграция `backend/migrations/versions/20260713_0027_push_subscriptions.py` (`down_revision = "20260712_0026"`), сырой SQL `op.execute(...)`: `CREATE TABLE ... DEFAULT uuidv7()`, `CREATE UNIQUE INDEX push_subscriptions_endpoint`, `CREATE INDEX push_subscriptions_user_id`; `downgrade` — `DROP TABLE`
- [ ] Порт `PushSubscriptionStore(Protocol)` в `backend/src/contexts/notifications/application/ports.py`: `upsert(...)`, `delete_by_endpoint(endpoint)`, `list_for_users(user_ids: set[UUID])`
- [ ] Адаптер `backend/src/contexts/notifications/infrastructure/push_subscription_repository.py` (`SqlAlchemyPushSubscriptionStore`): `upsert` = `INSERT ... ON CONFLICT (endpoint) DO UPDATE`
- [ ] `uv run alembic upgrade head` — миграция применяется без ошибок

## Фаза 2 — Backend: эндпоинты подписки

- [ ] `GET /push/vapid-public-key` → `{data: {public_key}}` из `settings.vapid_public_key` (публичный, без auth)
- [ ] `POST /push/subscriptions` (auth) — тело `{endpoint, keys:{p256dh, auth}}` → `upsert` на `viewer_id` (`get_current_user_id`)
- [ ] `DELETE /push/subscriptions` (auth) — тело `{endpoint}` → `delete_by_endpoint`
- [ ] Pydantic-схемы запросов/ответов рядом с `AlertItem` в `presentation/router.py`
- [ ] Проверить итоговые пути `/api/v1/push/*` (роутер уже включён без доп. префикса)

## Фаза 3 — Backend: рассылка (ядро)

- [ ] Порт `PushSender(Protocol)` в `application/ports.py`: `async def send_many(records: Iterable[NotificationRecord]) -> None`
- [ ] Адаптер `backend/src/contexts/notifications/infrastructure/web_push_sender.py` (`WebPushSender`):
  - [ ] группировка записей по `target_user_id`, выборка подписок `store.list_for_users(...)`
  - [ ] тонкий payload `{title, message, entity_type, entity_id, alert_id}` (минимизация чувствительных данных)
  - [ ] отправка `await asyncio.to_thread(webpush, ...)` (pywebpush синхронный — не блокировать loop)
  - [ ] на `WebPushException` 404/410 → `store.delete_by_endpoint(...)`; прочие ошибки — в лог, не роняя остальные
- [ ] Диспетчер `backend/src/contexts/notifications/application/push_dispatcher.py` (`PushDispatcher`): `dispatch(records)` → `asyncio.create_task`, трекинг `set` задач, `async def drain()`
- [ ] Синглтон-диспетчер создаётся в `app_factory`, кладётся в `app.state.push_dispatcher`
- [ ] В `lifespan` (`src/core/lifecycle.py`) — `await dispatcher.drain()` перед выходом
- [ ] `subscribers.py`: `WorkflowNotificationSubscriber` принимает `push_outbox: list[...]`, в `__call__` захватывает `records = await create_many(...)` (сейчас результат отбрасывается) и `push_outbox.extend(records)`
- [ ] `laboratory_workflow/application/commands.py::_publish_events`: создать `outbox=[]`, прокинуть в subscriber; **после `uow.commit()`** — `push_dispatcher.dispatch(outbox)`

## Фаза 4 — Контракт (SDK)

- [ ] `make be-lint be-test` зелёные
- [ ] Поднять API → `cd frontend && bun run sdk:generate` (новые `/push/*` попадут в `sdk.gen.ts`)
- [ ] `bun run typecheck` без ошибок

## Фаза 5 — Frontend: включить PWA + Service Worker

- [ ] `frontend/vite.config.ts`: раскомментировать `VitePWA`, `strategy: 'injectManifest'`, `srcDir: 'src'`, `filename: 'sw.ts'`, `registerType: 'autoUpdate'` (manifest и иконки `icon-192/512` уже есть)
- [ ] Новый `frontend/src/sw.ts`:
  - [ ] `precacheAndRoute(self.__WB_MANIFEST)`
  - [ ] обработчик `push` → `self.registration.showNotification(title, { body, icon, data: { url } })`
  - [ ] обработчик `notificationclick` → фокус/`clients.openWindow(url)` по `entity_type`+`entity_id`
- [ ] Регистрация SW в `frontend/src/main.ts` после `mount` (по образцу `initTelemetry`), `import { registerSW } from 'virtual:pwa-register'`; только при поддержке и не в dev-http

## Фаза 6 — Frontend: composable + UI + lifecycle

- [ ] Composable `frontend/src/shared/composables/usePushNotifications.ts` (синглтон, как `useSystemNotifications.ts`):
  - [ ] `isSupported` (`'serviceWorker' in navigator && 'PushManager' in window`)
  - [ ] реактивный `permission`
  - [ ] `enable()` — по user-gesture: `Notification.requestPermission()` → `pushManager.subscribe({ userVisibleOnly: true, applicationServerKey })` (ключ из `GET /push/vapid-public-key`, base64url→`Uint8Array`) → `POST /push/subscriptions`
  - [ ] `disable()` — `subscription.unsubscribe()` + `DELETE /push/subscriptions`
- [ ] UI-тумблер «Уведомления на этом устройстве» в `NotificationsSlideover.vue` (или в настройках профиля); `requestPermission` только по клику
- [ ] Отписка при `logout` (хук в `useAuth`); гейт «подписываться только после логина» (`isAuthenticated`)

## Фаза 7 — Тесты и DoD

- [ ] Backend unit: `SqlAlchemyPushSubscriptionStore` (upsert-конфликт, delete)
- [ ] Backend unit: `WebPushSender` с мок-`webpush` (маппинг record→payload; удаление подписки на 410)
- [ ] Backend unit: `PushDispatcher.drain()`
- [ ] Backend контракт: `POST/DELETE /push/subscriptions`, `GET /push/vapid-public-key` через `httpx.ASGITransport`
- [ ] `make be-lint be-test` (coverage ≥ 90 — покрыт новый код)
- [ ] Frontend unit: `usePushNotifications` с мок-`navigator.serviceWorker`/`PushManager` (`bun test tests/shared`)
- [ ] Frontend e2e (Playwright): `context.grantPermissions(['notifications'])`, регистрация SW + флоу `enable()`
- [ ] `cd frontend && bun run lint typecheck build`
- [ ] Ручная проверка end-to-end: DevTools → Application → Service Workers → *Push* (тестовый payload), затем реальный триггер (reject sample) → ОС-тост при закрытой вкладке

## Риски и пограничные случаи

| Риск | Митигция |
|---|---|
| Push по откатившейся транзакции | Отправка только после `uow.commit()` |
| Блокировка event loop синхронным `pywebpush` | `asyncio.to_thread` |
| Протухшие endpoint'ы (410/404) | Авто-удаление в `WebPushSender` |
| Потеря фоновых задач при рестарте | `PushDispatcher.drain()` в `lifespan` |
| Чувствительные данные в payload | Тонкий payload + детали по факту открытия |
| Разрешение отозвано пользователем | `enable()` идемпотентен, обрабатывает `denied` |
| HTTPS обязателен | prod `bio.tminww.space` на https; dev — localhost-исключение |

## Развилки (зафиксировать при старте)

- **VAPID public key для фронта:** через `GET /push/vapid-public-key` (рекомендуется, единый источник) vs `VITE_VAPID_PUBLIC_KEY` в env.
- **Шифрование/отправка:** `pywebpush` + `to_thread` (рекомендуется, MVP) vs `http-ece` + `httpx` (чистый async, больше кода).
- **Размещение UI-тумблера:** `NotificationsSlideover` vs страница настроек профиля.

## Дальнейшее усиление (вне MVP)

- Transactional outbox (таблица `push_outbox` + отдельный воркер) для гарантированной доставки с ретраями вместо fire-and-forget.
- «Мои устройства» в профиле (список активных подписок по `user_agent`, отзыв конкретного).

## Порядок PR

Технически один вертикальный слайс, но для ревью разумно разбить:
- **PR 1** — backend + миграция + SDK (Фазы 0–4).
- **PR 2** — frontend PWA/SW/UI (Фазы 5–6) + e2e.

Ориентировочный объём: backend ~1–1.5 дня, frontend ~1–1.5 дня.
