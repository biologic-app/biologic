<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DirectionWizardContext } from '@/modules/directions/composables/useDirectionWizard'

const props = defineProps<{ ctx: DirectionWizardContext }>()
const toast = useToast()
const { t } = useI18n()

const direction = computed(() => props.ctx.directions[props.ctx.currentIndex] ?? null)
const samples = computed(() => (direction.value ? props.ctx.samplesByDirection[direction.value.id] ?? [] : []))
// Крупный заголовок «№ 2025-461».
const directionHeading = computed(() => {
  const current = direction.value
  if (current?.year_no && current?.base_no) {
    return `№ ${current.year_no}-${current.base_no}`
  }
  return t('directionWizard.directionFallbackHeading')
})

// Оригинальные данные из legacy-файла (import_warnings.document) — врач и отдел отбора.
// Раньше рендерились как `[object Object]`; разбираем структуру по полям.
interface ImportDocument {
  document_number?: string | null
  lab_department?: string | null
  sampling_department?: string | null
  signer_name?: string | null
  signer_position?: string | null
}

const importDocument = computed<ImportDocument | null>(() => {
  const raw = direction.value?.import_warnings
  if (!raw || typeof raw !== 'object') {
    return null
  }
  const doc = (raw as Record<string, unknown>).document
  return doc && typeof doc === 'object' ? (doc as ImportDocument) : null
})

const importSigner = computed(() => {
  const doc = importDocument.value
  if (!doc?.signer_name) {
    return ''
  }
  return doc.signer_position ? `${doc.signer_name} (${doc.signer_position})` : doc.signer_name
})

const importSamplingDepartment = computed(() => importDocument.value?.sampling_department || '')

// Аккордеон образцов (UAccordion, type="single"): в один момент времени открыт
// максимум один образец. При смене направления открытый образец сбрасывается.
const openSampleId = ref<string | undefined>(undefined)

// Элементы аккордеона: value — id образца (им управляет открытие/закрытие),
// плюс сам образец и его порядковый номер для отрисовки заголовка и тела.
const sampleItems = computed(() =>
  samples.value.map((sample, index) => ({ value: sample.id, sample, index }))
)

watch(
  () => direction.value?.id,
  (id) => {
    openSampleId.value = undefined
    // Подгружаем существующие Research образцов направления и инициализируем наборы целей.
    if (id) {
      void props.ctx.ensureResearchForDirection(id)
    }
  },
  { immediate: true }
)

// Опции полного справочника целей для ручного добавления (label — «Название · Лаборатория»).
const researchGoalItems = computed(() =>
  props.ctx.researchGoalCatalog.map((goal) => ({
    label: goal.lab_name ? `${goal.name} · ${goal.lab_name}` : goal.name,
    value: goal.id
  }))
)

const sampleGoals = (sampleId: string): string[] => props.ctx.researchGoalsBySample[sampleId] ?? []

// Лаборатории образца (проставлены импортом из меток легаси) — источник деривации целей.
// Набор редактируемый: снятие лаборатории каскадно убирает её цели с образца.
const sampleLabs = (sampleId: string) => props.ctx.labsBySample[sampleId] ?? []
const sampleLabIds = (sampleId: string) => sampleLabs(sampleId).map((lab) => lab.id)

const labItems = computed(() =>
  props.ctx.labOptions.map((option) => ({
    label: option.label,
    value: String(option.value ?? '')
  }))
)

const setSampleLabIds = async (sampleId: string, next: unknown) => {
  const ids = Array.isArray(next) ? (next as string[]) : []
  const ok = await props.ctx.setSampleLabs(sampleId, ids)
  if (!ok) {
    toast.add({
      title: t('directionWizard.failedToUpdateSampleLabs'),
      color: 'error',
      icon: 'i-lucide-circle-alert'
    })
  }
}

const removeSampleLab = (sampleId: string, labId: string) =>
  setSampleLabIds(
    sampleId,
    sampleLabIds(sampleId).filter((id) => id !== labId)
  )

const goalMeta = (goalId: string): { name: string; lab_id: string | null; lab_name: string | null } =>
  props.ctx.goalLabById[goalId] ?? { name: goalId.slice(0, 8).toUpperCase(), lab_id: null, lab_name: null }

// Диффим выбор мультиселекта и проводим его через явные мутаторы набора.
const setSampleGoals = (sampleId: string, next: unknown) => {
  const nextIds = Array.isArray(next) ? (next as string[]) : []
  const current = sampleGoals(sampleId)
  for (const id of nextIds) {
    if (!current.includes(id)) {
      props.ctx.addSampleGoal(sampleId, id)
    }
  }
  for (const id of current) {
    if (!nextIds.includes(id)) {
      props.ctx.removeSampleGoal(sampleId, id)
    }
  }
}

// Автосохранение образца на бэкенд при изменении полей (без ожидания общего
// сохранения направления перед переходом дальше по мастеру).
const autoSaveSample = async (sample: (typeof samples.value)[number]) => {
  if (!direction.value) {
    return
  }
  const ok = await props.ctx.saveSample(direction.value.id, sample.id, {
    name: sample.name || null,
    sample_type_id: sample.sample_type_id,
    alternate_name: sample.alternate_name || null,
    mass: sample.mass || null,
    comment: sample.comment || null,
    is_urgent: sample.is_urgent
  })
  if (!ok) {
    toast.add({ title: t('directionWizard.failedToSaveSample'), color: 'error', icon: 'i-lucide-circle-alert' })
  }
}

// Авто-подстановка дефолтных целей при выборе/смене типа образца + немедленное сохранение.
const onSampleTypeChange = (sampleId: string, typeId: unknown) => {
  const value = typeof typeId === 'string' ? typeId : null
  const sample = samples.value.find((row) => row.id === sampleId)
  void props.ctx.applySampleTypeDefaults(sampleId, value).catch(() => {
    toast.add({
      title: t('directionWizard.failedToApplyGoalDefaults'),
      color: 'error',
      icon: 'i-lucide-circle-alert'
    })
  })
  if (sample) {
    void autoSaveSample(sample)
  }
}

const showNewDoctor = ref(false)
const showNewObject = ref(false)
const creatingDoctor = ref(false)
const creatingObject = ref(false)
const newDoctor = reactive({ first_name: '', last_name: '', patronymic: '' })
const newObject = reactive({ code: '', name: '', full_name: '', address: '' })

const missingClass = (value: unknown) =>
  value === null || value === undefined || value === '' ? 'ring-2 ring-warning/60 rounded-md' : ''

// Реквизиты направления (год/номер) — редактируемы; автосохранение на blur.
const saveRequisites = async () => {
  if (!direction.value) {
    return
  }
  const ok = await props.ctx.saveDirection(direction.value.id, {
    year_no: direction.value.year_no,
    base_no: direction.value.base_no
  })
  if (!ok) {
    toast.add({
      title: t('directionWizard.failedToSaveDirectionNumber'),
      description: t('directionWizard.directionNumberConflictHint'),
      color: 'error',
      icon: 'i-lucide-circle-alert'
    })
  }
}

// Добавление пустого образца в направление (раскрываем его в аккордеоне).
const adding = ref(false)
const addSample = async () => {
  if (!direction.value) {
    return
  }
  adding.value = true
  try {
    const id = await props.ctx.addSample(direction.value.id)
    if (id) {
      openSampleId.value = id
    } else {
      toast.add({ title: t('directionWizard.failedToAddSample'), color: 'error', icon: 'i-lucide-circle-alert' })
    }
  } finally {
    adding.value = false
  }
}

// Удаление образца — с подтверждением в модальном окне.
const pendingDelete = ref<{ id: string; label: string } | null>(null)
const deleting = ref(false)
const requestDelete = (sample: (typeof samples.value)[number]) => {
  pendingDelete.value = { id: sample.id, label: sample.name || t('directionWizard.withoutNameCapitalized') }
}
const confirmDelete = async () => {
  if (!direction.value || !pendingDelete.value) {
    return
  }
  const { id } = pendingDelete.value
  deleting.value = true
  try {
    const ok = await props.ctx.removeSample(direction.value.id, id)
    if (!ok) {
      toast.add({ title: t('directionWizard.failedToRemoveSample'), color: 'error', icon: 'i-lucide-circle-alert' })
      return
    }
    if (openSampleId.value === id) {
      openSampleId.value = undefined
    }
    pendingDelete.value = null
  } finally {
    deleting.value = false
  }
}

const createDoctor = async () => {
  if (!newDoctor.first_name.trim()) {
    return
  }
  creatingDoctor.value = true
  try {
    const id = await props.ctx.addDoctor({ ...newDoctor })
    if (id && direction.value) {
      direction.value.doctor_id = id
    }
    showNewDoctor.value = false
    newDoctor.first_name = ''
    newDoctor.last_name = ''
    newDoctor.patronymic = ''
    toast.add({ title: t('directionWizard.doctorCreated'), color: 'success', icon: 'i-lucide-user-check' })
  } catch {
    toast.add({ title: t('directionWizard.failedToCreateDoctor'), color: 'error', icon: 'i-lucide-circle-alert' })
  } finally {
    creatingDoctor.value = false
  }
}

const createObject = async () => {
  if (!newObject.code.trim() || !newObject.name.trim()) {
    return
  }
  creatingObject.value = true
  try {
    const id = await props.ctx.addObject({ ...newObject })
    if (id && direction.value) {
      direction.value.object_id = id
    }
    showNewObject.value = false
    newObject.code = ''
    newObject.name = ''
    newObject.full_name = ''
    newObject.address = ''
    toast.add({ title: t('directionWizard.objectCreated'), color: 'success', icon: 'i-lucide-building-2' })
  } catch {
    toast.add({ title: t('directionWizard.failedToCreateObject'), color: 'error', icon: 'i-lucide-circle-alert' })
  } finally {
    creatingObject.value = false
  }
}
</script>

<template>
  <div v-if="direction" class="flex flex-col gap-5">
    <h2
      class="text-lg font-semibold text-highlighted"
      data-testid="direction-fill-progress"
    >
      {{ directionHeading }}
    </h2>

    <section class="rounded-lg border border-default p-4">
      <h3 class="mb-3 text-sm font-semibold text-highlighted">
        {{ t('directionWizard.directionData') }}
      </h3>
      <div class="mb-4 grid gap-4 sm:grid-cols-2">
        <div class="flex flex-col gap-2">
          <label class="text-sm font-medium text-toned">{{ t('directionWizard.yearLabel') }} <span class="text-error">*</span></label>
          <UInput
            v-model.number="direction.year_no"
            type="number"
            :placeholder="t('directionWizard.yearLabel')"
            :class="missingClass(direction.year_no)"
            data-testid="direction-fill-year"
            @blur="saveRequisites"
          />
        </div>
        <div class="flex flex-col gap-2">
          <label class="text-sm font-medium text-toned">{{ t('directionWizard.numberLabel') }}</label>
          <UInput
            v-model.number="direction.base_no"
            type="number"
            :placeholder="t('directionWizard.numberLabel')"
            data-testid="direction-fill-base-no"
            @blur="saveRequisites"
          />
        </div>
      </div>
      <div class="grid gap-4 md:grid-cols-2">
        <div class="flex flex-col gap-2">
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium text-toned">{{ t('modes.sanitary_inspector.label') }}</label>
            <UButton
              :label="showNewDoctor ? t('common.cancel') : t('directionWizard.createNewDoctor')"
              :icon="showNewDoctor ? 'i-lucide-x' : 'i-lucide-plus'"
              color="neutral"
              variant="ghost"
              size="xs"
              data-telemetry="direction-fill-new-doctor"
              @click="showNewDoctor = !showNewDoctor"
            />
          </div>
          <USelectMenu
            v-model="direction.doctor_id"
            :items="ctx.doctorOptions"
            value-key="value"
            label-key="label"
            :search-input="{ placeholder: t('directionWizard.searchDoctor') }"
            :placeholder="t('directionWizard.chooseDoctor')"
            :class="missingClass(direction.doctor_id)"
            data-testid="direction-fill-doctor"
            clear
          />
          <p v-if="importSigner" class="text-xs text-muted">
            {{ t('directionWizard.directionListsDoctor') }} <span class="font-medium text-toned">{{ importSigner }}</span>
          </p>
          <div v-if="showNewDoctor" class="flex flex-col gap-2 rounded-md border border-default p-3">
            <UInput v-model="newDoctor.last_name" :placeholder="t('directionWizard.lastName')" size="sm" />
            <UInput v-model="newDoctor.first_name" :placeholder="t('directionWizard.firstNameRequired')" size="sm" />
            <UInput v-model="newDoctor.patronymic" :placeholder="t('directionWizard.patronymic')" size="sm" />
            <UButton
              :label="t('directionWizard.saveDoctor')"
              icon="i-lucide-save"
              color="primary"
              size="sm"
              :loading="creatingDoctor"
              :disabled="!newDoctor.first_name.trim()"
              @click="createDoctor"
            />
          </div>
        </div>

        <div class="flex flex-col gap-2">
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium text-toned">{{ t('directionWizard.tableObject') }}</label>
            <UButton
              :label="showNewObject ? t('common.cancel') : t('directionWizard.createNewObjectBtn')"
              :icon="showNewObject ? 'i-lucide-x' : 'i-lucide-plus'"
              color="neutral"
              variant="ghost"
              size="xs"
              data-telemetry="direction-fill-new-object"
              @click="showNewObject = !showNewObject"
            />
          </div>
          <USelectMenu
            v-model="direction.object_id"
            :items="ctx.objectOptions"
            value-key="value"
            label-key="label"
            :search-input="{ placeholder: t('directionWizard.searchObject') }"
            :placeholder="t('directionWizard.chooseObject')"
            :class="missingClass(direction.object_id)"
            data-testid="direction-fill-object"
            clear
          />
          <p v-if="importSamplingDepartment" class="text-xs text-muted">
            {{ t('directionWizard.samplingDeptLabel') }} <span class="font-medium text-toned">{{ importSamplingDepartment }}</span>
          </p>
          <div v-if="showNewObject" class="flex flex-col gap-2 rounded-md border border-default p-3">
            <UInput v-model="newObject.code" :placeholder="t('directionWizard.codeRequired')" size="sm" />
            <UInput v-model="newObject.name" :placeholder="t('directionWizard.nameRequired')" size="sm" />
            <UInput v-model="newObject.full_name" :placeholder="t('directionWizard.fullName')" size="sm" />
            <UInput v-model="newObject.address" :placeholder="t('directionWizard.address')" size="sm" />
            <UButton
              :label="t('directionWizard.saveObject')"
              icon="i-lucide-save"
              color="primary"
              size="sm"
              :loading="creatingObject"
              :disabled="!newObject.code.trim() || !newObject.name.trim()"
              @click="createObject"
            />
          </div>
        </div>
      </div>
    </section>

    <section class="flex flex-col gap-3">
      <div class="flex flex-wrap items-center gap-2">
        <UIcon name="i-lucide-test-tube-2" class="size-4 text-muted" />
        <h3 class="text-sm font-semibold text-highlighted">
          {{ t('directionWizard.directionSamples') }}
        </h3>
        <UBadge
          color="neutral"
          variant="subtle"
          size="sm"
          :label="String(samples.length)"
        />
        <UButton
          class="ml-auto"
          size="xs"
          icon="i-lucide-plus"
          :label="t('directionWizard.addSample')"
          :loading="adding"
          data-testid="direction-fill-add-sample"
          data-telemetry="direction-fill-add-sample"
          @click="addSample"
        />
      </div>

      <p v-if="!samples.length" class="text-sm text-muted">
        {{ t('directionWizard.noSamplesYet') }}
      </p>

      <UAccordion
        v-model="openSampleId"
        :items="sampleItems"
        class="rounded-lg border border-default px-4"
        :ui="{ label: 'flex flex-1 items-center gap-2 min-w-0' }"
      >
        <template #default="{ item }">
          <span
            class="truncate text-sm text-toned"
            data-testid="direction-fill-sample-toggle"
          >{{ item.sample.name || t('directionWizard.withoutNameCapitalized') }}</span>
          <UIcon
            v-if="!item.sample.name || !item.sample.sample_type_id"
            name="i-lucide-triangle-alert"
            class="size-4 shrink-0 text-warning"
          />
          <UBadge
            color="neutral"
            variant="outline"
            size="md"
            class="ml-auto"
            :label="t('directionWizard.indexOfTotal', { index: item.index + 1, total: samples.length })"
          />
          <UIcon
            name="i-lucide-trash-2"
            class="size-4 shrink-0 cursor-pointer text-muted hover:text-error"
            data-testid="direction-fill-remove-sample"
            data-telemetry="direction-fill-remove-sample"
            @click.stop="requestDelete(item.sample)"
          />
        </template>

        <template #body="{ item }">
          <div class="grid gap-4 md:grid-cols-2">
            <div class="flex flex-col gap-2">
              <label class="text-sm font-medium text-toned">{{ t('directionWizard.nameLabel') }}</label>
              <UInput
                v-model="item.sample.name"
                :placeholder="t('directionWizard.sampleNamePlaceholder')"
                :class="missingClass(item.sample.name)"
                data-testid="direction-fill-sample-name"
                @blur="autoSaveSample(item.sample)"
              />
            </div>
            <div class="flex flex-col gap-2">
              <label class="text-sm font-medium text-toned">{{ t('directionWizard.sampleTypeLabel') }}</label>
              <USelectMenu
                v-model="item.sample.sample_type_id"
                :items="ctx.sampleTypeOptions"
                value-key="value"
                label-key="label"
                :search-input="{ placeholder: t('directionWizard.searchType') }"
                :placeholder="t('directionWizard.chooseType')"
                :class="missingClass(item.sample.sample_type_id)"
                data-testid="direction-fill-sample-type"
                clear
                @update:model-value="(value) => onSampleTypeChange(item.sample.id, value)"
              />
            </div>
            <div class="flex flex-col gap-2">
              <label class="text-sm font-medium text-toned">{{ t('directionWizard.alternateName') }}</label>
              <UInput
                v-model="item.sample.alternate_name"
                :placeholder="t('directionWizard.alternateName')"
                @blur="autoSaveSample(item.sample)"
              />
            </div>
            <div class="flex flex-col gap-2">
              <label class="text-sm font-medium text-toned">{{ t('directionWizard.mass') }}</label>
              <UInput
                v-model="item.sample.mass"
                :placeholder="t('directionWizard.mass')"
                @blur="autoSaveSample(item.sample)"
              />
            </div>
            <div class="flex flex-col gap-2 md:col-span-2">
              <label class="text-sm font-medium text-toned">{{ t('workflowCommands.formFields.comment') }}</label>
              <UTextarea
                v-model="item.sample.comment"
                autoresize
                :rows="2"
                :placeholder="t('workflowCommands.formFields.comment')"
                @blur="autoSaveSample(item.sample)"
              />
            </div>
            <div class="flex flex-col gap-2 md:col-span-2">
              <label class="text-sm font-medium text-toned">{{ t('directionWizard.sampleLabs') }}</label>
              <USelectMenu
                :model-value="sampleLabIds(item.sample.id)"
                :items="labItems"
                value-key="value"
                label-key="label"
                multiple
                :search-input="{ placeholder: t('directionWizard.searchLab') }"
                data-testid="direction-fill-lab-select"
                data-telemetry="direction-fill-lab-select"
                @update:model-value="(value) => setSampleLabIds(item.sample.id, value)"
              >
                <div v-if="sampleLabs(item.sample.id).length" class="flex flex-wrap gap-1">
                  <UBadge
                    v-for="lab in sampleLabs(item.sample.id)"
                    :key="lab.id"
                    color="primary"
                    variant="subtle"
                    size="sm"
                    :title="lab.name || ''"
                    data-testid="direction-fill-lab-chip"
                  >
                    <span>{{ lab.code || lab.name || '' }}</span>
                    <UIcon
                      name="i-lucide-x"
                      class="size-3 cursor-pointer"
                      data-testid="direction-fill-lab-remove"
                      data-telemetry="direction-fill-lab-remove"
                      @click.stop="removeSampleLab(item.sample.id, lab.id)"
                    />
                  </UBadge>
                </div>
                <span v-else class="text-dimmed">{{ t('directionWizard.chooseLabs') }}</span>
              </USelectMenu>
              <p v-if="!sampleLabs(item.sample.id).length" class="text-xs text-muted">
                {{ t('directionWizard.noLabsHint') }}
              </p>
            </div>
            <div
              class="flex flex-col gap-2 md:col-span-2"
              data-testid="direction-fill-goals"
            >
              <label class="text-sm font-medium text-toned">{{ t('directionWizard.sampleResearchGoals') }}</label>
              <USelectMenu
                :model-value="sampleGoals(item.sample.id)"
                :items="researchGoalItems"
                value-key="value"
                label-key="label"
                multiple
                :disabled="!item.sample.sample_type_id"
                :search-input="{ placeholder: t('directionWizard.searchGoal') }"
                data-testid="direction-fill-goal-add"
                data-telemetry="direction-fill-goal-add"
                @update:model-value="(value) => setSampleGoals(item.sample.id, value)"
              >
                <div v-if="sampleGoals(item.sample.id).length" class="flex flex-wrap gap-1">
                  <UBadge
                    v-for="goalId in sampleGoals(item.sample.id)"
                    :key="goalId"
                    color="neutral"
                    variant="subtle"
                    size="sm"
                    :title="goalMeta(goalId).lab_name || ''"
                  >
                    <span>{{ goalMeta(goalId).name }}</span>
                    <UIcon
                      name="i-lucide-x"
                      class="size-3 cursor-pointer"
                      data-testid="direction-fill-goal-remove"
                      data-telemetry="direction-fill-goal-remove"
                      @click.stop="ctx.removeSampleGoal(item.sample.id, goalId)"
                    />
                  </UBadge>
                </div>
                <span v-else class="text-dimmed">
                  {{ item.sample.sample_type_id ? t('directionWizard.addGoalManually') : t('directionWizard.chooseTypeFirst') }}
                </span>
              </USelectMenu>
            </div>
          </div>
        </template>
      </UAccordion>
    </section>
  </div>

  <p v-else class="text-sm text-muted">
    {{ t('directionWizard.noDirectionsToFill') }}
  </p>

  <UModal
    :open="!!pendingDelete"
    :title="t('directionWizard.deleteSampleTitle')"
    :dismissible="!deleting"
    @update:open="(value) => { if (!value) pendingDelete = null }"
  >
    <template #body>
      <p class="text-sm text-toned">
        {{ t('directionWizard.deleteSampleConfirm', { label: pendingDelete?.label }) }}
      </p>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton
          :label="t('common.cancel')"
          color="neutral"
          variant="ghost"
          :disabled="deleting"
          @click="pendingDelete = null"
        />
        <UButton
          :label="t('common.delete')"
          color="error"
          icon="i-lucide-trash-2"
          :loading="deleting"
          data-testid="direction-fill-remove-confirm"
          @click="confirmDelete"
        />
      </div>
    </template>
  </UModal>
</template>
