<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import type { DirectionImportContext } from '@/modules/directions/composables/useDirectionImport'

const props = defineProps<{ ctx: DirectionImportContext }>()
const toast = useToast()

const direction = computed(() => props.ctx.directions[props.ctx.currentIndex] ?? null)
const samples = computed(() => (direction.value ? props.ctx.samplesByDirection[direction.value.id] ?? [] : []))
const total = computed(() => props.ctx.directions.length)

const directionWarnings = computed(() => {
  const raw = direction.value?.import_warnings
  if (!raw || typeof raw !== 'object') {
    return [] as string[]
  }
  return Object.entries(raw as Record<string, unknown>).map(([field, value]) => `${field}: ${String(value)}`)
})

const showNewDoctor = ref(false)
const showNewObject = ref(false)
const creatingDoctor = ref(false)
const creatingObject = ref(false)
const newDoctor = reactive({ first_name: '', last_name: '', patronymic: '' })
const newObject = reactive({ code: '', name: '', full_name: '', address: '' })

const missingClass = (value: unknown) =>
  value === null || value === undefined || value === '' ? 'ring-2 ring-warning/60 rounded-md' : ''

const saveCurrent = async () => {
  const current = direction.value
  if (!current) {
    return
  }
  const okDirection = await props.ctx.saveDirection(current.id, {
    doctor_id: current.doctor_id,
    object_id: current.object_id,
    is_urgent: current.is_urgent
  })
  let okSamples = true
  for (const sample of samples.value) {
    const saved = await props.ctx.saveSample(current.id, sample.id, {
      name: sample.name || null,
      sample_type_id: sample.sample_type_id,
      alternate_name: sample.alternate_name || null,
      mass: sample.mass || null,
      comment: sample.comment || null,
      is_urgent: sample.is_urgent
    })
    okSamples = okSamples && saved
  }
  if (okDirection && okSamples) {
    toast.add({ title: 'Данные направления сохранены', color: 'success', icon: 'i-lucide-circle-check' })
  } else {
    toast.add({ title: 'Не удалось сохранить часть данных', color: 'error', icon: 'i-lucide-circle-alert' })
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
      <div class="flex items-center gap-2">
        <UBadge
          color="primary"
          variant="subtle"
          :label="`Направление ${ctx.currentIndex + 1} из ${total}`"
          data-testid="direction-fill-progress"
        />
        <span class="text-sm text-muted">
          {{ [direction.year_no, direction.base_no ? `№ ${direction.base_no}` : null].filter(Boolean).join(' ') || 'Без номера' }}
        </span>
      </div>
      <div class="flex items-center gap-2">
        <UButton
          label="Назад"
          icon="i-lucide-chevron-left"
          color="neutral"
          variant="outline"
          size="sm"
          :disabled="ctx.currentIndex === 0"
          data-telemetry="direction-fill-prev"
          @click="ctx.prevDirection()"
        />
        <UButton
          label="Далее"
          icon="i-lucide-chevron-right"
          trailing
          color="neutral"
          variant="outline"
          size="sm"
          :disabled="ctx.currentIndex >= total - 1"
          data-telemetry="direction-fill-next"
          @click="ctx.nextDirection()"
        />
      </div>
    </div>

    <UAlert
      v-if="directionWarnings.length"
      color="warning"
      variant="subtle"
      icon="i-lucide-triangle-alert"
      title="Предупреждения импорта по направлению"
    >
      <template #description>
        <ul class="list-disc pl-4">
          <li v-for="(message, index) in directionWarnings" :key="index">
            {{ message }}
          </li>
        </ul>
      </template>
    </UAlert>

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
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-test-tube-2" class="size-4 text-muted" />
        <h3 class="text-sm font-semibold text-highlighted">
          Образцы направления
        </h3>
        <UBadge color="neutral" variant="subtle" :label="String(samples.length)" />
      </div>

      <p v-if="!samples.length" class="text-sm text-muted">
        У направления нет образцов.
      </p>

      <div
        v-for="(sample, sampleIndex) in samples"
        :key="sample.id"
        class="rounded-lg border border-default p-4"
      >
        <div class="mb-3 flex items-center gap-2">
          <UBadge
            color="neutral"
            variant="outline"
            size="sm"
            :label="`Образец ${sampleIndex + 1} из ${samples.length}`"
          />
        </div>
        <div class="grid gap-4 md:grid-cols-2">
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
        </div>
      </div>
    </section>

    <div class="flex justify-end">
      <UButton
        label="Сохранить направление и образцы"
        icon="i-lucide-save"
        color="primary"
        :loading="Boolean(ctx.savingKey)"
        data-testid="direction-fill-save"
        data-telemetry="direction-fill-save"
        @click="saveCurrent"
      />
    </div>
  </div>

  <p v-else class="text-sm text-muted">
    Нет направлений для дозаполнения.
  </p>
</template>
