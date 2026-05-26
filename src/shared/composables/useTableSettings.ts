import { ref, watch } from "vue";

interface TableSettings {
  filters?: Record<string, unknown>;
  sorting?: { field: string; order: 1 | -1 };
  pageSize?: number;
  columnVisibility?: Record<string, boolean>;
}

const readSettings = (key: string): TableSettings => {
  if (typeof window === "undefined") {
    return {};
  }

  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as TableSettings) : {};
  } catch {
    return {};
  }
};

const writeSettings = (key: string, patch: TableSettings) => {
  if (typeof window === "undefined") {
    return;
  }

  try {
    const current = readSettings(key);
    window.localStorage.setItem(key, JSON.stringify({ ...current, ...patch }));
  } catch {
    // Storage can be unavailable in private mode; table controls should still work.
  }
};

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
