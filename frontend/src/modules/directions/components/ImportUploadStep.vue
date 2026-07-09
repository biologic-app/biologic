<script setup lang="ts">
import { computed } from 'vue'
import type { DirectionImportContext } from '@/modules/directions/composables/useDirectionImport'
import type { ImportType } from '@/modules/directions/directions.api'

const props = defineProps<{ ctx: DirectionImportContext }>()

const typeOptions: Array<{ label: string; value: ImportType; icon: string; accept: string }> = [
  { label: 'Excel (.xlsx)', value: 'xlsx', icon: 'i-lucide-file-spreadsheet', accept: '.xlsx' },
  { label: 'JSON (.json)', value: 'json', icon: 'i-lucide-file-json', accept: '.json' },
  { label: 'Legacy Excel (.xls)', value: 'xls', icon: 'i-lucide-file-clock', accept: '.xls' }
]

const activeType = computed(() => typeOptions.find((option) => option.value === props.ctx.fileType) ?? typeOptions[0])

// Сохраняем e2e-совместимость: testid инпута зависит от выбранного типа.
const fileTestId = computed(() => (props.ctx.fileType === 'json' ? 'import-json-input' : 'import-excel-input'))

const onFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  props.ctx.setFile(input.files?.[0] ?? null)
}

const submit = () => {
  void props.ctx.runImport()
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <p class="text-sm text-muted">
      Загрузите файл направлений. Импорт создаст направления и образцы в статусе «черновик»,
      после чего мастер поможет дозаполнить недостающие данные и зарегистрировать их.
    </p>

    <div class="flex flex-col gap-2">
      <label class="text-sm font-medium text-toned">Формат файла</label>
      <div class="flex flex-wrap gap-2">
        <UButton
          v-for="option in typeOptions"
          :key="option.value"
          :label="option.label"
          :icon="option.icon"
          :color="ctx.fileType === option.value ? 'primary' : 'neutral'"
          :variant="ctx.fileType === option.value ? 'solid' : 'outline'"
          size="sm"
          :data-testid="`import-type-${option.value}`"
          :data-telemetry="`direction-import-type-${option.value}`"
          @click="ctx.setFileType(option.value)"
        />
      </div>
    </div>

    <div class="flex flex-col gap-2">
      <label class="text-sm font-medium text-toned">Файл</label>
      <input
        :key="fileTestId"
        type="file"
        :accept="activeType.accept"
        :data-testid="fileTestId"
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

    <div class="flex justify-end">
      <UButton
        label="Импортировать"
        icon="i-lucide-upload"
        color="primary"
        :loading="ctx.importing"
        :disabled="!ctx.fileName || ctx.importing"
        data-testid="direction-import-submit"
        data-telemetry="direction-import-submit"
        @click="submit"
      />
    </div>
  </div>
</template>
