<script setup lang="ts">
import { ref } from 'vue'
import NotificationsSlideover from '@/shared/components/NotificationsSlideover.vue'
import UserMenu from '@/shared/components/UserMenu.vue'
import { navigationSections } from '@/shared/config/navigation'
import { usePermission } from '@/shared/composables/usePermission'

const open = ref(false)
const { can } = usePermission()

const canOpen = (resource?: string) => {
  if (!resource) {
    return true
  }

  return can(resource as any, 'view')
}
</script>

<template>
  <UDashboardGroup unit="rem" storage="local">
    <UDashboardSidebar id="default" v-model:open="open" collapsible>
      <template #header="{ collapsed }">
        <UserMenu :collapsed="collapsed" />
      </template>

      <template #default="{ collapsed }">
        <div class="flex h-full flex-col gap-6">
          <section
            v-for="section in navigationSections"
            :key="section.title"
            class="space-y-2"
          >
            <p v-if="!collapsed" class="px-3 text-xs font-semibold uppercase tracking-[0.16em] text-muted">
              {{ section.title }}
            </p>

            <div class="grid gap-1">
              <template v-for="item in section.items" :key="item.to">
                <UTooltip :text="canOpen(item.resource) ? item.label : 'Недостаточно прав'">
                  <UButton
                    :to="canOpen(item.resource) ? item.to : undefined"
                    :icon="canOpen(item.resource) ? item.icon : 'i-lucide-lock'"
                    :label="collapsed ? undefined : item.label"
                    color="neutral"
                    variant="ghost"
                    block
                    :square="collapsed"
                    :disabled="!canOpen(item.resource)"
                    class="justify-start"
                  />
                </UTooltip>
              </template>
            </div>
          </section>
        </div>
      </template>
    </UDashboardSidebar>

    <RouterView />

    <NotificationsSlideover />
  </UDashboardGroup>
</template>
