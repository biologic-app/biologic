<script setup lang="ts">
import { computed, watch } from 'vue'
import type { StepperItem } from '@nuxt/ui'
import {
  useDirectionWizard,
  type WizardMode,
  type WizardStep
} from '@/modules/directions/composables/useDirectionWizard'
import ModeSelectStep from '@/modules/directions/components/ModeSelectStep.vue'
import ImportUploadStep from '@/modules/directions/components/ImportUploadStep.vue'
import ImportReviewStep from '@/modules/directions/components/ImportReviewStep.vue'
import ImportFillStep from '@/modules/directions/components/ImportFillStep.vue'
import ImportRegisterStep from '@/modules/directions/components/ImportRegisterStep.vue'

const props = defineProps<{
  open: boolean
  directionId?: string | null
  canImport?: boolean
  canCreate?: boolean
}>()
const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'finished', directionId: string | null): void
}>()

const ctx = useDirectionWizard()
const toast = useToast()

type NamedStep = Exclude<WizardStep, 'select'>

const STEP_META: Record<NamedStep, { title: string; icon: string }> = {
  upload: { title: 'Загрузка', icon: 'i-lucide-upload' },
  review: { title: 'Предпросмотр', icon: 'i-lucide-list-checks' },
  fill: { title: 'Дозаполнение', icon: 'i-lucide-pencil' },
  register: { title: 'Регистрация', icon: 'i-lucide-clipboard-check' }
}

// Активный набор шагов зависит от режима: импорт проходит загрузку и предпросмотр,
// ручное создание и дозаполнение черновика начинаются сразу с шага заполнения.
const MODE_STEPS: Record<WizardMode, WizardStep[]> = {
  select: [],
  import: ['upload', 'review', 'fill', 'register'],
  manual: ['fill', 'register'],
  draft: ['fill', 'register']
}

const activeSteps = computed(() => MODE_STEPS[ctx.mode])
const currentStepIndex = computed(() => activeSteps.value.indexOf(ctx.step))
const stepperItems = computed<StepperItem[]>(() =>
  activeSteps.value.map((step, index) => ({
    title: STEP_META[step as NamedStep].title,
    icon: STEP_META[step as NamedStep].icon,
    value: index
  }))
)

const stepTitle = computed(() =>
  ctx.step === 'select' ? '' : STEP_META[ctx.step as NamedStep].title
)
const modalTitle = computed(() =>
  stepTitle.value ? `Создание направления — ${stepTitle.value}` : 'Создание направления'
)

// Имя загруженного файла показываем подзаголовком в шапке модалки (только импорт).
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

const onChoose = async (mode: 'import' | 'manual') => {
  if (mode === 'import') {
    ctx.chooseImport()
    return
  }
  const result = await ctx.startManual()
  if (!result.ok) {
    toast.add({
      title: 'Не удалось создать направление',
      description: result.message,
      color: 'error',
      icon: 'i-lucide-circle-alert'
    })
  }
}

const finish = () => {
  emit('finished', ctx.directions[0]?.id ?? null)
  emit('update:open', false)
}

const goBack = () => {
  const index = currentStepIndex.value
  if (index > 0) {
    ctx.goToStep(activeSteps.value[index - 1])
  }
}

const submitUpload = () => {
  void ctx.runImport()
}

// «Далее: регистрация» только сохраняет данные и показывает сводку: направления
// остаются в статусе «Черновик» до явного нажатия «Зарегистрировать» на шаге регистрации.
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
  ctx.goToStep('register')
}

// Регистрация выполнена — на шаге регистрации уже есть результаты; кнопка меняется на «Готово».
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
    :title="modalTitle"
    :description="fileName || undefined"
    @update:open="emit('update:open', $event)"
  >
    <template #body>
      <div class="flex flex-col gap-6">
        <ModeSelectStep
          v-if="ctx.step === 'select'"
          :can-import="canImport"
          :can-create="canCreate"
          :loading="ctx.loadingResults"
          @choose="onChoose"
        />

        <template v-else>
          <UStepper
            :items="stepperItems"
            :model-value="currentStepIndex"
            disabled
            class="w-full"
          />

          <ImportUploadStep v-if="ctx.step === 'upload'" :ctx="ctx" />
          <ImportReviewStep v-else-if="ctx.step === 'review'" :ctx="ctx" />
          <ImportFillStep v-else-if="ctx.step === 'fill'" :ctx="ctx" />
          <ImportRegisterStep v-else :ctx="ctx" />
        </template>
      </div>
    </template>

    <template v-if="ctx.step !== 'select'" #footer>
      <div class="flex w-full items-center justify-between gap-3">
        <UButton
          v-if="currentStepIndex > 0"
          label="Назад"
          icon="i-lucide-chevron-left"
          color="primary"
          @click="goBack"
        />
        <span v-else />

        <div class="flex items-center gap-2">
          <UButton
            v-if="ctx.step === 'upload'"
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
            v-else-if="ctx.step === 'review'"
            label="Далее: дозаполнение"
            icon="i-lucide-chevron-right"
            trailing
            color="primary"
            :disabled="!ctx.directions.length"
            data-telemetry="direction-import-to-fill"
            @click="ctx.goToStep('fill')"
          />
          <UButton
            v-else-if="ctx.step === 'fill'"
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
            v-else-if="ctx.step === 'register' && !hasRegisterResults"
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
            v-else-if="ctx.step === 'register'"
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
