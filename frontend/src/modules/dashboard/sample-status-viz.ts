// Shared icon + lifecycle-ordering for sample statuses across the registrar
// dashboard (stacked-bar timeline + nested-donut). Status COLORS come from the
// backend `color` field via `shared/domain/status-color.ts` — not from here.
export interface SampleStatusStyle {
  code: string
  icon: string
}

export const SAMPLE_STATUS_STYLES: SampleStatusStyle[] = [
  { code: 'pending', icon: 'i-lucide-inbox' },
  { code: 'registered', icon: 'i-lucide-clipboard-check' },
  { code: 'in_progress', icon: 'i-lucide-loader' },
  { code: 'analyzed', icon: 'i-lucide-microscope' },
  { code: 'completed', icon: 'i-lucide-circle-check' },
  { code: 'rejected', icon: 'i-lucide-triangle-alert' }
]

const ORDER_BY_CODE = new Map(SAMPLE_STATUS_STYLES.map((style, index) => [style.code, index]))

export const sampleStatusOrder = (code: string | null | undefined): number =>
  (code ? ORDER_BY_CODE.get(code) : undefined) ?? SAMPLE_STATUS_STYLES.length

// Rotating palette for the nested-donut inner (laboratory) ring.
export const LAB_RING_COLORS = [
  '#0ea5e9',
  '#8b5cf6',
  '#f59e0b',
  '#14b8a6',
  '#ec4899',
  '#64748b',
  '#84cc16',
  '#f43f5e'
]
