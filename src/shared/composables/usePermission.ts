import { useAuthStore } from '@/modules/auth/auth.store'
import type { Action, Resource } from '@/shared/types/permissions'

export const usePermission = () => {
  const auth = useAuthStore()

  const can = (resource: Resource, action: Action) => auth.can(resource, action)

  return { can }
}
