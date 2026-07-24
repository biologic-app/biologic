// composables/useWorkflowNodeMenu.ts
// Видимая «⋯» в шапке каждой ноды (n8n-подобный референс) открывает то же
// контекст-меню, что и правый клик по ноде — единая точка входа, заданная
// в JournalBuilder.vue через provide.
import { inject, provide, type InjectionKey } from 'vue'

type OpenNodeMenu = (nodeId: string, event: MouseEvent) => void

const WF_NODE_MENU_KEY: InjectionKey<OpenNodeMenu> = Symbol('wf-node-menu')

export function provideWorkflowNodeMenu(handler: OpenNodeMenu) {
  provide(WF_NODE_MENU_KEY, handler)
}

export function useWorkflowNodeMenu(): OpenNodeMenu {
  return inject(WF_NODE_MENU_KEY, () => {})
}
