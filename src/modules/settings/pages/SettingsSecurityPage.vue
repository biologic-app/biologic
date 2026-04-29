<script setup lang="ts">
import * as z from 'zod'
import { computed, reactive } from 'vue'
import type { FormError } from '@nuxt/ui'
import { useI18n } from 'vue-i18n'
import { workflowEntityActions } from '@/modules/workflows/data'
import { useWorkflowRole } from '@/modules/workflows/useWorkflowRole'

const { t } = useI18n()
const { selectedRoleKey } = useWorkflowRole()
const isUserAdmin = computed(() => selectedRoleKey.value === 'user_admin')

type PasswordSchema = {
  current: string
  new: string
}

const passwordSchema = computed(() => z.object({
  current: z.string().min(8, t('settings.securityPage.minLength')),
  new: z.string().min(8, t('settings.securityPage.minLength'))
}))

const password = reactive<Partial<PasswordSchema>>({
  current: '',
  new: ''
})

const validate = (state: Partial<PasswordSchema>): FormError[] => {
  const errors: FormError[] = []
  if (state.current && state.new && state.current === state.new) {
    errors.push({ name: 'new', message: t('settings.securityPage.passwordsDifferent') })
  }
  return errors
}

const rolePermissionRows = computed(() => {
  const roles = ['registrar', 'lab_doctor', 'lab_assistant', 'lab_chief', 'user_admin']

  return roles.map(role => ({
    role,
    permissions: workflowEntityActions
      .filter(action => action.roles.includes(role))
      .map(action => `${action.resource}.${action.action}`)
      .slice(0, 6)
  }))
})
</script>

<template>
  <div v-if="isUserAdmin" class="mb-4 flex flex-col gap-4">
    <section class="rounded-lg border border-default bg-elevated/40 p-4">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 class="text-base font-semibold text-highlighted">
            Roles & permissions
          </h2>
          <p class="mt-1 text-sm text-muted">
            Матрица UI-действий для ролей. Реальный контроль доступа остаётся на backend.
          </p>
        </div>
        <UButton icon="i-lucide-shield-check" label="Обновить роль" />
      </div>
    </section>

    <div class="overflow-hidden rounded-lg border border-default">
      <div v-for="row in rolePermissionRows" :key="row.role" class="grid gap-3 border-b border-default p-4 last:border-b-0 lg:grid-cols-[12rem_minmax(0,1fr)]">
        <p class="text-sm font-semibold text-highlighted">
          {{ row.role }}
        </p>
        <div class="flex flex-wrap gap-2">
          <UBadge
            v-for="permission in row.permissions"
            :key="permission"
            :label="permission"
            color="neutral"
            variant="subtle"
          />
        </div>
      </div>
    </div>
  </div>

  <UPageCard
    :title="t('settings.securityPage.passwordTitle')"
    :description="t('settings.securityPage.passwordDescription')"
    variant="subtle"
  >
    <UForm
      :schema="passwordSchema"
      :state="password"
      :validate="validate"
      class="flex flex-col gap-4 max-w-xs"
    >
      <UFormField name="current">
        <UInput
          v-model="password.current"
          type="password"
          :placeholder="t('settings.securityPage.currentPassword')"
          class="w-full"
        />
      </UFormField>

      <UFormField name="new">
        <UInput
          v-model="password.new"
          type="password"
          :placeholder="t('settings.securityPage.newPassword')"
          class="w-full"
        />
      </UFormField>

      <UButton :label="t('common.update')" class="w-fit" type="submit" />
    </UForm>
  </UPageCard>

  <UPageCard
    :title="t('settings.securityPage.accountTitle')"
    :description="t('settings.securityPage.accountDescription')"
    class="bg-gradient-to-tl from-error/10 from-5% to-default"
  >
    <template #footer>
      <UButton :label="t('settings.securityPage.deleteAccount')" color="error" />
    </template>
  </UPageCard>
</template>
