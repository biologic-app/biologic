<script setup lang="ts">
import * as z from 'zod'
import { computed, reactive } from 'vue'
import type { FormError } from '@nuxt/ui'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

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
</script>

<template>
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
