export type Resource =
  | 'dashboard'
  | 'customers'
  | 'inbox'
  | 'directions'
  | 'samples'
  | 'sample-targets'
  | 'protocols'
  | 'results'
  | 'conclusions'
  | 'tests'
  | 'doctors'
  | 'branches'
  | 'labs'
  | 'users'
  | 'research-goals'
  | 'sample-types'
  | 'indicators'
  | 'protocol-types'
  | 'statuses'
  | 'user-types'
  | 'objects'

export type Action = 'view' | 'create' | 'edit' | 'delete'

export interface Permission {
  resource: Resource
  action: Action
}

export interface PermissionOverride {
  resource: Resource
  action: Action
  allowed: boolean
}

export interface PermissionSummary {
  view: number
  create: number
  edit: number
  delete: number
}
