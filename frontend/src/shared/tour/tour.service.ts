import { computed, nextTick, ref, watch } from 'vue'
import type { TourStep } from '@nuxt/ui/composables'
import { router } from '@/app/router'
import { tourRegistry } from '@/shared/tour/tour.registry'
import { hasSeenTour, markTourSeen } from '@/shared/tour/tour.storage'
import { runTourAction } from '@/shared/tour/tour.actions'
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

// True for as long as the *current* step owns a dialog it opened via its own
// `action` (from when that action runs until we advance to a different
// step) — the window in which a foreign-looking dialog being open is
// actually expected and legitimately ours, not a conflict to resolve.
let currentStepOwnsDialog = false

// A step's `action` (e.g. opening a modal) mounts a Reka UI dialog/popover
// layer *after* our own tour popover — Reka's DismissableLayer stack then
// disables pointer-events on every layer below the most recently opened one,
// making the tour popover unclickable (and hidden from a11y via aria-hidden).
// Detect that lockout and transparently remount our popover so it re-registers
// as the topmost layer — reclaims click-through, visual stacking, and a11y
// visibility all at once, since all three are decided by DOM/registration order.
// Only do this while `currentStepOwnsDialog` — i.e. the dialog burying us is
// the one *we* opened via the current step's own action, not a dialog the
// user opened independently (that case is handled below by yielding instead
// of reclaiming).
let suppressPersist = false
let reclaiming = false

async function reclaimTopLayer() {
  if (reclaiming || !engine.open.value) {
    return
  }

  reclaiming = true
  const index = engine.index.value
  suppressPersist = true
  engine.finish()
  await nextTick()
  engine.goTo(index)
  suppressPersist = false
  reclaiming = false
}

if (typeof document !== 'undefined' && typeof MutationObserver !== 'undefined') {
  const overlayObserver = new MutationObserver(() => {
    if (currentStepOwnsDialog && engine.open.value && document.body.style.pointerEvents === 'none') {
      void reclaimTopLayer()
    }
  })
  overlayObserver.observe(document.body, { attributes: true, attributeFilter: ['style'] })
}

// A step's own `action` legitimately opens a dialog (handled above) — but if
// the *user* opens an unrelated dialog while the tour is sitting on an
// ordinary step (e.g. they click "Create direction" themselves instead of
// following the tour), that dialog and our popover become two independent
// DismissableLayer roots. Unlike the same-layer lockout above, this one
// isn't self-healing by remounting on top — the user's dialog has its own
// focus trap. Yield to it: end the tour so the user's action isn't blocked.
function isOpenDialog(element: Element) {
  return element.getAttribute('role') === 'dialog' && element.getAttribute('data-state') === 'open'
}

function isForeignOpenDialogElement(element: Element) {
  return isOpenDialog(element) && !element.querySelector('[data-tour-popover]')
}

function mutationOpensForeignDialog(mutation: MutationRecord) {
  if (mutation.type === 'attributes') {
    return mutation.target instanceof Element && isForeignOpenDialogElement(mutation.target)
  }

  // Reka mounts a dialog's content fresh on each open with `data-state="open"`
  // already set — that's a childList insertion, not an attribute change on an
  // existing node, so it needs its own check.
  return Array.from(mutation.addedNodes).some(
    (node) =>
      node instanceof Element &&
      (isForeignOpenDialogElement(node) ||
        Array.from(node.querySelectorAll('[role="dialog"]')).some(isForeignOpenDialogElement))
  )
}

if (typeof document !== 'undefined' && typeof MutationObserver !== 'undefined') {
  const foreignDialogObserver = new MutationObserver((mutations) => {
    if (!engine.open.value || currentStepOwnsDialog) {
      return
    }
    if (mutations.some(mutationOpensForeignDialog)) {
      engine.finish()
    }
  })
  foreignDialogObserver.observe(document.body, {
    attributes: true,
    attributeFilter: ['data-state'],
    childList: true,
    subtree: true
  })
}

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

  // Steps whose target only appears after their `action` runs (e.g. opening a
  // modal) can't be checked up front — assume present, `waitForStepTarget`
  // handles the actual wait once the step is reached.
  if (step.action) {
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

// Autostart runs after an async permissions/context load, so a user who
// clicks fast (e.g. "Create direction") can already have an unrelated modal
// open by the time it fires. Starting the tour on top of it stacks two
// independent DismissableLayer roots — Reka then intercepts pointer events
// on both the modal's and the tour's own buttons, and neither closes via the
// usual gestures. Wait for any such foreign dialog to close before autostarting.
function hasOpenForeignDialog() {
  if (typeof document === 'undefined') {
    return false
  }

  return Boolean(document.querySelector('[role="dialog"][data-state="open"]'))
}

async function waitForNoForeignDialog(attempts = 150) {
  for (let index = 0; index < attempts; index += 1) {
    if (!hasOpenForeignDialog()) {
      return true
    }

    await waitForFrame()
  }

  return !hasOpenForeignDialog()
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

  // Reset before the new step's own `action` (if any) runs, so it starts
  // scoped to just this step rather than inheriting the previous one's.
  currentStepOwnsDialog = false

  await ensureRoute(step)
  if (step.action) {
    currentStepOwnsDialog = true
    await runTourAction(step.action)
    await waitForFrame()
  }
  await waitForStepTarget(step)
  engine.goTo(index)

  // The overlay observer above only reacts to a *change* on body's
  // `pointer-events` style — but a step's action can open a dialog that had
  // already set it to `none` before our popover even mounted, so there's no
  // fresh mutation to catch. Check directly instead of waiting for one.
  if (currentStepOwnsDialog) {
    await waitForFrame()
    if (document.body.style.pointerEvents === 'none') {
      await reclaimTopLayer()
    }
  }
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
  if (!wasOpen || isOpen || suppressPersist) {
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

  if (hasOpenForeignDialog() && !(await waitForNoForeignDialog())) {
    return false
  }

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
