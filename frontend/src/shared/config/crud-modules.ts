import type { CrudModuleConfig } from '@/shared/types/crud'
import type { TableFilterField } from '@/shared/types/table'
import {
  DIRECTION_STATUS_FLOW,
  SAMPLE_STATUS_FLOW,
  SAMPLE_STATUS_REJECTED
} from '@/shared/domain/status-timeline'
import { i18n } from '@/shared/i18n'

const t = (key: string, params?: Record<string, unknown>) =>
  i18n.global.t(key, params ?? {}).toString()

const textFilter = () => ({ value: '', matchMode: 'contains' })
const dateFilter = () => ({ value: [null, null], matchMode: 'between' })
const multiFilter = () => ({ value: '', matchMode: 'equals' })
// Multi-select filter: value is an array of selected ids (IN-list on the API).
const multiSelectFilter = () => ({ value: [] as string[], matchMode: 'in' })
const currentYear = new Date().getFullYear()
const directionYearOptions = Array.from(
  { length: currentYear - 2000 + 1 },
  (_, index) => {
    const year = 2000 + index
    return { label: String(year), value: year }
  }
).reverse()
// Год направления при редактировании — только текущий год и 5 лет назад.
const directionEditYearOptions = Array.from(
  { length: 6 },
  (_, index) => {
    const year = currentYear - index
    return { label: String(year), value: year }
  }
)
const yesNoOptions = () => [
  { label: t('access.yes'), value: true },
  { label: t('access.no'), value: false }
]
const subscriptionEntityTypeOptions = () => [
  { label: t('nav.directions'), value: 'directions' },
  { label: t('nav.samples'), value: 'samples' }
]
// Статус для правила подписки — код должен соответствовать выбранному типу
// сущности (проверяется на бэкенде); подписи с префиксом помогают не перепутать.
const subscriptionStatusCodeOptions = () => [
  ...DIRECTION_STATUS_FLOW().map((step) => ({ label: `${t('nav.directions')}: ${step.name}`, value: step.code })),
  ...SAMPLE_STATUS_FLOW().map((step) => ({ label: `${t('nav.samples')}: ${step.name}`, value: step.code })),
  { label: `${t('nav.samples')}: ${SAMPLE_STATUS_REJECTED().name}`, value: SAMPLE_STATUS_REJECTED().code }
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
  filter: { type: 'select', options: yesNoOptions() }
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

const multiSelectFilterField = (
  field: string,
  header: string,
  source: string,
  placeholder = header
): TableFilterField => ({
  field,
  header,
  filter: { type: 'multiSelect', placeholder, source }
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
    title: t('nav.directions'),
    description: t('crudModules.directions.description'),
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
      status_id: multiSelectFilter(),
      sampled_at: dateFilter(),
      received_at: dateFilter(),
      completed_at: dateFilter(),
      is_done: multiFilter(),
      is_urgent: multiFilter()
    },
    filterFields: [
      {
        field: 'year_no',
        header: t('crudFields.year'),
        filter: { type: 'select', placeholder: t('crudFields.year'), options: directionYearOptions }
      },
      textFilterField('base_no', t('crudFields.number')),
      selectFilterField('doctor_id', t('crudFields.doctor'), '/doctors'),
      selectFilterField('object_id', t('crudFields.object'), '/objects'),
      multiSelectFilterField('status_id', t('common.status'), '/direction_statuses'),
      booleanFilterField('is_done', t('crudFields.completed')),
      booleanFilterField('is_urgent', t('crudFields.urgent')),
      dateFilterField('sampled_at', t('crudFields.sampling')),
      dateFilterField('received_at', t('crudFields.receiving')),
      dateFilterField('completed_at', t('crudFields.completion'))
    ],
    columns: [
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'base_no', header: t('crudFields.numberShort'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.number') } },
      {
        field: 'doctor.name',
        header: t('crudFields.doctor'),
        sortable: true,
        filter: { type: 'text', placeholder: t('crudFields.doctor') },
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
        header: t('crudFields.object'),
        sortable: true,
        width: '220px',
        wrap: true,
        filter: { type: 'text', placeholder: t('crudFields.object') },
        body: (row: Record<string, unknown>) => {
          const object = row.object as { code?: string | null, name?: string | null } | null | undefined
          if (!object) {
            return '-'
          }
          return object.name || object.code || '-'
        }
      },
      { field: 'status.name', header: t('common.status'), sortable: true, width: '150px', filter: { type: 'text', placeholder: t('common.status') } },
      { field: 'sampled_at', header: t('crudFields.sampling'), sortable: true, filter: { type: 'dateRange' } },
      { field: 'received_at', header: t('crudFields.receiving'), sortable: true, filter: { type: 'dateRange' } },
      { field: 'completed_at', header: t('crudFields.completion'), sortable: true, filter: { type: 'dateRange' } },
      {
        field: 'is_done',
        header: t('crudFields.completed'),
        sortable: true,
        filter: {
          type: 'select',
          options: [
            ...yesNoOptions()
          ]
        }
      },
      {
        field: 'is_urgent',
        header: t('crudFields.urgent'),
        sortable: true,
        filter: {
          type: 'select',
          options: [
            ...yesNoOptions()
          ]
        }
      }
    ],
    defaultHiddenColumns: ['sampled_at', 'is_done'],
    fields: [
      { key: 'year_no', label: t('crudFields.year'), type: 'select', required: true, options: directionEditYearOptions, layout: { span: 4 } },
      { key: 'base_no', label: t('crudFields.number'), type: 'number', layout: { span: 4 } },
      { key: 'is_urgent', label: t('crudFields.urgent'), type: 'boolean', layout: { span: 6 } },
      { key: 'doctor_id', label: t('crudFields.doctor'), type: 'select', source: '/doctors', layout: { span: 4 } },
      { key: 'object_id', label: t('crudFields.object'), type: 'select', source: '/objects', layout: { span: 4 } },
      { key: 'sampled_at', label: t('crudFields.sampling'), type: 'date', layout: { span: 4 } },
      { key: 'received_at', label: t('crudFields.receiving'), type: 'date', layout: { span: 4 } },
      { key: 'completed_at', label: t('crudFields.completion'), type: 'date', layout: { span: 4 }, editable: false }
    ]
  },
  samples: {
    resource: 'samples',
    title: t('nav.samples'),
    description: t('crudModules.samples.description'),
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
      status_id: multiSelectFilter(),
      protocol_id: textFilter(),
      is_urgent: multiFilter(),
      is_done: multiFilter(),
      sampled_at: dateFilter(),
      received_at: dateFilter(),
      completed_at: dateFilter(),
      deadline: dateFilter()
    },
    filterFields: [
      textFilterField('month_no', t('crudFields.month')),
      textFilterField('name', t('access.columns.name')),
      textFilterField('alternate_name', t('crudFields.alternateName')),
      textFilterField('nomenclature_code', t('crudFields.nomenclatureCode')),
      textFilterField('batch_code', t('crudFields.batchCode')),
      textFilterField('supplier', t('crudFields.supplier')),
      selectFilterField('sample_type_id', t('crudFields.sampleType'), '/sample_types'),
      selectFilterField('direction_id', t('crudFields.direction'), '/directions'),
      multiSelectFilterField('status_id', t('common.status'), '/sample_statuses'),
      selectFilterField('protocol_id', t('crudFields.protocol'), '/protocols'),
      booleanFilterField('is_urgent', t('crudFields.urgent')),
      booleanFilterField('is_done', t('crudFields.ready')),
      dateFilterField('sampled_at', t('crudFields.sampled')),
      dateFilterField('received_at', t('crudFields.received')),
      dateFilterField('completed_at', t('crudFields.completedM')),
      dateFilterField('deadline', t('crudFields.deadline'))
    ],
    columns: [
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'name', header: t('access.columns.name'), sortable: true, width: '220px', wrap: true, filter: { type: 'text', placeholder: t('access.columns.name') } },
      { field: 'alternate_name', header: t('crudFields.alternateName'), sortable: true, width: '220px', wrap: true, filter: { type: 'text', placeholder: t('crudFields.alternateName') } },
      { field: 'sample_type.name', header: t('crudFields.sampleType'), filter: { type: 'text', placeholder: t('crudFields.sampleType') } },
      { field: 'direction.name', header: t('crudFields.direction'), filter: { type: 'text', placeholder: t('crudFields.direction') } },
      { field: 'status.name', header: t('common.status'), width: '150px', filter: { type: 'text', placeholder: t('common.status') } },
      {
        field: 'is_urgent',
        header: t('crudFields.urgent'),
        sortable: true,
        filter: {
          type: 'select',
          options: [
            ...yesNoOptions()
          ]
        }
      },
      {
        field: 'is_done',
        header: t('crudFields.ready'),
        sortable: true,
        filter: {
          type: 'select',
          options: [
            ...yesNoOptions()
          ]
        }
      },
      { field: 'received_at', header: t('crudFields.received'), sortable: true, filter: { type: 'dateRange' } }
    ],
    // Бэкенд не отдаёт sample_type/direction вложенными объектами в списке
    // образцов (в отличие от status) — колонки резолвят название через
    // справочник, поэтому его нужно подгрузить сразу, а не только при
    // открытии панели фильтров.
    displayReferenceFields: ['sample_type_id', 'direction_id'],
    defaultHiddenColumns: ['is_urgent', 'alternate_name', 'is_done'],
    fields: [
      { key: 'month_no', label: t('crudFields.month'), type: 'number', layout: { span: 4 } },
      { key: 'name', label: t('access.columns.name'), required: true, layout: { span: 4 } },
      { key: 'alternate_name', label: t('crudFields.alternateName'), layout: { span: 4 } },
      { key: 'mass', label: t('directionWizard.mass') },
      { key: 'target_description', label: t('crudFields.targetDescription'), type: 'textarea' },
      { key: 'comment', label: t('workflowCommands.formFields.comment'), type: 'textarea' },
      { key: 'section', label: t('crudFields.section'), layout: { span: 4 } },
      { key: 'delivery', label: t('crudFields.delivery'), layout: { span: 4 } },
      { key: 'nomenclature_code', label: t('crudFields.nomenclatureCode'), layout: { span: 4 } },
      { key: 'batch_code', label: t('crudFields.batchCode'), layout: { span: 4 } },
      { key: 'supplier', label: t('crudFields.supplier'), layout: { span: 4 } },
      { key: 'is_urgent', label: t('crudFields.urgent'), type: 'boolean', layout: { span: 6 } },
      { key: 'is_done', label: t('crudFields.ready'), type: 'boolean', layout: { span: 6 } },
      { key: 'sample_type_id', label: t('crudFields.sampleType'), type: 'select', source: '/sample_types', layout: { span: 4 } },
      { key: 'direction_id', label: t('crudFields.direction'), type: 'select', source: '/directions', layout: { span: 4 } },
      { key: 'protocol_id', label: t('crudFields.protocol'), type: 'select', source: '/protocols', layout: { span: 4 } },
      { key: 'sampled_at', label: t('crudFields.sampled'), type: 'date', layout: { span: 4 } },
      { key: 'received_at', label: t('crudFields.received'), type: 'date', layout: { span: 4 } },
      { key: 'completed_at', label: t('crudFields.completedM'), type: 'date', layout: { span: 4 }, editable: false }
    ]
  },
  objects: {
    resource: 'objects',
    title: t('crudModules.objects.title'),
    description: t('crudModules.objects.description'),
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
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'code', header: t('access.columns.code'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.code') } },
      { field: 'name', header: t('access.columns.name'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.name') } },
      { field: 'full_name', header: t('crudFields.fullName'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.fullName') } },
      { field: 'address', header: t('crudFields.address'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.address') } },
      { field: 'branch.name', header: t('crudFields.branch'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.branch') } },
      { field: 'updated_at', header: t('crudFields.updated'), sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'code', label: t('access.columns.code'), required: true },
      { key: 'name', label: t('access.columns.name'), required: true },
      { key: 'full_name', label: t('crudFields.fullName') },
      { key: 'address', label: t('crudFields.address') },
      { key: 'branch_id', label: t('crudFields.branch'), type: 'select', source: '/branches' }
    ]
  },
  branches: {
    resource: 'branches',
    title: t('crudModules.branches.title'),
    description: t('crudModules.branches.description'),
    endpoint: '/branches',
    presetKey: 'branches',
    pageId: 'branches',
    initialFilters: {
      global: textFilter(),
      name: textFilter(),
      code: textFilter()
    },
    columns: [
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'name', header: t('access.columns.name'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.name') } },
      { field: 'code', header: t('access.columns.code'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.code') } }
    ],
    fields: [
      { key: 'name', label: t('access.columns.name'), required: true },
      { key: 'code', label: t('access.columns.code') }
    ]
  },
  'direction-statuses': {
    resource: 'statuses',
    title: t('dictionaries.directionsStatusesTitle'),
    description: t('dictionaries.directionsStatusesDescription'),
    endpoint: '/direction_statuses',
    presetKey: 'direction-statuses',
    pageId: 'direction-statuses',
    initialFilters: {
      global: textFilter(),
      code: textFilter(),
      updated_at: dateFilter()
    },
    columns: [
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'code', header: t('access.columns.code'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.code') } },
      { field: 'label', header: t('access.columns.name'), sortable: false },
      { field: 'updated_at', header: t('crudFields.updated'), sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'color', label: t('crudFields.color'), type: 'color', required: true }
    ]
  },
  'sample-statuses': {
    resource: 'statuses',
    title: t('dictionaries.samplesStatusesTitle'),
    description: t('dictionaries.samplesStatusesDescription'),
    endpoint: '/sample_statuses',
    presetKey: 'sample-statuses',
    pageId: 'sample-statuses',
    initialFilters: {
      global: textFilter(),
      code: textFilter(),
      updated_at: dateFilter()
    },
    columns: [
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'code', header: t('access.columns.code'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.code') } },
      { field: 'label', header: t('access.columns.name'), sortable: false },
      { field: 'updated_at', header: t('crudFields.updated'), sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'color', label: t('crudFields.color'), type: 'color', required: true }
    ]
  },
  'research-statuses': {
    resource: 'statuses',
    title: t('dictionaries.researchStatusesTitle'),
    description: t('crudModules.researchStatuses.description'),
    endpoint: '/research_statuses',
    presetKey: 'research-statuses',
    pageId: 'research-statuses',
    initialFilters: {
      global: textFilter(),
      code: textFilter(),
      updated_at: dateFilter()
    },
    columns: [
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'code', header: t('access.columns.code'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.code') } },
      { field: 'label', header: t('access.columns.name'), sortable: false },
      { field: 'updated_at', header: t('crudFields.updated'), sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'color', label: t('crudFields.color'), type: 'color', required: true }
    ]
  },
  'test-statuses': {
    resource: 'statuses',
    title: t('dictionaries.testsStatusesTitle'),
    description: t('dictionaries.testsStatusesDescription'),
    endpoint: '/test_statuses',
    presetKey: 'test-statuses',
    pageId: 'test-statuses',
    initialFilters: {
      global: textFilter(),
      code: textFilter(),
      updated_at: dateFilter()
    },
    columns: [
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'code', header: t('access.columns.code'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.code') } },
      { field: 'label', header: t('access.columns.name'), sortable: false },
      { field: 'updated_at', header: t('crudFields.updated'), sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'color', label: t('crudFields.color'), type: 'color', required: true }
    ]
  },
  doctors: {
    resource: 'doctors',
    title: t('crudModules.doctors.title'),
    description: t('crudModules.doctors.description'),
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
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'first_name', header: t('crudFields.firstName'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.firstName') } },
      {
        field: 'last_name',
        header: t('access.columns.lastName'),
        sortable: true,
        filter: { type: 'text', placeholder: t('access.columns.lastName') },
        body: (row: Record<string, unknown>) => [row.last_name, row.patronymic].filter(Boolean).join(' ') || '-'
      },
      { field: 'updated_at', header: t('crudFields.updated'), sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'first_name', label: t('crudFields.firstName'), required: true },
      { key: 'last_name', label: t('directionWizard.lastName') },
      { key: 'patronymic', label: t('directionWizard.patronymic') },
      // Привязка к учётной записи — на её основании врач автоматически
      // подписывается на направления/образцы, где он указан как санитарный врач.
      { key: 'user_id', label: t('crudFields.account'), type: 'select', source: '/users', layout: { span: 6 } }
    ]
  },
  labs: {
    resource: 'labs',
    title: t('crudModules.labs.title'),
    description: t('crudModules.labs.description'),
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
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'code', header: t('access.columns.code'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.code') } },
      { field: 'name', header: t('access.columns.name'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.name') } },
      { field: 'full_name', header: t('crudFields.fullName'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.fullName') } },
      { field: 'branch.name', header: t('crudFields.branch'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.branch') } }
    ],
    fields: [
      { key: 'code', label: t('access.columns.code') },
      { key: 'name', label: t('access.columns.name') },
      { key: 'full_name', label: t('crudFields.fullName') },
      { key: 'branch_id', label: t('crudFields.branch'), type: 'select', source: '/branches' }
    ]
  },
  'role-subscription-rules': {
    // Права на управление правилами подписки проверяются в связке с
    // ролями/правами доступа — тот же ресурс, что у /role_permissions.
    resource: 'user-types',
    title: t('crudModules.roleSubscriptionRules.title'),
    description: t('crudModules.roleSubscriptionRules.description'),
    endpoint: '/role_subscription_rules',
    presetKey: 'role-subscription-rules',
    pageId: 'role-subscription-rules',
    initialFilters: {
      global: textFilter(),
      role_id: textFilter(),
      entity_type: textFilter()
    },
    columns: [
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'role_name', header: t('access.columns.role'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.role') } },
      {
        field: 'entity_type',
        header: t('crudFields.entityType'),
        sortable: true,
        filter: { type: 'select', options: subscriptionEntityTypeOptions() }
      },
      { field: 'branch_name', header: t('crudFields.branch'), filter: { type: 'text', placeholder: t('crudFields.branchEmptyAll') } },
      { field: 'lab_name', header: t('access.columns.laboratory'), filter: { type: 'text', placeholder: t('crudFields.labEmptyAll') } },
      { field: 'status_code', header: t('common.status'), filter: { type: 'select', options: subscriptionStatusCodeOptions() } }
    ],
    fields: [
      { key: 'role_id', label: t('access.columns.role'), type: 'select', source: '/roles', required: true, layout: { span: 6 } },
      {
        key: 'entity_type',
        label: t('crudFields.entityType'),
        type: 'select',
        required: true,
        options: subscriptionEntityTypeOptions(),
        layout: { span: 6 }
      },
      {
        key: 'branch_id',
        label: t('crudFields.branchEmptyAll'),
        type: 'select',
        source: '/branches',
        layout: { span: 6 }
      },
      {
        key: 'lab_id',
        label: t('crudFields.labEmptyAllSamplesOnly'),
        type: 'select',
        source: '/labs',
        layout: { span: 6 }
      },
      {
        key: 'status_code',
        label: t('crudFields.statusEmptyAny'),
        type: 'select',
        options: subscriptionStatusCodeOptions(),
        layout: { span: 12 }
      }
    ]
  },
  'research-goals': {
    resource: 'research-goals',
    title: t('dictionaries.researchGoals'),
    description: t('crudModules.researchGoals.description'),
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
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'code', header: t('access.columns.code'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.code') } },
      { field: 'name', header: t('access.columns.name'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.name') } },
      { field: 'comment', header: t('workflowCommands.formFields.comment'), sortable: true, filter: { type: 'text', placeholder: t('workflowCommands.formFields.comment') } },
      { field: 'lab.name', header: t('access.columns.laboratory'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.laboratory') } }
    ],
    fields: [
      { key: 'code', label: t('access.columns.code'), required: true },
      { key: 'name', label: t('access.columns.name'), required: true },
      { key: 'comment', label: t('workflowCommands.formFields.comment'), type: 'textarea' },
      { key: 'lab_id', label: t('access.columns.laboratory'), type: 'select', source: '/labs' }
    ]
  },
  'sample-types': {
    resource: 'sample-types',
    title: t('dictionaries.sampleTypes'),
    description: t('crudModules.sampleTypes.description'),
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
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'code', header: t('access.columns.code'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.code') } },
      { field: 'name', header: t('access.columns.name'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.name') } },
      { field: 'updated_at', header: t('crudFields.updated'), sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'code', label: t('access.columns.code') },
      { key: 'name', label: t('access.columns.name'), required: true }
    ]
  },
  indicators: {
    resource: 'indicators',
    title: t('dictionaries.indicators'),
    description: t('crudModules.indicators.description'),
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
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'name', header: t('access.columns.name'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.name') } },
      { field: 'unit', header: t('crudFields.unit'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.unit') } },
      { field: 'lab.name', header: t('access.columns.laboratory'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.laboratory') } },
      { field: 'sample_type.name', header: t('crudFields.sampleType'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.sampleType') } }
    ],
    fields: [
      { key: 'name', label: t('access.columns.name'), required: true },
      { key: 'unit', label: t('crudFields.unitOfMeasure') },
      { key: 'norm_text', label: t('crudFields.normText'), type: 'textarea' },
      { key: 'norm_value', label: t('crudFields.normValue') },
      { key: 'default_text', label: t('crudFields.defaultText'), type: 'textarea' },
      { key: 'comment', label: t('workflowCommands.formFields.comment'), type: 'textarea' },
      { key: 'lab_id', label: t('access.columns.laboratory'), type: 'select', source: '/labs' },
      { key: 'sample_type_id', label: t('crudFields.sampleType'), type: 'select', source: '/sample_types' }
    ]
  },
  'protocol-types': {
    resource: 'protocol-types',
    title: t('dictionaries.protocolTypes'),
    description: t('crudModules.protocolTypes.description'),
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
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'code', header: t('access.columns.code'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.code') } },
      { field: 'name', header: t('access.columns.name'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.name') } },
      { field: 'updated_at', header: t('crudFields.updated'), sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'code', label: t('access.columns.code') },
      { key: 'name', label: t('access.columns.name'), required: true }
    ]
  },
  conclusions: {
    resource: 'conclusions',
    title: t('dictionaries.conclusions'),
    description: t('crudModules.conclusions.description'),
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
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'code', header: t('access.columns.code'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.code') } },
      { field: 'name', header: t('access.columns.name'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.name') } },
      { field: 'text_singular', header: t('crudFields.singularHeader'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.singularHeader') } },
      { field: 'text_plural', header: t('crudFields.pluralHeader'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.pluralHeader') } },
      { field: 'updated_at', header: t('crudFields.updated'), sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'code', label: t('access.columns.code'), required: true },
      { key: 'name', label: t('access.columns.name'), required: true },
      { key: 'text_singular', label: t('crudFields.singularText'), type: 'textarea', required: true },
      { key: 'text_plural', label: t('crudFields.pluralText'), type: 'textarea', required: true },
      { key: 'comment', label: t('workflowCommands.formFields.comment'), type: 'textarea' }
    ]
  },
  protocols: {
    resource: 'protocols',
    title: t('nav.protocols'),
    description: t('crudModules.protocols.description'),
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
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'year_no', header: t('crudFields.yearNumber'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.yearNumber') } },
      { field: 'copies', header: t('crudFields.copies'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.copies') } },
      { field: 'protocol_type.name', header: t('crudFields.protocolType'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.protocolType') } },
      { field: 'conclusion.name', header: t('crudFields.conclusion'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.conclusion') } },
      {
        field: 'is_signed',
        header: t('crudFields.signed'),
        sortable: true,
        filter: {
          type: 'select',
          options: [
            { label: t('access.yes'), value: true },
            { label: t('access.no'), value: false }
          ]
        }
      },
      { field: 'issued_at', header: t('crudFields.issueDate'), sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'year_no', label: t('crudFields.yearNumber'), type: 'number', required: true, layout: { span: 4 } },
      { key: 'copies', label: t('crudFields.copies'), type: 'number', layout: { span: 4 } },
      { key: 'is_signed', label: t('crudFields.signed'), type: 'boolean', layout: { span: 4 } },
      { key: 'protocol_copy_name', label: t('crudFields.protocolCopyName') },
      { key: 'excerpt_copy_name', label: t('crudFields.excerptName') },
      { key: 'protocol_type_id', label: t('crudFields.protocolType'), type: 'select', source: '/protocol_types', layout: { span: 4 } },
      { key: 'conclusion_id', label: t('crudFields.conclusion'), type: 'select', source: '/conclusions', layout: { span: 4 } },
      { key: 'issued_at', label: t('crudFields.issueDate'), type: 'date', layout: { span: 4 } }
    ]
  },
  research: {
    resource: 'research',
    title: t('nav.research'),
    description: t('crudModules.research.description'),
    endpoint: '/research',
    include: 'sample,research_goal,lab,status',
    presetKey: 'research',
    pageId: 'research',
    initialFilters: {
      global: textFilter(),
      sample_id: textFilter(),
      research_goal_id: textFilter(),
      lab_id: textFilter(),
      status_id: multiSelectFilter(),
      comment: textFilter(),
      recommendation: textFilter(),
      created_at: dateFilter(),
      received_at: dateFilter(),
      completed_at: dateFilter()
    },
    filterFields: [
      selectFilterField('sample_id', t('entityHelpers.relationLabels.samples'), '/samples'),
      selectFilterField('research_goal_id', t('crudFields.researchGoal'), '/research_goals'),
      selectFilterField('lab_id', t('access.columns.laboratory'), '/labs'),
      multiSelectFilterField('status_id', t('common.status'), '/research_statuses'),
      dateFilterField('received_at', t('crudFields.received')),
      dateFilterField('completed_at', t('crudFields.completedM'))
    ],
    columns: [
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'sample.name', header: t('entityHelpers.relationLabels.samples'), sortable: true, filter: { type: 'text', placeholder: t('entityHelpers.relationLabels.samples') } },
      { field: 'research_goal.name', header: t('crudFields.researchGoal'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.researchGoal') } },
      { field: 'lab.name', header: t('access.columns.laboratory'), sortable: true, filter: { type: 'text', placeholder: t('access.columns.laboratory') } },
      { field: 'status.name', header: t('common.status'), sortable: true, filter: { type: 'text', placeholder: t('common.status') } },
      { field: 'comment', header: t('workflowCommands.formFields.comment'), sortable: true, filter: { type: 'text', placeholder: t('workflowCommands.formFields.comment') } },
      { field: 'recommendation', header: t('crudFields.recommendation'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.recommendation') } },
      { field: 'created_at', header: t('entityDetail.timeline.created'), sortable: true, filter: { type: 'dateRange' } },
      { field: 'received_at', header: t('crudFields.received'), sortable: true, filter: { type: 'dateRange' } },
      { field: 'completed_at', header: t('crudFields.completedM'), sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'sample_id', label: t('entityHelpers.relationLabels.samples'), type: 'select', source: '/samples', required: true, layout: { span: 6 } },
      { key: 'research_goal_id', label: t('crudFields.researchGoal'), type: 'select', source: '/research_goals', required: true, layout: { span: 6 } },
      { key: 'lab_id', label: t('access.columns.laboratory'), type: 'select', source: '/labs', layout: { span: 6 } },
      { key: 'comment', label: t('workflowCommands.formFields.comment'), type: 'textarea' },
      { key: 'recommendation', label: t('crudFields.recommendation'), type: 'textarea' },
      { key: 'received_at', label: t('crudFields.received'), type: 'date', layout: { span: 6 } },
      { key: 'completed_at', label: t('crudFields.completedM'), type: 'date', layout: { span: 6 } }
    ]
  },
  tests: {
    resource: 'tests',
    title: t('nav.tests'),
    description: t('crudModules.tests.description'),
    endpoint: '/tests',
    include: 'research,indicator,status',
    presetKey: 'tests',
    pageId: 'tests',
    initialFilters: {
      global: textFilter(),
      research_id: textFilter(),
      indicator_id: textFilter(),
      status_id: multiSelectFilter(),
      value: textFilter(),
      norm: textFilter(),
      comment: textFilter(),
      is_active: multiFilter()
    },
    filterFields: [
      selectFilterField('research_id', t('entityHelpers.relationLabels.research'), '/research'),
      selectFilterField('indicator_id', t('crudFields.indicator'), '/indicators'),
      multiSelectFilterField('status_id', t('common.status'), '/test_statuses'),
      textFilterField('value', t('workflowCommands.formFields.value')),
      textFilterField('norm', t('workflowCommands.formFields.norm')),
      textFilterField('comment', t('workflowCommands.formFields.comment')),
      booleanFilterField('is_active', t('crudFields.active'))
    ],
    columns: [
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'research.name', header: t('entityHelpers.relationLabels.research'), sortable: true, filter: { type: 'text', placeholder: t('entityHelpers.relationLabels.research') } },
      { field: 'indicator.name', header: t('crudFields.indicator'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.indicator') } },
      { field: 'status.name', header: t('common.status'), sortable: true, filter: { type: 'text', placeholder: t('common.status') } },
      { field: 'value', header: t('workflowCommands.formFields.value'), sortable: true, filter: { type: 'text', placeholder: t('workflowCommands.formFields.value') } },
      {
        field: 'is_active',
        header: t('crudFields.active'),
        sortable: true,
        filter: {
          type: 'select',
          options: [
            ...yesNoOptions()
          ]
        }
      },
      { field: 'updated_at', header: t('crudFields.updated'), sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'research_id', label: t('entityHelpers.relationLabels.research'), type: 'select', source: '/research', required: true },
      { key: 'indicator_id', label: t('crudFields.indicator'), type: 'select', source: '/indicators' },
      { key: 'value', label: t('workflowCommands.formFields.value') },
      { key: 'norm', label: t('workflowCommands.formFields.norm') },
      { key: 'comment', label: t('workflowCommands.formFields.comment'), type: 'textarea' },
      { key: 'is_active', label: t('crudFields.active'), type: 'boolean' }
    ]
  },
  'sample-targets': {
    resource: 'sample-targets',
    title: t('permissions.resourceLabels.sample-targets'),
    description: t('crudModules.sampleTargets.description'),
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
      { field: 'id', header: t('crudFields.id'), sortable: true },
      { field: 'sample.name', header: t('entityHelpers.relationLabels.samples'), sortable: true, filter: { type: 'text', placeholder: t('entityHelpers.relationLabels.samples') } },
      { field: 'research_goal.name', header: t('crudFields.researchGoal'), sortable: true, filter: { type: 'text', placeholder: t('crudFields.researchGoal') } },
      { field: 'status.name', header: t('common.status'), sortable: true, filter: { type: 'text', placeholder: t('common.status') } },
      { field: 'updated_at', header: t('crudFields.updated'), sortable: true, filter: { type: 'dateRange' } }
    ],
    fields: [
      { key: 'sample_id', label: t('entityHelpers.relationLabels.samples'), type: 'select', source: '/samples', required: true },
      { key: 'research_goal_id', label: t('crudFields.researchGoal'), type: 'select', source: '/research_goals', required: true },
      { key: 'status_id', label: t('common.status'), type: 'select', source: '/statuses' }
    ]
  }
}
