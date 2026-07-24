// composables/useWorkflowHighlight.ts
// При наведении на ноду в билдере соседние (связанные рёбрами) ноды остаются
// чёткими, остальные — притухают (item 7 фидбека по дизайну канваса).
// Провайдер живёт в JournalBuilder.vue; каждая нода сама решает, входит ли её
// id в подсвеченный набор — без мутации persisted nodes/edges (не триггерит autosave).
import { computed, inject, provide, ref, unref, type ComputedRef, type InjectionKey, type MaybeRef, type Ref } from 'vue'

const WF_HIGHLIGHT_KEY: InjectionKey<Ref<Set<string> | null>> = Symbol('wf-highlight-ids')

export function provideWorkflowHighlight() {
  const highlightIds = ref<Set<string> | null>(null)
  provide(WF_HIGHLIGHT_KEY, highlightIds)
  return highlightIds
}

export function useWorkflowNodeDimmed(nodeId: MaybeRef<string>): ComputedRef<boolean> {
  const highlightIds = inject(WF_HIGHLIGHT_KEY, ref(null))
  return computed(() => highlightIds.value !== null && !highlightIds.value.has(unref(nodeId)))
}
