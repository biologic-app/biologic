<script setup lang="ts">
// Страница «Исследования V2» — проведение исследования образца по выбранному
// рабочему процессу (журналу): пошаговое заполнение с сохранением прогресса,
// комментариями к шагам и историей изменений.
import { computed, onMounted, ref } from 'vue'
import JournalRunner from '@/modules/journals/components/JournalRunner.vue'
import { useJournalUser } from '@/modules/journals/composables/useJournalUser'
import { getTemplate, getTemplates, initDemoData } from '@/modules/journals/composables/useJournalStorage'
import { microbiologyStudy } from '@/modules/journals/data/microbiology-study'
import { patientIntake } from '@/modules/journals/data/patient-intake'
import type { JournalSchema, JournalTemplate } from '@/modules/journals/types/journal'

const toast = useToast()
const { current: currentUser, override, setUser } = useJournalUser()

const templates = ref<JournalTemplate[]>([])
const selectedId = ref<string | undefined>(undefined)

onMounted(() => {
  initDemoData([patientIntake, microbiologyStudy])
  templates.value = getTemplates()
  selectedId.value = templates.value[0]?.id
})

const processItems = computed(() =>
  templates.value.map((template) => ({ label: template.title, value: template.id })),
)

const selectedTemplate = computed(() =>
  selectedId.value ? getTemplate(selectedId.value) ?? null : null,
)

const currentSchema = computed<JournalSchema | null>(() => {
  const template = selectedTemplate.value
  if (!template) {
    return null
  }
  return template.versions[template.currentVersion - 1]?.schema ?? null
})

// Ручной override имени исполнителя (по умолчанию — ФИО из аутентификации).
const userName = computed({
  get: () => override.value,
  set: (value: string) => setUser(value),
})

function onEntryCompleted() {
  toast.add({ title: 'Исследование завершено', color: 'success', icon: 'i-lucide-flag' })
}
</script>

<template>
  <UDashboardPanel id="research-v2" :ui="{ body: 'min-h-0 overflow-auto' }">
    <template #header>
      <UDashboardNavbar title="Исследования">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #title>
          <div class="flex items-center gap-2">
            <span>Исследования</span>
            <UBadge color="primary" variant="subtle" size="sm">
              V2
            </UBadge>
          </div>
        </template>
        <template #right>
          <UInput
            v-model="userName"
            icon="i-lucide-user"
            size="sm"
            :placeholder="currentUser || 'Исполнитель'"
            class="w-48"
          />
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
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
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <div class="mx-auto w-full max-w-5xl p-4">
        <JournalRunner
          v-if="currentSchema && selectedId"
          :key="`${selectedId}-${currentSchema.version}`"
          :schema="currentSchema"
          :template-id="selectedId"
          @entry-completed="onEntryCompleted"
        />
        <div v-else class="py-16 text-center text-muted">
          <UIcon name="i-lucide-flask-conical" class="mx-auto mb-3 size-12 opacity-50" />
          <p class="font-medium">
            Нет доступных рабочих процессов
          </p>
          <p class="text-sm">
            Создайте процесс на странице «Рабочие процессы», затем вернитесь сюда для проведения исследования.
          </p>
        </div>
      </div>
    </template>
  </UDashboardPanel>
</template>
