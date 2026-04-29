<script setup lang="ts">
import { computed, ref } from 'vue'
import { useWorkflowRole } from '@/modules/workflows/useWorkflowRole'
import { useWorkflowMock } from '@/modules/workflows/useWorkflowMock'

const toast = useToast()
const { selectedRoleKey } = useWorkflowRole()
const { users } = useWorkflowMock()

const query = ref('')
const createOpen = ref(false)
const scopeOpen = ref(false)
const selectedUserId = ref<number | null>(null)

const isUserAdmin = computed(() => selectedRoleKey.value === 'user_admin')
const selectedUser = computed(() => users.value.find(user => user.id === selectedUserId.value) ?? null)
const filteredUsers = computed(() => {
  const normalizedQuery = query.value.trim().toLocaleLowerCase()

  return users.value.filter(user => !normalizedQuery
    || user.name.toLocaleLowerCase().includes(normalizedQuery)
    || user.login.toLocaleLowerCase().includes(normalizedQuery)
    || user.role.toLocaleLowerCase().includes(normalizedQuery)
    || user.scope.toLocaleLowerCase().includes(normalizedQuery))
})

const missingScopeCount = computed(() => users.value.filter(user => user.status === 'missing_scope').length)

function createUser() {
  users.value.unshift({
    id: Date.now(),
    name: 'Новый пользователь',
    login: 'new.user',
    role: 'Ассистент-лаборант',
    scope: 'Не назначен',
    status: 'missing_scope'
  })
  createOpen.value = false
  toast.add({ title: 'Пользователь создан', color: 'success' })
}

function openScope(userId: number) {
  selectedUserId.value = userId
  scopeOpen.value = true
}

function saveScope() {
  if (selectedUser.value) {
    selectedUser.value.scope = 'Микробиология'
    selectedUser.value.status = 'active'
  }
  scopeOpen.value = false
  toast.add({ title: 'Scope назначен', color: 'success' })
}

function softDelete(userId: number) {
  const user = users.value.find(item => item.id === userId)
  if (!user) return
  user.status = 'deleted'
  toast.add({ title: 'Пользователь скрыт', color: 'warning' })
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <section class="grid gap-3 sm:grid-cols-3">
      <div class="rounded-lg border border-default bg-elevated/40 p-4">
        <p class="text-xs uppercase text-muted">
          Пользователи
        </p>
        <p class="mt-2 text-2xl font-semibold text-highlighted">
          {{ users.length }}
        </p>
      </div>
      <div class="rounded-lg border border-default bg-elevated/40 p-4">
        <p class="text-xs uppercase text-muted">
          Без scope
        </p>
        <p class="mt-2 text-2xl font-semibold text-highlighted">
          {{ missingScopeCount }}
        </p>
      </div>
      <div class="rounded-lg border border-default bg-elevated/40 p-4">
        <p class="text-xs uppercase text-muted">
          Режим
        </p>
        <p class="mt-2 text-sm font-semibold text-highlighted">
          {{ isUserAdmin ? 'Администрирование' : 'Просмотр настроек' }}
        </p>
      </div>
    </section>

    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <UInput
        v-model="query"
        icon="i-lucide-search"
        placeholder="Пользователь, роль или scope"
        class="w-full sm:max-w-sm"
      />
      <UButton
        v-if="isUserAdmin"
        icon="i-lucide-user-plus"
        label="Создать пользователя"
        @click="createOpen = true"
      />
    </div>

    <div class="overflow-hidden rounded-lg border border-default">
      <div class="grid grid-cols-[minmax(0,1fr)_9rem_11rem_auto] gap-3 border-b border-default px-4 py-2 text-xs font-medium uppercase text-muted">
        <span>Пользователь</span>
        <span>Роль</span>
        <span>Scope</span>
        <span />
      </div>
      <div v-for="user in filteredUsers" :key="user.id" class="grid grid-cols-[minmax(0,1fr)_9rem_11rem_auto] items-center gap-3 border-b border-default px-4 py-3 last:border-b-0">
        <div class="min-w-0">
          <p class="truncate text-sm font-medium text-highlighted">
            {{ user.name }}
          </p>
          <p class="truncate text-xs text-muted">
            {{ user.login }}
          </p>
        </div>
        <UBadge :label="user.role" color="neutral" variant="subtle" />
        <UBadge :label="user.scope" :color="user.status === 'missing_scope' ? 'warning' : 'neutral'" variant="outline" />
        <div class="flex justify-end gap-1">
          <UButton
            v-if="isUserAdmin"
            icon="i-lucide-user-cog"
            color="neutral"
            variant="ghost"
            size="sm"
            @click="openScope(user.id)"
          />
          <UButton
            v-if="isUserAdmin && user.status !== 'deleted'"
            icon="i-lucide-trash-2"
            color="error"
            variant="ghost"
            size="sm"
            @click="softDelete(user.id)"
          />
        </div>
      </div>
    </div>

    <UModal v-model:open="createOpen" title="Форма пользователя" description="Логин, ФИО, роль и начальный scope.">
      <template #body>
        <div class="grid gap-3 sm:grid-cols-2">
          <UInput model-value="new.user" placeholder="Логин" />
          <UInput model-value="Новый пользователь" placeholder="ФИО" />
          <USelect model-value="Ассистент-лаборант" :items="['Санитарный врач', 'Регистратор', 'Врач-лаборант', 'Ассистент-лаборант', 'Начальник лаборатории']" />
          <UInput model-value="Не назначен" placeholder="Scope" />
        </div>
      </template>
      <template #footer>
        <UButton
          label="Отмена"
          color="neutral"
          variant="ghost"
          @click="createOpen = false"
        />
        <UButton label="Создать" icon="i-lucide-user-plus" @click="createUser" />
      </template>
    </UModal>

    <UModal v-model:open="scopeOpen" title="User scopes" description="Привязка к филиалу, лаборатории или объекту.">
      <template #body>
        <div class="grid gap-3">
          <UInput :model-value="selectedUser?.name" placeholder="Пользователь" />
          <USelect model-value="Микробиология" :items="['Центральный филиал', 'Микробиология', 'Санитарная химия', 'Объекты ЦФ']" />
        </div>
      </template>
      <template #footer>
        <UButton
          label="Отмена"
          color="neutral"
          variant="ghost"
          @click="scopeOpen = false"
        />
        <UButton label="Сохранить scope" icon="i-lucide-save" @click="saveScope" />
      </template>
    </UModal>
  </div>
</template>
