// Чистые помощники карточки сущности, вынесенные из EntityDetailDialogBase.vue.
// Без реактивности и зависимостей от props — только форматирование значений
// и сборка событий таймлайна. Тестируемы и переиспользуемы между табами.
import { formatDateTime } from "@/shared/utils/format";
import { getValueByPath } from "@/shared/utils/object";

export type DetailFieldValue = string | number | boolean | null;

export type DetailRow = {
  id: string | number;
  [key: string]: unknown;
};

export type RelationKind = "directions" | "samples" | "research" | "tests";

export type EntityKind = "directions" | "samples" | "research";

export interface RelatedRow extends DetailRow {
  relationKind: RelationKind;
  type: string;
  title: string;
  statusText: string;
  updatedAtText: string;
}

export interface DetailTimelineEvent {
  id: string;
  label: string;
  description: string;
  actor: string;
  date?: string | null;
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function compact<T>(items: Array<T | null | undefined | false | "">): T[] {
  return items.filter(Boolean) as T[];
}

export function compactEvents(items: Array<DetailTimelineEvent | null>): DetailTimelineEvent[] {
  return items.filter(Boolean) as DetailTimelineEvent[];
}

export function namedValue(value: unknown): string {
  if (isRecord(value)) {
    return formatPlain(value.name ?? value.full_name ?? value.code ?? value.id);
  }

  return "";
}

export function booleanStatus(row: DetailRow): string {
  if (typeof row.is_done === "boolean") {
    return row.is_done ? "Завершено" : "В работе";
  }

  return "";
}

export function pickText(row: DetailRow, paths: string[]): string {
  for (const path of paths) {
    const value = getValueByPath(row, path);
    const text = formatPlain(value);
    if (text !== "-") return text;
  }

  return "";
}

export function formatPlain(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Да" : "Нет";
  if (isRecord(value)) return namedValue(value) || JSON.stringify(value);
  return String(value);
}

export function formatDisplay(value: unknown): string {
  if (typeof value === "string" && /(T|\d{4}-\d{2}-\d{2})/.test(value)) {
    return formatDateTime(value);
  }

  return formatPlain(value);
}

export function makeEvent(
  id: string,
  label: string,
  description: string,
  actor: string,
  date: unknown,
): DetailTimelineEvent {
  return {
    id,
    label,
    description,
    actor: actor || "system",
    date: typeof date === "string" ? date : null,
  };
}

export function relationLabel(kind: RelationKind): string {
  const labels: Record<RelationKind, string> = {
    directions: "Направление",
    samples: "Образец",
    research: "Исследование",
    tests: "Тест",
  };

  return labels[kind];
}

export function entityDisplayCode(value: unknown): string {
  if (typeof value !== "string" && typeof value !== "number") {
    return "";
  }

  const text = String(value);
  const uuidPrefix = text.match(/^[0-9a-f]{8}/i)?.[0];
  return `#${(uuidPrefix ?? text.slice(0, 8)).toUpperCase()}`;
}

export function normalizeFormValue(value: unknown): DetailFieldValue {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return value;
  }

  if (value === null || value === undefined) {
    return null;
  }

  return String(value);
}
