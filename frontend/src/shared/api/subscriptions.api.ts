import { apiReadListRequest } from '@/shared/api/client.api'

// Подписки на направления/образцы. source: role — мандатная подписка по роли
// (настраивается администратором в role_subscription_rules, опционально в
// разрезе филиала/лаборатории), owner — создатель направления (свои), doctor —
// пользователь, привязанный к санитарному врачу направления (doctors.user_id),
// manual — кнопка подписки.
export type SubscriptionEntity = 'directions' | 'samples'

export interface SubscriberRow {
  user_id: string
  username: string
  first_name: string | null
  last_name: string | null
  patronymic: string | null
  source: 'role' | 'owner' | 'doctor' | 'manual'
}

export const fetchSubscribers = async (
  entity: SubscriptionEntity,
  entityId: string
): Promise<SubscriberRow[]> => {
  const response = await apiReadListRequest<SubscriberRow>(
    `/${entity}/${entityId}/subscriptions`,
    { method: 'GET' }
  )
  return response.items
}

export const subscribeToEntity = async (
  entity: SubscriptionEntity,
  entityId: string
): Promise<SubscriberRow[]> => {
  const response = await apiReadListRequest<SubscriberRow>(`/${entity}/${entityId}/subscribe`, {
    method: 'POST',
    body: {}
  })
  return response.items
}

export const unsubscribeFromEntity = async (
  entity: SubscriptionEntity,
  entityId: string
): Promise<SubscriberRow[]> => {
  const response = await apiReadListRequest<SubscriberRow>(`/${entity}/${entityId}/unsubscribe`, {
    method: 'POST',
    body: {}
  })
  return response.items
}

// Id сущностей, на которые текущий пользователь подписан вручную (source manual).
// Питает колонку-пин в таблицах: закреплённые сверху = отслеживаемые записи.
// Неявные подписки (роль/владелец/сан.врач) сюда не входят — только ручные.
export const fetchMySubscriptionIds = async (
  entity: SubscriptionEntity
): Promise<string[]> => {
  const response = await apiReadListRequest<{ entity_id: string }>(
    `/${entity}/subscriptions/mine`,
    { method: 'GET' }
  )
  return response.items.map((row) => String(row.entity_id))
}
