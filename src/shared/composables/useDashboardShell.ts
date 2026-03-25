import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createSharedComposable } from '@vueuse/core'

const _useDashboardShell = () => {
  const route = useRoute()
  const router = useRouter()
  const isNotificationsSlideoverOpen = ref(false)

  defineShortcuts({
    h: () => router.push('/dashboard'),
    i: () => router.push('/inbox'),
    c: () => router.push('/customers'),
    s: () => router.push('/settings'),
    n: () => {
      isNotificationsSlideoverOpen.value = !isNotificationsSlideoverOpen.value
    }
  })

  watch(() => route.fullPath, () => {
    isNotificationsSlideoverOpen.value = false
  })

  return {
    isNotificationsSlideoverOpen
  }
}

export const useDashboardShell = createSharedComposable(_useDashboardShell)
