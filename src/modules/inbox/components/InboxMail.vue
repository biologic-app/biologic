<script setup lang="ts">
import { format } from 'date-fns'
import { useI18n } from 'vue-i18n'
import { useLocale } from '@/shared/composables/useLocale'
import type { Mail } from '@/shared/types'

defineProps<{
  mail: Mail
}>()

const emit = defineEmits<{
  close: []
}>()
const { t } = useI18n()
const { dateFnsLocale } = useLocale()

function formatMailDate(date: string) {
  return format(new Date(date), 'dd MMM HH:mm', { locale: dateFnsLocale.value })
}
</script>

<template>
  <UDashboardPanel id="inbox-2">
    <UDashboardNavbar :title="mail.subject" :toggle="false">
      <template #leading>
        <UButton
          icon="i-lucide-x"
          color="neutral"
          variant="ghost"
          class="-ms-1.5"
          @click="emit('close')"
        />
      </template>

      <template #right>
        <UTooltip :text="t('inbox.archive')">
          <UButton
            icon="i-lucide-inbox"
            color="neutral"
            variant="ghost"
          />
        </UTooltip>
      </template>
    </UDashboardNavbar>

    <div class="flex flex-col sm:flex-row justify-between gap-1 p-4 sm:px-6 border-b border-default">
      <div class="flex items-start gap-4 sm:my-1.5">
        <UAvatar
          v-bind="mail.from.avatar"
          :alt="mail.from.name"
          size="3xl"
        />

        <div class="min-w-0">
          <p class="font-semibold text-highlighted">
            {{ mail.from.name }}
          </p>
          <p class="text-muted">
            {{ mail.from.email }}
          </p>
        </div>
      </div>

      <p class="max-sm:pl-16 text-muted text-sm sm:mt-2">
        {{ formatMailDate(mail.date) }}
      </p>
    </div>

    <div class="flex-1 p-4 sm:p-6 overflow-y-auto">
      <div class="mb-4 flex items-center gap-2 text-sm text-muted">
        <UIcon name="i-lucide-badge-info" class="size-4" />
        <span>{{ t('inbox.systemTitle') }}</span>
      </div>

      <p class="whitespace-pre-wrap">
        {{ mail.body }}
      </p>
    </div>
  </UDashboardPanel>
</template>
