import type { Action, CommandAction, CrudAction, Resource } from '@/shared/types/permissions'

export const resources: Resource[] = [
  'dashboard',
  'directions',
  'research',
  'samples',
  'sample-targets',
  'protocols',
  'results',
  'conclusions',
  'tests',
  'doctors',
  'branches',
  'labs',
  'users',
  'research-goals',
  'sample-types',
  'indicators',
  'protocol-types',
  'statuses',
  'user-types',
  'objects'
]

export const crudActions: CrudAction[] = ['view', 'create', 'edit', 'delete']

export const actions = crudActions

export const commandActions: CommandAction[] = [
  'import',
  'export',
  'register',
  'start',
  'complete',
  'release',
  'reject',
  'requeue',
  'approve'
]

export const crudPermissionResources: Resource[] = [
  'directions',
  'research',
  'samples',
  'sample-targets',
  'protocols',
  'results',
  'conclusions',
  'tests',
  'doctors',
  'branches',
  'labs',
  'research-goals',
  'sample-types',
  'indicators',
  'protocol-types',
  'statuses',
  'objects',
  'users',
  'user-types'
]

export interface ResourceCommand {
  resource: Resource
  action: CommandAction
}

export const resourceCommands: ResourceCommand[] = [
  { resource: 'directions', action: 'import' },
  { resource: 'directions', action: 'register' },
  { resource: 'directions', action: 'release' },
  { resource: 'research', action: 'start' },
  { resource: 'research', action: 'complete' },
  { resource: 'samples', action: 'import' },
  { resource: 'samples', action: 'register' },
  { resource: 'samples', action: 'reject' },
  { resource: 'tests', action: 'start' },
  { resource: 'tests', action: 'complete' },
  { resource: 'tests', action: 'reject' },
  { resource: 'tests', action: 'requeue' },
  { resource: 'protocols', action: 'release' },
  { resource: 'results', action: 'approve' },
  { resource: 'conclusions', action: 'release' },
  { resource: 'users', action: 'import' },
  { resource: 'user-types', action: 'export' }
]

export const resourceLabels: Record<Resource, string> = {
  dashboard: 'Главная',
  directions: 'Направления',
  research: 'Исследования',
  samples: 'Образцы',
  'sample-targets': 'Цели образцов',
  protocols: 'Протоколы',
  results: 'Результаты',
  conclusions: 'Заключения',
  tests: 'Тесты',
  doctors: 'Врачи',
  branches: 'Филиалы',
  labs: 'Лаборатории',
  users: 'Пользователи',
  'research-goals': 'Цели исследований',
  'sample-types': 'Типы образцов',
  indicators: 'Показатели',
  'protocol-types': 'Типы протоколов',
  statuses: 'Статусы',
  'user-types': 'Роли',
  objects: 'Объекты'
}

export const actionLabels: Record<Action, string> = {
  view: 'Просмотр',
  create: 'Создание',
  edit: 'Редактирование',
  delete: 'Удаление',
  import: 'Импорт',
  export: 'Экспорт',
  register: 'Регистрация',
  start: 'Запуск',
  complete: 'Завершение',
  release: 'Выпуск',
  reject: 'Отклонение',
  requeue: 'Повторная очередь',
  approve: 'Подтверждение'
}
