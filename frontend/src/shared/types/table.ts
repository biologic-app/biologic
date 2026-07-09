export type FilterType = 'text' | 'dateRange' | 'multiSelect' | 'select'

export interface TableFilterOption {
  label: string
  value: string | number | boolean
}

export interface TableColumn {
  field: string
  header: string
  sortable?: boolean
  width?: string
  filter?: {
    type: FilterType
    placeholder?: string
    options?: TableFilterOption[]
    source?: string
  }
  body?: (row: Record<string, any>) => string | number | null | undefined
}

export type TableFilterField = Pick<TableColumn, 'field' | 'header' | 'filter'>

export type TableFilters = Record<string, { value: any; matchMode?: string }>
