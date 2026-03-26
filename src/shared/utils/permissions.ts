import type { Permission, PermissionSummary } from '@/shared/types/permissions'

export const summarizePermissions = (permissions: Permission[]): PermissionSummary => {
  const summary: PermissionSummary = {
    view: 0,
    create: 0,
    edit: 0,
    delete: 0
  }

  permissions.forEach((permission) => {
    summary[permission.action] += 1
  })

  return summary
}
