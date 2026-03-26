import type { CrudModuleConfig } from '@/shared/pages/CrudModulePage.vue'

const textFilter = () => ({ value: '', matchMode: 'contains' })
const dateFilter = () => ({ value: [null, null], matchMode: 'between' })
const multiFilter = () => ({ value: [], matchMode: 'in' })

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
      'doctor.name': textFilter(),
      'object.name': textFilter(),
      'status.name': textFilter(),
      sampled_at: dateFilter(),
      received_at: dateFilter(),
      completed_at: dateFilter(),
      is_done: multiFilter(),
      is_urgent: multiFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'year_no', header: 'Год', sortable: true, filter: { type: 'text', placeholder: 'Год' } },
      { field: 'base_no', header: 'Номер', sortable: true, filter: { type: 'text', placeholder: 'Номер' } },
      { field: 'doctor.name', header: 'Врач', sortable: true, filter: { type: 'text', placeholder: 'Врач' } },
      { field: 'object.name', header: 'Объект', sortable: true, filter: { type: 'text', placeholder: 'Объект' } },
      { field: 'status.name', header: 'Статус', sortable: true, filter: { type: 'text', placeholder: 'Статус' } },
      { field: 'sampled_at', header: 'Отбор', sortable: true, filter: { type: 'dateRange' } },
      { field: 'received_at', header: 'Получение', sortable: true, filter: { type: 'dateRange' } },
      { field: 'completed_at', header: 'Завершение', sortable: true, filter: { type: 'dateRange' } },
      {
        field: 'is_done',
        header: 'Завершено',
        sortable: true,
        filter: {
          type: 'multiSelect',
          options: [
            { label: 'Да', value: true },
            { label: 'Нет', value: false }
          ]
        }
      },
      {
        field: 'is_urgent',
        header: 'Срочно',
        sortable: true,
        filter: {
          type: 'multiSelect',
          options: [
            { label: 'Да', value: true },
            { label: 'Нет', value: false }
          ]
        }
      }
    ],
    fields: [
      { key: 'year_no', label: 'Год', type: 'number', required: true },
      { key: 'base_no', label: 'Номер', type: 'number' },
      { key: 'is_done', label: 'Завершено', type: 'boolean' },
      { key: 'is_urgent', label: 'Срочно', type: 'boolean' },
      { key: 'doctor_id', label: 'Врач', type: 'select', source: '/doctors' },
      { key: 'object_id', label: 'Объект', type: 'select', source: '/objects' },
      { key: 'status_id', label: 'Статус', type: 'select', source: '/statuses' },
      { key: 'sampled_at', label: 'Отбор', type: 'date' },
      { key: 'received_at', label: 'Получение', type: 'date' },
      { key: 'completed_at', label: 'Завершение', type: 'date' }
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
      name: textFilter(),
      alternate_name: textFilter(),
      'sample_type.name': textFilter(),
      'direction.name': textFilter(),
      'status.name': textFilter(),
      is_urgent: multiFilter(),
      is_done: multiFilter(),
      received_at: dateFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'name', header: 'Название', sortable: true, filter: { type: 'text', placeholder: 'Название' } },
      { field: 'alternate_name', header: 'Альтернативное имя', sortable: true, filter: { type: 'text', placeholder: 'Альтернативное имя' } },
      { field: 'sample_type.name', header: 'Тип образца', sortable: true, filter: { type: 'text', placeholder: 'Тип образца' } },
      { field: 'direction.name', header: 'Направление', sortable: true, filter: { type: 'text', placeholder: 'Направление' } },
      { field: 'status.name', header: 'Статус', sortable: true, filter: { type: 'text', placeholder: 'Статус' } },
      {
        field: 'is_urgent',
        header: 'Срочно',
        sortable: true,
        filter: {
          type: 'multiSelect',
          options: [
            { label: 'Да', value: true },
            { label: 'Нет', value: false }
          ]
        }
      },
      {
        field: 'is_done',
        header: 'Готов',
        sortable: true,
        filter: {
          type: 'multiSelect',
          options: [
            { label: 'Да', value: true },
            { label: 'Нет', value: false }
          ]
        }
      },
      { field: 'received_at', header: 'Получен', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'month_no', label: 'Месяц', type: 'number' },
      { key: 'name', label: 'Название', required: true },
      { key: 'alternate_name', label: 'Альтернативное имя' },
      { key: 'mass', label: 'Масса' },
      { key: 'target_description', label: 'Описание цели', type: 'textarea' },
      { key: 'comment', label: 'Комментарий', type: 'textarea' },
      { key: 'section', label: 'Раздел' },
      { key: 'delivery', label: 'Доставка' },
      { key: 'nomenclature_code', label: 'Код номенклатуры' },
      { key: 'batch_code', label: 'Код партии' },
      { key: 'supplier', label: 'Поставщик' },
      { key: 'is_urgent', label: 'Срочно', type: 'boolean' },
      { key: 'is_done', label: 'Готов', type: 'boolean' },
      { key: 'sample_type_id', label: 'Тип образца', type: 'select', source: '/sample_types' },
      { key: 'status_id', label: 'Статус', type: 'select', source: '/statuses' },
      { key: 'direction_id', label: 'Направление', type: 'select', source: '/directions' },
      { key: 'protocol_id', label: 'Протокол', type: 'select', source: '/protocols' },
      { key: 'sampled_at', label: 'Отобран', type: 'date' },
      { key: 'received_at', label: 'Получен', type: 'date' },
      { key: 'completed_at', label: 'Завершён', type: 'date' }
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
  statuses: {
    resource: 'statuses',
    title: 'Статусы',
    description: 'Статусы для направлений, результатов и связанных сущностей.',
    endpoint: '/statuses',
    presetKey: 'statuses',
    pageId: 'statuses',
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
        body: (row) => [row.last_name, row.patronymic].filter(Boolean).join(' ') || '-'
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
    description: 'Заключения и их статусы.',
    endpoint: '/conclusions',
    include: 'conclusion_status',
    presetKey: 'conclusions',
    pageId: 'conclusions',
    initialFilters: {
      global: textFilter(),
      comment: textFilter(),
      'conclusion_status.name': textFilter(),
      updated_at: dateFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'comment', header: 'Комментарий', sortable: true, filter: { type: 'text', placeholder: 'Комментарий' } },
      { field: 'conclusion_status.name', header: 'Статус заключения', sortable: true, filter: { type: 'text', placeholder: 'Статус' } },
      { field: 'updated_at', header: 'Обновлено', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'comment', label: 'Комментарий', type: 'textarea' },
      { key: 'conclusion_status_id', label: 'Статус заключения', type: 'select', source: '/conclusion_statuses', required: true }
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
          type: 'multiSelect',
          options: [
            { label: 'Да', value: true },
            { label: 'Нет', value: false }
          ]
        }
      },
      { field: 'issued_at', header: 'Дата выдачи', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'year_no', label: 'Год / номер', type: 'number', required: true },
      { key: 'copies', label: 'Копии', type: 'number' },
      { key: 'is_signed', label: 'Подписан', type: 'boolean' },
      { key: 'protocol_copy_name', label: 'Название копии протокола' },
      { key: 'excerpt_copy_name', label: 'Название выписки' },
      { key: 'protocol_type_id', label: 'Тип протокола', type: 'select', source: '/protocol_types' },
      { key: 'conclusion_id', label: 'Заключение', type: 'select', source: '/conclusions' },
      { key: 'issued_at', label: 'Дата выдачи', type: 'date' }
    ]
  },
  results: {
    resource: 'results',
    title: 'Результаты',
    description: 'Результаты исследований по образцам.',
    endpoint: '/results',
    include: 'sample,lab,status',
    presetKey: 'results',
    pageId: 'results',
    initialFilters: {
      global: textFilter(),
      'sample.name': textFilter(),
      'lab.name': textFilter(),
      'status.name': textFilter(),
      is_done: multiFilter(),
      received_at: dateFilter(),
      completed_at: dateFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'sample.name', header: 'Образец', sortable: true, filter: { type: 'text', placeholder: 'Образец' } },
      { field: 'lab.name', header: 'Лаборатория', sortable: true, filter: { type: 'text', placeholder: 'Лаборатория' } },
      { field: 'status.name', header: 'Статус', sortable: true, filter: { type: 'text', placeholder: 'Статус' } },
      {
        field: 'is_done',
        header: 'Завершён',
        sortable: true,
        filter: {
          type: 'multiSelect',
          options: [
            { label: 'Да', value: true },
            { label: 'Нет', value: false }
          ]
        }
      },
      { field: 'received_at', header: 'Получен', sortable: true, filter: { type: 'dateRange' } },
      { field: 'completed_at', header: 'Завершён', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'sample_id', label: 'Образец', type: 'select', source: '/samples', required: true },
      { key: 'lab_id', label: 'Лаборатория', type: 'select', source: '/labs' },
      { key: 'status_id', label: 'Статус', type: 'select', source: '/statuses' },
      { key: 'is_done', label: 'Завершён', type: 'boolean' },
      { key: 'comment', label: 'Комментарий', type: 'textarea' },
      { key: 'recommendation', label: 'Рекомендация', type: 'textarea' },
      { key: 'received_at', label: 'Получен', type: 'date' },
      { key: 'completed_at', label: 'Завершён', type: 'date' }
    ]
  },
  tests: {
    resource: 'tests',
    title: 'Тесты',
    description: 'Результаты отдельных тестов и показателей.',
    endpoint: '/tests',
    include: 'result,indicator,status',
    presetKey: 'tests',
    pageId: 'tests',
    initialFilters: {
      global: textFilter(),
      'result.name': textFilter(),
      'indicator.name': textFilter(),
      'status.name': textFilter(),
      value: textFilter(),
      is_active: multiFilter(),
      updated_at: dateFilter()
    },
    columns: [
      { field: 'id', header: 'ID', sortable: true },
      { field: 'result.name', header: 'Результат', sortable: true, filter: { type: 'text', placeholder: 'Результат' } },
      { field: 'indicator.name', header: 'Показатель', sortable: true, filter: { type: 'text', placeholder: 'Показатель' } },
      { field: 'status.name', header: 'Статус', sortable: true, filter: { type: 'text', placeholder: 'Статус' } },
      { field: 'value', header: 'Значение', sortable: true, filter: { type: 'text', placeholder: 'Значение' } },
      {
        field: 'is_active',
        header: 'Активен',
        sortable: true,
        filter: {
          type: 'multiSelect',
          options: [
            { label: 'Да', value: true },
            { label: 'Нет', value: false }
          ]
        }
      },
      { field: 'updated_at', header: 'Обновлено', sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'result_id', label: 'Результат', type: 'select', source: '/results', required: true },
      { key: 'indicator_id', label: 'Показатель', type: 'select', source: '/indicators' },
      { key: 'status_id', label: 'Статус', type: 'select', source: '/statuses' },
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
