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
  // Поля колонок, скрытые по умолчанию (пока пользователь не включит вручную
  // через меню видимости колонок) — id колонки, не заголовок.
  defaultHiddenColumns?: string[];
  // Ключи select-полей фильтров (например 'sample_type_id'), чьи справочники
  // нужно подгрузить сразу при монтировании таблицы — не ради самого фильтра,
  // а потому что колонка без body-рендера использует их как fallback подписи
  // (бэкенд не отдаёт вложенный объект для этой связи). Не путать с полным
  // набором фильтров — тот подгружается лениво только при открытии панели.
  displayReferenceFields?: string[];
}
