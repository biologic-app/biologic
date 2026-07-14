import { computed, ref, watch } from 'vue'
import type { TourStep } from '@nuxt/ui/composables'
import { router } from '@/app/router'
import { tourRegistry } from '@/shared/tour/tour.registry'
import { hasSeenTour, markTourSeen } from '@/shared/tour/tour.storage'
import type {
  AppTourStep,
  ResolvedTour,
  TourContext,
  TourDefinition,
  TourScope
} from '@/shared/tour/types'

const attemptedAutostarts = new Set<string>()

const activeSteps = ref<TourStep[]>([])
const activeTour = ref<ResolvedTour | null>(null)
const activeContext = ref<TourContext | null>(null)

const engine = useTour(activeSteps, { scrollIntoView: true })

function resolveTourKey(tour: TourDefinition, context: TourContext) {
  const completionScope = tour.completionScope || 'user'
  const rolePart = completionScope === 'role' ? context.user.role : 'user'
  return `${tour.scope}:${tour.id}:${tour.version}:${rolePart}`
}

function isTourAvailable(tour: TourDefinition, context: TourContext, scope: TourScope) {
  if (tour.scope !== scope) {
    return false
  }

  if (tour.roles?.length && !tour.roles.includes(context.user.role)) {
    return false
  }

  return tour.isAvailable ? tour.isAvailable(context) : true
}

function isCurrentRoute(step: AppTourStep) {
  return !step.routeName || router.currentRoute.value.name === step.routeName
}

function resolveTargetElement(step: AppTourStep) {
  const target = step.target
  if (!target || typeof document === 'undefined') {
    return undefined
  }

  if (typeof target === 'function') {
    return target()
  }

  if (typeof target === 'string') {
    const selector = target.startsWith('#') || target.startsWith('.') ? target : `#${target}`
    return document.querySelector(selector) ?? undefined
  }

  return target
}

function resolveElement(step: AppTourStep) {
  if (!step.target) {
    return true
  }

  if (!isCurrentRoute(step)) {
    return true
  }

  return Boolean(resolveTargetElement(step))
}

function resolveSteps(steps: AppTourStep[]) {
  return steps.filter((step) => resolveElement(step))
}

function waitForFrame() {
  if (typeof window === 'undefined') {
    return Promise.resolve()
  }

  return new Promise<void>((resolve) => {
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => resolve())
    })
  })
}

async function ensureRoute(step: AppTourStep | undefined) {
  if (!step?.routeName || router.currentRoute.value.name === step.routeName) {
    return
  }

  await router.push({ name: step.routeName })
  await waitForFrame()
  await waitForFrame()
}

async function waitForStepTarget(step: AppTourStep | undefined, attempts = 40) {
  if (!step?.target) {
    return
  }

  for (let index = 0; index < attempts; index += 1) {
    if (resolveTargetElement(step)) {
      return
    }

    await waitForFrame()
  }
}

async function goToStep(index: number) {
  const step = activeSteps.value[index] as AppTourStep | undefined
  if (!step) {
    return
  }

  await ensureRoute(step)
  await waitForStepTarget(step)
  engine.goTo(index)
}

async function stepNext() {
  if (engine.hasNext.value) {
    await goToStep(engine.index.value + 1)
    return
  }

  engine.finish()
}

async function stepPrev() {
  if (engine.hasPrev.value) {
    await goToStep(engine.index.value - 1)
  }
}

watch(engine.open, (isOpen, wasOpen) => {
  if (!wasOpen || isOpen) {
    return
  }

  const tour = activeTour.value
  const context = activeContext.value
  if (tour && context) {
    markTourSeen(context.user.id, {
      key: tour.key,
      tourId: tour.id,
      scope: tour.scope,
      version: tour.version,
      roleKey: tour.completionScope === 'role' ? context.user.role : null,
      seenAt: new Date().toISOString()
    })
  }

  activeTour.value = null
  activeContext.value = null
})

export function getResolvedTours(scope: TourScope, context: TourContext): ResolvedTour[] {
  return tourRegistry
    .filter((tour) => isTourAvailable(tour, context, scope))
    .map((tour) => {
      const key = resolveTourKey(tour, context)
      return {
        ...tour,
        key,
        seen: hasSeenTour(context.user.id, key)
      }
    })
    .sort((left, right) => right.priority - left.priority)
}

export function getPrimaryTour(scope: TourScope, context: TourContext) {
  return getResolvedTours(scope, context)[0] || null
}

export async function startResolvedTour(tour: ResolvedTour, context: TourContext) {
  const steps = resolveSteps(tour.steps(context))
  if (!steps.length) {
    return false
  }

  activeTour.value = tour
  activeContext.value = context
  activeSteps.value = steps

  await goToStep(0)
  return true
}

export async function startTourById(scope: TourScope, tourId: string, context: TourContext) {
  const tour = getResolvedTours(scope, context).find((item) => item.id === tourId)
  if (!tour) {
    return false
  }

  return startResolvedTour(tour, context)
}

export async function startPrimaryTour(scope: TourScope, context: TourContext) {
  const tour = getPrimaryTour(scope, context)
  if (!tour) {
    return false
  }

  return startResolvedTour(tour, context)
}

export async function startAutostartTour(scope: TourScope, context: TourContext) {
  const tour = getPrimaryTour(scope, context)
  if (!tour) {
    return false
  }

  if (!tour.autostart || tour.seen) {
    return false
  }

  const attemptKey = `${context.user.id}:${tour.key}`
  if (attemptedAutostarts.has(attemptKey)) {
    return false
  }

  attemptedAutostarts.add(attemptKey)
  return startResolvedTour(tour, context)
}

export const tourEngine = {
  open: engine.open,
  index: engine.index,
  total: engine.total,
  hasNext: engine.hasNext,
  hasPrev: engine.hasPrev,
  reference: engine.reference,
  current: computed(() => engine.current.value as AppTourStep | undefined),
  next: stepNext,
  prev: stepPrev,
  finish: engine.finish
}
