<script setup lang="ts">
import { format, isToday } from 'date-fns'
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLocale } from '@/shared/composables/useLocale'
import type { ResearchSample, ResearchStatus } from '@/shared/types'

const props = defineProps<{
  samples: ResearchSample[]
  loading?: boolean
  hasMore?: boolean
}>()

const emit = defineEmits<{
  loadMore: []
}>()

const selectedSample = defineModel<ResearchSample | null>()
const { t } = useI18n()
const { dateFnsLocale } = useLocale()
const sampleRefs = ref<Record<number, Element | null>>({})

const statusColors: Record<ResearchStatus, 'neutral' | 'primary' | 'info' | 'success' | 'error'> = {
  registered: 'neutral',
  inProgress: 'primary',
  review: 'info',
  completed: 'success',
  rejected: 'error'
}

watch(selectedSample, () => {
  if (!selectedSample.value) {
    return
  }

  sampleRefs.value[selectedSample.value.id]?.scrollIntoView({ block: 'nearest' })
})

defineShortcuts({
  arrowdown: () => {
    const index = props.samples.findIndex(sample => sample.id === selectedSample.value?.id)
    selectedSample.value = index === -1 ? props.samples[0] : props.samples[Math.min(index + 1, props.samples.length - 1)]
  },
  arrowup: () => {
    const index = props.samples.findIndex(sample => sample.id === selectedSample.value?.id)
    selectedSample.value = index === -1 ? props.samples[props.samples.length - 1] : props.samples[Math.max(index - 1, 0)]
  }
})

function formatListDate(date: string) {
  const currentDate = new Date(date)

  return isToday(currentDate)
    ? format(currentDate, 'HH:mm', { locale: dateFnsLocale.value })
    : format(currentDate, 'dd MMM', { locale: dateFnsLocale.value })
}

function onScroll(event: Event) {
  const element = event.currentTarget as HTMLElement

  if (element.scrollTop + element.clientHeight >= element.scrollHeight - 160) {
    emit('loadMore')
  }
}
</script>

<template>
  <div class="overflow-y-auto divide-y divide-default" @scroll="onScroll">
    <div
      v-for="sample in samples"
      :key="sample.id"
      :ref="(element) => { sampleRefs[sample.id] = element as Element | null }"
    >
      <button
        type="button"
        class="block w-full border-l-2 p-4 text-left text-sm transition-colors sm:px-6"
        :class="selectedSample?.id === sample.id
          ? 'border-primary bg-primary/10'
          : 'border-bg hover:border-primary hover:bg-primary/5'"
        @click="selectedSample = sample"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <p class="truncate font-semibold text-highlighted">
                {{ sample.code }}
              </p>
              <UBadge
                v-if="sample.priority === 'urgent'"
                color="warning"
                variant="subtle"
                size="xs"
                :label="t('research.priority.urgent')"
              />
            </div>
            <p class="truncate text-toned">
              {{ sample.patient.name }}
            </p>
          </div>

          <span class="shrink-0 text-xs text-muted">{{ formatListDate(sample.updatedAt) }}</span>
        </div>

        <div class="mt-3 flex items-center justify-between gap-3">
          <div class="min-w-0">
            <p class="truncate text-muted">
              {{ sample.material }} · {{ sample.direction }}
            </p>
            <p class="truncate text-dimmed">
              {{ sample.comment }}
            </p>
          </div>

          <UBadge
            :color="statusColors[sample.status]"
            variant="subtle"
            size="sm"
            :label="t(`research.status.${sample.status}`)"
          />
        </div>
      </button>
    </div>

    <div v-if="loading" class="flex items-center justify-center gap-2 p-4 text-sm text-muted">
      <UIcon name="i-lucide-loader-circle" class="size-4 animate-spin" />
      <span>{{ t('research.loading') }}</span>
    </div>

    <div v-else-if="!samples.length" class="flex flex-col items-center justify-center gap-3 p-10 text-center">
      <UIcon name="i-lucide-flask-conical" class="size-10 text-dimmed" />
      <p class="text-sm text-muted">
        {{ t('research.empty') }}
      </p>
    </div>

    <div v-else-if="!hasMore" class="p-4 text-center text-xs text-dimmed">
      {{ t('research.end') }}
    </div>
  </div>
</template>
