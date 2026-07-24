import type { JournalSchema } from '@/modules/workflows/types/journal'

// Эталон US-009 (schema-doc §8.2): свободный отчётный процесс БЕЗ доменных
// действий — проверяет универсальность движка (секции, dictionary, таблицы,
// файлы, условие по json-logic над строками таблицы). Ничего не пишет в домен:
// ни одного `actions`, поэтому раннер проходит его как обычную запись журнала.
//
// Шаг «Осмотр помещений» собирает произвольный набор помещений (table `rooms`),
// условие «Есть нарушения?» ветвит по наличию помещения без исправного
// огнетушителя (json-logic `some`), и только тогда запрашивает план устранения.
export const fireSafety: JournalSchema = {
  id: 'fire-safety-v1',
  title: 'Отчёт о пожарной безопасности',
  formatVersion: 2,
  version: 1,
  nodes: [
    { id: 'start', type: 'start', position: { x: 0, y: 220 }, data: { label: 'Начало' } },
    {
      id: 'inspection',
      type: 'step',
      position: { x: 260, y: 160 },
      data: {
        label: 'Осмотр помещений',
        fields: [],
        screen: {
          rows: [
            {
              id: 'r1',
              blocks: [
                { id: 's1', span: 12, kind: 'section', title: 'Общие сведения' },
              ],
            },
            {
              id: 'r2',
              blocks: [
                {
                  id: 'b1',
                  span: 6,
                  kind: 'field',
                  field: {
                    id: 'inspector',
                    label: 'Проверяющий',
                    type: 'dictionary',
                    required: true,
                    source: {
                      endpoint: 'doctors',
                      labelKey: 'last_name',
                      valueKey: 'id',
                      searchable: true,
                    },
                  },
                },
                {
                  id: 'b2',
                  span: 6,
                  kind: 'field',
                  field: {
                    id: 'date',
                    label: 'Дата осмотра',
                    type: 'date',
                    required: true,
                  },
                },
              ],
            },
            {
              id: 'r3',
              blocks: [
                {
                  id: 't1',
                  span: 12,
                  kind: 'table',
                  table: {
                    fieldId: 'rooms',
                    label: 'Помещения',
                    minRows: 1,
                    addLabel: 'Добавить помещение',
                    columns: [
                      { id: 'room', label: 'Помещение', type: 'text', required: true },
                      { id: 'extinguisher_ok', label: 'Огнетушитель', type: 'boolean' },
                      { id: 'note', label: 'Замечание', type: 'text' },
                    ],
                  },
                },
              ],
            },
            {
              id: 'r4',
              blocks: [
                {
                  id: 'b3',
                  span: 12,
                  kind: 'field',
                  field: {
                    id: 'photo',
                    label: 'Фото нарушений',
                    type: 'file',
                    accept: 'image/*',
                    validation: [{ kind: 'maxSizeMb', value: 10 }],
                  },
                },
              ],
            },
          ],
        },
      },
    },
    {
      id: 'hasViolations',
      type: 'condition',
      position: { x: 640, y: 180 },
      data: {
        label: 'Есть нарушения?',
        rule: {
          some: [
            { var: 'rooms' },
            { '==': [{ var: 'extinguisher_ok' }, false] },
          ],
        },
      },
    },
    {
      id: 'remediation',
      type: 'step',
      position: { x: 1000, y: 40 },
      data: {
        label: 'План устранения',
        fields: [],
        screen: {
          rows: [
            {
              id: 'r5',
              blocks: [
                {
                  id: 'b4',
                  span: 12,
                  kind: 'field',
                  field: {
                    id: 'plan',
                    label: 'Мероприятия',
                    type: 'textarea',
                    required: true,
                  },
                },
              ],
            },
          ],
        },
      },
    },
    { id: 'end', type: 'end', position: { x: 1000, y: 360 }, data: { label: 'Отчёт готов' } },
  ],
  edges: [
    { id: 'e1', source: 'start', target: 'inspection' },
    { id: 'e2', source: 'inspection', target: 'hasViolations' },
    { id: 'e3', source: 'hasViolations', target: 'remediation', sourceHandle: 'true' },
    { id: 'e4', source: 'hasViolations', target: 'end', sourceHandle: 'false' },
    { id: 'e5', source: 'remediation', target: 'end' },
  ],
}
