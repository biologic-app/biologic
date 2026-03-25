export type Resource =
  | 'dashboard'
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
