<script setup lang="ts">
import type { DirectionImportContext } from '@/modules/directions/composables/useDirectionImport'

const props = defineProps<{ ctx: DirectionImportContext }>()

// Формат данных из UI — только Excel. Бэкенд сам определяет `.xls` (legacy-парсер)
// vs `.xlsx` по имени файла, поэтому в контракт всегда уходит type="xlsx".
// JSON поддерживается только для межсистемного взаимодействия и в UI не предлагается.
const onFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  props.ctx.setFile(input.files?.[0] ?? null)
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <p class="text-sm text-muted">
      Загрузите файл направлений в формате Excel (.xlsx или .xls). Импорт создаст
      направления и образцы в статусе «черновик», после чего мастер поможет дозаполнить
      недостающие данные и зарегистрировать их.
    </p>

    <div class="flex flex-col gap-2">
      <label class="text-sm font-medium text-toned">Файл Excel</label>
      <input
        type="file"
        accept=".xlsx,.xls"
        data-testid="import-excel-input"
        data-telemetry="direction-import-file"
        class="block w-full text-sm text-muted file:mr-3 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-2 file:text-sm file:font-medium file:text-inverted hover:file:bg-primary/90"
        @change="onFileChange"
      >
      <p v-if="ctx.fileName" class="text-xs text-muted">
        Выбран файл: {{ ctx.fileName }}
      </p>
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
