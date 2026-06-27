import { ref, watch } from "vue";
import { readJson, writeJson } from "@/shared/composables/useJsonStorage";

export interface TableSettings {
  filters?: Record<string, unknown>;
  sorting?: { field: string; order: 1 | -1 };
  pageSize?: number;
  columnVisibility?: Record<string, boolean>;
}

export const readTableSettings = (key: string): TableSettings => readJson(key, {} as TableSettings);

export const writeTableSettings = (key: string, patch: TableSettings) =>
  writeJson(key, { ...readTableSettings(key), ...patch });

const readSettings = readTableSettings;
const writeSettings = writeTableSettings;

const defaultColumnVisibility: Record<string, boolean> = {
  id: false,
};

export const useTableColumnVisibility = (
  key: string,
  defaults: Record<string, boolean> = {},
) => {
  const stored = readSettings(key).columnVisibility ?? {};
  const columnVisibility = ref<Record<string, boolean>>({
    ...defaultColumnVisibility,
    ...defaults,
    ...stored,
  });

  watch(
    columnVisibility,
    (value) => {
      writeSettings(key, { columnVisibility: value });
    },
    { deep: true },
  );

  return columnVisibility;
};

export const usePersistedTableSetting = <T>(
  key: string,
  field: keyof TableSettings | string,
  defaultValue: T,
) => {
  const stored = readSettings(key) as Record<string, unknown>;
  const value = ref((stored[field as string] as T | undefined) ?? defaultValue);

  watch(
    value,
    (next) => {
      writeSettings(key, { [field]: next } as TableSettings);
    },
    { deep: true },
  );

  return value;
};
