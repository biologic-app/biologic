import type { DriveStep } from 'driver.js'
import type { AuthUser } from '@/shared/types/auth'
import type { Permission } from '@/shared/types/permissions'

export type TourKind = 'onboarding' | 'whats-new'
export type TourScope = string
export type TourCompletionScope = 'user' | 'role'

export interface TourContext {
  user: AuthUser
  permissions: Permission[]
  can: (resource: Permission['resource'], action: Permission['action']) => boolean
}

export interface TourDefinition {
  id: string
  scope: TourScope
  kind: TourKind
  version: string
  priority: number
  autostart?: boolean
  completionScope?: TourCompletionScope
  roles?: string[]
  title: (context: TourContext) => string
  menuLabel: (context: TourContext) => string
  steps: (context: TourContext) => DriveStep[]
  isAvailable?: (context: TourContext) => boolean
}

export interface TourRecord {
  key: string
  tourId: string
  scope: TourScope
  kind: TourKind
  version: string
  roleKey: string | null
  seenAt: string
}

export interface TourStorageState {
  version: number
  records: TourRecord[]
}

export interface ResolvedTour extends TourDefinition {
  key: string
  seen: boolean
  titleText: string
  menuLabelText: string
}
