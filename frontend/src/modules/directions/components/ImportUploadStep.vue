<script setup lang="ts">
import { ref } from 'vue'
import type { DirectionImportContext } from '@/modules/directions/composables/useDirectionImport'

const props = defineProps<{ ctx: DirectionImportContext }>()

const fileInput = ref<HTMLInputElement | null>(null)
const isDragOver = ref(false)

// Формат данных из UI — только Excel. Бэкенд сам определяет `.xls` (legacy-парсер)
// vs `.xlsx` по имени файла, поэтому в контракт всегда уходит type="xlsx".
// JSON поддерживается только для межсистемного взаимодействия и в UI не предлагается.
const onFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  props.ctx.setFile(input.files?.[0] ?? null)
}

const openFileDialog = () => {
  fileInput.value?.click()
}

const onDrop = (event: DragEvent) => {
  isDragOver.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) {
    props.ctx.setFile(file)
  }
}

const pickAnotherFile = () => {
  props.ctx.setFile(null)
  if (fileInput.value) {
    fileInput.value.value = ''
  }
  fileInput.value?.click()
}

const formatFileSize = (bytes: number): string => {
  if (!bytes) {
    return ''
  }
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} КБ`
    : `${(bytes / (1024 * 1024)).toFixed(1)} МБ`
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <p class="text-sm text-muted">
      Загрузите файл направлений в формате Excel (.xlsx или .xls). Импорт создаст
      направления и образцы в статусе «черновик», после чего мастер поможет дозаполнить
      недостающие данные и зарегистрировать их.
    </p>

    <div
      class="flex flex-col items-center justify-center gap-2 rounded-lg border-2 p-8 text-center transition-colors cursor-pointer"
      :class="[
        ctx.fileName
          ? 'border-solid border-success bg-success/5'
          : 'border-dashed',
        !ctx.fileName && (isDragOver ? 'border-primary bg-primary/5' : 'border-muted hover:border-primary/50'),
      ]"
      data-testid="import-excel-dropzone"
      @click="openFileDialog"
      @dragover.prevent="isDragOver = true"
      @dragleave.prevent="isDragOver = false"
      @drop.prevent="onDrop"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".xlsx,.xls"
        data-testid="import-excel-input"
        data-telemetry="direction-import-file"
        class="hidden"
        @change="onFileChange"
      >

      <template v-if="ctx.fileName">
        <div
          class="flex size-14 items-center justify-center rounded-full bg-success text-inverted ring-4 ring-success/20"
          data-testid="import-excel-selected-icon"
        >
          <UIcon name="i-lucide-check" class="size-7" />
        </div>
        <p class="text-sm font-semibold text-success">
          Файл готов к импорту
        </p>
        <p class="flex items-center gap-1.5 text-sm font-medium text-highlighted">
          <UIcon name="i-lucide-file-spreadsheet" class="size-4 shrink-0 text-success" />
          <span class="truncate">{{ ctx.fileName }}</span>
          <span v-if="ctx.fileSize" class="shrink-0 text-xs font-normal text-muted">
            · {{ formatFileSize(ctx.fileSize) }}
          </span>
        </p>
        <UButton
          size="xs"
          color="neutral"
          variant="soft"
          icon="i-lucide-x"
          label="Выбрать другой файл"
          data-testid="import-excel-clear"
          @click.stop="pickAnotherFile"
        />
      </template>
      <template v-else>
        <UIcon name="i-lucide-upload" class="size-8 text-muted" />
        <p class="text-sm text-toned">
          <span class="font-medium text-primary">Выберите файл</span> или перетащите его сюда
        </p>
        <p class="text-xs text-muted">
          Excel (.xlsx или .xls)
        </p>
      </template>
    </div>

    <UAlert
      v-if="ctx.importError"
      color="error"
      variant="subtle"
      icon="i-lucide-circle-alert"
      title="Не удалось импортировать"
      :description="ctx.importError"
    />
  </div>
</template>
