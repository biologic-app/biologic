<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useAuth } from '@/modules/auth'
import {
  fetchSubscribers,
  subscribeToEntity,
  unsubscribeFromEntity,
  type SubscriberRow,
  type SubscriptionEntity
} from '@/shared/api/subscriptions.api'

// Компактная кнопка отслеживания: один иконочный тоггл с бейджем-счётчиком
// подписчиков (UChip). Список подписчиков и явное управление подпиской — в
// поповере по клику, чтобы не занимать место в ряду действий карточки.
// Роль (по мандатному правилу), владелец направления и привязанный санитарный
// врач подписаны неявно (source role/owner/doctor) и отписаться не могут;
// остальные управляют подпиской кнопкой (source manual).
const props = defineProps<{
  entity: SubscriptionEntity
  entityId?: string | null
}>()

const auth = useAuth()
const toast = useToast()

const subscribers = ref<SubscriberRow[]>([])
const loading = ref(false)
const pending = ref(false)

const load = async () => {
  if (!props.entityId) {
    subscribers.value = []
    return
  }
  loading.value = true
  try {
    subscribers.value = await fetchSubscribers(props.entity, props.entityId)
  } catch {
    subscribers.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.entityId, () => void load(), { immediate: true })

const mine = computed(() =>
  subscribers.value.find((row) => row.user_id === auth.user?.id) ?? null
)
const isSubscribed = computed(() => Boolean(mine.value))
// Неявная подписка (роль/владелец) — кнопка недоступна для отписки.
const isImplicit = computed(() => Boolean(mine.value && mine.value.source !== 'manual'))

const SOURCE_HINTS: Record<SubscriberRow['source'], string> = {
  role: 'Отслеживается по роли',
  owner: 'Отслеживается как владельцем направления',
  doctor: 'Отслеживается как санитарным врачом направления',
  manual: 'Отслеживается вручную'
}

const buttonTooltip = computed(() => {
  if (!props.entityId) {
    return 'Недоступно для демо-данных'
  }
  if (!isSubscribed.value) {
    return 'Отслеживать уведомления'
  }
  return SOURCE_HINTS[mine.value?.source ?? 'manual']
})

const initials = (row: SubscriberRow): string => {
  const parts = [row.last_name, row.first_name].filter(
    (part): part is string => Boolean(part && part.trim())
  )
  if (parts.length) {
    return parts.map((part) => part.trim()[0].toUpperCase()).join('')
  }
  return row.username.slice(0, 2).toUpperCase()
}

const fullName = (row: SubscriberRow): string =>
  [row.last_name, row.first_name, row.patronymic].filter(Boolean).join(' ') || row.username

const SOURCE_LABELS: Record<SubscriberRow['source'], string> = {
  role: 'По роли',
  owner: 'Владелец направления',
  doctor: 'Санитарный врач направления',
  manual: 'Отслеживает вручную'
}

const toggle = async () => {
  if (!props.entityId || pending.value || isImplicit.value) {
    return
  }
  pending.value = true
  try {
    subscribers.value = isSubscribed.value
      ? await unsubscribeFromEntity(props.entity, props.entityId)
      : await subscribeToEntity(props.entity, props.entityId)
  } catch {
    toast.add({
      title: 'Не удалось изменить подписку',
      color: 'error',
      icon: 'i-lucide-circle-alert'
    })
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <UPopover :content="{ side: 'bottom', align: 'end' }">
    <UTooltip :text="buttonTooltip">
      <UChip
        :text="subscribers.length ? String(subscribers.length) : undefined"
        :show="subscribers.length > 0"
        size="3xs"
        color="neutral"
      >
        <UButton
          :icon="isSubscribed ? 'i-lucide-bell-ring' : 'i-lucide-bell-plus'"
          :color="isSubscribed ? 'primary' : 'neutral'"
          :variant="isSubscribed ? 'subtle' : 'outline'"
          size="sm"
          square
          :loading="loading"
          data-testid="subscribe-button"
        />
      </UChip>
    </UTooltip>

    <template #content>
      <div class="w-72 p-3">
        <p class="px-1 pb-2 text-xs font-medium text-muted">
          Отслеживают ({{ subscribers.length }})
        </p>
        <ul v-if="subscribers.length" class="max-h-64 space-y-0.5 overflow-y-auto">
          <li
            v-for="row in subscribers"
            :key="row.user_id"
            class="flex items-center gap-2 rounded-md px-1 py-1.5"
          >
            <UAvatar :text="initials(row)" size="xs" />
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-highlighted">
                {{ fullName(row) }}
              </p>
              <p class="truncate text-xs text-muted">
                {{ SOURCE_LABELS[row.source] }}
              </p>
            </div>
          </li>
        </ul>
        <p v-else class="px-1 pb-2 text-xs text-muted">
          Пока никто не отслеживает.
        </p>

        <UButton
          class="mt-2"
          block
          :icon="isSubscribed ? 'i-lucide-bell-off' : 'i-lucide-bell-plus'"
          :label="isSubscribed ? 'Перестать отслеживать' : 'Отслеживать'"
          :color="isSubscribed ? 'neutral' : 'primary'"
          :variant="isSubscribed ? 'outline' : 'solid'"
          :loading="pending"
          :disabled="!entityId || isImplicit"
          data-testid="subscribe-toggle"
          @click="toggle"
        />
      </div>
    </template>
  </UPopover>
</template>
