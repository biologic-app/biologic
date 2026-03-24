<script setup lang="ts">
import { useLocale } from './composables/useLocale'

const { nuxtUiLocale } = useLocale()
</script>

<template>
  <Suspense>
    <UApp :locale="nuxtUiLocale">
      <RouterView />
    </UApp>
  </Suspense>
</template>
