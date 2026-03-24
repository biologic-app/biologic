<script setup lang="ts">
import { computed, ref } from 'vue'
import { useStorage } from '@vueuse/core'
import type { NavigationMenuItem } from '@nuxt/ui'
import { useI18n } from 'vue-i18n'

const toast = useToast()
const { t } = useI18n()

const open = ref(false)

const links = computed<NavigationMenuItem[][]>(() => [[{
  label: t('nav.home'),
  icon: 'i-lucide-layout-dashboard',
  to: '/',
  onSelect: () => { open.value = false }
}, {
  label: t('nav.inbox'),
  icon: 'i-lucide-inbox',
  to: '/inbox',
  badge: '4',
  onSelect: () => { open.value = false }
}, {
  label: t('nav.customers'),
  icon: 'i-lucide-users',
  to: '/customers',
  onSelect: () => { open.value = false }
}, {
  label: t('nav.requests'),
  icon: 'i-lucide-clipboard-list',
  to: '/requests',
  type: 'trigger',
  defaultOpen: false,
  children: [{
    label: t('nav.requestsAll'),
    to: '/requests',
    exact: true,
    onSelect: () => { open.value = false }
  }, {
    label: t('nav.requestsNew'),
    to: '/requests/new',
    onSelect: () => { open.value = false }
  }, {
    label: t('nav.requestsArchive'),
    to: '/requests/archive',
    onSelect: () => { open.value = false }
  }]
}, {
  label: t('nav.samples'),
  icon: 'i-lucide-flask-conical',
  to: '/samples',
  type: 'trigger',
  defaultOpen: false,
  children: [{
    label: t('nav.samplesJournal'),
    to: '/samples',
    exact: true,
    onSelect: () => { open.value = false }
  }, {
    label: t('nav.samplesMovement'),
    to: '/samples/movement',
    onSelect: () => { open.value = false }
  }]
}, {
  label: t('nav.results'),
  icon: 'i-lucide-chart-bar',
  to: '/results',
  type: 'trigger',
  defaultOpen: false,
  children: [{
    label: t('nav.resultsInput'),
    to: '/results',
    exact: true,
    onSelect: () => { open.value = false }
  }, {
    label: t('nav.resultsVerification'),
    to: '/results/verification',
    onSelect: () => { open.value = false }
  }, {
    label: t('nav.resultsReports'),
    to: '/results/reports',
    onSelect: () => { open.value = false }
  }]
}, {
  label: t('nav.dictionaries'),
  icon: 'i-lucide-book-copy',
  to: '/dictionaries',
  type: 'trigger',
  defaultOpen: false,
  children: [{
    label: t('nav.dictionariesAnalyses'),
    to: '/dictionaries/analyses',
    onSelect: () => { open.value = false }
  }, {
    label: t('nav.dictionariesObjects'),
    to: '/dictionaries/objects',
    onSelect: () => { open.value = false }
  }, {
    label: t('nav.dictionariesReferences'),
    to: '/dictionaries/references',
    onSelect: () => { open.value = false }
  }, {
    label: t('nav.dictionariesOrganizations'),
    to: '/dictionaries/organizations',
    onSelect: () => { open.value = false }
  }]
}, {
  label: t('nav.settings'),
  icon: 'i-lucide-settings',
  to: '/settings',
  type: 'trigger',
  defaultOpen: false,
  children: [{
    label: t('nav.settingsUsers'),
    to: '/settings/users',
    onSelect: () => { open.value = false }
  }, {
    label: t('nav.settingsBranches'),
    to: '/settings/branches',
    onSelect: () => { open.value = false }
  }, {
    label: t('nav.settingsSystem'),
    to: '/settings/system',
    onSelect: () => { open.value = false }
  }]
}], [{
  label: t('nav.documentation'),
  icon: 'i-lucide-book-open',
  to: 'https://github.com/nuxt-ui-templates/dashboard-vue',
  target: '_blank'
}]])

const groups = computed(() => [{
  id: 'links',
  label: t('layout.goTo'),
  items: links.value.flat() as any[]
}, {
  id: 'quick-actions',
  label: t('layout.quickActions'),
  items: [{
    label: t('layout.createOrder'),
    icon: 'i-lucide-plus',
    to: '/orders/new'
  }, {
    label: t('layout.importData'),
    icon: 'i-lucide-plus',
    to: '/import'
  }, {
    label: t('layout.exportData'),
    icon: 'i-lucide-plus',
    to: '/export'
  }]
}])

const cookie = useStorage('cookie-consent', 'pending')
if (cookie.value !== 'accepted') {
  toast.add({
    title: t('layout.cookieTitle'),
    duration: 0,
    close: false,
    actions: [{
      label: t('layout.accept'),
      color: 'neutral',
      variant: 'outline',
      onClick: () => {
        cookie.value = 'accepted'
      }
    }, {
      label: t('layout.decline'),
      color: 'neutral',
      variant: 'ghost'
    }]
  })
}
</script>

<template>
  <UDashboardGroup unit="rem" storage="local">
    <UDashboardSidebar
      id="default"
      
      v-model:open="open"
      collapsible
      :ui="{ header: 'lg:border-b lg:border-default' }"
    >
      <template #header="{ collapsed }">
        <UserMenu :collapsed="collapsed" />
      </template>

      <template #default="{ collapsed }">
        <UDashboardSearchButton :collapsed="collapsed" class="bg-transparent ring-default" />

        <UNavigationMenu
          :collapsed="collapsed"
          :items="links[0]"
          orientation="vertical"
          tooltip
          popover
        />

        <UNavigationMenu
          :collapsed="collapsed"
          :items="links[1]"
          orientation="vertical"
          tooltip
          class="mt-auto"
        />
      </template>
    </UDashboardSidebar>

    <UDashboardSearch :groups="groups" />

    <RouterView />

    <NotificationsSlideover />
  </UDashboardGroup>
</template>
