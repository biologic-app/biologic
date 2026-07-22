export type FieldType = 'text' | 'textarea' | 'number' | 'boolean' | 'date' | 'select' | 'file' | 'color'

export interface FieldOption {
  label: string
  value: string | number | boolean | null
}

export type FieldLayoutSpan = 4 | 6 | 12

export interface FieldLayout {
  span?: FieldLayoutSpan
}

export interface FormField {
  key: string
  label: string
  type?: FieldType
  required?: boolean
  options?: FieldOption[]
  placeholder?: string
  accept?: string
  source?: string
  layout?: FieldLayout
  // По умолчанию поле редактируемо; readonly-поля показываются только в просмотре.
  editable?: boolean
}
