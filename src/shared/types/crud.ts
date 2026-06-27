import type { FormField } from '@/shared/types/form'
import type { Resource } from '@/shared/types/permissions'
import type { TableColumn, TableFilterField, TableFilters } from '@/shared/types/table'

export type CrudRow = {
  id: string | number;
  [key: string]: unknown;
};

export interface CrudModuleConfig {
  resource: Resource;
  title: string;
  description: string;
  endpoint: string;
  include?: string;
  presetKey: string;
  pageId: string;
  columns: TableColumn[];
  filterFields?: TableFilterField[];
  fields: FormField[];
  initialFilters: TableFilters;
  pageSize?: number;
}
