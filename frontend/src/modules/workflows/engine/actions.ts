// engine/actions.ts
// Резолвер доменных действий шага (schema-doc §6) и трекер попыток execute-step.
// Чистый TS, без Vue: по DomainAction + answers + actor + scope собирает
// resolved_args для backend `execute-step`. Исполнение — только на сервере; здесь
// только детерминированная сборка тела запроса, поэтому логика юнит-тестируема.

import type { AnswerRef, DomainAction, JournalAnswers } from '@/modules/workflows/types/journal'
import { findActionCommand } from '@/modules/workflows/engine/action-commands'

// Контекст резолва: ответы шага, id актора (auth-пользователь, UUID) и id области
// (scope) — например id исследования, к которому привязана запись раннера.
export interface ActionResolveContext {
  answers: JournalAnswers
  actorId: string | null
  scopeId?: string
}

// Одно действие, готовое к отправке: backend читает command + resolved_args, в
// котором уже лежат id цели (под targetKey команды) и аргументы (в т.ч. actor_id).
export interface ResolvedActionRequest {
  actionId: string
  command: string
  resolvedArgs: Record<string, unknown>
}

// Разрешить один аргумент по ссылке AnswerRef (§6).
export function resolveRef(ref: AnswerRef, ctx: ActionResolveContext): unknown {
  switch (ref.from) {
    case 'answer':
      return ctx.answers[ref.fieldId]
    case 'const':
      return ref.value
    case 'actor':
      return ctx.actorId
  }
}

// Id целевой сущности: из scope (id области, напр. исследования) либо из значения
// поля targetField (обычно dictionary-поле, хранящее id).
export function resolveTargetId(action: DomainAction, ctx: ActionResolveContext): unknown {
  if (action.targetFrom === 'scope') {
    return ctx.scopeId
  }
  return action.targetField ? ctx.answers[action.targetField] : undefined
}

const isBlank = (value: unknown): boolean => value === undefined || value === null

// Собрать resolved_args: аргументы из argsMapping + id цели под targetKey команды.
// Пустые (null/undefined) значения опускаем — тогда backend применяет свои
// фолбэки (напр. actor_id из тела запроса) вместо явного None, который их ломает.
export function resolveActionArgs(
  action: DomainAction,
  ctx: ActionResolveContext,
): Record<string, unknown> {
  const args: Record<string, unknown> = {}
  for (const [key, ref] of Object.entries(action.argsMapping)) {
    const value = resolveRef(ref, ctx)
    if (!isBlank(value)) {
      args[key] = value
    }
  }
  // Id цели кладём под ключ из реестра команд (совпадает с backend target_key).
  // Явный argsMapping приоритетнее автоинъекции.
  const targetKey = findActionCommand(action.command)?.targetKey
  if (targetKey && args[targetKey] === undefined) {
    const targetId = resolveTargetId(action, ctx)
    if (!isBlank(targetId)) {
      args[targetKey] = targetId
    }
  }
  return args
}

export function resolveAction(action: DomainAction, ctx: ActionResolveContext): ResolvedActionRequest {
  return {
    actionId: action.id,
    command: action.command,
    resolvedArgs: resolveActionArgs(action, ctx),
  }
}

export function resolveActions(
  actions: DomainAction[],
  ctx: ActionResolveContext,
): ResolvedActionRequest[] {
  return actions.map((action) => resolveAction(action, ctx))
}

// Трекер попыток execute-step по (run, node). Идемпотентность гарантирует backend
// (UNIQUE(run_id, node_id, attempt)): прозрачный ретрай (сетевой сбой) шлёт ТОТ ЖЕ
// attempt и сворачивается в `already_applied` без двойной мутации; осознанный
// повтор пользователем берёт `nextAttempt` — новую попытку, которую сервер оценит
// заново (и, если переход уже невозможен, вернёт 409).
export class StepAttemptTracker {
  private readonly attempts = new Map<string, number>()

  private key(runId: string, nodeId: string): string {
    return `${runId}::${nodeId}`
  }

  // Attempt для ближайшего исполнения этого шага (по умолчанию 1). Стабилен между
  // вызовами, пока не запрошен явный повтор — поэтому прозрачный ретрай тот же.
  current(runId: string, nodeId: string): number {
    return this.attempts.get(this.key(runId, nodeId)) ?? 1
  }

  // Осознанный повтор: инкремент и возврат нового attempt.
  nextAttempt(runId: string, nodeId: string): number {
    const next = this.current(runId, nodeId) + 1
    this.attempts.set(this.key(runId, nodeId), next)
    return next
  }

  // Сбросить попытки шага (например, при сбросе записи раннера).
  reset(runId: string, nodeId: string): void {
    this.attempts.delete(this.key(runId, nodeId))
  }
}
