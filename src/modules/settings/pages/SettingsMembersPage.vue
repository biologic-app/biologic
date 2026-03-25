<script setup lang="ts">
import { computed, ref } from 'vue'
import { useFetch } from '@vueuse/core'
import { useI18n } from 'vue-i18n'
import SettingsMembersList from '@/modules/settings/components/SettingsMembersList.vue'
import type { Member } from '@/shared/types'

const { data: members } = useFetch<Member[]>('https://dashboard-template.nuxt.dev/api/members', { initialData: [] }).json<Member[]>()
const { t } = useI18n()

const query = ref('')

const filteredMembers = computed(() => {
  return members.value?.filter((member) => {
    return member.name.search(new RegExp(query.value, 'i')) !== -1 || member.username.search(new RegExp(query.value, 'i')) !== -1
  }) ?? []
})
</script>

<template>
  <div>
    <UPageCard
      :title="t('settings.membersPage.title')"
      :description="t('settings.membersPage.description')"
      variant="naked"
      orientation="horizontal"
      class="mb-4"
    >
      <UButton
        :label="t('settings.membersPage.invite')"
        color="neutral"
        class="w-fit lg:ms-auto"
      />
    </UPageCard>

    <UPageCard variant="subtle" :ui="{ container: 'p-0 sm:p-0 gap-y-0', wrapper: 'items-stretch', header: 'p-4 mb-0 border-b border-default' }">
      <template #header>
        <UInput
          v-model="query"
          icon="i-lucide-search"
          :placeholder="t('settings.membersPage.search')"
          autofocus
          class="w-full"
        />
      </template>

      <SettingsMembersList :members="filteredMembers" />
    </UPageCard>
  </div>
</template>
