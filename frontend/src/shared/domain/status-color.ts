// THE single place that maps a status color to renderable CSS, and the SOURCE
// OF TRUTH for the color vocabulary. The backend only assigns and stores a
// design-system-neutral color NAME per status (returned on status catalogs and
// dashboard aggregates) — it does NOT constrain which names are valid. The
// FRONTEND owns the vocabulary: `STATUS_BASE_COLORS` × `STATUS_COLOR_MODIFIERS`
// below define the recognised set; anything unknown falls back to `DEFAULT`.
//
// The model is the full Tailwind palette (base color) crossed with a lightness
// modifier (light/base/dark). Tailwind v4 emits its full default palette to
// `:root` as `--color-<name>-<shade>`, so we reference those vars directly — no
// per-color CSS, no tree-shaking risk. Adding/retargeting a color is a change to
// `STATUS_BASE_COLORS` / `ACCENT_SHADE` here.
//
// Rule for the whole codebase: if a payload carries a backend `color`, feed it
// to the helpers here. Never re-derive color from a status code — the stored
// `color` value is authoritative.

// Full Tailwind default palette base names (excluding pure black/white).
export const STATUS_BASE_COLORS = [
  'red',
  'orange',
  'amber',
  'yellow',
  'lime',
  'green',
  'emerald',
  'teal',
  'cyan',
  'sky',
  'blue',
  'indigo',
  'violet',
  'purple',
  'fuchsia',
  'pink',
  'rose',
  'slate',
  'gray',
  'zinc',
  'neutral',
  'stone',
] as const
export type StatusBaseColor = (typeof STATUS_BASE_COLORS)[number]

// Lightness modifier applied on top of a base color.
export const STATUS_COLOR_MODIFIERS = ['light', 'base', 'dark'] as const
export type StatusColorModifier = (typeof STATUS_COLOR_MODIFIERS)[number]

// Stored token grammar: `<base>` (= base modifier) | `<base>-light` | `<base>-dark`.

// Tailwind shade picked for each modifier.
export const ACCENT_SHADE: Record<StatusColorModifier, number> = {
  light: 400,
  base: 500,
  dark: 700,
}

const BASE_SET = new Set<string>(STATUS_BASE_COLORS)
const MODIFIER_SET = new Set<string>(STATUS_COLOR_MODIFIERS)

const DEFAULT: { base: StatusBaseColor; modifier: StatusColorModifier } = {
  base: 'zinc',
  modifier: 'base',
}

/**
 * Parse a stored color token into `{ base, modifier }`. Splits on the LAST `-`:
 * a bare valid base (`green`) → `{ green, base }`; `blue-dark` → `{ blue, dark }`.
 * Anything invalid/missing falls back to `DEFAULT`.
 */
export const parseStatusColor = (
  token?: string | null,
): { base: StatusBaseColor; modifier: StatusColorModifier } => {
  if (!token) return DEFAULT

  // Bare base name → base modifier.
  if (BASE_SET.has(token)) {
    return { base: token as StatusBaseColor, modifier: 'base' }
  }

  const idx = token.lastIndexOf('-')
  if (idx <= 0) return DEFAULT

  const base = token.slice(0, idx)
  const modifier = token.slice(idx + 1)
  if (BASE_SET.has(base) && MODIFIER_SET.has(modifier)) {
    return { base: base as StatusBaseColor, modifier: modifier as StatusColorModifier }
  }

  return DEFAULT
}

/**
 * Resolve a stored token to the accent CSS color value
 * (`var(--color-<base>-<shade>)`) — a raw color usable in SVG/inline styles.
 */
export const statusColorAccentVar = (token?: string | null): string => {
  const { base, modifier } = parseStatusColor(token)
  return `var(--color-${base}-${ACCENT_SHADE[modifier]})`
}

/**
 * Inline style for a custom subtle status chip: accent text over a theme-adaptive
 * tint of the same accent (via `color-mix`), readable in light and dark.
 */
export const statusColorBadgeStyle = (
  token?: string | null,
): { color: string; backgroundColor: string } => {
  const accent = statusColorAccentVar(token)
  return {
    color: accent,
    backgroundColor: `color-mix(in oklab, ${accent} 16%, transparent)`,
  }
}

/**
 * Raw accent color value for charts / SVG fills (alias of `statusColorAccentVar`).
 */
export const statusColorVar = statusColorAccentVar

/**
 * The flat allowed list (base × modifier = 66) for pickers. `swatch` is the
 * accent CSS value. For the `base` modifier the `value` is the bare base name
 * (e.g. `green`), not `green-base`. Ordered by base, then modifier.
 */
export const STATUS_COLOR_OPTIONS: Array<{
  value: string
  base: StatusBaseColor
  modifier: StatusColorModifier
  swatch: string
}> = STATUS_BASE_COLORS.flatMap((base) =>
  STATUS_COLOR_MODIFIERS.map((modifier) => {
    const value = modifier === 'base' ? base : `${base}-${modifier}`
    return { value, base, modifier, swatch: statusColorAccentVar(value) }
  }),
)
