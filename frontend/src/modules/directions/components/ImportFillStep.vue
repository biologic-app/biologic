<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { DirectionImportContext } from '@/modules/directions/composables/useDirectionImport'

const props = defineProps<{ ctx: DirectionImportContext }>()
const toast = useToast()

const direction = computed(() => props.ctx.directions[props.ctx.currentIndex] ?? null)
const samples = computed(() => (direction.value ? props.ctx.samplesByDirection[direction.value.id] ?? [] : []))
const total = computed(() => props.ctx.directions.length)

// Крупный заголовок «Направление 2025 № 461 — N-е из M».
const directionHeading = computed(() => {
  const current = direction.value
  const label = current
    ? [current.year_no, current.base_no ? `№ ${current.base_no}` : null].filter(Boolean).join(' ')
    : ''
  const base = label ? `Направление ${label}` : 'Направление'
  return `${base} — ${props.ctx.currentIndex + 1}-е из ${total.value}`
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

// Сворачивание карточек образцов (до 94 на направление). Свёрнуто по умолчанию;
// при смене направления образцы нового направления сворачиваются заново.
const collapsedSamples = reactive<Record<string, boolean>>({})

// Пагинация образцов: на направлении бывает до ~94 образцов — не рендерим все сразу.
// Введённые данные живут в реактивном composable, поэтому листание страниц их не теряет.
const SAMPLES_PER_PAGE = 5
const samplePage = ref(1)
const sampleTotalPages = computed(() => Math.max(1, Math.ceil(samples.value.length / SAMPLES_PER_PAGE)))
const pagedSamples = computed(() => {
  const start = (samplePage.value - 1) * SAMPLES_PER_PAGE
  return samples.value
    .slice(start, start + SAMPLES_PER_PAGE)
    .map((sample, offset) => ({ sample, index: start + offset }))
})
const sampleRangeStart = computed(() => (samples.value.length ? (samplePage.value - 1) * SAMPLES_PER_PAGE + 1 : 0))
const sampleRangeEnd = computed(() => Math.min(samplePage.value * SAMPLES_PER_PAGE, samples.value.length))
const prevSamplePage = () => {
  if (samplePage.value > 1) {
    samplePage.value -= 1
  }
}
const nextSamplePage = () => {
  if (samplePage.value < sampleTotalPages.value) {
    samplePage.value += 1
  }
}

watch(
  () => direction.value?.id,
  (id) => {
    samplePage.value = 1
    for (const sample of samples.value) {
      collapsedSamples[sample.id] = true
    }
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
const sampleLabs = (sampleId: string) => props.ctx.labsBySample[sampleId] ?? []

const goalMeta = (goalId: string): { name: string; lab_name: string | null } =>
  props.ctx.goalLabById[goalId] ?? { name: goalId.slice(0, 8).toUpperCase(), lab_name: null }

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

// Авто-подстановка дефолтных целей при выборе/смене типа образца.
const onSampleTypeChange = (sampleId: string, typeId: unknown) => {
  const value = typeof typeId === 'string' ? typeId : null
  void props.ctx.applySampleTypeDefaults(sampleId, value).catch(() => {
    toast.add({
      title: 'Не удалось подтянуть цели по типу образца',
      color: 'error',
      icon: 'i-lucide-circle-alert'
    })
  })
}

const isSampleCollapsed = (id: string) => Boolean(collapsedSamples[id])
const toggleSample = (id: string) => {
  collapsedSamples[id] = !collapsedSamples[id]
}
const allCollapsed = computed(
  () => samples.value.length > 0 && samples.value.every((sample) => collapsedSamples[sample.id])
)
const toggleAllSamples = () => {
  const collapse = !allCollapsed.value
  for (const sample of samples.value) {
    collapsedSamples[sample.id] = collapse
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

const saveCurrent = async (options: { silent?: boolean } = {}): Promise<boolean> => {
  const current = direction.value
  if (!current) {
    return true
  }
  // Сохранение направления + образцов + синхронизация целей живёт в composable
  // (переиспользуется футером мастера для массового сохранения перед регистрацией).
  const ok = await props.ctx.persistDirection(current.id)
  if (ok) {
    if (!options.silent) {
      toast.add({ title: 'Данные направления сохранены', color: 'success', icon: 'i-lucide-circle-check' })
    }
  } else {
    toast.add({ title: 'Не удалось сохранить часть данных', color: 'error', icon: 'i-lucide-circle-alert' })
  }
  return ok
}

// Навигация не сбрасывает состояние (оно живёт в реактивном composable);
// перед сменой направления авто-сохраняем текущее, чтобы не потерять правки.
const goNext = async () => {
  await saveCurrent({ silent: true })
  props.ctx.nextDirection()
}
const goPrev = async () => {
  await saveCurrent({ silent: true })
  props.ctx.prevDirection()
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
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2
        class="text-lg font-semibold text-highlighted"
        data-testid="direction-fill-progress"
      >
        {{ directionHeading }}
      </h2>
      <div class="flex items-center gap-2">
        <UButton
          label="Пред. направление"
          icon="i-lucide-chevron-left"
          color="neutral"
          variant="outline"
          size="sm"
          :disabled="ctx.currentIndex === 0"
          data-telemetry="direction-fill-prev"
          @click="goPrev"
        />
        <UButton
          label="След. направление"
          icon="i-lucide-chevron-right"
          trailing
          color="neutral"
          variant="outline"
          size="sm"
          :disabled="ctx.currentIndex >= total - 1"
          data-telemetry="direction-fill-next"
          @click="goNext"
        />
      </div>
    </div>

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
        <UBadge color="neutral" variant="subtle" :label="String(samples.length)" />
        <UButton
          v-if="samples.length"
          :label="allCollapsed ? 'Развернуть все' : 'Свернуть все'"
          :icon="allCollapsed ? 'i-lucide-chevrons-up-down' : 'i-lucide-chevrons-down-up'"
          color="neutral"
          variant="ghost"
          size="xs"
          class="ml-auto"
          data-telemetry="direction-fill-toggle-all-samples"
          @click="toggleAllSamples"
        />
      </div>

      <p v-if="!samples.length" class="text-sm text-muted">
        У направления нет образцов.
      </p>

      <div
        v-for="{ sample, index } in pagedSamples"
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
          <UBadge
            color="neutral"
            variant="outline"
            size="sm"
            :label="`Образец ${index + 1} из ${samples.length}`"
          />
          <span class="truncate text-sm text-toned">{{ sample.name || 'Без названия' }}</span>
          <UIcon
            v-if="!sample.name || !sample.sample_type_id"
            name="i-lucide-triangle-alert"
            class="ml-auto size-4 shrink-0 text-warning"
          />
        </button>
        <div v-show="!isSampleCollapsed(sample.id)" class="grid gap-4 md:grid-cols-2">
          <div class="flex flex-col gap-2 md:col-span-2">
            <label class="text-sm font-medium text-toned">Лаборатории образца</label>
            <div v-if="sampleLabs(sample.id).length" class="flex flex-wrap gap-1.5">
              <UBadge
                v-for="lab in sampleLabs(sample.id)"
                :key="lab.id"
                color="primary"
                variant="subtle"
                size="sm"
                :label="lab.code || lab.name || ''"
                :title="lab.name || ''"
              />
            </div>
            <p v-else class="text-xs text-muted">
              Лаборатории не проставлены (нет меток легаси) — цели по типу подобрать нельзя.
            </p>
          </div>
          <div class="flex flex-col gap-2">
            <label class="text-sm font-medium text-toned">Название</label>
            <UInput
              v-model="sample.name"
              placeholder="Название образца"
              :class="missingClass(sample.name)"
              data-testid="direction-fill-sample-name"
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
            <UInput v-model="sample.alternate_name" placeholder="Альтернативное имя" />
          </div>
          <div class="flex flex-col gap-2">
            <label class="text-sm font-medium text-toned">Масса</label>
            <UInput v-model="sample.mass" placeholder="Масса" />
          </div>
          <div class="flex flex-col gap-2 md:col-span-2">
            <label class="text-sm font-medium text-toned">Комментарий</label>
            <UTextarea
              v-model="sample.comment"
              autoresize
              :rows="2"
              placeholder="Комментарий"
            />
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
              :search-input="{ placeholder: 'Поиск цели' }"
              placeholder="Добавить цель из справочника"
              data-testid="direction-fill-goal-add"
              data-telemetry="direction-fill-goal-add"
              @update:model-value="(value) => setSampleGoals(sample.id, value)"
            />
            <ul v-if="sampleGoals(sample.id).length" class="flex flex-col gap-1">
              <li
                v-for="goalId in sampleGoals(sample.id)"
                :key="goalId"
                class="flex items-center gap-2 rounded-md border border-default px-2 py-1"
              >
                <span class="text-sm text-toned">{{ goalMeta(goalId).name }}</span>
                <UBadge
                  v-if="goalMeta(goalId).lab_name"
                  color="neutral"
                  variant="subtle"
                  size="sm"
                  :label="goalMeta(goalId).lab_name || ''"
                />
                <UButton
                  icon="i-lucide-x"
                  color="neutral"
                  variant="ghost"
                  size="xs"
                  class="ml-auto"
                  data-testid="direction-fill-goal-remove"
                  data-telemetry="direction-fill-goal-remove"
                  @click="ctx.removeSampleGoal(sample.id, goalId)"
                />
              </li>
            </ul>
            <p v-else class="text-xs text-muted">
              Цели не выбраны. Выберите тип образца для авто-подстановки или добавьте вручную.
            </p>
          </div>
        </div>
      </div>

      <div
        v-if="sampleTotalPages > 1"
        class="flex items-center justify-center gap-3"
      >
        <UButton
          icon="i-lucide-chevron-left"
          color="neutral"
          variant="ghost"
          size="sm"
          :disabled="samplePage === 1"
          data-telemetry="direction-fill-samples-prev-page"
          @click="prevSamplePage"
        />
        <span class="text-sm text-muted">
          {{ sampleRangeStart }}–{{ sampleRangeEnd }} из {{ samples.length }}
        </span>
        <UButton
          icon="i-lucide-chevron-right"
          color="neutral"
          variant="ghost"
          size="sm"
          :disabled="samplePage >= sampleTotalPages"
          data-telemetry="direction-fill-samples-next-page"
          @click="nextSamplePage"
        />
      </div>
    </section>
  </div>

  <p v-else class="text-sm text-muted">
    Нет направлений для дозаполнения.
  </p>
</template>
