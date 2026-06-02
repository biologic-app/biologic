<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useLocale } from '@/shared/composables/useLocale'
import { useAppearanceSettings } from '@/shared/composables/useAppearanceSettings'

const { nuxtUiLocale } = useLocale()
const toaster = { expand: false }

useAppearanceSettings()

const preventContextMenu = (event: MouseEvent) => {
  event.preventDefault()
}

onMounted(() => {
  document.addEventListener('contextmenu', preventContextMenu, { capture: true })
})

onUnmounted(() => {
  document.removeEventListener('contextmenu', preventContextMenu, { capture: true })
})
</script>

<template>
  <Suspense>
    <UApp :toaster="toaster" :locale="nuxtUiLocale"  >
      <RouterView />
    </UApp>
  </Suspense>
</template>
