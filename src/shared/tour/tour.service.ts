import { driver } from 'driver.js'
import type { Config, DriveStep, Driver } from 'driver.js'
import { tourRegistry } from '@/shared/tour/tour.registry'
import { hasSeenTour, markTourSeen } from '@/shared/tour/tour.storage'
import type { ResolvedTour, TourContext, TourDefinition, TourScope } from '@/shared/tour/types'
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

function resolveElement(step: DriveStep) {
  if (!step.element || typeof document === 'undefined') {
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

function resolveSteps(steps: DriveStep[]) {
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
        seen: hasSeenTour(context.user.id, key),
        titleText: tour.title(context),
        menuLabelText: tour.menuLabel(context)
      }
    })
    .sort((left, right) => right.priority - left.priority)
}

export async function startResolvedTour(tour: ResolvedTour, context: TourContext) {
  await waitForFrame()

  const steps = resolveSteps(tour.steps(context))
  if (!steps.length) {
    return false
  }

  if (activeRun) {
    activeRun.persistOnDestroy = false
    activeRun.driver.destroy()
  }

  const instance = driver(createDriverConfig())
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
          kind: tour.kind,
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

export async function startAutostartTour(scope: TourScope, context: TourContext) {
  const tour = getResolvedTours(scope, context).find((item) => item.autostart && !item.seen)
  if (!tour) {
    return false
  }

  const attemptKey = `${context.user.id}:${tour.key}`
  if (attemptedAutostarts.has(attemptKey)) {
    return false
  }

  attemptedAutostarts.add(attemptKey)
  return startResolvedTour(tour, context)
}
