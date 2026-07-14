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

// Кнопка «Подписаться» + стек аватаров подписчиков сущности.
// Роль (по мандатному правилу), владелец направления и привязанный санитарный
// врач подписаны неявно (source role/owner/doctor) и отписаться не могут;
// остальные управляют подпиской кнопкой (source manual).
const props = defineProps<{
  entity: SubscriptionEntity
  entityId?: string | null
  compact?: boolean
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
  doctor: 'Отслеживается как санитарный врач направления',
  manual: 'Перестать отслеживать'
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

const AVATARS_LIMIT = 4
const visibleSubscribers = computed(() => subscribers.value.slice(0, AVATARS_LIMIT))
const restCount = computed(() => Math.max(0, subscribers.value.length - AVATARS_LIMIT))

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
  <div class="flex items-center gap-2">
    <UPopover v-if="subscribers.length" :content="{ side: 'bottom', align: 'start' }">
      <button
        type="button"
        class="flex items-center rounded-full outline-none"
        :class="compact ? '' : '-space-x-1.5'"
        data-testid="subscribers-list-trigger"
      >
        <template v-if="!compact">
          <UTooltip
            v-for="row in visibleSubscribers"
            :key="row.user_id"
            :text="`${fullName(row)} — ${SOURCE_HINTS[row.source]}`"
          >
            <UAvatar
              :text="initials(row)"
              size="2xs"
              class="ring-2 ring-bg"
            />
          </UTooltip>
          <span v-if="restCount" class="pl-2.5 text-xs text-muted">+{{ restCount }}</span>
        </template>
        <UBadge
          v-else
          :label="`${subscribers.length}`"
          icon="i-lucide-users"
          color="neutral"
          variant="subtle"
          size="sm"
        />
      </button>

      <template #content>
        <div class="w-72 p-1">
          <p class="px-2 py-1.5 text-xs font-medium text-muted">
            Отслеживают ({{ subscribers.length }})
          </p>
          <ul class="max-h-64 overflow-y-auto">
            <li
              v-for="row in subscribers"
              :key="row.user_id"
              class="flex items-center gap-2 rounded-md px-2 py-1.5"
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
        </div>
      </template>
    </UPopover>

    <UTooltip :text="buttonTooltip">
      <UButton
        :icon="isSubscribed ? 'i-lucide-bell-ring' : 'i-lucide-bell-plus'"
        :label="compact ? undefined : isSubscribed ? 'Отслеживается' : 'Отслеживать'"
        :color="isSubscribed ? 'primary' : 'neutral'"
        :variant="isSubscribed ? 'subtle' : 'outline'"
        :size="compact ? 'xs' : 'sm'"
        :loading="pending || loading"
        :disabled="!entityId || isImplicit"
        data-testid="subscribe-button"
        data-telemetry="entity-subscribe-toggle"
        @click="toggle"
      />
    </UTooltip>
  </div>
</template>
