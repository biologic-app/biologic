<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { DirectionImportContext } from '@/modules/directions/composables/useDirectionImport'

const props = defineProps<{ ctx: DirectionImportContext }>()
const toast = useToast()

const direction = computed(() => props.ctx.directions[props.ctx.currentIndex] ?? null)
const samples = computed(() => (direction.value ? props.ctx.samplesByDirection[direction.value.id] ?? [] : []))
// Крупный заголовок «№ 2025-461».
const directionHeading = computed(() => {
  const current = direction.value
  if (current?.year_no && current?.base_no) {
    return `№ ${current.year_no}-${current.base_no}`
  }
  return 'Направление'
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

// Аккордеон образцов: в один момент времени открыт максимум один образец.
// При смене направления открытый образец сбрасывается.
const openSampleId = ref<string | null>(null)

// Все образцы направления рендерятся сразу (без пагинации); аккордеон держит
// открытым максимум один, поэтому DOM большого направления остаётся лёгким.
const allSamples = computed(() => samples.value.map((sample, index) => ({ sample, index })))

watch(
  () => direction.value?.id,
  (id) => {
    openSampleId.value = null
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
      title: 'Не удалось обновить лаборатории образца',
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
    toast.add({ title: 'Не удалось сохранить образец', color: 'error', icon: 'i-lucide-circle-alert' })
  }
}

// Авто-подстановка дефолтных целей при выборе/смене типа образца + немедленное сохранение.
const onSampleTypeChange = (sampleId: string, typeId: unknown) => {
  const value = typeof typeId === 'string' ? typeId : null
  const sample = samples.value.find((row) => row.id === sampleId)
  void props.ctx.applySampleTypeDefaults(sampleId, value).catch(() => {
    toast.add({
      title: 'Не удалось подтянуть цели по типу образца',
      color: 'error',
      icon: 'i-lucide-circle-alert'
    })
  })
  if (sample) {
    void autoSaveSample(sample)
  }
}

const isSampleCollapsed = (id: string) => openSampleId.value !== id
const toggleSample = (id: string) => {
  openSampleId.value = openSampleId.value === id ? null : id
}

const showNewDoctor = ref(false)
const showNewObject = ref(false)
const creatingDoctor = ref(false)
const creatingObject = ref(false)
const newDoctor = reactive({ first_name: '', last_name: '', patronymic: '' })
const newObject = reactive({ code: '', name: '', full_name: '', address: '' })

const missingClass = (value: unknown) =>
  value === null || value === undefined || value === '' ? 'ring-2 ring-warning/60 rounded-md' : ''

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
    toast.add({ title: 'Санитарный врач создан', color: 'success', icon: 'i-lucide-user-check' })
  } catch {
    toast.add({ title: 'Не удалось создать врача', color: 'error', icon: 'i-lucide-circle-alert' })
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
    toast.add({ title: 'Объект создан', color: 'success', icon: 'i-lucide-building-2' })
  } catch {
    toast.add({ title: 'Не удалось создать объект', color: 'error', icon: 'i-lucide-circle-alert' })
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
        Данные направления
      </h3>
      <div class="grid gap-4 md:grid-cols-2">
        <div class="flex flex-col gap-2">
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium text-toned">Санитарный врач</label>
            <UButton
              :label="showNewDoctor ? 'Отмена' : 'Создать нового'"
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
            :search-input="{ placeholder: 'Поиск врача' }"
            placeholder="Выберите врача"
            :class="missingClass(direction.doctor_id)"
            data-testid="direction-fill-doctor"
            clear
          />
          <p v-if="importSigner" class="text-xs text-muted">
            В направлении указан врач: <span class="font-medium text-toned">{{ importSigner }}</span>
          </p>
          <div v-if="showNewDoctor" class="flex flex-col gap-2 rounded-md border border-default p-3">
            <UInput v-model="newDoctor.last_name" placeholder="Фамилия" size="sm" />
            <UInput v-model="newDoctor.first_name" placeholder="Имя (обязательно)" size="sm" />
            <UInput v-model="newDoctor.patronymic" placeholder="Отчество" size="sm" />
            <UButton
              label="Сохранить врача"
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
            <label class="text-sm font-medium text-toned">Объект</label>
            <UButton
              :label="showNewObject ? 'Отмена' : 'Создать новый'"
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
            :search-input="{ placeholder: 'Поиск объекта' }"
            placeholder="Выберите объект"
            :class="missingClass(direction.object_id)"
            data-testid="direction-fill-object"
            clear
          />
          <p v-if="importSamplingDepartment" class="text-xs text-muted">
            Отдел отбора / объект: <span class="font-medium text-toned">{{ importSamplingDepartment }}</span>
          </p>
          <div v-if="showNewObject" class="flex flex-col gap-2 rounded-md border border-default p-3">
            <UInput v-model="newObject.code" placeholder="Код (обязательно)" size="sm" />
            <UInput v-model="newObject.name" placeholder="Название (обязательно)" size="sm" />
            <UInput v-model="newObject.full_name" placeholder="Полное название" size="sm" />
            <UInput v-model="newObject.address" placeholder="Адрес" size="sm" />
            <UButton
              label="Сохранить объект"
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
          Образцы направления
        </h3>
        <UBadge
          color="neutral"
          variant="subtle"
          size="sm"
          :label="String(samples.length)"
        />
      </div>

      <p v-if="!samples.length" class="text-sm text-muted">
        У направления нет образцов.
      </p>

      <div
        v-for="{ sample, index } in allSamples"
        :key="sample.id"
        class="rounded-lg border border-default p-4"
      >
        <button
          type="button"
          class="flex w-full items-center gap-2 text-left"
          :class="isSampleCollapsed(sample.id) ? '' : 'mb-3'"
          data-testid="direction-fill-sample-toggle"
          @click="toggleSample(sample.id)"
        >
          <UIcon
            :name="isSampleCollapsed(sample.id) ? 'i-lucide-chevron-right' : 'i-lucide-chevron-down'"
            class="size-4 text-muted"
          />
          <span class="truncate text-sm text-toned">{{ sample.name || 'Без названия' }}</span>
          <UIcon
            v-if="!sample.name || !sample.sample_type_id"
            name="i-lucide-triangle-alert"
            class="size-4 shrink-0 text-warning"
          />
          <UBadge
            color="neutral"
            variant="outline"
            size="md"
            class="ml-auto"
            :label="`${index + 1} из ${samples.length}`"
          />
        </button>
        <div v-show="!isSampleCollapsed(sample.id)" class="grid gap-4 md:grid-cols-2">
          <div class="flex flex-col gap-2">
            <label class="text-sm font-medium text-toned">Название</label>
            <UInput
              v-model="sample.name"
              placeholder="Название образца"
              :class="missingClass(sample.name)"
              data-testid="direction-fill-sample-name"
              @blur="autoSaveSample(sample)"
            />
          </div>
          <div class="flex flex-col gap-2">
            <label class="text-sm font-medium text-toned">Тип образца</label>
            <USelectMenu
              v-model="sample.sample_type_id"
              :items="ctx.sampleTypeOptions"
              value-key="value"
              label-key="label"
              :search-input="{ placeholder: 'Поиск типа' }"
              placeholder="Выберите тип"
              :class="missingClass(sample.sample_type_id)"
              data-testid="direction-fill-sample-type"
              clear
              @update:model-value="(value) => onSampleTypeChange(sample.id, value)"
            />
          </div>
          <div class="flex flex-col gap-2">
            <label class="text-sm font-medium text-toned">Альтернативное имя</label>
            <UInput
              v-model="sample.alternate_name"
              placeholder="Альтернативное имя"
              @blur="autoSaveSample(sample)"
            />
          </div>
          <div class="flex flex-col gap-2">
            <label class="text-sm font-medium text-toned">Масса</label>
            <UInput
              v-model="sample.mass"
              placeholder="Масса"
              @blur="autoSaveSample(sample)"
            />
          </div>
          <div class="flex flex-col gap-2 md:col-span-2">
            <label class="text-sm font-medium text-toned">Комментарий</label>
            <UTextarea
              v-model="sample.comment"
              autoresize
              :rows="2"
              placeholder="Комментарий"
              @blur="autoSaveSample(sample)"
            />
          </div>
          <div class="flex flex-col gap-2 md:col-span-2">
            <label class="text-sm font-medium text-toned">Лаборатории образца</label>
            <USelectMenu
              :model-value="sampleLabIds(sample.id)"
              :items="labItems"
              value-key="value"
              label-key="label"
              multiple
              :search-input="{ placeholder: 'Поиск лаборатории' }"
              data-testid="direction-fill-lab-select"
              data-telemetry="direction-fill-lab-select"
              @update:model-value="(value) => setSampleLabIds(sample.id, value)"
            >
              <div v-if="sampleLabs(sample.id).length" class="flex flex-wrap gap-1">
                <UBadge
                  v-for="lab in sampleLabs(sample.id)"
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
                    @click.stop="removeSampleLab(sample.id, lab.id)"
                  />
                </UBadge>
              </div>
              <span v-else class="text-dimmed">Выберите лаборатории</span>
            </USelectMenu>
            <p v-if="!sampleLabs(sample.id).length" class="text-xs text-muted">
              Лаборатории не проставлены — добавьте вручную, иначе цели по типу подобрать нельзя.
            </p>
          </div>
          <div
            class="flex flex-col gap-2 md:col-span-2"
            data-testid="direction-fill-goals"
          >
            <label class="text-sm font-medium text-toned">Цели исследования</label>
            <USelectMenu
              :model-value="sampleGoals(sample.id)"
              :items="researchGoalItems"
              value-key="value"
              label-key="label"
              multiple
              :disabled="!sample.sample_type_id"
              :search-input="{ placeholder: 'Поиск цели' }"
              data-testid="direction-fill-goal-add"
              data-telemetry="direction-fill-goal-add"
              @update:model-value="(value) => setSampleGoals(sample.id, value)"
            >
              <div v-if="sampleGoals(sample.id).length" class="flex flex-wrap gap-1">
                <UBadge
                  v-for="goalId in sampleGoals(sample.id)"
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
                    @click.stop="ctx.removeSampleGoal(sample.id, goalId)"
                  />
                </UBadge>
              </div>
              <span v-else class="text-dimmed">
                {{ sample.sample_type_id ? 'Добавьте цель вручную' : 'Сначала выберите тип образца' }}
              </span>
            </USelectMenu>
          </div>
        </div>
      </div>
    </section>
  </div>

  <p v-else class="text-sm text-muted">
    Нет направлений для дозаполнения.
  </p>
</template>
