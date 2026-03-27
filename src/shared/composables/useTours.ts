import { computed } from 'vue'
import { useAuthStore } from '@/modules/auth'
import { getPrimaryTour, startAutostartTour, startPrimaryTour } from '@/shared/tour/tour.service'
import type { TourContext, TourScope } from '@/shared/tour/types'

export function useTours(scope: TourScope) {
  const auth = useAuthStore()

  const context = computed<TourContext | null>(() => {
    if (!auth.user) {
      return null
    }

    return {
      user: auth.user,
      permissions: auth.permissions,
      can: (resource, action) => auth.can(resource, action)
    }
  })

  const tour = computed(() => {
    if (!context.value) {
      return null
    }

    return getPrimaryTour(scope, context.value)
  })

  const hasUnseenTour = computed(() => Boolean(tour.value && !tour.value.seen))

  async function startBaseTour() {
    if (!context.value) {
      return false
    }

    return startPrimaryTour(scope, context.value)
  }

  async function startWhatsNew() {
    return startBaseTour()
  }

  async function startAutostart() {
    if (!context.value) {
      return false
    }

    return startAutostartTour(scope, context.value)
  }

  return {
    tour,
    hasUnseenTour,
    startBaseTour,
    startWhatsNew,
    startAutostart
  }
}
