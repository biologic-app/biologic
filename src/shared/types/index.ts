import type { AvatarProps } from '@nuxt/ui'

export type UserStatus = 'subscribed' | 'unsubscribed' | 'bounced'
export type SaleStatus = 'paid' | 'failed' | 'refunded'
export type ResearchStatus = 'registered' | 'inProgress' | 'review' | 'completed' | 'rejected'
export type WorkspaceMode = 'editable' | 'readonly' | 'closing' | 'admin'
export type EntityStatusCode =
  | 'draft'
  | 'registered'
  | 'pending'
  | 'ordered'
  | 'in_progress'
  | 'analyzed'
  | 'completed'
  | 'rejected'
  | 'issued'

export interface WorkflowScreenConfig {
  id: string
  title: string
  route: string
  roles: string[]
  mode: WorkspaceMode
  defaultFilters?: Record<string, string>
  primaryActions: string[]
}

export interface WorkflowEntityAction {
  resource: 'direction' | 'sample' | 'research' | 'test' | 'protocol' | 'user' | 'alert'
  action: string
  fromStatus?: EntityStatusCode
  toStatus?: EntityStatusCode
  roles: string[]
  label: string
  icon: string
  confirmation?: string
}

export interface User {
  id: number
  name: string
  email: string
  avatar?: AvatarProps
  status: UserStatus
  location: string
}

export interface Mail {
  id: number
  unread?: boolean
  from: User
  subject: string
  body: string
  date: string
}

export interface Member {
  name: string
  username: string
  role: 'member' | 'owner'
  avatar: AvatarProps
}

export interface Sale {
  id: string
  date: string
  status: SaleStatus
  email: string
  amount: number
}

export interface Notification {
  id: number
  unread?: boolean
  sender: User
  body: string
  date: string
}

export interface ResearchHistoryEntry {
  id: number
  status: ResearchStatus
  date: string
  actor: string
  note: string
}

export interface ResearchTest {
  id: number
  code: string
  group: string
  name: string
  method: string
  applies: boolean
  result: string
  reference: string
  unit: string
  note: string
  interpretation: 'normal' | 'warning' | 'critical' | 'pending'
}

export interface ResearchSample {
  id: number
  code: string
  patient: User
  material: string
  direction: string
  priority: 'normal' | 'urgent'
  status: ResearchStatus
  registeredAt: string
  updatedAt: string
  comment: string
  tests: ResearchTest[]
  history: ResearchHistoryEntry[]
}
