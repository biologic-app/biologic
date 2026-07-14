// Чистые помощники карточки сущности, вынесенные из EntityDetailDialogBase.vue.
// Без реактивности и зависимостей от props — только форматирование значений
// и сборка событий таймлайна. Тестируемы и переиспользуемы между табами.
import { formatDateTime } from "@/shared/utils/format";
import { getValueByPath } from "@/shared/utils/object";
import { SAMPLE_STATUS_REJECTED_CODE } from "@/shared/domain/status-timeline";
import { i18n } from "@/shared/i18n";

const t = (key: string, params?: Record<string, unknown>) =>
  i18n.global.t(key, params ?? {}).toString();

export type DetailFieldValue = string | number | boolean | null;

export type DetailRow = {
  id: string | number;
  [key: string]: unknown;
};

export type RelationKind = "directions" | "samples" | "research" | "tests";

export type EntityKind = "directions" | "samples" | "research" | "protocols";

export interface RelatedRow extends DetailRow {
  relationKind: RelationKind;
  type: string;
  title: string;
  statusText: string;
  // Нормализованный код статуса (resolveStatusCode) — для группировки строк и
  // логики статусов, консистентно со списками в DictionaryCrudContent.
  statusCode: string;
  // Реальный цвет статуса из include=status (бэкенд) — сырой токен для StatusBadge.
  // Пусто, если статус не пришёл с записью.
  statusColor?: string | null;
  updatedAtText: string;
  // Лаборатория исследования (research_goal/lab приходят в include). Пусто для
  // образцов.
  labName?: string;
  // Тип образца — резолвится на фронте из справочника /sample_types, т.к. бэкенд
  // не отдаёт sample_type вложенным объектом (populate только status/creator).
  sampleTypeName?: string;
  // Дочерние строки дерева «образец → исследования» (вкладка образцов).
  children?: RelatedRow[];
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

// «Фамилия И.О.» из полей персоны (врачи/пользователи не имеют поля name).
export function shortPersonName(value: Record<string, unknown>): string {
  const lastName = typeof value.last_name === "string" ? value.last_name.trim() : "";
  const initials = [value.first_name, value.patronymic]
    .map((part) => (typeof part === "string" && part.trim() ? `${part.trim()[0].toUpperCase()}.` : ""))
    .join("");
  return [lastName, initials].filter(Boolean).join(" ");
}

export function namedValue(value: unknown): string {
  if (isRecord(value)) {
    const named = value.name ?? value.full_name ?? value.code;
    if (named !== null && named !== undefined && named !== "") {
      return formatPlain(named);
    }
    // ID в интерфейсе не показываем — лучше ФИО или пусто.
    return shortPersonName(value);
  }

  return "";
}

export function booleanStatus(row: DetailRow): string {
  if (typeof row.is_done === "boolean") {
    return row.is_done ? t("entityHelpers.completed") : t("entityHelpers.inProgress");
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
  if (typeof value === "boolean") return value ? t("access.yes") : t("access.no");
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
    actor: actor || t("entityHelpers.systemActor"),
    date: typeof date === "string" ? date : null,
  };
}

export function relationLabel(kind: RelationKind): string {
  const labels: Record<RelationKind, string> = {
    directions: t("entityHelpers.relationLabels.directions"),
    samples: t("entityHelpers.relationLabels.samples"),
    research: t("entityHelpers.relationLabels.research"),
    tests: t("entityHelpers.relationLabels.tests"),
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

// Код записи: номер вместе с годом — «№ 2025-461»; для сущностей без номера —
// короткий код по UUID.
export function recordCode(row: Record<string, unknown> & { id: string | number }): string {
  const baseNo = row.base_no;
  if (typeof baseNo === "number" || (typeof baseNo === "string" && baseNo.trim())) {
    const yearNo = row.year_no;
    const hasYear = typeof yearNo === "number" || (typeof yearNo === "string" && yearNo.trim());
    return hasYear ? `№ ${yearNo}-${baseNo}` : `№ ${baseNo}`;
  }
  return entityDisplayCode(row.id);
}

// Провал дедлайна выпуска образца: если deadline не задан — false; иначе
// сравниваем дедлайн с фактическим выпуском (completed_at) или «сейчас», если
// образец ещё не выпущен. Совпадает с формулой deadlineStatus в
// EntityDetailDialogBase — вынесено для переиспользования в таблице и списке.
// «Брак» — терминальный статус: выпуска не будет, поэтому дедлайн не считается
// проваленным (согласовано с deadlineTrailItem, который скрывает индикатор).
export function isSampleDeadlineOverdue(row: Record<string, unknown>): boolean {
  const statusCode = row.statusCode ?? getValueByPath(row, "status.code");
  if (statusCode === SAMPLE_STATUS_REJECTED_CODE) return false;
  const deadlineRaw = row.deadline;
  if (deadlineRaw === null || deadlineRaw === undefined || deadlineRaw === "") return false;
  const deadline = new Date(String(deadlineRaw)).getTime();
  if (!Number.isFinite(deadline)) return false;
  const completedRaw = row.completed_at;
  const release = completedRaw ? new Date(String(completedRaw)).getTime() : Date.now();
  return release > deadline;
}

// Срочность образца/направления — сырое поле is_urgent (research/tests его не
// имеют, но получают через наследование от родительского образца).
export function isRowUrgent(row: Record<string, unknown>): boolean {
  return row.is_urgent === true;
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
