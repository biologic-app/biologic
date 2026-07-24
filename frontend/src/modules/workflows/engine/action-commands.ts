// engine/action-commands.ts
// Реестр известных доменных команд шага (schema-doc §6). Чистый TS, без Vue/i18n —
// используется и резолвером (engine/actions.ts берёт targetKey), и редактором
// действий шага (StepActionsEditor — выбор команды и её аргументов).
//
// Зеркалит backend COMMAND_REGISTRY (application/workflows/command_registry.py):
// каждая команда — мутация целевой сущности с precondition-статусом и `targetKey`
// (ключ в resolved_args, под которым сервер ждёт id целевой сущности). Реализация
// перехода — только на сервере; здесь лишь метаданные для сборки resolved_args и UI.

export interface ActionCommandArg {
  key: string // ключ в resolved_args, который читает backend (snake_case)
  label: string // подпись аргумента в редакторе
  required?: boolean
}

export interface ActionCommandDef {
  key: string // DomainAction.command, напр. 'tests.complete'
  label: string // «Завершить тест» — показывается в раннере/редакторе
  resource: string // ресурс status-policy (для документации/подсказок)
  targetKey: string // куда положить резолвнутый id цели в resolved_args
  // Целевая сущность должна быть в одном из этих статусов, иначе backend вернёт 409.
  preconditionStatuses: string[]
  args: ActionCommandArg[] // аргументы команды (помимо target id)
}

export const ACTION_COMMANDS: ActionCommandDef[] = [
  {
    key: 'tests.complete',
    label: 'Завершить тест',
    resource: 'tests',
    targetKey: 'test_id',
    preconditionStatuses: ['in_progress'],
    args: [
      { key: 'result', label: 'Результат', required: true },
      { key: 'verdict', label: 'Вердикт' },
      { key: 'norm', label: 'Норма' },
      { key: 'comment', label: 'Комментарий' },
      { key: 'actor_id', label: 'Исполнитель' },
    ],
  },
  {
    key: 'tests.reject',
    label: 'Отклонить тест',
    resource: 'tests',
    targetKey: 'test_id',
    preconditionStatuses: ['in_progress'],
    args: [
      { key: 'reason', label: 'Причина', required: true },
      { key: 'actor_id', label: 'Исполнитель' },
    ],
  },
]

export function findActionCommand(key: string): ActionCommandDef | undefined {
  return ACTION_COMMANDS.find((command) => command.key === key)
}
