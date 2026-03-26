import type { Action, Resource } from '@/shared/types/permissions'

export const resources: Resource[] = [
  'dashboard',
  'customers',
  'inbox',
  'directions',
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

export const actions: Action[] = ['view', 'create', 'edit', 'delete']

export const resourceLabels: Record<Resource, string> = {
  dashboard: 'Главная',
  customers: 'Пациенты',
  inbox: 'Входящие',
  directions: 'Направления',
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
  delete: 'Удаление'
}
