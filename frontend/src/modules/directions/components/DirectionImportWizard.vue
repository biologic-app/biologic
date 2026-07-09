<script setup lang="ts">
import { computed, watch } from 'vue'
import type { StepperItem } from '@nuxt/ui'
import { useDirectionImport } from '@/modules/directions/composables/useDirectionImport'
import ImportUploadStep from '@/modules/directions/components/ImportUploadStep.vue'
import ImportReviewStep from '@/modules/directions/components/ImportReviewStep.vue'
import ImportFillStep from '@/modules/directions/components/ImportFillStep.vue'
import ImportRegisterStep from '@/modules/directions/components/ImportRegisterStep.vue'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'finished'): void
}>()

const ctx = useDirectionImport()

const steps: StepperItem[] = [
  { title: 'Загрузка', icon: 'i-lucide-upload', value: 0 },
  { title: 'Предпросмотр', icon: 'i-lucide-list-checks', value: 1 },
  { title: 'Дозаполнение', icon: 'i-lucide-pencil', value: 2 },
  { title: 'Регистрация', icon: 'i-lucide-clipboard-check', value: 3 }
]

const stepTitle = computed(() => steps[ctx.step]?.title ?? 'Импорт направлений')

watch(
  () => props.open,
  (open) => {
    if (open) {
      ctx.reset()
    }
  }
)

const close = () => {
  emit('update:open', false)
}

const finish = () => {
  emit('finished')
  emit('update:open', false)
}
</script>

<template>
  <UModal
    :open="open"
    :dismissible="!ctx.importing && !ctx.registering"
    :ui="{ content: 'max-w-4xl' }"
    :title="`Импорт направлений — ${stepTitle}`"
    @update:open="emit('update:open', $event)"
  >
    <template #body>
      <div class="flex flex-col gap-6">
        <UStepper
          :items="steps"
          :model-value="ctx.step"
          disabled
          class="w-full"
        />

        <ImportUploadStep v-if="ctx.step === 0" :ctx="ctx" />
        <ImportReviewStep v-else-if="ctx.step === 1" :ctx="ctx" />
        <ImportFillStep v-else-if="ctx.step === 2" :ctx="ctx" />
        <ImportRegisterStep v-else :ctx="ctx" />
      </div>
    </template>

    <template #footer>
      <div class="flex w-full items-center justify-between gap-3">
        <UButton
          v-if="ctx.step > 0"
          label="Загрузить другой файл"
          icon="i-lucide-rotate-ccw"
          color="neutral"
          variant="ghost"
          size="sm"
          @click="ctx.reset()"
        />
        <span v-else />

        <div class="flex items-center gap-2">
          <UButton
            label="Закрыть"
            color="neutral"
            variant="ghost"
            @click="close"
          />
          <UButton
            v-if="ctx.step === 1"
            label="Далее: дозаполнение"
            icon="i-lucide-chevron-right"
            trailing
            color="primary"
            :disabled="!ctx.directions.length"
            data-telemetry="direction-import-to-fill"
            @click="ctx.goToStep(2)"
          />
          <UButton
            v-else-if="ctx.step === 2"
            label="Далее: регистрация"
            icon="i-lucide-chevron-right"
            trailing
            color="primary"
            data-telemetry="direction-import-to-register"
            @click="ctx.goToStep(3)"
          />
          <UButton
            v-else-if="ctx.step === 3"
            label="Готово"
            icon="i-lucide-check"
            color="primary"
            data-telemetry="direction-import-finish"
            @click="finish"
          />
        </div>
      </div>
    </template>
  </UModal>
</template>
