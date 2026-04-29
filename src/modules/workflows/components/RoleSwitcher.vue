<script setup lang="ts">
import { useWorkflowRole } from "@/modules/workflows/useWorkflowRole";

defineProps<{
  collapsed?: boolean;
}>();

const { roleItems, selectedRole, selectedRoleKey } = useWorkflowRole();
</script>

<template>
  <div class="px-2 py-2">
    <UTooltip
      v-if="collapsed"
      :text="selectedRole.title"
      :content="{ side: 'right' }"
    >
      <UButton
        color="neutral"
        variant="subtle"
        square
        block
        :label="selectedRole.shortName"
        class="font-semibold"
      />
    </UTooltip>

    <div v-else class="rounded-lg border border-default bg-elevated/40 p-2">
      <div class="mb-2 flex items-center gap-2 px-1">
        <UIcon name="i-lucide-user-cog" class="size-4 shrink-0 text-muted" />
        <div class="min-w-0">
          <p class="truncate text-xs font-medium uppercase text-muted">
            Роль приложения
          </p>
          <p class="truncate text-sm font-semibold text-highlighted">
            {{ selectedRole.title }}
          </p>
        </div>
      </div>

      <USelect
        v-model="selectedRoleKey"
        :items="roleItems"
        color="neutral"
        variant="outline"
        class="w-full"
      />
    </div>
  </div>
</template>
