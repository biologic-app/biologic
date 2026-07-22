<script setup lang="ts">
import { computed } from 'vue'
import type { TableColumn } from '@nuxt/ui'
import {
  actionLabels,
  crudActions,
  crudPermissionResources,
  resourceCommands,
  resourceLabels,
  type ResourceCommand
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

// Матрица «ресурс × CRUD-действие»: строки — ресурсы, колонки — действия;
// содержимое ячейки рендерится именованным слотом `#${action}-cell`.
type ResourceRow = { resource: Resource }

const resourceRows = computed<ResourceRow[]>(() =>
  visibleResources.value.map((resource) => ({ resource }))
)

const resourceGridColumns = computed<TableColumn<ResourceRow>[]>(() => [
  { id: 'resource', header: 'Ресурс' },
  ...crudActions.map((action) => ({ id: action, header: actionLabels[action] }))
])

const permissionMatrixUi = {
  root: 'overflow-auto rounded-lg border border-default',
  base: 'border-separate border-spacing-0',
  thead: '[&>tr]:bg-elevated/60 [&>tr]:after:content-none',
  tr: '[&:last-child>td]:border-b-0',
  th: 'border-b border-e border-default px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-muted last:border-e-0',
  td: 'whitespace-normal border-b border-e border-default px-3 py-2 align-top last:border-e-0'
} as const

const commandColumns: TableColumn<ResourceCommand>[] = [
  { accessorKey: 'resource', header: 'Ресурс' },
  { accessorKey: 'action', header: 'Команда' },
  { id: 'access', header: 'Доступ' }
]
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

      <UTable :data="resourceRows" :columns="resourceGridColumns" :ui="permissionMatrixUi">
        <template #resource-cell="{ row }">
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm font-medium text-highlighted">
              {{ resourceLabels[row.original.resource] }}
            </span>
            <UBadge
              :color="mode === 'permissions' ? 'success' : 'warning'"
              variant="subtle"
              :label="String(permissionCount(row.original.resource))"
            />
          </div>
        </template>

        <template
          v-for="action in crudActions"
          :key="action"
          #[`${action}-cell`]="{ row }"
        >
          <template v-if="mode === 'permissions'">
            <div class="space-y-2">
              <USelect
                :model-value="permissionState(row.original.resource, action)"
                :items="permissionStateOptions"
                value-key="value"
                label-key="label"
                :disabled="readOnly"
                size="xs"
                class="w-full"
                aria-label="Действие"
                @update:model-value="setPermissionState(row.original.resource, action, $event as PermissionStateValue)"
              />
              <USelectMenu
                v-if="isAllowed(row.original.resource, action)"
                :model-value="permissionScope(row.original.resource, action)"
                :items="scopeOptions"
                value-key="value"
                label-key="label"
                :disabled="readOnly"
                size="xs"
                class="w-full"
                aria-label="Ограничение"
                @update:model-value="setPermissionScope(row.original.resource, action, $event as AccessScope)"
              />
            </div>
          </template>

          <template v-else>
            <p class="mb-2 text-xs text-muted">
              Роль: {{ inheritedAllowed(row.original.resource, action) ? `разрешено · ${inheritedScope(row.original.resource, action) || 'all'}` : 'запрещено' }}
            </p>
            <div class="space-y-2">
              <USelect
                :model-value="overrideState(row.original.resource, action)"
                :items="overrideStateOptions"
                value-key="value"
                label-key="label"
                :disabled="readOnly"
                size="xs"
                class="w-full"
                aria-label="Действие"
                @update:model-value="setOverride(row.original.resource, action, $event as OverrideStateValue)"
              />
              <USelectMenu
                v-if="overrideState(row.original.resource, action) === 'allow'"
                :model-value="getOverride(row.original.resource, action)?.scope || 'all'"
                :items="scopeOptions"
                value-key="value"
                label-key="label"
                :disabled="readOnly"
                size="xs"
                class="w-full"
                aria-label="Ограничение"
                @update:model-value="setOverrideScope(row.original.resource, action, $event as AccessScope)"
              />
            </div>
          </template>
        </template>
      </UTable>
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

      <UTable :data="resourceCommands" :columns="commandColumns" :ui="permissionMatrixUi">
        <template #resource-cell="{ row }">
          <span class="text-sm font-medium text-highlighted">
            {{ resourceLabels[row.original.resource] }}
          </span>
        </template>

        <template #action-cell="{ row }">
          <span class="text-sm text-muted">
            {{ actionLabels[row.original.action] }}
          </span>
        </template>

        <template #access-cell="{ row }">
          <template v-if="mode === 'permissions'">
            <div class="space-y-2">
              <USelect
                :model-value="permissionState(row.original.resource, row.original.action)"
                :items="permissionStateOptions"
                value-key="value"
                label-key="label"
                :disabled="readOnly"
                size="xs"
                class="w-full"
                aria-label="Действие"
                @update:model-value="setPermissionState(row.original.resource, row.original.action, $event as PermissionStateValue)"
              />
              <USelectMenu
                v-if="isAllowed(row.original.resource, row.original.action)"
                :model-value="permissionScope(row.original.resource, row.original.action)"
                :items="scopeOptions"
                value-key="value"
                label-key="label"
                :disabled="readOnly"
                size="xs"
                class="w-full"
                aria-label="Ограничение"
                @update:model-value="setPermissionScope(row.original.resource, row.original.action, $event as AccessScope)"
              />
            </div>
          </template>

          <template v-else>
            <p class="mb-2 text-xs text-muted">
              Роль: {{ inheritedAllowed(row.original.resource, row.original.action) ? `разрешено · ${inheritedScope(row.original.resource, row.original.action) || 'all'}` : 'запрещено' }}
            </p>
            <div class="space-y-2">
              <USelect
                :model-value="overrideState(row.original.resource, row.original.action)"
                :items="overrideStateOptions"
                value-key="value"
                label-key="label"
                :disabled="readOnly"
                size="xs"
                class="w-full"
                aria-label="Действие"
                @update:model-value="setOverride(row.original.resource, row.original.action, $event as OverrideStateValue)"
              />
              <USelectMenu
                v-if="overrideState(row.original.resource, row.original.action) === 'allow'"
                :model-value="getOverride(row.original.resource, row.original.action)?.scope || 'all'"
                :items="scopeOptions"
                value-key="value"
                label-key="label"
                :disabled="readOnly"
                size="xs"
                class="w-full"
                aria-label="Ограничение"
                @update:model-value="setOverrideScope(row.original.resource, row.original.action, $event as AccessScope)"
              />
            </div>
          </template>
        </template>
      </UTable>
    </section>
  </div>
</template>
