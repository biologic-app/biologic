// engine/field-icons.ts
// Иконка поля по FieldType — ускоряет сканирование карточки шага/цикла
// (иконка считывается быстрее серого текстового бейджа типа).
import type { FieldType } from '@/modules/workflows/types/journal'

const FIELD_TYPE_ICONS: Record<FieldType, string> = {
  text: 'i-lucide-type',
  number: 'i-lucide-hash',
  boolean: 'i-lucide-check-square',
  select: 'i-lucide-list',
  date: 'i-lucide-calendar',
  textarea: 'i-lucide-align-left',
  dictionary: 'i-lucide-book-open',
  file: 'i-lucide-paperclip',
  computed: 'i-lucide-sigma',
}

export function fieldTypeIcon(type: FieldType): string {
  return FIELD_TYPE_ICONS[type] ?? 'i-lucide-circle'
}
