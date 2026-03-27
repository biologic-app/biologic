import { computed } from 'vue'
import { useAuthStore } from '@/modules/auth'
import { getResolvedTours, startAutostartTour, startTourById } from '@/shared/tour/tour.service'
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

  const tours = computed(() => {
    if (!context.value) {
      return []
    }

    return getResolvedTours(scope, context.value)
  })

  const onboardingTour = computed(() => tours.value.find((tour) => tour.kind === 'onboarding') || null)
  const whatsNewTours = computed(() => tours.value.filter((tour) => tour.kind === 'whats-new'))
  const unseenTours = computed(() => tours.value.filter((tour) => !tour.seen))
  const hasUnseenTours = computed(() => unseenTours.value.length > 0)

  async function startTour(tourId: string) {
    if (!context.value) {
      return false
    }

    return startTourById(scope, tourId, context.value)
  }

  async function startOnboarding() {
    if (!onboardingTour.value) {
      return false
    }

    return startTour(onboardingTour.value.id)
  }

  async function startLatestWhatsNew() {
    const target = whatsNewTours.value.find((tour) => !tour.seen) || whatsNewTours.value[0]
    if (!target) {
      return false
    }

    return startTour(target.id)
  }

  async function startAutostart() {
    if (!context.value) {
      return false
    }

    return startAutostartTour(scope, context.value)
  }

  return {
    tours,
    onboardingTour,
    whatsNewTours,
    unseenTours,
    hasUnseenTours,
    startTour,
    startOnboarding,
    startLatestWhatsNew,
    startAutostart
  }
}
