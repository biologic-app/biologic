import { i18n } from '@/shared/i18n'
import type { Action, CommandAction, CrudAction, Resource } from '@/shared/types/permissions'

const t = (key: string, params?: Record<string, unknown>) =>
  i18n.global.t(key, params ?? {}).toString();

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
  'roles',
  'objects'
]

export const crudActions: CrudAction[] = ['view', 'create', 'edit', 'delete']

export const actions = crudActions

export const commandActions: CommandAction[] = [
  'import',
  'export',
  'register',
  'confirm',
  'start',
  'complete',
  'close',
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
  { resource: 'research', action: 'confirm' },
  { resource: 'research', action: 'start' },
  { resource: 'research', action: 'complete' },
  { resource: 'samples', action: 'import' },
  { resource: 'samples', action: 'register' },
  { resource: 'samples', action: 'reject' },
  { resource: 'samples', action: 'close' },
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
  dashboard: t('permissions.resourceLabels.dashboard'),
  directions: t('permissions.resourceLabels.directions'),
  research: t('permissions.resourceLabels.research'),
  samples: t('permissions.resourceLabels.samples'),
  'sample-targets': t('permissions.resourceLabels.sample-targets'),
  protocols: t('permissions.resourceLabels.protocols'),
  results: t('permissions.resourceLabels.results'),
  conclusions: t('permissions.resourceLabels.conclusions'),
  tests: t('permissions.resourceLabels.tests'),
  doctors: t('permissions.resourceLabels.doctors'),
  branches: t('permissions.resourceLabels.branches'),
  labs: t('permissions.resourceLabels.labs'),
  users: t('permissions.resourceLabels.users'),
  'research-goals': t('permissions.resourceLabels.research-goals'),
  'sample-types': t('permissions.resourceLabels.sample-types'),
  indicators: t('permissions.resourceLabels.indicators'),
  'protocol-types': t('permissions.resourceLabels.protocol-types'),
  statuses: t('permissions.resourceLabels.statuses'),
  'user-types': t('permissions.resourceLabels.user-types'),
  objects: t('permissions.resourceLabels.objects'),
  roles: t('permissions.resourceLabels.user-types'),
}

export const actionLabels: Record<Action, string> = {
  view: t('permissions.actionLabels.view'),
  create: t('permissions.actionLabels.create'),
  edit: t('permissions.actionLabels.edit'),
  delete: t('permissions.actionLabels.delete'),
  import: t('permissions.actionLabels.import'),
  export: t('permissions.actionLabels.export'),
  register: t('permissions.actionLabels.register'),
  confirm: t('permissions.actionLabels.confirm'),
  start: t('permissions.actionLabels.start'),
  complete: t('permissions.actionLabels.complete'),
  close: t('permissions.actionLabels.close'),
  release: t('permissions.actionLabels.release'),
  reject: t('permissions.actionLabels.reject'),
  requeue: t('permissions.actionLabels.requeue'),
  approve: t('permissions.actionLabels.approve'),
  read: t('permissions.actionLabels.view'),
  update: t('permissions.actionLabels.edit'),
}
