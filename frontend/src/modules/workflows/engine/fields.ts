// engine/fields.ts
// Чистая логика полей раннера (schema-doc §4): видимость (visibleWhen),
// валидация (ValidationRule[]) и вычисляемые поля (computed/expr). Без Vue —
// используется и движком (canGoNext / пересчёт computed), и рендерером (ошибки
// под полем), и юнит-тестами.

import jsonLogic from 'json-logic-js'
import type {
  JournalAnswerValue,
  JournalAnswers,
  JournalField,
  JsonLogicRule,
} from '@/modules/workflows/types/journal'

// Пусто ли значение поля (для required-проверки). Массивы (table/file) —
// пустой массив считается незаполненным.
export function isEmpty(value: unknown): boolean {
  if (value === undefined || value === null || value === '') return true
  if (Array.isArray(value)) return value.length === 0
  return false
}

// Видимо ли поле при текущих ответах. Нет visibleWhen → всегда видимо.
// Скрытое поле не рендерится, не обязательно и не участвует в валидации.
export function isVisible(field: JournalField, answers: JournalAnswers): boolean {
  if (!field.visibleWhen) return true
  return Boolean(jsonLogic.apply(field.visibleWhen as never, answers as never))
}

// Длина строки или само число — для правил min/max.
function measure(value: JournalAnswerValue): number | null {
  if (typeof value === 'number') return value
  if (typeof value === 'string') return value.length
  return null
}

// Проверить значение поля по его ValidationRule[]. Возвращает текст первой
// ошибки или null (валидно). Пустые значения пропускаются — их закрывает
// required-проверка. `maxSizeMb` проверяется при загрузке файла, не здесь.
export function validateField(field: JournalField, value: unknown): string | null {
  if (!field.validation?.length) return null
  if (isEmpty(value)) return null

  for (const rule of field.validation) {
    if (rule.kind === 'min') {
      const m = measure(value as JournalAnswerValue)
      if (m !== null && m < rule.value) {
        return rule.message ?? `Минимум ${rule.value}`
      }
    } else if (rule.kind === 'max') {
      const m = measure(value as JournalAnswerValue)
      if (m !== null && m > rule.value) {
        return rule.message ?? `Максимум ${rule.value}`
      }
    } else if (rule.kind === 'regex') {
      if (typeof value === 'string') {
        let re: RegExp
        try {
          re = new RegExp(rule.pattern)
        } catch {
          continue
        }
        if (!re.test(value)) {
          return rule.message ?? 'Неверный формат'
        }
      }
    }
    // maxSizeMb — вне области значений answers (проверяется при upload).
  }
  return null
}

// Лимит размера файла (МБ) из правил поля, если задан.
export function maxSizeMb(field: JournalField): number | null {
  const rule = field.validation?.find((r) => r.kind === 'maxSizeMb')
  return rule && rule.kind === 'maxSizeMb' ? rule.value : null
}

// Заполнено ли обязательное видимое поле и проходит ли валидацию.
export function isFieldSatisfied(field: JournalField, answers: JournalAnswers): boolean {
  if (!isVisible(field, answers)) return true
  const value = answers[field.id]
  if (field.required && isEmpty(value)) return false
  return validateField(field, value) === null
}

// Все поля экрана заполнены/валидны (для canGoNext / canAddLoopItem).
export function fieldsSatisfied(fields: JournalField[], answers: JournalAnswers): boolean {
  return fields.every((f) => isFieldSatisfied(f, answers))
}

// Значение computed-поля: json-logic поверх текущих answers.
export function evaluateComputed(field: JournalField, answers: JournalAnswers): JournalAnswerValue {
  const expr = (field.expr ?? {}) as JsonLogicRule
  const result = jsonLogic.apply(expr as never, answers as never)
  if (
    result === null
    || typeof result === 'string'
    || typeof result === 'number'
    || typeof result === 'boolean'
  ) {
    return result
  }
  // json-logic может вернуть undefined/массив/объект — для answers сводим к null.
  return result === undefined ? null : String(result)
}

// Пересчитать все computed-поля и записать результат в answers (in place).
// Возвращает true, если хотя бы одно значение изменилось. Один проход за вызов —
// для MVP достаточно; циклические зависимости не разрешаются (schema-doc §4).
export function applyComputedFields(fields: JournalField[], answers: JournalAnswers): boolean {
  let changed = false
  for (const field of fields) {
    if (field.type !== 'computed') continue
    const next = evaluateComputed(field, answers)
    if (answers[field.id] !== next) {
      answers[field.id] = next
      changed = true
    }
  }
  return changed
}
