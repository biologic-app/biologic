# Уведомления — только SSE (Web Push удалён)

**Статус: Web Push удалён 2026-07-13.** Причина — развёртывание без интернета:
OS Web Push обязательно проходит через внешний push-сервис (FCM/Mozilla) и в
изолированной сети не работает. Единственный надёжный канал на LAN-контуре — SSE,
поэтому оставлен только он. PWA/Service Worker сохранён (установка приложения +
офлайн-оболочка), но без push-обработчиков.

## Как работают уведомления сейчас

- Доменное событие workflow → `WorkflowNotificationSubscriber` создаёт адресную
  запись `Notification` (по `target_user_id`) в той же транзакции (UoW).
- Фронт держит `EventSource('/api/v1/alerts/stream')`
  (`frontend/src/shared/composables/useSystemNotifications.ts`); backend опрашивает
  БД раз в 1 c (`NotificationService.stream_after`) и отдаёт событие
  `notification.created` → тост + запись в колокольчике. Непрочитанное доступно
  при следующем заходе (`GET /alerts`, фильтр по `target_user_id == viewer`).
- Service Worker (`frontend/src/sw.ts`) — только precache; регистрируется в
  `frontend/src/app/registerServiceWorker.ts` (no-op в dev).

## Что удалено (для истории)

Backend: `push_dispatcher`, `push_sender`, `push_ports`, `push_router`,
`push_subscription_repository`, модель `PushSubscription`, VAPID-конфиг и
зависимость `pywebpush`. Таблица `push_subscriptions` удалена миграцией
`20260713_0027_drop_push_subscriptions` (она же смёржила висячий alembic-head
`20260710_0018` в основную линию). Frontend: `usePushNotifications`, UI-тумблер,
мягкий пре-промпт и push/`notificationclick`-обработчики в `sw.ts`.

## Проверить SSE вручную

```bash
make be-dev                        # API :8080 (нужна поднятая БД: make be-migrate)
cd frontend && bun run dev         # :5177 → залогиниться, открыть колокольчик
# в отдельном терминале — создать адресное уведомление своему пользователю:
cd backend && PYTHONPATH=$PWD uv run python -m scripts.create_test_notification \
  --target-user-id <ВАШ_UUID> --title "Проверка" --message "SSE работает"
```
Через ≤1 c — тост в приложении и запись в списке.
