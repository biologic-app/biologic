<script setup lang="ts">
// components/WorkflowFieldControl.vue
// Один контрол поля раннера (schema-doc §4). Инкапсулирует все типы полей —
// 6 примитивов + dictionary/file/computed — и показывает ошибку валидации под
// полем. Переиспользуется и как top-level поле экрана, и как ячейка table-блока.
// Видимость (visibleWhen) решает родитель (v-if) — здесь не дублируется.

import { computed, onMounted, ref } from 'vue'
import { useToast } from '@nuxt/ui/composables'
import type {
  AnswerRow,
  AttachmentRef,
  JournalAnswerValue,
  JournalField,
} from '@/modules/workflows/types/journal'
import { maxSizeMb, validateField } from '@/modules/workflows/engine/fields'
import {
  getAttachmentUrl,
  loadDictionaryOptions,
  uploadAttachment,
  type DictionaryOption,
} from '@/modules/workflows/api/workflows.api'

const props = withDefaults(
  defineProps<{
    field: JournalField
    // Run id нужен для загрузки файлов (upload требует существующую запись).
    runId?: string | null
    disabled?: boolean
    // В ячейке таблицы подпись даёт заголовок колонки — своя не нужна.
    hideLabel?: boolean
  }>(),
  { runId: null, disabled: false, hideLabel: false },
)

// Значение поля: скаляр (примитивы/dictionary/computed) либо AttachmentRef[]
// (file). Тип совпадает с индексом JournalAnswers, чтобы биндиться и к
// answers[fieldId], и к ячейке строки таблицы (top-level поле table не бывает).
const model = defineModel<JournalAnswerValue | AnswerRow[] | AttachmentRef[]>()

// Глобальный дефолт лимита размера, если у file-поля нет правила maxSizeMb.
const DEFAULT_MAX_SIZE_MB = 25

const toast = useToast()

// ─── Прокси значений под конкретные контролы ────────────────────────────────

const scalar = computed<JournalAnswerValue>({
  get: () => (Array.isArray(model.value) ? null : model.value ?? null),
  set: (v) => {
    model.value = v
  },
})

const boolValue = computed<boolean>({
  get: () => model.value === true,
  set: (v) => {
    model.value = v
  },
})

const fileRefs = computed<AttachmentRef[]>(() =>
  Array.isArray(model.value) ? (model.value as AttachmentRef[]) : [],
)

// Значение computed приходит из движка; здесь — только read-only отображение.
const computedDisplay = computed(() =>
  model.value === null || model.value === undefined ? '' : String(model.value),
)

const selectItems = computed(() =>
  (props.field.options ?? []).map((o) => ({ label: o.label, value: o.value })),
)

// Ошибка валидации под полем (min/max/regex). Пустые/невидимые — без ошибки.
const validationError = computed(() => validateField(props.field, model.value))

// ─── Dictionary: опции из справочника (кэшируются в API-слое) ────────────────

const dictOptions = ref<DictionaryOption[]>([])
const dictLoading = ref(false)

async function loadDict() {
  const source = props.field.source
  if (props.field.type !== 'dictionary' || !source) return
  dictLoading.value = true
  try {
    dictOptions.value = await loadDictionaryOptions(source)
  } catch {
    dictOptions.value = []
    toast.add({
      title: 'Не удалось загрузить справочник',
      description: source.endpoint,
      color: 'error',
    })
  } finally {
    dictLoading.value = false
  }
}

onMounted(loadDict)

// USelectMenu поиск: searchable !== false → показываем строку поиска.
const dictSearchInput = computed(() =>
  props.field.source?.searchable === false ? false : { placeholder: 'Поиск…' },
)

// ─── File: немедленная загрузка → AttachmentRef[] в answers ──────────────────

const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const fileError = ref<string | null>(null)

// Загрузка доступна только при существующей записи (preview/без run id — нет).
const fileUploadEnabled = computed(() => !props.disabled && !!props.runId)

const fileLimitMb = computed(() => maxSizeMb(props.field) ?? DEFAULT_MAX_SIZE_MB)

function pickFile() {
  fileError.value = null
  fileInput.value?.click()
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = '' // разрешить повторный выбор того же файла
  if (!files.length || !props.runId) return

  const limitBytes = fileLimitMb.value * 1024 * 1024
  uploading.value = true
  fileError.value = null
  try {
    for (const file of files) {
      if (file.size > limitBytes) {
        fileError.value = `Файл «${file.name}» больше ${fileLimitMb.value} МБ`
        continue
      }
      const attachment = await uploadAttachment(props.runId, props.field.id, file)
      const next: AttachmentRef = {
        attachmentId: attachment.id,
        filename: attachment.filename,
        sizeBytes: attachment.size_bytes,
      }
      model.value = [...fileRefs.value, next]
    }
  } catch {
    fileError.value = 'Ошибка загрузки файла'
  } finally {
    uploading.value = false
  }
}

function removeFile(index: number) {
  model.value = fileRefs.value.filter((_, i) => i !== index)
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} КБ`
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`
}
</script>

<template>
  <UFormField
    :label="hideLabel ? undefined : field.label"
    :required="field.required"
    :description="hideLabel ? undefined : field.description"
    :error="validationError || fileError || undefined"
  >
    <template v-if="field.type === 'text'">
      <UInput
        v-model="scalar as string"
        :placeholder="field.placeholder"
        :disabled="disabled"
        class="w-full"
      />
    </template>

    <template v-else-if="field.type === 'textarea'">
      <UTextarea
        v-model="scalar as string"
        :placeholder="field.placeholder"
        :rows="3"
        :disabled="disabled"
        class="w-full"
      />
    </template>

    <template v-else-if="field.type === 'number'">
      <UInput
        v-model.number="scalar as number"
        type="number"
        :placeholder="field.placeholder"
        :disabled="disabled"
        class="w-full"
      />
    </template>

    <template v-else-if="field.type === 'boolean'">
      <USwitch v-model="boolValue" :disabled="disabled" />
    </template>

    <template v-else-if="field.type === 'select'">
      <USelect
        v-model="scalar as string"
        :items="selectItems"
        :placeholder="field.placeholder"
        :disabled="disabled"
        class="w-full"
      />
    </template>

    <template v-else-if="field.type === 'date'">
      <UInput
        v-model="scalar as string"
        type="date"
        :disabled="disabled"
        class="w-full"
      />
    </template>

    <template v-else-if="field.type === 'dictionary'">
      <USelectMenu
        v-model="scalar"
        :items="dictOptions"
        value-key="value"
        label-key="label"
        :loading="dictLoading"
        :search-input="dictSearchInput"
        :placeholder="field.placeholder ?? 'Выберите…'"
        :disabled="disabled"
        class="w-full"
      />
    </template>

    <template v-else-if="field.type === 'computed'">
      <UInput
        :model-value="computedDisplay"
        disabled
        class="w-full"
        :ui="{ base: 'text-muted' }"
      />
    </template>

    <template v-else-if="field.type === 'file'">
      <div class="flex flex-col gap-2">
        <input
          ref="fileInput"
          type="file"
          :accept="field.accept"
          multiple
          class="hidden"
          @change="onFileChange"
        >
        <div class="flex items-center gap-2">
          <UButton
            size="sm"
            variant="soft"
            icon="i-lucide-upload"
            :loading="uploading"
            :disabled="!fileUploadEnabled"
            @click="pickFile"
          >
            Загрузить файл
          </UButton>
          <span class="text-xs text-muted">до {{ fileLimitMb }} МБ</span>
        </div>
        <p v-if="!fileUploadEnabled" class="text-xs text-muted">
          Загрузка станет доступна после создания записи.
        </p>
        <ul v-if="fileRefs.length" class="flex flex-col gap-1">
          <li
            v-for="(att, i) in fileRefs"
            :key="att.attachmentId"
            class="flex items-center gap-2 rounded-md border border-default bg-elevated/40 px-2 py-1"
          >
            <UIcon name="i-lucide-paperclip" class="size-3.5 shrink-0 text-muted" />
            <a
              :href="getAttachmentUrl(att.attachmentId)"
              target="_blank"
              rel="noopener"
              class="min-w-0 flex-1 truncate text-xs text-primary hover:underline"
            >
              {{ att.filename }}
            </a>
            <span class="shrink-0 text-[10.5px] text-dimmed">{{ formatSize(att.sizeBytes) }}</span>
            <UButton
              size="xs"
              color="error"
              variant="ghost"
              icon="i-lucide-x"
              :disabled="disabled"
              @click="removeFile(i)"
            />
          </li>
        </ul>
      </div>
    </template>

    <!-- Неизвестный тип: безопасный read-only фолбэк (без падения рендера). -->
    <template v-else>
      <UInput :model-value="computedDisplay" disabled class="w-full" />
    </template>
  </UFormField>
</template>
