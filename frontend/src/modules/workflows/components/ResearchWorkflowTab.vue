<script setup lang="ts">
// Вкладка «Рабочий процесс» карточки исследования (Исследования V2):
// вместо таба тестов — проведение исследования по выбранному журналу
// (пошаговый воркфлоу), записи привязаны к конкретному исследованию.
import { computed, onMounted, ref, watch } from 'vue'
import JournalRunner from '@/modules/workflows/components/JournalRunner.vue'
import { getTemplate, initDemoData, listTemplates } from '@/modules/workflows/api/workflows.api'
import { microbiologyStudy } from '@/modules/workflows/data/microbiology-study'
import { patientIntake } from '@/modules/workflows/data/patient-intake'
import type { JournalSchema, JournalTemplate } from '@/modules/workflows/types/journal'
import type { CrudRow } from '@/shared/types/crud'

const props = defineProps<{
  research: CrudRow | null
}>()

const templates = ref<JournalTemplate[]>([])
const selectedId = ref<string | undefined>(undefined)
const currentSchema = ref<JournalSchema | null>(null)

onMounted(async () => {
  await initDemoData([patientIntake, microbiologyStudy])
  templates.value = await listTemplates()
  if (!selectedId.value) {
    selectedId.value = templates.value[0]?.id
  }
})

// Схема выбранного процесса подгружается из API при смене выбора.
watch(selectedId, async (id) => {
  if (!id) {
    currentSchema.value = null
    return
  }
  const template = await getTemplate(id)
  currentSchema.value = template ? template.versions[template.currentVersion - 1]?.schema ?? null : null
})

const processItems = computed(() =>
  templates.value.map((template) => ({ label: template.title, value: template.id })),
)

// Область записей — id исследования (записи журнала привязаны к нему).
const scope = computed(() => (props.research?.id != null ? String(props.research.id) : undefined))

// Предзаголовок новой записи — по образцу/цели исследования.
const defaultTitle = computed(() => {
  const row = props.research as Record<string, unknown> | null
  const sample = (row?.sample as { name?: string } | undefined)?.name
  const goal = (row?.research_goal as { name?: string } | undefined)?.name
  return [sample, goal].filter(Boolean).join(' · ') || 'Исследование'
})
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-4">
    <div class="flex items-center gap-2">
      <span class="text-sm text-muted">Рабочий процесс:</span>
      <USelectMenu
        v-model="selectedId"
        :items="processItems"
        value-key="value"
        placeholder="Выберите процесс…"
        icon="i-lucide-workflow"
        class="w-72"
      />
    </div>

    <JournalRunner
      v-if="currentSchema && selectedId && scope"
      :key="`${scope}-${selectedId}-${currentSchema.version}`"
      :schema="currentSchema"
      :template-id="selectedId"
      :scope="scope"
      :default-title="defaultTitle"
    />
    <div v-else class="py-12 text-center text-muted">
      <UIcon name="i-lucide-workflow" class="mx-auto mb-3 size-10 opacity-50" />
      <p class="font-medium">
        Нет доступных рабочих процессов
      </p>
      <p class="text-sm">
        Создайте процесс на странице «Рабочие процессы», затем вернитесь к исследованию.
      </p>
    </div>
  </div>
</template>
