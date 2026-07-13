import { i18n } from '@/shared/i18n'

// Entity kind used to scope the i18n status-label lookup (`statusLabels.<entity>`).
export type StatusEntity = 'direction' | 'sample' | 'research' | 'test'

/**
 * Translate a lifecycle status by (entity, code) via the `statusLabels` i18n
 * namespace. Falls back to the raw backend `name` when the key is missing,
 * else the code itself.
 */
export function statusLabel(
  entity: StatusEntity,
  code?: string | null,
  fallbackName?: string | null,
): string {
  if (code) {
    const key = `statusLabels.${entity}.${code}`
    if (i18n.global.te(key)) {
      return i18n.global.t(key)
    }
  }
  return fallbackName?.trim() || code || ''
}
