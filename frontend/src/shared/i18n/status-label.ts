import { i18n } from '@/shared/i18n'
import { parseStatusColor } from '@/shared/domain/status-color'

// Entity kind used to scope the i18n status-label lookup (`statusLabels.<entity>`).
export type StatusEntity = 'direction' | 'sample' | 'research' | 'test'

/**
 * Translate a lifecycle status by (entity, code) via the `statusLabels` i18n
 * namespace. i18n is the single source of truth for status labels — the raw
 * backend `name` is never used. Falls back to the code itself when no key
 * exists (surfaces a missing translation instead of masking it).
 */
export function statusLabel(entity: StatusEntity, code?: string | null): string {
  if (code) {
    const key = `statusLabels.${entity}.${code}`
    if (i18n.global.te(key)) {
      return i18n.global.t(key)
    }
  }
  return code || ''
}

/**
 * Human-readable name for a status color token via the `colorNames` /
 * `colorModifiers` i18n namespaces, e.g. `blue-dark` → «Синий (тёмный)».
 * The `base` modifier is omitted, so `blue` → «Синий».
 */
export function statusColorName(token?: string | null): string {
  const { base, modifier } = parseStatusColor(token)
  const baseName = i18n.global.t(`colorNames.${base}`)
  if (modifier === 'base') {
    return baseName
  }
  return `${baseName} (${i18n.global.t(`colorModifiers.${modifier}`)})`
}
