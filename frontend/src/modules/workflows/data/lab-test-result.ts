import type { JournalSchema } from '@/modules/workflows/types/journal'

// Эталон US-007 (schema-doc §8.1): двусторонняя интеграция раннера с backend.
// Шаг «Выбор теста» подтягивает тесты в статусе in_progress (dictionary с
// filters.status), шаг «Результат» по завершении вызывает доменную команду
// tests.complete через execute-step: id цели берётся из поля test_id, значение и
// вердикт — из ответов, актор — текущий пользователь.
//
// ПРЕДУСЛОВИЕ сида: целевой тест должен быть в статусе in_progress — политика
// tests допускает только переход in_progress → completed (иначе backend вернёт 409).
export const labTestResult: JournalSchema = {
  id: 'lab-test-result-v1',
  title: 'Выполнение теста исследования',
  formatVersion: 2,
  version: 1,
  nodes: [
    { id: 'start', type: 'start', position: { x: 0, y: 160 }, data: { label: 'Начало' } },
    {
      id: 'selectTest',
      type: 'step',
      position: { x: 240, y: 120 },
      data: {
        label: 'Выбор теста',
        role: 'lab_assistant',
        fields: [],
        screen: {
          rows: [
            {
              id: 'r1',
              blocks: [
                {
                  id: 'b1',
                  span: 12,
                  kind: 'field',
                  field: {
                    id: 'test_id',
                    label: 'Тест (в работе)',
                    type: 'dictionary',
                    required: true,
                    source: {
                      endpoint: 'tests',
                      labelKey: 'name',
                      valueKey: 'id',
                      searchable: true,
                      filters: { status: 'in_progress' },
                    },
                  },
                },
              ],
            },
          ],
        },
      },
    },
    {
      id: 'result',
      type: 'step',
      position: { x: 560, y: 120 },
      data: {
        label: 'Результат',
        role: 'lab_assistant',
        fields: [],
        screen: {
          rows: [
            {
              id: 'r2',
              blocks: [
                {
                  id: 'b2',
                  span: 6,
                  kind: 'field',
                  field: {
                    id: 'result_value',
                    label: 'Значение',
                    type: 'number',
                    required: true,
                    validation: [{ kind: 'min', value: 0 }],
                  },
                },
                {
                  id: 'b3',
                  span: 6,
                  kind: 'field',
                  field: {
                    id: 'verdict',
                    label: 'Вердикт',
                    type: 'select',
                    required: true,
                    options: [
                      { label: 'Соответствует', value: 'pass' },
                      { label: 'Не соответствует', value: 'fail' },
                    ],
                  },
                },
              ],
            },
          ],
        },
        actions: [
          {
            id: 'a1',
            label: 'Завершить тест',
            command: 'tests.complete',
            targetFrom: 'field',
            targetField: 'test_id',
            argsMapping: {
              result: { from: 'answer', fieldId: 'result_value' },
              verdict: { from: 'answer', fieldId: 'verdict' },
              actor_id: { from: 'actor' },
            },
          },
        ],
      },
    },
    { id: 'end', type: 'end', position: { x: 880, y: 160 }, data: { label: 'Готово' } },
  ],
  edges: [
    { id: 'e1', source: 'start', target: 'selectTest' },
    { id: 'e2', source: 'selectTest', target: 'result' },
    { id: 'e3', source: 'result', target: 'end' },
  ],
}
