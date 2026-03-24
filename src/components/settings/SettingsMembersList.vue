<script setup lang="ts">
import { computed } from 'vue'
import type { Member } from '../../types'
import type { DropdownMenuItem } from '@nuxt/ui'
import { useI18n } from 'vue-i18n'

defineProps<{
  members: Member[]
}>()

const { t } = useI18n()

const items = computed<DropdownMenuItem[]>(() => [{
  label: t('settings.memberList.edit'),
  onSelect: () => console.log('Edit member')
}, {
  label: t('settings.memberList.remove'),
  color: 'error' as const,
  onSelect: () => console.log('Remove member')
}])

const roleItems = computed(() => [
  { label: t('settings.memberList.member'), value: 'member' },
  { label: t('settings.memberList.owner'), value: 'owner' }
])
</script>

<template>
  <ul role="list" class="divide-y divide-default">
    <li
      v-for="(member, index) in members"
      :key="index"
      class="flex items-center justify-between gap-3 py-3 px-4 sm:px-6"
    >
      <div class="flex items-center gap-3 min-w-0">
        <UAvatar
          v-bind="member.avatar"
          size="md"
        />

        <div class="text-sm min-w-0">
          <p class="text-highlighted font-medium truncate">
            {{ member.name }}
          </p>
          <p class="text-muted truncate">
            {{ member.username }}
          </p>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <USelect
          :model-value="member.role"
          :items="roleItems"
          color="neutral"
          :ui="{ value: 'capitalize', item: 'capitalize' }"
        />

        <UDropdownMenu :items="items" :content="{ align: 'end' }">
          <UButton
            icon="i-lucide-ellipsis-vertical"
            color="neutral"
            variant="ghost"
          />
        </UDropdownMenu>
      </div>
    </li>
  </ul>
</template>
