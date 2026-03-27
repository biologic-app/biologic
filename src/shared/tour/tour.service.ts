import { driver } from 'driver.js'
import type { Config, Driver } from 'driver.js'
import { router } from '@/app/router'
import { tourRegistry } from '@/shared/tour/tour.registry'
import { hasSeenTour, markTourSeen } from '@/shared/tour/tour.storage'
import type { AppTourStep, ResolvedTour, TourContext, TourDefinition, TourScope } from '@/shared/tour/types'
import { i18n } from '@/shared/i18n'

const attemptedAutostarts = new Set<string>()

let activeRun:
  | {
      driver: Driver
      persistOnDestroy: boolean
    }
  | null = null

const t = (key: string) => i18n.global.t(key).toString()

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
  if (!step.routeName) {
    return true
  }

  return router.currentRoute.value.name === step.routeName
}

function resolveElement(step: AppTourStep) {
  if (!step.element || typeof document === 'undefined') {
    return true
  }

  if (!isCurrentRoute(step)) {
    return true
  }

  if (typeof step.element === 'string') {
    return Boolean(document.querySelector(step.element))
  }

  if (typeof step.element === 'function') {
    return Boolean(step.element())
  }

  return Boolean(step.element)
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

async function waitForStepElement(step: AppTourStep | undefined, attempts = 40) {
  if (!step?.element || typeof document === 'undefined') {
    return
  }

  for (let index = 0; index < attempts; index += 1) {
    if (typeof step.element === 'string' && document.querySelector(step.element)) {
      return
    }

    if (typeof step.element === 'function' && step.element()) {
      return
    }

    if (typeof step.element !== 'string' && typeof step.element !== 'function' && step.element) {
      return
    }

    await waitForFrame()
  }
}

function getNavigationHandler(direction: 'next' | 'previous', steps: AppTourStep[], index: number, instance: Driver) {
  return async () => {
    const targetIndex = direction === 'next' ? index + 1 : index - 1
    const targetStep = steps[targetIndex]
    if (!targetStep) {
      if (direction === 'next') {
        instance.destroy()
      }
      return
    }

    await ensureRoute(targetStep)
    await waitForStepElement(targetStep)

    if (direction === 'next') {
      instance.moveNext()
      return
    }

    instance.movePrevious()
  }
}

function prepareSteps(steps: AppTourStep[], instance: Driver): AppTourStep[] {
  return steps.map((step, index) => ({
    ...step,
    popover: {
      ...step.popover,
      onNextClick: getNavigationHandler('next', steps, index, instance),
      onPrevClick: getNavigationHandler('previous', steps, index, instance)
    }
  }))
}

function createDriverConfig(): Config {
  return {
    animate: true,
    smoothScroll: true,
    allowClose: true,
    overlayOpacity: 0.55,
    overlayColor: '#0f172a',
    stagePadding: 12,
    stageRadius: 20,
    popoverClass: 'biologic-tour',
    showButtons: ['previous', 'next', 'close'],
    showProgress: true,
    nextBtnText: t('tour.actions.next'),
    prevBtnText: t('tour.actions.previous'),
    doneBtnText: t('tour.actions.done')
  }
}

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
  const baseSteps = resolveSteps(tour.steps(context))
  const firstStep = baseSteps[0]
  await ensureRoute(firstStep)
  await waitForStepElement(firstStep)

  const instance = driver(createDriverConfig())
  const steps = prepareSteps(baseSteps, instance)
  if (!steps.length) {
    return false
  }

  if (activeRun) {
    activeRun.persistOnDestroy = false
    activeRun.driver.destroy()
  }

  const run = {
    driver: instance,
    persistOnDestroy: true
  }

  activeRun = run

  instance.setConfig({
    ...createDriverConfig(),
    steps,
    onDestroyed: () => {
      if (run.persistOnDestroy) {
        markTourSeen(context.user.id, {
          key: tour.key,
          tourId: tour.id,
          scope: tour.scope,
          version: tour.version,
          roleKey: tour.completionScope === 'role' ? context.user.role : null,
          seenAt: new Date().toISOString()
        })
      }

      if (activeRun === run) {
        activeRun = null
      }
    }
  })

  instance.drive()
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
