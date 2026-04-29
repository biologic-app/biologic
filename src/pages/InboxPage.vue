<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useBreakpoints, breakpointsTailwind } from '@vueuse/core'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import InboxList from '@/modules/inbox/components/InboxList.vue'
import InboxMail from '@/modules/inbox/components/InboxMail.vue'
import { useSystemMessages } from '@/modules/inbox/composables/useSystemMessages'
import { useWorkflowMock, type WorkflowAlert } from '@/modules/workflows/useWorkflowMock'
import { useWorkflowRole } from '@/modules/workflows/useWorkflowRole'
import type { Mail } from '@/shared/types'

const { t } = useI18n()
const tabItems = computed(() => [{
  label: t('inbox.all'),
  value: 'all'
}, {
  label: t('inbox.unread'),
  value: 'unread'
}])
const selectedTab = ref('all')
const route = useRoute()
const router = useRouter()
const { mails, unreadMails } = useSystemMessages()
const { hideAlert, visibleAlerts } = useWorkflowMock()
const { selectedRoleKey } = useWorkflowRole()
const selectedAlert = ref<WorkflowAlert | null>(null)
const alertMode = computed(() => ['sanitary_inspector', 'branch_chief'].includes(selectedRoleKey.value))

const filteredMails = computed(() => {
  if (selectedTab.value === 'unread') {
    return unreadMails.value
  }

  return mails.value
})

const selectedMail = ref<Mail | null>()

const isMailPanelOpen = computed({
  get() {
    return !!selectedMail.value
  },
  set(value: boolean) {
    if (!value) {
      selectedMail.value = null
    }
  }
})

function setSelectedMail(mail: Mail | null | undefined) {
  selectedMail.value = mail ?? null

  if (mail) {
    if (route.query.id !== String(mail.id)) {
      router.replace({ query: { ...route.query, id: String(mail.id) } })
    }
    return
  }

  if (route.query.id) {
    const nextQuery = { ...route.query }
    delete nextQuery.id
    router.replace({ query: nextQuery })
  }
}

watch(mails, () => {
  if (!mails.value.find(mail => mail.id === selectedMail.value?.id)) {
    selectedMail.value = null
  }
})

watch([mails, () => route.query.id], () => {
  const rawId = route.query.id
  const id = typeof rawId === 'string' ? Number(rawId) : Number.NaN

  if (!Number.isFinite(id)) {
    return
  }

  const mail = mails.value.find(item => item.id === id) ?? null
  if (!mail) {
    setSelectedMail(null)
    return
  }

  if (selectedMail.value?.id !== mail.id) {
    setSelectedMail(mail)
  }
}, { immediate: true })

const breakpoints = useBreakpoints(breakpointsTailwind)
const isMobile = breakpoints.smaller('lg')

function openAlert(alert: WorkflowAlert) {
  selectedAlert.value = alert
  router.replace({ query: { ...route.query, entity_type: alert.entityType, entity_id: String(alert.entityId) } })
}

function hideSelectedAlert(alert: WorkflowAlert) {
  hideAlert(alert)
  selectedAlert.value = null
}
</script>

<template>
  <UDashboardPanel
    id="inbox-1"
    :default-size="25"
    :min-size="20"
    :max-size="30"
    resizable
  >
    <UDashboardNavbar :title="t('inbox.title')">
      <template #leading>
        <UDashboardSidebarCollapse />
      </template>
      <template #trailing>
        <UBadge :label="alertMode ? visibleAlerts.length : filteredMails.length" variant="subtle" />
      </template>

      <template #right>
        <div data-tour="inbox-tabs">
          <UTabs
            v-model="selectedTab"
            :items="tabItems"
            :content="false"
            size="xs"
          />
        </div>
      </template>
    </UDashboardNavbar>

    <div v-if="alertMode" class="flex-1 overflow-y-auto divide-y divide-default">
      <button
        v-for="alert in visibleAlerts"
        :key="alert.id"
        type="button"
        class="block w-full border-l-2 p-4 text-left text-sm transition-colors sm:px-6"
        :class="selectedAlert?.id === alert.id ? 'border-primary bg-primary/10' : 'border-transparent hover:border-primary hover:bg-primary/5'"
        @click="openAlert(alert)"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="truncate font-semibold text-highlighted">
              {{ alert.title }}
            </p>
            <p class="mt-1 text-xs text-muted">
              {{ alert.entityType }} #{{ alert.entityId }}
            </p>
          </div>
          <UBadge :label="alert.severity" :color="alert.severity === 'critical' ? 'error' : alert.severity === 'warning' ? 'warning' : 'info'" variant="subtle" />
        </div>
      </button>
    </div>

    <InboxList
      v-else
      :model-value="selectedMail"
      :mails="filteredMails"
      @update:model-value="setSelectedMail"
    />
  </UDashboardPanel>

  <UDashboardPanel v-if="alertMode && selectedAlert" id="alerts-detail" class="hidden lg:flex">
    <UDashboardNavbar :title="selectedAlert.title" :toggle="false" />
    <template #body>
      <div class="mx-auto flex w-full max-w-3xl flex-col gap-4">
        <UAlert
          icon="i-lucide-siren"
          :color="selectedAlert.severity === 'critical' ? 'error' : 'warning'"
          variant="subtle"
          :title="selectedAlert.title"
          :description="`Событие связано с ${selectedAlert.entityType} #${selectedAlert.entityId}. Переход выполняется через entity_type + entity_id.`"
        />
        <div class="flex gap-2">
          <UButton :to="selectedAlert.entityType === 'protocol' ? '/directions?protocol=ready' : `/directions?id=${selectedAlert.entityId}`" icon="i-lucide-arrow-up-right" label="Открыть сущность" />
          <UButton
            icon="i-lucide-eye-off"
            label="Скрыть"
            color="neutral"
            variant="outline"
            @click="hideSelectedAlert(selectedAlert)"
          />
        </div>
      </div>
    </template>
  </UDashboardPanel>
  <InboxMail v-else-if="selectedMail" :mail="selectedMail" @close="setSelectedMail(null)" />
  <div v-else class="hidden lg:flex flex-1 flex-col items-center justify-center gap-3">
    <UIcon name="i-lucide-inbox" class="size-32 text-dimmed" />
    <p class="text-sm text-muted">
      {{ alertMode ? 'Выберите уведомление.' : filteredMails.length ? t('inbox.open') : t('inbox.empty') }}
    </p>
  </div>

  <USlideover v-if="isMobile" v-model:open="isMailPanelOpen">
    <template #content>
      <InboxMail v-if="selectedMail" :mail="selectedMail" @close="setSelectedMail(null)" />
    </template>
  </USlideover>
</template>
