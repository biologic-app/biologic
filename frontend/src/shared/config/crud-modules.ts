import type { CrudModuleConfig } from '@/shared/types/crud'
import type { TableFilterField } from '@/shared/types/table'

const textFilter = () => ({ value: '', matchMode: 'contains' })
const dateFilter = () => ({ value: [null, null], matchMode: 'between' })
const multiFilter = () => ({ value: '', matchMode: 'equals' })
const currentYear = new Date().getFullYear()
const directionYearOptions = Array.from(
  { length: currentYear - 2000 + 1 },
  (_, index) => {
    const year = 2000 + index
    return { label: String(year), value: year }
  }
).reverse()
const yesNoOptions = [
  { label: 'Да', value: true },
  { label: 'Нет', value: false }
]

const textFilterField = (field: string, header: string, placeholder = header): TableFilterField => ({
  field,
  header,
  filter: { type: 'text', placeholder }
})

const dateFilterField = (field: string, header: string): TableFilterField => ({
  field,
  header,
  filter: { type: 'dateRange' }
})

const booleanFilterField = (field: string, header: string): TableFilterField => ({
  field,
  header,
  filter: { type: 'select', options: yesNoOptions }
})

const selectFilterField = (
  field: string,
  header: string,
  source: string,
  placeholder = header
): TableFilterField => ({
  field,
  header,
  filter: { type: 'select', placeholder, source }
})

const auditFilterFields = new Set(['created_at', 'updated_at'])
const referenceFilterSources: Record<string, Record<string, { field: string, source: string }>> = {
  objects: {
    'branch.name': { field: 'branch_id', source: '/branches' }
  },
  labs: {
    'branch.name': { field: 'branch_id', source: '/branches' }
  },
  'research-goals': {
    'lab.name': { field: 'lab_id', source: '/labs' }
  },
  indicators: {
    'lab.name': { field: 'lab_id', source: '/labs' },
    'sample_type.name': { field: 'sample_type_id', source: '/sample_types' }
  },
  protocols: {
    'protocol_type.name': { field: 'protocol_type_id', source: '/protocol_types' },
    'conclusion.name': { field: 'conclusion_id', source: '/conclusions' }
  },
  'sample-targets': {
    'sample.name': { field: 'sample_id', source: '/samples' },
    'research_goal.name': { field: 'research_goal_id', source: '/research_goals' }
  }
}

export const getCrudModuleFilterFields = (config: CrudModuleConfig): TableFilterField[] =>
  (config.filterFields ?? config.columns)
    .filter((field) => field.filter && !auditFilterFields.has(field.field))
    .map((field) => {
      const reference = referenceFilterSources[config.presetKey]?.[field.field]
      return reference
        ? selectFilterField(reference.field, field.header, reference.source, field.header)
        : field
    })

export const crudModules: Record<string, CrudModuleConfig> = {
  directions: {
    resource: 'directions',
    title: 'Направления',
    description: 'Журнал направлений, статусов и сроков исполнения.',
    endpoint: '/directions',
    include: 'doctor,object,status',
    presetKey: 'directions',
    pageId: 'directions',
    initialFilters: {
      global: textFilter(),
      year_no: textFilter(),
      base_no: textFilter(),
      doctor_id: textFilter(),
      object_id: textFilter(),
      status_id: textFilter(),
      sampled_at: dateFilter(),
      received_at: dateFilter(),
      completed_at: dateFilter(),
      is_done: multiFilter(),
      is_urgent: multiFilter()
    },
    filterFields: [
      {
        field: 'year_no',
        header: 'Год',
        filter: { type: 'select', placeholder: 'Год', options: directionYearOptions }
      },
      textFilterField('base_no', 'Номер'),
      selectFilterField('doctor_id', 'Врач', '/doctors'),
      selectFilterField('object_id', 'Объект', '/objects'),
      selectFilterField('status_id', 'Статус', '/direction_statuses'),
      booleanFilterField('is_done', 'Завершено'),
      booleanFilterField('is_urgent', 'Срочно'),
      dateFilterField('sampled_at', 'Отбор'),
      dateFilterField('received_at', 'Получение'),
      dateFilterField('completed_at', 'Завершение')
    ],
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'year_no', header: 'Год', sortable: true, filter: { type: 'text', placeholder: 'Год' } },
      { field: 'base_no', header: 'Номер', sortable: true, filter: { type: 'text', placeholder: 'Номер' } },
      {
        field: 'doctor.name',
        header: 'Врач',
        sortable: true,
        filter: { type: 'text', placeholder: 'Врач' },
        body: (row: Record<string, unknown>) => {
          const doctor = row.doctor as
            | { first_name?: string | null, last_name?: string | null, patronymic?: string | null }
            | null
            | undefined
          if (!doctor) {
            return '-'
          }
          const initials = [doctor.first_name, doctor.patronymic]
            .filter((part): part is string => Boolean(part && String(part).trim()))
            .map((part) => `${String(part).trim().charAt(0).toUpperCase()}.`)
            .join('')
          return [doctor.last_name, initials].filter(Boolean).join(' ').trim() || '-'
        }
      },
      {
        field: 'object.name',
        header: 'Объект',
        sortable: true,
        filter: { type: 'text', placeholder: 'Объект' },
        body: (row: Record<string, unknown>) => {
          const object = row.object as { code?: string | null, name?: string | null } | null | undefined
          if (!object) {
            return '-'
          }
          return [object.code, object.name].filter(Boolean).join(' — ') || '-'
        }
      },
      { field: 'status.name', header: 'Статус', sortable: true, filter: { type: 'text', placeholder: 'Статус' } },
      { field: 'sampled_at', header: 'Отбор', sortable: true, filter: { type: 'dateRange' } },
      { field: 'received_at', header: 'Получение', sortable: true, filter: { type: 'dateRange' } },
      { field: 'completed_at', header: 'Завершение', sortable: true, filter: { type: 'dateRange' } },
      {
        field: 'is_done',
        header: 'Завершено',
        sortable: true,
        filter: {
          type: 'select',
          options: [
            ...yesNoOptions
          ]
        }
      },
      {
        field: 'is_urgent',
        header: 'Срочно',
        sortable: true,
        filter: {
          type: 'select',
          options: [
            ...yesNoOptions
          ]
        }
      }
    ],
    fields: [
      { key: 'year_no', label: 'Год', type: 'number', required: true, layout: { span: 4 } },
      { key: 'base_no', label: 'Номер', type: 'number', layout: { span: 4 } },
      { key: 'is_done', label: 'Завершено', type: 'boolean', layout: { span: 6 } },
      { key: 'is_urgent', label: 'Срочно', type: 'boolean', layout: { span: 6 } },
      { key: 'doctor_id', label: 'Врач', type: 'select', source: '/doctors', layout: { span: 4 } },
      { key: 'object_id', label: 'Объект', type: 'select', source: '/objects', layout: { span: 4 } },
      { key: 'sampled_at', label: 'Отбор', type: 'date', layout: { span: 4 } },
      { key: 'received_at', label: 'Получение', type: 'date', layout: { span: 4 } },
      { key: 'completed_at', label: 'Завершение', type: 'date', layout: { span: 4 } }
    ]
  },
  samples: {
    resource: 'samples',
    title: 'Образцы',
    description: 'Журнал образцов с типами, статусами и периодами обработки.',
    endpoint: '/samples',
    include: 'sample_type,status,direction,protocol',
    presetKey: 'samples',
    pageId: 'samples',
    initialFilters: {
      global: textFilter(),
      month_no: textFilter(),
      name: textFilter(),
      alternate_name: textFilter(),
      nomenclature_code: textFilter(),
      batch_code: textFilter(),
      supplier: textFilter(),
      sample_type_id: textFilter(),
      direction_id: textFilter(),
      status_id: textFilter(),
      protocol_id: textFilter(),
      is_urgent: multiFilter(),
      is_done: multiFilter(),
      sampled_at: dateFilter(),
      received_at: dateFilter(),
      completed_at: dateFilter(),
      deadline: dateFilter()
    },
    filterFields: [
      textFilterField('month_no', 'Месяц'),
      textFilterField('name', 'Название'),
      textFilterField('alternate_name', 'Альтернативное имя'),
      textFilterField('nomenclature_code', 'Код номенклатуры'),
      textFilterField('batch_code', 'Код партии'),
      textFilterField('supplier', 'Поставщик'),
      selectFilterField('sample_type_id', 'Тип образца', '/sample_types'),
      selectFilterField('direction_id', 'Направление', '/directions'),
      selectFilterField('status_id', 'Статус', '/sample_statuses'),
      selectFilterField('protocol_id', 'Протокол', '/protocols'),
      booleanFilterField('is_urgent', 'Срочно'),
      booleanFilterField('is_done', 'Готов'),
      dateFilterField('sampled_at', 'Отобран'),
      dateFilterField('received_at', 'Получен'),
      dateFilterField('completed_at', 'Завершён'),
      dateFilterField('deadline', 'Срок')
    ],
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'name', header: 'Название', sortable: true, filter: { type: 'text', placeholder: 'Название' } },
      { field: 'alternate_name', header: 'Альтернативное имя', sortable: true, filter: { type: 'text', placeholder: 'Альтернативное имя' } },
      { field: 'sample_type.name', header: 'Тип образца', filter: { type: 'text', placeholder: 'Тип образца' } },
      { field: 'direction.name', header: 'Направление', filter: { type: 'text', placeholder: 'Направление' } },
      { field: 'status.name', header: 'Статус', filter: { type: 'text', placeholder: 'Статус' } },
      {
        field: 'is_urgent',
        header: 'Срочно',
        sortable: true,
        filter: {
          type: 'select',
          options: [
            ...yesNoOptions
          ]
        }
      },
      {
        field: 'is_done',
        header: 'Готов',
        sortable: true,
        filter: {
          type: 'select',
          options: [
            ...yesNoOptions
          ]
        }
      },
      { field: 'received_at', header: 'Получен', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'month_no', label: 'Месяц', type: 'number', layout: { span: 4 } },
      { key: 'name', label: 'Название', required: true, layout: { span: 4 } },
      { key: 'alternate_name', label: 'Альтернативное имя', layout: { span: 4 } },
      { key: 'mass', label: 'Масса' },
      { key: 'target_description', label: 'Описание цели', type: 'textarea' },
      { key: 'comment', label: 'Комментарий', type: 'textarea' },
      { key: 'section', label: 'Раздел', layout: { span: 4 } },
      { key: 'delivery', label: 'Доставка', layout: { span: 4 } },
      { key: 'nomenclature_code', label: 'Код номенклатуры', layout: { span: 4 } },
      { key: 'batch_code', label: 'Код партии', layout: { span: 4 } },
      { key: 'supplier', label: 'Поставщик', layout: { span: 4 } },
      { key: 'is_urgent', label: 'Срочно', type: 'boolean', layout: { span: 6 } },
      { key: 'is_done', label: 'Готов', type: 'boolean', layout: { span: 6 } },
      { key: 'sample_type_id', label: 'Тип образца', type: 'select', source: '/sample_types', layout: { span: 4 } },
      { key: 'direction_id', label: 'Направление', type: 'select', source: '/directions', layout: { span: 4 } },
      { key: 'protocol_id', label: 'Протокол', type: 'select', source: '/protocols', layout: { span: 4 } },
      { key: 'sampled_at', label: 'Отобран', type: 'date', layout: { span: 4 } },
      { key: 'received_at', label: 'Получен', type: 'date', layout: { span: 4 } },
      { key: 'completed_at', label: 'Завершён', type: 'date', layout: { span: 4 } }
    ]
  },
  objects: {
    resource: 'objects',
    title: 'Объекты',
    description: 'Справочник объектов исследований.',
    endpoint: '/objects',
    include: 'branch',
    presetKey: 'objects',
    pageId: 'objects',
    initialFilters: {
      global: textFilter(),
      code: textFilter(),
      name: textFilter(),
      full_name: textFilter(),
      address: textFilter(),
      'branch.name': textFilter(),
      updated_at: dateFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'code', header: 'Код', sortable: true, filter: { type: 'text', placeholder: 'Код' } },
      { field: 'name', header: 'Название', sortable: true, filter: { type: 'text', placeholder: 'Название' } },
      { field: 'full_name', header: 'Полное название', sortable: true, filter: { type: 'text', placeholder: 'Полное название' } },
      { field: 'address', header: 'Адрес', sortable: true, filter: { type: 'text', placeholder: 'Адрес' } },
      { field: 'branch.name', header: 'Филиал', sortable: true, filter: { type: 'text', placeholder: 'Филиал' } },
      { field: 'updated_at', header: 'Обновлено', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'code', label: 'Код', required: true },
      { key: 'name', label: 'Название', required: true },
      { key: 'full_name', label: 'Полное название' },
      { key: 'address', label: 'Адрес' },
      { key: 'branch_id', label: 'Филиал', type: 'select', source: '/branches' }
    ]
  },
  branches: {
    resource: 'branches',
    title: 'Филиалы',
    description: 'Справочник филиалов и площадок.',
    endpoint: '/branches',
    presetKey: 'branches',
    pageId: 'branches',
    initialFilters: {
      global: textFilter(),
      name: textFilter(),
      code: textFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'name', header: 'Название', sortable: true, filter: { type: 'text', placeholder: 'Название' } },
      { field: 'code', header: 'Код', sortable: true, filter: { type: 'text', placeholder: 'Код' } }
    ],
    fields: [
      { key: 'name', label: 'Название', required: true },
      { key: 'code', label: 'Код' }
    ]
  },
  'direction-statuses': {
    resource: 'statuses',
    title: 'Статусы направлений',
    description: 'Статусы жизненного цикла направлений.',
    endpoint: '/direction_statuses',
    presetKey: 'direction-statuses',
    pageId: 'direction-statuses',
    initialFilters: {
      global: textFilter(),
      code: textFilter(),
      name: textFilter(),
      updated_at: dateFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'code', header: 'Код', sortable: true, filter: { type: 'text', placeholder: 'Код' } },
      { field: 'name', header: 'Название', sortable: true, filter: { type: 'text', placeholder: 'Название' } },
      { field: 'updated_at', header: 'Обновлено', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'name', label: 'Название', required: true }
    ]
  },
  'sample-statuses': {
    resource: 'statuses',
    title: 'Статусы образцов',
    description: 'Статусы приёмки, работы и закрытия образцов.',
    endpoint: '/sample_statuses',
    presetKey: 'sample-statuses',
    pageId: 'sample-statuses',
    initialFilters: {
      global: textFilter(),
      code: textFilter(),
      name: textFilter(),
      updated_at: dateFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'code', header: 'Код', sortable: true, filter: { type: 'text', placeholder: 'Код' } },
      { field: 'name', header: 'Название', sortable: true, filter: { type: 'text', placeholder: 'Название' } },
      { field: 'updated_at', header: 'Обновлено', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'name', label: 'Название', required: true }
    ]
  },
  'research-statuses': {
    resource: 'statuses',
    title: 'Статусы исследований',
    description: 'Статусы лабораторных исследований.',
    endpoint: '/research_statuses',
    presetKey: 'research-statuses',
    pageId: 'research-statuses',
    initialFilters: {
      global: textFilter(),
      code: textFilter(),
      name: textFilter(),
      updated_at: dateFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'code', header: 'Код', sortable: true, filter: { type: 'text', placeholder: 'Код' } },
      { field: 'name', header: 'Название', sortable: true, filter: { type: 'text', placeholder: 'Название' } },
      { field: 'updated_at', header: 'Обновлено', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'name', label: 'Название', required: true }
    ]
  },
  'test-statuses': {
    resource: 'statuses',
    title: 'Статусы тестов',
    description: 'Статусы отдельных лабораторных тестов.',
    endpoint: '/test_statuses',
    presetKey: 'test-statuses',
    pageId: 'test-statuses',
    initialFilters: {
      global: textFilter(),
      code: textFilter(),
      name: textFilter(),
      updated_at: dateFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'code', header: 'Код', sortable: true, filter: { type: 'text', placeholder: 'Код' } },
      { field: 'name', header: 'Название', sortable: true, filter: { type: 'text', placeholder: 'Название' } },
      { field: 'updated_at', header: 'Обновлено', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'name', label: 'Название', required: true }
    ]
  },
  doctors: {
    resource: 'doctors',
    title: 'Врачи',
    description: 'Справочник врачей и направителей.',
    endpoint: '/doctors',
    presetKey: 'doctors',
    pageId: 'doctors',
    initialFilters: {
      global: textFilter(),
      first_name: textFilter(),
      last_name: textFilter(),
      patronymic: textFilter(),
      updated_at: dateFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'first_name', header: 'Имя', sortable: true, filter: { type: 'text', placeholder: 'Имя' } },
      {
        field: 'last_name',
        header: 'Фамилия / Отчество',
        sortable: true,
        filter: { type: 'text', placeholder: 'Фамилия / Отчество' },
        body: (row: Record<string, unknown>) => [row.last_name, row.patronymic].filter(Boolean).join(' ') || '-'
      },
      { field: 'updated_at', header: 'Обновлено', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'first_name', label: 'Имя', required: true },
      { key: 'last_name', label: 'Фамилия' },
      { key: 'patronymic', label: 'Отчество' }
    ]
  },
  labs: {
    resource: 'labs',
    title: 'Лаборатории',
    description: 'Подразделения и лабораторные отделы.',
    endpoint: '/labs',
    include: 'branch',
    presetKey: 'labs',
    pageId: 'labs',
    initialFilters: {
      global: textFilter(),
      code: textFilter(),
      name: textFilter(),
      full_name: textFilter(),
      'branch.name': textFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'code', header: 'Код', sortable: true, filter: { type: 'text', placeholder: 'Код' } },
      { field: 'name', header: 'Название', sortable: true, filter: { type: 'text', placeholder: 'Название' } },
      { field: 'full_name', header: 'Полное название', sortable: true, filter: { type: 'text', placeholder: 'Полное название' } },
      { field: 'branch.name', header: 'Филиал', sortable: true, filter: { type: 'text', placeholder: 'Филиал' } }
    ],
    fields: [
      { key: 'code', label: 'Код' },
      { key: 'name', label: 'Название' },
      { key: 'full_name', label: 'Полное название' },
      { key: 'branch_id', label: 'Филиал', type: 'select', source: '/branches' }
    ]
  },
  'research-goals': {
    resource: 'research-goals',
    title: 'Цели исследований',
    description: 'Справочник целей и задач исследований.',
    endpoint: '/research_goals',
    include: 'lab',
    presetKey: 'research-goals',
    pageId: 'research-goals',
    initialFilters: {
      global: textFilter(),
      code: textFilter(),
      name: textFilter(),
      comment: textFilter(),
      'lab.name': textFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'code', header: 'Код', sortable: true, filter: { type: 'text', placeholder: 'Код' } },
      { field: 'name', header: 'Название', sortable: true, filter: { type: 'text', placeholder: 'Название' } },
      { field: 'comment', header: 'Комментарий', sortable: true, filter: { type: 'text', placeholder: 'Комментарий' } },
      { field: 'lab.name', header: 'Лаборатория', sortable: true, filter: { type: 'text', placeholder: 'Лаборатория' } }
    ],
    fields: [
      { key: 'code', label: 'Код', required: true },
      { key: 'name', label: 'Название', required: true },
      { key: 'comment', label: 'Комментарий', type: 'textarea' },
      { key: 'lab_id', label: 'Лаборатория', type: 'select', source: '/labs' }
    ]
  },
  'sample-types': {
    resource: 'sample-types',
    title: 'Типы образцов',
    description: 'Справочник типов образцов.',
    endpoint: '/sample_types',
    presetKey: 'sample-types',
    pageId: 'sample-types',
    initialFilters: {
      global: textFilter(),
      code: textFilter(),
      name: textFilter(),
      updated_at: dateFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'code', header: 'Код', sortable: true, filter: { type: 'text', placeholder: 'Код' } },
      { field: 'name', header: 'Название', sortable: true, filter: { type: 'text', placeholder: 'Название' } },
      { field: 'updated_at', header: 'Обновлено', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'code', label: 'Код' },
      { key: 'name', label: 'Название', required: true }
    ]
  },
  indicators: {
    resource: 'indicators',
    title: 'Показатели',
    description: 'Лабораторные показатели и их нормы.',
    endpoint: '/indicators',
    include: 'lab,sample_type',
    presetKey: 'indicators',
    pageId: 'indicators',
    initialFilters: {
      global: textFilter(),
      name: textFilter(),
      unit: textFilter(),
      'lab.name': textFilter(),
      'sample_type.name': textFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'name', header: 'Название', sortable: true, filter: { type: 'text', placeholder: 'Название' } },
      { field: 'unit', header: 'Единица', sortable: true, filter: { type: 'text', placeholder: 'Единица' } },
      { field: 'lab.name', header: 'Лаборатория', sortable: true, filter: { type: 'text', placeholder: 'Лаборатория' } },
      { field: 'sample_type.name', header: 'Тип образца', sortable: true, filter: { type: 'text', placeholder: 'Тип образца' } }
    ],
    fields: [
      { key: 'name', label: 'Название', required: true },
      { key: 'unit', label: 'Единица измерения' },
      { key: 'norm_text', label: 'Норма (текст)', type: 'textarea' },
      { key: 'norm_value', label: 'Норма (значение)' },
      { key: 'default_text', label: 'Текст по умолчанию', type: 'textarea' },
      { key: 'comment', label: 'Комментарий', type: 'textarea' },
      { key: 'lab_id', label: 'Лаборатория', type: 'select', source: '/labs' },
      { key: 'sample_type_id', label: 'Тип образца', type: 'select', source: '/sample_types' }
    ]
  },
  'protocol-types': {
    resource: 'protocol-types',
    title: 'Типы протоколов',
    description: 'Справочник типов протоколов.',
    endpoint: '/protocol_types',
    presetKey: 'protocol-types',
    pageId: 'protocol-types',
    initialFilters: {
      global: textFilter(),
      code: textFilter(),
      name: textFilter(),
      updated_at: dateFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'code', header: 'Код', sortable: true, filter: { type: 'text', placeholder: 'Код' } },
      { field: 'name', header: 'Название', sortable: true, filter: { type: 'text', placeholder: 'Название' } },
      { field: 'updated_at', header: 'Обновлено', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'code', label: 'Код' },
      { key: 'name', label: 'Название', required: true }
    ]
  },
  conclusions: {
    resource: 'conclusions',
    title: 'Заключения',
    description: 'Справочник предопределённых формулировок заключений.',
    endpoint: '/conclusions',
    include: undefined,
    presetKey: 'conclusions',
    pageId: 'conclusions',
    initialFilters: {
      global: textFilter(),
      code: textFilter(),
      name: textFilter(),
      updated_at: dateFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'code', header: 'Код', sortable: true, filter: { type: 'text', placeholder: 'Код' } },
      { field: 'name', header: 'Название', sortable: true, filter: { type: 'text', placeholder: 'Название' } },
      { field: 'text_singular', header: 'Ед. число', sortable: true, filter: { type: 'text', placeholder: 'Ед. число' } },
      { field: 'text_plural', header: 'Мн. число', sortable: true, filter: { type: 'text', placeholder: 'Мн. число' } },
      { field: 'updated_at', header: 'Обновлено', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'code', label: 'Код', required: true },
      { key: 'name', label: 'Название', required: true },
      { key: 'text_singular', label: 'Текст в единственном числе', type: 'textarea', required: true },
      { key: 'text_plural', label: 'Текст во множественном числе', type: 'textarea', required: true },
      { key: 'comment', label: 'Комментарий', type: 'textarea' }
    ]
  },
  protocols: {
    resource: 'protocols',
    title: 'Протоколы',
    description: 'Реестр лабораторных протоколов.',
    endpoint: '/protocols',
    include: 'protocol_type,conclusion',
    presetKey: 'protocols',
    pageId: 'protocols',
    initialFilters: {
      global: textFilter(),
      year_no: textFilter(),
      copies: textFilter(),
      'protocol_type.name': textFilter(),
      'conclusion.name': textFilter(),
      is_signed: multiFilter(),
      issued_at: dateFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'year_no', header: 'Год / номер', sortable: true, filter: { type: 'text', placeholder: 'Год / номер' } },
      { field: 'copies', header: 'Копии', sortable: true, filter: { type: 'text', placeholder: 'Копии' } },
      { field: 'protocol_type.name', header: 'Тип протокола', sortable: true, filter: { type: 'text', placeholder: 'Тип протокола' } },
      { field: 'conclusion.name', header: 'Заключение', sortable: true, filter: { type: 'text', placeholder: 'Заключение' } },
      {
        field: 'is_signed',
        header: 'Подписан',
        sortable: true,
        filter: {
          type: 'select',
          options: [
            { label: 'Да', value: true },
            { label: 'Нет', value: false }
          ]
        }
      },
      { field: 'issued_at', header: 'Дата выдачи', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'year_no', label: 'Год / номер', type: 'number', required: true, layout: { span: 4 } },
      { key: 'copies', label: 'Копии', type: 'number', layout: { span: 4 } },
      { key: 'is_signed', label: 'Подписан', type: 'boolean', layout: { span: 4 } },
      { key: 'protocol_copy_name', label: 'Название копии протокола' },
      { key: 'excerpt_copy_name', label: 'Название выписки' },
      { key: 'protocol_type_id', label: 'Тип протокола', type: 'select', source: '/protocol_types', layout: { span: 4 } },
      { key: 'conclusion_id', label: 'Заключение', type: 'select', source: '/conclusions', layout: { span: 4 } },
      { key: 'issued_at', label: 'Дата выдачи', type: 'date', layout: { span: 4 } }
    ]
  },
  research: {
    resource: 'research',
    title: 'Исследования',
    description: 'Исследования по образцам с целями, лабораториями и статусами.',
    endpoint: '/research',
    include: 'sample,research_goal,lab,status',
    presetKey: 'research',
    pageId: 'research',
    initialFilters: {
      global: textFilter(),
      sample_id: textFilter(),
      research_goal_id: textFilter(),
      lab_id: textFilter(),
      status_id: textFilter(),
      comment: textFilter(),
      recommendation: textFilter(),
      created_at: dateFilter(),
      received_at: dateFilter(),
      completed_at: dateFilter()
    },
    filterFields: [
      selectFilterField('sample_id', 'Образец', '/samples'),
      selectFilterField('research_goal_id', 'Цель исследования', '/research_goals'),
      selectFilterField('lab_id', 'Лаборатория', '/labs'),
      selectFilterField('status_id', 'Статус', '/research_statuses'),
      dateFilterField('received_at', 'Получен'),
      dateFilterField('completed_at', 'Завершён')
    ],
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'sample.name', header: 'Образец', sortable: true, filter: { type: 'text', placeholder: 'Образец' } },
      { field: 'research_goal.name', header: 'Цель исследования', sortable: true, filter: { type: 'text', placeholder: 'Цель исследования' } },
      { field: 'lab.name', header: 'Лаборатория', sortable: true, filter: { type: 'text', placeholder: 'Лаборатория' } },
      { field: 'status.name', header: 'Статус', sortable: true, filter: { type: 'text', placeholder: 'Статус' } },
      { field: 'comment', header: 'Комментарий', sortable: true, filter: { type: 'text', placeholder: 'Комментарий' } },
      { field: 'recommendation', header: 'Рекомендация', sortable: true, filter: { type: 'text', placeholder: 'Рекомендация' } },
      { field: 'created_at', header: 'Создано', sortable: true, filter: { type: 'dateRange' } },
      { field: 'received_at', header: 'Получен', sortable: true, filter: { type: 'dateRange' } },
      { field: 'completed_at', header: 'Завершён', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'sample_id', label: 'Образец', type: 'select', source: '/samples', required: true, layout: { span: 6 } },
      { key: 'research_goal_id', label: 'Цель исследования', type: 'select', source: '/research_goals', required: true, layout: { span: 6 } },
      { key: 'lab_id', label: 'Лаборатория', type: 'select', source: '/labs', layout: { span: 6 } },
      { key: 'comment', label: 'Комментарий', type: 'textarea' },
      { key: 'recommendation', label: 'Рекомендация', type: 'textarea' },
      { key: 'received_at', label: 'Получен', type: 'date', layout: { span: 6 } },
      { key: 'completed_at', label: 'Завершён', type: 'date', layout: { span: 6 } }
    ]
  },
  tests: {
    resource: 'tests',
    title: 'Тесты',
    description: 'Результаты отдельных тестов и показателей.',
    endpoint: '/tests',
    include: 'research,indicator,status',
    presetKey: 'tests',
    pageId: 'tests',
    initialFilters: {
      global: textFilter(),
      research_id: textFilter(),
      indicator_id: textFilter(),
      status_id: textFilter(),
      value: textFilter(),
      norm: textFilter(),
      comment: textFilter(),
      is_active: multiFilter()
    },
    filterFields: [
      selectFilterField('research_id', 'Исследование', '/research'),
      selectFilterField('indicator_id', 'Показатель', '/indicators'),
      selectFilterField('status_id', 'Статус', '/test_statuses'),
      textFilterField('value', 'Значение'),
      textFilterField('norm', 'Норма'),
      textFilterField('comment', 'Комментарий'),
      booleanFilterField('is_active', 'Активен')
    ],
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'research.name', header: 'Исследование', sortable: true, filter: { type: 'text', placeholder: 'Исследование' } },
      { field: 'indicator.name', header: 'Показатель', sortable: true, filter: { type: 'text', placeholder: 'Показатель' } },
      { field: 'status.name', header: 'Статус', sortable: true, filter: { type: 'text', placeholder: 'Статус' } },
      { field: 'value', header: 'Значение', sortable: true, filter: { type: 'text', placeholder: 'Значение' } },
      {
        field: 'is_active',
        header: 'Активен',
        sortable: true,
        filter: {
          type: 'select',
          options: [
            ...yesNoOptions
          ]
        }
      },
      { field: 'updated_at', header: 'Обновлено', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'research_id', label: 'Исследование', type: 'select', source: '/research', required: true },
      { key: 'indicator_id', label: 'Показатель', type: 'select', source: '/indicators' },
      { key: 'value', label: 'Значение' },
      { key: 'norm', label: 'Норма' },
      { key: 'comment', label: 'Комментарий', type: 'textarea' },
      { key: 'is_active', label: 'Активен', type: 'boolean' }
    ]
  },
  'sample-targets': {
    resource: 'sample-targets',
    title: 'Цели образцов',
    description: 'Связка образцов и целей исследований.',
    endpoint: '/sample_targets',
    include: 'sample,research_goal,status',
    presetKey: 'sample-targets',
    pageId: 'sample-targets',
    initialFilters: {
      global: textFilter(),
      'sample.name': textFilter(),
      'research_goal.name': textFilter(),
      'status.name': textFilter(),
      updated_at: dateFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'sample.name', header: 'Образец', sortable: true, filter: { type: 'text', placeholder: 'Образец' } },
      { field: 'research_goal.name', header: 'Цель исследования', sortable: true, filter: { type: 'text', placeholder: 'Цель исследования' } },
      { field: 'status.name', header: 'Статус', sortable: true, filter: { type: 'text', placeholder: 'Статус' } },
      { field: 'updated_at', header: 'Обновлено', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'sample_id', label: 'Образец', type: 'select', source: '/samples', required: true },
      { key: 'research_goal_id', label: 'Цель исследования', type: 'select', source: '/research_goals', required: true },
      { key: 'status_id', label: 'Статус', type: 'select', source: '/statuses' }
    ]
  }
}
