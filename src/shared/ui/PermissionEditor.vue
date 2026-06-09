<script setup lang="ts">
import { computed } from 'vue'
import {
  actionLabels,
  crudActions,
  crudPermissionResources,
  resourceCommands,
  resourceLabels
} from '@/shared/constants/permissions'
import type { Permission, PermissionOverride, Resource, Action, AccessScope } from '@/shared/types/permissions'

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

const scopeOptions: Array<{ label: string; value: AccessScope }> = [
  { label: 'Только свои', value: 'own' },
  { label: 'Своя лаборатория', value: 'own_lab' },
  { label: 'Все лаборатории', value: 'all_labs' },
  { label: 'Свой филиал', value: 'own_branch' },
  { label: 'Все филиалы', value: 'all_branches' },
  { label: 'Все записи', value: 'all' }
]

type PermissionStateValue = 'deny' | 'allow'
type OverrideStateValue = 'inherit' | 'allow' | 'deny'

const permissionStateOptions: Array<{ label: string; value: PermissionStateValue }> = [
  { label: 'Запрещено', value: 'deny' },
  { label: 'Разрешено', value: 'allow' }
]

const overrideStateOptions: Array<{ label: string; value: OverrideStateValue }> = [
  { label: 'От роли', value: 'inherit' },
  { label: 'Разрешено', value: 'allow' },
  { label: 'Запрещено', value: 'deny' }
]

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

const getPermission = (resource: Resource, action: Action) =>
  (props.permissions || []).find((permission) => permission.resource === resource && permission.action === action)

const isAllowed = (resource: Resource, action: Action) => allowedSet.value.has(`${resource}:${action}`)
const inheritedAllowed = (resource: Resource, action: Action) => roleSet.value.has(`${resource}:${action}`)

const inheritedScope = (resource: Resource, action: Action) =>
  (props.rolePermissions || []).find((permission) => permission.resource === resource && permission.action === action)?.scope || null

const permissionScope = (resource: Resource, action: Action) =>
  getPermission(resource, action)?.scope || 'all'

const setPermission = (resource: Resource, action: Action, allowed: boolean) => {
  if (props.readOnly || props.mode !== 'permissions') {
    return
  }

  const next = (props.permissions || []).filter(
    (permission) => !(permission.resource === resource && permission.action === action)
  )

  if (allowed) {
    next.push({ ...getPermission(resource, action), resource, action, scope: permissionScope(resource, action) })
  }

  emit('update:permissions', next)
}

const permissionState = (resource: Resource, action: Action): PermissionStateValue =>
  isAllowed(resource, action) ? 'allow' : 'deny'

const setPermissionState = (resource: Resource, action: Action, state: PermissionStateValue) => {
  setPermission(resource, action, state === 'allow')
}

const setPermissionScope = (resource: Resource, action: Action, scope: AccessScope) => {
  if (props.readOnly || props.mode !== 'permissions') {
    return
  }

  const next = (props.permissions || []).map((permission) =>
    permission.resource === resource && permission.action === action
      ? { ...permission, scope }
      : permission
  )

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
    nextOverrides.push({
      ...getOverride(resource, action),
      resource,
      action,
      allowed: true,
      scope: getOverride(resource, action)?.scope || inheritedScope(resource, action) || 'all'
    })
  }

  if (nextState === 'deny') {
    nextOverrides.push({ ...getOverride(resource, action), resource, action, allowed: false, scope: null })
  }

  emit('update:overrides', nextOverrides)
}

const setOverrideScope = (resource: Resource, action: Action, scope: AccessScope) => {
  if (props.readOnly || props.mode !== 'overrides') {
    return
  }

  const nextOverrides = (props.overrides || []).map((override) =>
    override.resource === resource && override.action === action
      ? { ...override, scope }
      : override
  )

  emit('update:overrides', nextOverrides)
}

const overrideState = (resource: Resource, action: Action) => {
  const override = getOverride(resource, action)
  if (!override) {
    return 'inherit'
  }
  return override.allowed ? 'allow' : 'deny'
}

const visibleResources = computed(() => crudPermissionResources)

const commandCount = computed(() =>
  resourceCommands.filter((command) =>
    props.mode === 'permissions'
      ? isAllowed(command.resource, command.action)
      : overrideState(command.resource, command.action) !== 'inherit'
  ).length
)

const permissionCount = (resource: Resource) =>
  props.mode === 'permissions'
    ? (props.permissions || []).filter((permission) => permission.resource === resource).length
    : (props.overrides || []).filter((override) => override.resource === resource).length
</script>

<template>
  <div class="space-y-5">
    <section class="space-y-3">
      <div class="flex items-center justify-between gap-3">
        <h4 class="text-sm font-semibold text-highlighted">
          CRUD справочников
        </h4>
        <UBadge
          color="neutral"
          variant="outline"
          :label="`${visibleResources.length} ресурсов`"
        />
      </div>

      <div class="overflow-hidden rounded-lg border border-default">
        <div class="overflow-auto">
          <div class="min-w-[860px]">
            <div class="grid grid-cols-[13rem_repeat(4,minmax(10rem,1fr))] border-b border-default bg-elevated/60 text-xs font-semibold uppercase tracking-wide text-muted">
              <div class="px-3 py-2">
                Ресурс
              </div>
              <div
                v-for="action in crudActions"
                :key="action"
                class="border-s border-default px-3 py-2"
              >
                {{ actionLabels[action] }}
              </div>
            </div>

            <div
              v-for="resource in visibleResources"
              :key="resource"
              class="grid grid-cols-[13rem_repeat(4,minmax(10rem,1fr))] border-b border-default last:border-b-0"
            >
              <div class="flex items-center justify-between gap-2 px-3 py-3">
                <span class="text-sm font-medium text-highlighted">
                  {{ resourceLabels[resource] }}
                </span>
                <UBadge
                  :color="mode === 'permissions' ? 'success' : 'warning'"
                  variant="subtle"
                  :label="String(permissionCount(resource))"
                />
              </div>

              <div
                v-for="action in crudActions"
                :key="`${resource}-${action}`"
                class="border-s border-default px-3 py-2"
              >
                <template v-if="mode === 'permissions'">
                  <div class="space-y-2">
                    <USelect
                      :model-value="permissionState(resource, action)"
                      :items="permissionStateOptions"
                      value-key="value"
                      label-key="label"
                      :disabled="readOnly"
                      size="xs"
                      class="w-full"
                      aria-label="Действие"
                      @update:model-value="setPermissionState(resource, action, $event as PermissionStateValue)"
                    />
                    <USelectMenu
                      v-if="isAllowed(resource, action)"
                      :model-value="permissionScope(resource, action)"
                      :items="scopeOptions"
                      value-key="value"
                      label-key="label"
                      :disabled="readOnly"
                      size="xs"
                      class="w-full"
                      aria-label="Ограничение"
                      @update:model-value="setPermissionScope(resource, action, $event as AccessScope)"
                    />
                  </div>
                </template>

                <template v-else>
                  <p class="mb-2 text-xs text-muted">
                    Роль: {{ inheritedAllowed(resource, action) ? `разрешено · ${inheritedScope(resource, action) || 'all'}` : 'запрещено' }}
                  </p>
                  <div class="space-y-2">
                    <USelect
                      :model-value="overrideState(resource, action)"
                      :items="overrideStateOptions"
                      value-key="value"
                      label-key="label"
                      :disabled="readOnly"
                      size="xs"
                      class="w-full"
                      aria-label="Действие"
                      @update:model-value="setOverride(resource, action, $event as OverrideStateValue)"
                    />
                    <USelectMenu
                      v-if="overrideState(resource, action) === 'allow'"
                      :model-value="getOverride(resource, action)?.scope || 'all'"
                      :items="scopeOptions"
                      value-key="value"
                      label-key="label"
                      :disabled="readOnly"
                      size="xs"
                      class="w-full"
                      aria-label="Ограничение"
                      @update:model-value="setOverrideScope(resource, action, $event as AccessScope)"
                    />
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="space-y-3">
      <div class="flex items-center justify-between gap-3">
        <h4 class="text-sm font-semibold text-highlighted">
          Команды ресурсов
        </h4>
        <UBadge
          color="neutral"
          variant="outline"
          :label="`${commandCount} активных`"
        />
      </div>

      <div class="overflow-hidden rounded-lg border border-default">
        <div class="grid grid-cols-[13rem_1fr_minmax(13rem,auto)] border-b border-default bg-elevated/60 text-xs font-semibold uppercase tracking-wide text-muted">
          <div class="px-3 py-2">
            Ресурс
          </div>
          <div class="border-s border-default px-3 py-2">
            Команда
          </div>
          <div class="border-s border-default px-3 py-2">
            Доступ
          </div>
        </div>

        <div
          v-for="command in resourceCommands"
          :key="`${command.resource}-${command.action}`"
          class="grid grid-cols-[13rem_1fr_minmax(13rem,auto)] border-b border-default last:border-b-0"
        >
          <div class="px-3 py-3 text-sm font-medium text-highlighted">
            {{ resourceLabels[command.resource] }}
          </div>
          <div class="border-s border-default px-3 py-3 text-sm text-muted">
            {{ actionLabels[command.action] }}
          </div>
          <div class="border-s border-default px-3 py-2">
            <template v-if="mode === 'permissions'">
              <div class="space-y-2">
                <USelect
                  :model-value="permissionState(command.resource, command.action)"
                  :items="permissionStateOptions"
                  value-key="value"
                  label-key="label"
                  :disabled="readOnly"
                  size="xs"
                  class="w-full"
                  aria-label="Действие"
                  @update:model-value="setPermissionState(command.resource, command.action, $event as PermissionStateValue)"
                />
                <USelectMenu
                  v-if="isAllowed(command.resource, command.action)"
                  :model-value="permissionScope(command.resource, command.action)"
                  :items="scopeOptions"
                  value-key="value"
                  label-key="label"
                  :disabled="readOnly"
                  size="xs"
                  class="w-full"
                  aria-label="Ограничение"
                  @update:model-value="setPermissionScope(command.resource, command.action, $event as AccessScope)"
                />
              </div>
            </template>

            <template v-else>
              <p class="mb-2 text-xs text-muted">
                Роль: {{ inheritedAllowed(command.resource, command.action) ? `разрешено · ${inheritedScope(command.resource, command.action) || 'all'}` : 'запрещено' }}
              </p>
              <div class="space-y-2">
                <USelect
                  :model-value="overrideState(command.resource, command.action)"
                  :items="overrideStateOptions"
                  value-key="value"
                  label-key="label"
                  :disabled="readOnly"
                  size="xs"
                  class="w-full"
                  aria-label="Действие"
                  @update:model-value="setOverride(command.resource, command.action, $event as OverrideStateValue)"
                />
                <USelectMenu
                  v-if="overrideState(command.resource, command.action) === 'allow'"
                  :model-value="getOverride(command.resource, command.action)?.scope || 'all'"
                  :items="scopeOptions"
                  value-key="value"
                  label-key="label"
                  :disabled="readOnly"
                  size="xs"
                  class="w-full"
                  aria-label="Ограничение"
                  @update:model-value="setOverrideScope(command.resource, command.action, $event as AccessScope)"
                />
              </div>
            </template>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
