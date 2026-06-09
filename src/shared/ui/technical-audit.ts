import type { TechnicalAuditEvent } from "@/shared/ui/TechnicalAuditTimeline.vue";

export type TechnicalAuditHistoryEntry = {
  id: string;
  entity_type?: string | null;
  entity_id?: string | null;
  action?: string | null;
  actor_id?: string | null;
  actor_name?: string | null;
  diff?: Record<string, unknown> | null;
  snapshot?: Record<string, unknown> | null;
  created_at?: string | null;
};

const fieldLabels: Record<string, string> = {
  recommendation: "Рекомендация",
  comment: "Комментарий",
  status_code: "Статус",
  status_id: "Статус",
};

export function historyEntryToTechnicalAuditEvent(
  entry: TechnicalAuditHistoryEntry,
): TechnicalAuditEvent {
  return {
    id: entry.id,
    label: actionLabel(entry.action),
    description: diffDescription(entry.diff),
    actor: entry.actor_name || entry.actor_id || "api",
    date: entry.created_at ?? null,
  };
}

function actionLabel(action: string | null | undefined) {
  if (action === "research.update") return "Исследование обновлено";
  if (action === "research_assigned") return "Исследование назначено";
  if (action === "research_completed") return "Исследование завершено";
  if (!action) return "Событие аудита";

  return action.replace(/[._-]/g, " ");
}

function diffDescription(diff: Record<string, unknown> | null | undefined) {
  if (!diff || Object.keys(diff).length === 0) {
    return "Изменения записаны в журнал аудита.";
  }

  return Object.entries(diff)
    .map(([field, value]) => formatDiffField(field, value))
    .join("; ");
}

function formatDiffField(field: string, value: unknown) {
  const label = fieldLabels[field] ?? field;
  if (isRecord(value) && ("from" in value || "to" in value)) {
    return `${label}: ${formatAuditValue(value.from)} -> ${formatAuditValue(value.to)}`;
  }

  return `${label}: ${formatAuditValue(value)}`;
}

function formatAuditValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Да" : "Нет";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
