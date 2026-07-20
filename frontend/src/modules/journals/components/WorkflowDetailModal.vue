<script setup lang="ts">
// Карточка рабочего процесса — тот же каркас, что и у карточек направлений/образцов
// (EntityDetailModalShell): слева список процессов, справа — поля + история версий.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { TabsItem, TimelineItem } from '@nuxt/ui'
import EntityDetailModalShell, { type DetailListItem } from '@/shared/ui/EntityDetailModalShell.vue'
import EntityFieldGrid, { type GridField } from '@/shared/ui/EntityFieldGrid.vue'
import JournalBuilder from '@/modules/journals/components/JournalBuilder.vue'
import JournalRunner from '@/modules/journals/components/JournalRunner.vue'
import { useLocale } from '@/shared/composables/useLocale'
import type { JournalSchema, JournalTemplate } from '@/modules/journals/types/journal'

const props = defineProps<{
  open: boolean
  template: JournalTemplate | null
  listItems: DetailListItem[]
  selectedId: string | null
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'select', id: string | number): void
  (e: 'rename', template: JournalTemplate): void
  (e: 'delete', template: JournalTemplate): void
  (e: 'version-saved', version: number): void
}>()

const activeTab = defineModel<string>('activeTab', { default: 'card' })

const { t } = useI18n()
const { intlLocale } = useLocale()

const tabs = computed<TabsItem[]>(() => [
  { label: t('workflows.detail.tabCard'), icon: 'i-lucide-square-pen', value: 'card' },
  { label: t('workflows.detail.tabBuilder'), icon: 'i-lucide-workflow', value: 'builder' },
  { label: t('workflows.detail.tabRun'), icon: 'i-lucide-play', value: 'run' },
])

const builderSchema = ref<JournalSchema | null>(null)

watch(
  () => props.template,
  (template) => {
    builderSchema.value = template ? template.versions[template.currentVersion - 1]?.schema ?? null : null
  },
  { immediate: true },
)

function onVersionSaved(version: number) {
  emit('version-saved', version)
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(intlLocale.value, { dateStyle: 'long', timeStyle: 'short' })
}

const currentVersion = computed(() =>
  props.template ? props.template.versions[props.template.currentVersion - 1] : null,
)

const entriesCount = computed(() => currentVersion.value?.entries.length ?? 0)

const fields = computed<GridField[]>(() => {
  const template = props.template
  if (!template) {
    return []
  }
  return [
    { key: 'title', label: t('workflows.detail.fields.title'), value: template.title },
    { key: 'versions', label: t('workflows.detail.fields.versions'), value: template.versions.length },
    {
      key: 'currentVersion',
      label: t('workflows.detail.fields.currentVersion'),
      value: t('workflows.version', { version: template.currentVersion }),
    },
    { key: 'entries', label: t('workflows.detail.fields.entries'), value: entriesCount.value },
    { key: 'createdAt', label: t('workflows.detail.fields.createdAt'), value: formatDateTime(template.createdAt) },
    { key: 'updatedAt', label: t('workflows.detail.fields.updatedAt'), value: formatDateTime(template.updatedAt) },
  ]
})

const versionTimeline = computed<TimelineItem[]>(() => {
  const template = props.template
  if (!template) {
    return []
  }
  return template.versions.map((version, index) => ({
    title: t('workflows.detail.versionLabel', { version: index + 1 }),
    description: t('workflows.detail.entriesCount', { count: version.entries.length }),
    date: version.schema.updatedAt ? formatDateTime(version.schema.updatedAt) : undefined,
    icon: index + 1 === template.currentVersion ? 'i-lucide-circle-dot' : 'i-lucide-circle',
  }))
})
</script>

<template>
  <EntityDetailModalShell
    v-model:active-tab="activeTab"
    :open="open"
    :eyebrow="t('workflows.detail.eyebrow')"
    :title="template?.title ?? ''"
    :subtitle="template ? t('workflows.detail.subtitle', { current: template.currentVersion, total: template.versions.length }) : undefined"
    :tabs="tabs"
    size="lg"
    :body-class="activeTab === 'builder' ? 'overflow-hidden p-0' : undefined"
    :list-items="listItems"
    :list-label="t('workflows.detail.listLabel')"
    :selected-id="selectedId"
    @update:open="emit('update:open', $event)"
    @select="emit('select', $event)"
  >
    <template #header-actions>
      <UButton
        v-if="template"
        :label="t('workflows.actions.rename')"
        icon="i-lucide-pencil"
        color="neutral"
        variant="outline"
        size="sm"
        @click="emit('rename', template)"
      />
      <UButton
        v-if="template"
        :label="t('workflows.actions.delete')"
        icon="i-lucide-trash-2"
        color="error"
        variant="outline"
        size="sm"
        @click="emit('delete', template)"
      />
    </template>

    <div v-if="template && activeTab === 'card'" class="grid gap-4 lg:grid-cols-[1fr_20rem]">
      <section class="space-y-3">
        <h3 class="text-sm font-semibold text-highlighted">
          {{ t('workflows.detail.fieldsTitle') }}
        </h3>
        <EntityFieldGrid :fields="fields" :editing="false" :form-state="{}" />
      </section>

      <aside class="h-full min-w-0">
        <div class="h-full rounded-lg border border-default p-4">
          <h3 class="mb-3 text-sm font-semibold text-highlighted">
            {{ t('workflows.detail.versionsHistory') }}
          </h3>
          <UTimeline
            v-if="versionTimeline.length"
            :items="versionTimeline"
            :default-value="template.currentVersion - 1"
            orientation="vertical"
            size="lg"
            class="w-full"
          />
        </div>
      </aside>
    </div>

    <div v-else-if="template && activeTab === 'builder'" class="h-full p-4">
      <JournalBuilder
        v-if="builderSchema"
        :key="template.id"
        v-model="builderSchema"
        :template-id="template.id"
        @version-saved="onVersionSaved"
      />
    </div>

    <div v-else-if="template && activeTab === 'run'" class="h-full">
      <JournalRunner
        v-if="currentVersion"
        :key="`${template.id}-${template.currentVersion}`"
        :schema="currentVersion.schema"
        :template-id="template.id"
      />
    </div>
  </EntityDetailModalShell>
</template>
