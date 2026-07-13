// THE single place where a status color is mapped to a design-system token.
// The backend stores a design-system-neutral color NAME per status (the API
// contract vocabulary) and returns it on status catalogs and dashboard
// aggregates. Everything visual routes through here, so retargeting the UI to a
// different design system is a one-line change to TOKEN_BY_COLOR.
//
// Rule for the whole codebase: if a payload carries a backend `color`, feed it
// to `statusColorToken` / `statusColorVar`. Never re-derive color from a status
// code — the backend DB is the single source of truth.

// Design-system-neutral color names the backend sends.
export type StatusColorName =
  | 'gray'
  | 'indigo'
  | 'blue'
  | 'violet'
  | 'lime'
  | 'green'
  | 'amber'
  | 'red'

// Nuxt UI `:color` tokens we target (swap this map to retarget a design system).
export type StatusToken =
  | 'neutral'
  | 'indigo'
  | 'info'
  | 'violet'
  | 'lime'
  | 'success'
  | 'warning'
  | 'error'

const TOKEN_BY_COLOR: Record<StatusColorName, StatusToken> = {
  gray: 'neutral',
  indigo: 'indigo',
  blue: 'info',
  violet: 'violet',
  lime: 'lime',
  green: 'success',
  amber: 'warning',
  red: 'error',
}

/**
 * Map a backend color name to a Nuxt UI `:color` token for `<UBadge>` etc.
 * Falls back to `'neutral'` for unknown/missing names.
 */
export const statusColorToken = (name?: string | null): StatusToken =>
  (name ? TOKEN_BY_COLOR[name as StatusColorName] : undefined) ?? 'neutral'

/**
 * Map a backend color name to a CSS variable (`var(--ui-color-<token>-500)`)
 * for charts / SVG swatches where a raw color value is required.
 */
export const statusColorVar = (name?: string | null): string =>
  `var(--ui-color-${statusColorToken(name)}-500)`
