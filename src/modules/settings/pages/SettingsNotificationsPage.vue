<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useI18n } from 'vue-i18n'

const state = reactive<Record<string, boolean>>({
  email: true,
  desktop: false,
  product_updates: true,
  weekly_digest: false,
  important_updates: true
})
const { t } = useI18n()

const sections = computed(() => [{
  title: t('settings.notificationsPage.channelsTitle'),
  description: t('settings.notificationsPage.channelsDescription'),
  fields: [{
    name: 'email',
    label: t('settings.notificationsPage.email'),
    description: t('settings.notificationsPage.emailDescription')
  }, {
    name: 'desktop',
    label: t('settings.notificationsPage.desktop'),
    description: t('settings.notificationsPage.desktopDescription')
  }]
}, {
  title: t('settings.notificationsPage.updatesTitle'),
  description: t('settings.notificationsPage.updatesDescription'),
  fields: [{
    name: 'weekly_digest',
    label: t('settings.notificationsPage.weeklyDigest'),
    description: t('settings.notificationsPage.weeklyDigestDescription')
  }, {
    name: 'product_updates',
    label: t('settings.notificationsPage.productUpdates'),
    description: t('settings.notificationsPage.productUpdatesDescription')
  }, {
    name: 'important_updates',
    label: t('settings.notificationsPage.importantUpdates'),
    description: t('settings.notificationsPage.importantUpdatesDescription')
  }]
}])

async function onChange() {
  console.log(state)
}
</script>

<template>
  <div v-for="(section, index) in sections" :key="index">
    <UPageCard
      :title="section.title"
      :description="section.description"
      variant="naked"
      class="mb-4"
    />

    <UPageCard variant="subtle" :ui="{ container: 'divide-y divide-default' }">
      <UFormField
        v-for="field in section.fields"
        :key="field.name"
        :name="field.name"
        :label="field.label"
        :description="field.description"
        class="flex items-center justify-between not-last:pb-4 gap-2"
      >
        <USwitch
          v-model="state[field.name]"
          @update:model-value="onChange"
        />
      </UFormField>
    </UPageCard>
  </div>
</template>
