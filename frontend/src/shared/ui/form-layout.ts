import type { FormField, FieldLayoutSpan } from '@/shared/types/form'

const spanClasses: Record<FieldLayoutSpan, string> = {
  4: 'md:col-span-4',
  6: 'md:col-span-6',
  12: 'md:col-span-12'
}

export const getFormFieldLayoutClass = (field: FormField) => {
  const span = field.layout?.span ?? (field.type === 'textarea' ? 12 : 6)
  return spanClasses[span]
}
