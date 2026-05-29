<script setup lang="ts">
import { computed } from 'vue'
import {
  actionLabels,
  crudActions,
  crudPermissionResources,
  resourceCommands,
  resourceLabels
} from '@/shared/constants/permissions'
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
                  <UCheckbox
                    :model-value="isAllowed(resource, action)"
                    :disabled="readOnly"
                    label="Разрешено"
                    @update:model-value="setPermission(resource, action, Boolean($event))"
                  />
                </template>

                <template v-else>
                  <p class="mb-2 text-xs text-muted">
                    Роль: {{ inheritedAllowed(resource, action) ? 'разрешено' : 'запрещено' }}
                  </p>
                  <div class="flex flex-wrap gap-1">
                    <UButton
                      color="neutral"
                      size="xs"
                      :variant="overrideState(resource, action) === 'inherit' ? 'solid' : 'outline'"
                      :disabled="readOnly"
                      label="Роль"
                      @click="setOverride(resource, action, 'inherit')"
                    />
                    <UButton
                      color="success"
                      size="xs"
                      :variant="overrideState(resource, action) === 'allow' ? 'solid' : 'outline'"
                      :disabled="readOnly"
                      label="Да"
                      @click="setOverride(resource, action, 'allow')"
                    />
                    <UButton
                      color="error"
                      size="xs"
                      :variant="overrideState(resource, action) === 'deny' ? 'solid' : 'outline'"
                      :disabled="readOnly"
                      label="Нет"
                      @click="setOverride(resource, action, 'deny')"
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
              <UCheckbox
                :model-value="isAllowed(command.resource, command.action)"
                :disabled="readOnly"
                label="Разрешено"
                @update:model-value="setPermission(command.resource, command.action, Boolean($event))"
              />
            </template>

            <template v-else>
              <p class="mb-2 text-xs text-muted">
                Роль: {{ inheritedAllowed(command.resource, command.action) ? 'разрешено' : 'запрещено' }}
              </p>
              <div class="flex flex-wrap gap-1">
                <UButton
                  color="neutral"
                  size="xs"
                  :variant="overrideState(command.resource, command.action) === 'inherit' ? 'solid' : 'outline'"
                  :disabled="readOnly"
                  label="Роль"
                  @click="setOverride(command.resource, command.action, 'inherit')"
                />
                <UButton
                  color="success"
                  size="xs"
                  :variant="overrideState(command.resource, command.action) === 'allow' ? 'solid' : 'outline'"
                  :disabled="readOnly"
                  label="Да"
                  @click="setOverride(command.resource, command.action, 'allow')"
                />
                <UButton
                  color="error"
                  size="xs"
                  :variant="overrideState(command.resource, command.action) === 'deny' ? 'solid' : 'outline'"
                  :disabled="readOnly"
                  label="Нет"
                  @click="setOverride(command.resource, command.action, 'deny')"
                />
              </div>
            </template>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
