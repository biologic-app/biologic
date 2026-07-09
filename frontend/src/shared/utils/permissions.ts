import type { CrudAction, Permission, PermissionSummary } from '@/shared/types/permissions'

const crudActions = new Set<CrudAction>(['view', 'create', 'edit', 'delete'])

export const summarizePermissions = (permissions: Permission[]): PermissionSummary => {
  const summary: PermissionSummary = {
    view: 0,
    create: 0,
    edit: 0,
    delete: 0
  }

  permissions.forEach((permission) => {
    if (crudActions.has(permission.action as CrudAction)) {
      summary[permission.action as CrudAction] += 1
    }
  })

  return summary
}
