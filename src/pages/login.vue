<route lang="json">
{
  "meta": {
    "layout": "auth"
  }
}
</route>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { z } from 'zod'
import type { AuthFormField, FormSubmitEvent } from '@nuxt/ui'
import { useI18n } from 'vue-i18n'
import LoginPreferences from '../components/LoginPreferences.vue'

type LoginSchema = {
  username: string
  password: string
  remember?: boolean
}

const router = useRouter()
const toast = useToast()
const { t } = useI18n()

const schema = computed(() => z.object({
  username: z.string()
    .trim()
    .min(1, { message: t('login.validation.usernameRequired') })
    .min(3, { message: t('login.validation.usernameMin') })
    .max(64, { message: t('login.validation.usernameMax') })
    .regex(/^[a-zA-Z0-9._-]+$/, { message: t('login.validation.usernameFormat') }),

  password: z.string()
    .min(1, { message: t('login.validation.passwordRequired') })
    .min(8, { message: t('login.validation.passwordMin') })
    .max(128, { message: t('login.validation.passwordMax') }),

  remember: z.boolean().default(false)
}))
const fields = computed<AuthFormField[]>(() => [
  {
    name: 'username',
    type: 'text',
    label: t('login.username'),
    placeholder: t('login.usernamePlaceholder'),
    autocomplete: 'username',
    icon: 'i-lucide-user-round',
    required: true,
    defaultValue: ''
  },
  {
    name: 'password',
    type: 'password',
    label: t('login.password'),
    placeholder: t('login.passwordPlaceholder'),
    autocomplete: 'current-password',
    icon: 'i-lucide-lock',
    required: true,
    defaultValue: ''
  },
  {
    name: 'remember',
    type: 'checkbox',
    label: t('login.remember'),
    description: t('login.rememberHint'),
    defaultValue: false
  }
])

async function onSubmit(event?: FormSubmitEvent<Partial<LoginSchema>>) {
  if (!event) {
    return
  }

  const username = event.data.username ?? ''

  toast.add({
    title: t('common.success'),
    description: t('login.successDescription', { username }),
    color: 'success',
    icon: 'i-lucide-badge-check'
  })

  await router.push('/')
}
</script>

<template>
  <div class="grid w-full gap-10 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
    <section class="hidden lg:block">
      <div class="max-w-2xl space-y-8">
        <UBadge 
          :label="t('login.badge')" 
          variant="subtle" 
          color="primary" 
          size="xl" 
        />
        <div class="space-y-4">
          <h1 class="max-w-xl text-5xl font-semibold tracking-tight text-highlighted">
            {{ t('login.heroTitle') }}
          </h1>
          <p class="max-w-xl text-lg leading-8 text-toned">
            {{ t('login.heroDescription') }}
          </p>
          <LoginPreferences />
        </div>
      </div>
    </section>
    <section class="mx-auto w-full max-w-md">
      <div class="space-y-4">
        <div class="flex justify-end lg:hidden">
          <LoginPreferences />
        </div>

        <UPageCard
          variant="subtle"
          class="border border-default/70 bg-default/90 shadow-2xl backdrop-blur"
        >
          <UAuthForm
            :schema="schema"
            :fields="fields"
            :title="t('login.title')"
            :description="t('login.description')"
            class="w-full"
            novalidate
            :ui="{
              title: 'text-left text-2xl font-semibold text-highlighted',
              description: 'text-left text-sm text-toned '
            }"
            @submit="onSubmit"
          />
        </UPageCard>
      </div>
    </section>
  </div>
</template>
