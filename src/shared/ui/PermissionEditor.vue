<script setup lang="ts">
import { computed } from 'vue'
import { actions, actionLabels, resources, resourceLabels } from '@/shared/constants/permissions'
import type { Permission, PermissionOverride, Resource, Action } from '@/shared/types/permissions'

const props = defineProps<{
  mode: 'permissions' | 'overrides'
  permissions?: Permission[]
  rolePermissions?: Permission[]
  overrides?: PermissionOverride[]
  readOnly?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:permissions', value: Permission[]): void
  (e: 'update:overrides', value: PermissionOverride[]): void
}>()

const allowedSet = computed(() => {
  const set = new Set<string>()
  ;(props.permissions || []).forEach((permission) => {
    set.add(`${permission.resource}:${permission.action}`)
  })
  return set
})

const roleSet = computed(() => {
  const set = new Set<string>()
  ;(props.rolePermissions || []).forEach((permission) => {
    set.add(`${permission.resource}:${permission.action}`)
  })
  return set
})

const getOverride = (resource: Resource, action: Action) =>
  (props.overrides || []).find((override) => override.resource === resource && override.action === action)

const isAllowed = (resource: Resource, action: Action) => allowedSet.value.has(`${resource}:${action}`)
const inheritedAllowed = (resource: Resource, action: Action) => roleSet.value.has(`${resource}:${action}`)

const setPermission = (resource: Resource, action: Action, allowed: boolean) => {
  if (props.readOnly || props.mode !== 'permissions') {
    return
  }

  const next = (props.permissions || []).filter(
    (permission) => !(permission.resource === resource && permission.action === action)
  )

  if (allowed) {
    next.push({ resource, action })
  }

  emit('update:permissions', next)
}

const setOverride = (resource: Resource, action: Action, nextState: 'inherit' | 'allow' | 'deny') => {
  if (props.readOnly || props.mode !== 'overrides') {
    return
  }

  const nextOverrides = (props.overrides || []).filter(
    (override) => !(override.resource === resource && override.action === action)
  )

  if (nextState === 'allow') {
    nextOverrides.push({ resource, action, allowed: true })
  }

  if (nextState === 'deny') {
    nextOverrides.push({ resource, action, allowed: false })
  }

  emit('update:overrides', nextOverrides)
}

const overrideState = (resource: Resource, action: Action) => {
  const override = getOverride(resource, action)
  if (!override) {
    return 'inherit'
  }
  return override.allowed ? 'allow' : 'deny'
}
</script>

<template>
  <div class="grid gap-4">
    <UCard
      v-for="resource in resources.filter((item) => item !== 'customers' && item !== 'inbox')"
      :key="resource"
      :ui="{ body: 'space-y-4' }"
    >
      <template #header>
        <div class="flex items-center justify-between gap-3">
          <div>
            <h3 class="text-sm font-semibold text-highlighted">
              {{ resourceLabels[resource] }}
            </h3>
            <p class="text-xs text-toned">
              {{ mode === 'permissions' ? 'Права роли' : 'Индивидуальные override-права' }}
            </p>
          </div>
          <UBadge
            :color="mode === 'permissions' ? 'success' : 'warning'"
            variant="subtle"
          >
            {{
              mode === 'permissions'
                ? (permissions || []).filter((permission) => permission.resource === resource).length
                : (overrides || []).filter((override) => override.resource === resource).length
            }}
          </UBadge>
        </div>
      </template>

      <div
        v-for="action in actions"
        :key="`${resource}-${action}`"
        class="grid gap-3 rounded-xl border border-default p-3 lg:grid-cols-[160px_1fr]"
      >
        <div class="space-y-1">
          <div class="text-sm font-medium text-highlighted">
            {{ actionLabels[action] }}
          </div>
          <div v-if="mode === 'overrides'" class="text-xs text-toned">
            Роль: {{ inheritedAllowed(resource, action) ? 'разрешено' : 'запрещено' }}
          </div>
        </div>

        <div class="flex flex-wrap gap-2">
          <template v-if="mode === 'permissions'">
            <UButton
              :color="isAllowed(resource, action) ? 'success' : 'neutral'"
              :variant="isAllowed(resource, action) ? 'solid' : 'outline'"
              :disabled="readOnly"
              label="Разрешить"
              @click="setPermission(resource, action, true)"
            />
            <UButton
              color="neutral"
              :variant="isAllowed(resource, action) ? 'outline' : 'solid'"
              :disabled="readOnly"
              label="Запретить"
              @click="setPermission(resource, action, false)"
            />
          </template>

          <template v-else>
            <UButton
              color="neutral"
              :variant="overrideState(resource, action) === 'inherit' ? 'solid' : 'outline'"
              :disabled="readOnly"
              :label="`Наследовать (${inheritedAllowed(resource, action) ? 'allow' : 'deny'})`"
              @click="setOverride(resource, action, 'inherit')"
            />
            <UButton
              color="success"
              :variant="overrideState(resource, action) === 'allow' ? 'solid' : 'outline'"
              :disabled="readOnly"
              label="Allow"
              @click="setOverride(resource, action, 'allow')"
            />
            <UButton
              color="error"
              :variant="overrideState(resource, action) === 'deny' ? 'solid' : 'outline'"
              :disabled="readOnly"
              label="Deny"
              @click="setOverride(resource, action, 'deny')"
            />
          </template>
        </div>
      </div>
    </UCard>
  </div>
</template>
