// engine/preview.ts
// Перехват доменных действий шага для preview-песочницы (US-008). Чистый TS, без
// Vue и без единого обращения к API: по шагу + контексту резолва собирает запись
// «что БЫЛО БЫ отправлено» через execute-step, НЕ вызывая его. Это делает логику
// перехвата юнит-тестируемой и структурно доказывает нулевую персистентность
// (модуль не импортирует createEntry/saveEntryProgress/executeStep).

import type { ActionResolveContext } from '@/modules/workflows/engine/actions'
import { resolveActions } from '@/modules/workflows/engine/actions'
import { findActionCommand } from '@/modules/workflows/engine/action-commands'
import type { DomainAction, JournalNode, JournalStepData } from '@/modules/workflows/types/journal'

// Один перехваченный доменный вызов: резолвнутое тело + читаемая подпись команды.
export interface PreviewActionCall {
  actionId: string
  command: string
  label: string // подпись команды (реестр) или action.label, иначе сам command
  resolvedArgs: Record<string, unknown>
}

// Запись журнала перехвата по одному шагу: узел + список действий, которые сервер
// выполнил бы при завершении шага в реальном раннере.
export interface PreviewActionEntry {
  nodeId: string
  nodeLabel: string
  calls: PreviewActionCall[]
}

// Доменные действия узла (только step-узлы их несут). Массив может отсутствовать
// на старых схемах — тогда пусто.
export function stepActions(node: JournalNode): DomainAction[] {
  return node.type === 'step' ? (node.data as JournalStepData).actions ?? [] : []
}

// Собрать запись перехвата для шага. null — если у шага нет действий (нечего
// логировать). Использует ТОЛЬКО чистый резолвер resolveActions и реестр команд;
// сеть не затрагивается — здесь лишь то, что было бы отправлено.
export function buildPreviewActionEntry(
  node: JournalNode,
  ctx: ActionResolveContext,
): PreviewActionEntry | null {
  const actions = stepActions(node)
  if (!actions.length) return null

  const resolved = resolveActions(actions, ctx)
  const calls: PreviewActionCall[] = resolved.map((request) => {
    const def = findActionCommand(request.command)
    const source = actions.find((a) => a.id === request.actionId)
    return {
      actionId: request.actionId,
      command: request.command,
      label: def?.label ?? source?.label ?? request.command,
      resolvedArgs: request.resolvedArgs,
    }
  })

  return {
    nodeId: node.id,
    nodeLabel: (node.data as JournalStepData).label ?? node.id,
    calls,
  }
}
