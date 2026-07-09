import type { DriveStep } from 'driver.js'
import type { AuthUser } from '@/shared/types/auth'
import type { Permission } from '@/shared/types/permissions'

export type TourScope = string
export type TourCompletionScope = 'user' | 'role'

export interface AppTourStep extends DriveStep {
  routeName?: string
}

export interface TourContext {
  user: AuthUser
  permissions: Permission[]
  can: (resource: Permission['resource'], action: Permission['action']) => boolean
}

export interface TourDefinition {
  id: string
  scope: TourScope
  version: string
  priority: number
  autostart?: boolean
  completionScope?: TourCompletionScope
  roles?: string[]
  steps: (context: TourContext) => AppTourStep[]
  isAvailable?: (context: TourContext) => boolean
}

export interface TourRecord {
  key: string
  tourId: string
  scope: TourScope
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
}
