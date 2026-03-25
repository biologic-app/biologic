<script setup lang="ts">
import { useLocale } from '@/shared/composables/useLocale'

const { nuxtUiLocale } = useLocale()
</script>

<template>
  <Suspense>
    <UApp :locale="nuxtUiLocale">
      <RouterView />
    </UApp>
  </Suspense>
</template>
