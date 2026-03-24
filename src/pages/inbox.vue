<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useBreakpoints, breakpointsTailwind } from '@vueuse/core'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type { Mail } from '../types'
import { useSystemMessages } from '../composables/useSystemMessages'

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
        <UBadge :label="filteredMails.length" variant="subtle" />
      </template>

      <template #right>
        <UTabs
          v-model="selectedTab"
          :items="tabItems"
          :content="false"
          size="xs"
        />
      </template>
    </UDashboardNavbar>

    <InboxList
      :model-value="selectedMail"
      :mails="filteredMails"
      @update:model-value="setSelectedMail"
    />
  </UDashboardPanel>

  <InboxMail v-if="selectedMail" :mail="selectedMail" @close="setSelectedMail(null)" />
  <div v-else class="hidden lg:flex flex-1 flex-col items-center justify-center gap-3">
    <UIcon name="i-lucide-inbox" class="size-32 text-dimmed" />
    <p class="text-sm text-muted">
      {{ filteredMails.length ? t('inbox.open') : t('inbox.empty') }}
    </p>
  </div>

  <USlideover v-if="isMobile" v-model:open="isMailPanelOpen">
    <template #content>
      <InboxMail v-if="selectedMail" :mail="selectedMail" @close="setSelectedMail(null)" />
    </template>
  </USlideover>
</template>
