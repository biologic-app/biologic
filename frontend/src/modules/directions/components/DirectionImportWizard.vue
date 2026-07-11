<script setup lang="ts">
import { computed, watch } from 'vue'
import type { StepperItem } from '@nuxt/ui'
import { useDirectionImport, type WizardStep } from '@/modules/directions/composables/useDirectionImport'
import ImportUploadStep from '@/modules/directions/components/ImportUploadStep.vue'
import ImportReviewStep from '@/modules/directions/components/ImportReviewStep.vue'
import ImportFillStep from '@/modules/directions/components/ImportFillStep.vue'
import ImportRegisterStep from '@/modules/directions/components/ImportRegisterStep.vue'

const props = defineProps<{ open: boolean; directionId?: string | null }>()
const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'finished', directionId: string | null): void
}>()

const ctx = useDirectionImport()

const steps: StepperItem[] = [
  { title: 'Загрузка', icon: 'i-lucide-upload', value: 0 },
  { title: 'Предпросмотр', icon: 'i-lucide-list-checks', value: 1 },
  { title: 'Дозаполнение', icon: 'i-lucide-pencil', value: 2 },
  { title: 'Регистрация', icon: 'i-lucide-clipboard-check', value: 3 }
]

const stepTitle = computed(() => steps[ctx.step]?.title ?? 'Импорт направлений')

// Имя загруженного файла показываем подзаголовком в шапке модалки.
const fileName = computed(() => ctx.fileName || ctx.summary?.filename || '')

watch(
  () => props.open,
  (open) => {
    if (!open) {
      return
    }
    if (props.directionId) {
      void ctx.loadExistingDraft(props.directionId)
    } else {
      ctx.reset()
    }
  }
)

const finish = () => {
  emit('finished', ctx.directions[0]?.id ?? null)
  emit('update:open', false)
}

const goBack = () => {
  ctx.goToStep((ctx.step - 1) as WizardStep)
}

const submitUpload = () => {
  void ctx.runImport()
}

// «Далее: регистрация» только сохраняет данные и показывает сводку: направления
// остаются в статусе «Черновик» до явного нажатия «Зарегистрировать» на шаге 4.
const toast = useToast()

const proceedToRegister = async () => {
  if (ctx.savingKey || ctx.registering) {
    return
  }
  const ok = await ctx.persistAll()
  if (!ok) {
    toast.add({
      title: 'Не удалось сохранить часть данных',
      description: 'Проверьте направление и образцы, затем попробуйте снова.',
      color: 'error',
      icon: 'i-lucide-circle-alert'
    })
    return
  }
  ctx.goToStep(3)
}

// Регистрация выполнена — на шаге 4 уже есть результаты; кнопка меняется на «Готово».
const hasRegisterResults = computed(() => Object.keys(ctx.registerResults).length > 0)

const submitRegister = async () => {
  if (ctx.registering) {
    return
  }
  await ctx.registerAll()
}
</script>

<template>
  <UModal
    :open="open"
    :dismissible="!ctx.importing && !ctx.registering"
    :ui="{ content: 'max-w-4xl' }"
    :title="`Импорт направлений — ${stepTitle}`"
    :description="fileName || undefined"
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
          v-if="ctx.step > 0 && !(ctx.existingDraft && ctx.step === 2)"
          label="Назад"
          icon="i-lucide-chevron-left"
          color="primary"
          @click="goBack"
        />
        <span v-else />

        <div class="flex items-center gap-2">
          <UButton
            v-if="ctx.step === 0"
            label="Далее"
            icon="i-lucide-chevron-right"
            trailing
            color="primary"
            :loading="ctx.importing"
            :disabled="!ctx.fileName || ctx.importing"
            data-testid="direction-import-submit"
            data-telemetry="direction-import-submit"
            @click="submitUpload"
          />
          <UButton
            v-else-if="ctx.step === 1"
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
            :loading="Boolean(ctx.savingKey) || ctx.registering"
            :disabled="Boolean(ctx.savingKey) || ctx.registering || !ctx.directions.length"
            data-telemetry="direction-import-to-register"
            @click="proceedToRegister"
          />
          <UButton
            v-else-if="ctx.step === 3 && !hasRegisterResults"
            label="Зарегистрировать"
            icon="i-lucide-clipboard-check"
            color="primary"
            :loading="ctx.registering"
            :disabled="ctx.registering || !ctx.directions.length"
            data-testid="direction-import-register"
            data-telemetry="direction-import-register"
            @click="submitRegister"
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
