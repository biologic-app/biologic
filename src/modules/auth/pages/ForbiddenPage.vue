<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const error = computed(() => ({
  statusCode: 403,
  statusMessage: t('errors.forbidden.title'),
  message: t('errors.forbidden.description')
}))
</script>

<template>
  <UError
    :clear="{
      color: 'neutral',
      size: 'xl',
      icon: 'i-lucide-arrow-left',
      class: 'rounded-full',
      to: '/'
    }"
    :error="error"
    :ui="{
      statusCode: 'text-primary text-4xl sm:text-5xl font-bold tracking-tight',
    }"
  />
</template>
