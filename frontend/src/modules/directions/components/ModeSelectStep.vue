<script setup lang="ts">
const props = defineProps<{
  canImport?: boolean
  canCreate?: boolean
  loading?: boolean
}>()
const emit = defineEmits<{ (e: 'choose', mode: 'import' | 'manual'): void }>()

const choose = (mode: 'import' | 'manual', enabled: boolean | undefined) => {
  if (!enabled || props.loading) {
    return
  }
  emit('choose', mode)
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <p class="text-sm text-muted">
      Выберите способ создания направлений: загрузить файл Excel с несколькими
      направлениями или создать одно направление вручную и наполнить его образцами.
    </p>

    <div class="grid gap-4 sm:grid-cols-2">
      <button
        type="button"
        class="flex flex-col items-center gap-3 rounded-lg border-2 border-default p-6 text-center transition-colors"
        :class="canImport && !loading
          ? 'cursor-pointer hover:border-primary/60 hover:bg-elevated/50'
          : 'cursor-not-allowed opacity-60'"
        data-testid="direction-mode-import"
        data-telemetry="direction-mode-import"
        :disabled="!canImport || loading"
        @click="choose('import', canImport)"
      >
        <div class="flex size-14 items-center justify-center rounded-full bg-primary/10 text-primary">
          <UIcon name="i-lucide-file-up" class="size-7" />
        </div>
        <span class="text-base font-semibold text-highlighted">Импорт из файла</span>
        <span class="text-sm text-muted">
          Загрузите Excel (.xlsx / .xls) — направления и образцы создаются массово.
        </span>
        <span v-if="!canImport" class="text-xs text-warning">Нет прав на импорт</span>
      </button>

      <button
        type="button"
        class="flex flex-col items-center gap-3 rounded-lg border-2 border-default p-6 text-center transition-colors"
        :class="canCreate && !loading
          ? 'cursor-pointer hover:border-primary/60 hover:bg-elevated/50'
          : 'cursor-not-allowed opacity-60'"
        data-testid="direction-mode-manual"
        data-telemetry="direction-mode-manual"
        :disabled="!canCreate || loading"
        @click="choose('manual', canCreate)"
      >
        <div class="flex size-14 items-center justify-center rounded-full bg-primary/10 text-primary">
          <UIcon
            :name="loading ? 'i-lucide-loader-circle' : 'i-lucide-file-plus-2'"
            class="size-7"
            :class="loading ? 'animate-spin' : ''"
          />
        </div>
        <span class="text-base font-semibold text-highlighted">Создать вручную</span>
        <span class="text-sm text-muted">
          Одно направление с авто-номером — добавляйте и заполняйте образцы вручную.
        </span>
        <span v-if="!canCreate" class="text-xs text-warning">Нет прав на создание</span>
      </button>
    </div>
  </div>
</template>
