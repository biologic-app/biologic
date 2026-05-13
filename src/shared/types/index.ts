import type { AvatarProps } from '@nuxt/ui'

export type UserStatus = 'subscribed' | 'unsubscribed' | 'bounced'
export type SaleStatus = 'paid' | 'failed' | 'refunded'
export type ResearchStatus = 'registered' | 'inProgress' | 'review' | 'completed' | 'rejected'

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
