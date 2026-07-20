import {
  entityDisplayCode,
  makeEvent,
  type DetailTimelineEvent,
} from "@/shared/ui/entity-detail.helpers";
import { i18n } from "@/shared/i18n";

const t = (key: string, params?: Record<string, unknown>) =>
  i18n.global.t(key, params ?? {}).toString();

// Резервные события технического аудита, когда backend /history пуст.
// Три опорные точки: запись создана → последнее сохранение → текущее состояние.
// Раньше почти идентично дублировалось в трёх модалках
// (EntityDetailDialogBase / AccessEntityDetailModal / DictionaryCrudDetailModal).
export function buildFallbackAuditEvents(
  row: { id: string | number; [key: string]: unknown },
  options: {
    // Подпись текущего состояния (статус/активность/«Актуальная запись»).
    stateLabel: string;
    // Описание события «Последнее сохранение».
    savedDescription?: string;
    // Доменные события, вставляемые между «сохранением» и «состоянием».
    extra?: Array<DetailTimelineEvent | null>;
  },
): DetailTimelineEvent[] {
  const created = row.created_at ?? row.inserted_at ?? null;
  const updated = row.updated_at ?? row.modified_at ?? null;

  return [
    makeEvent(
      "entity",
      t("technicalAudit.recordCreated"),
      t("technicalAudit.recordCode", { code: entityDisplayCode(row.id) }),
      "system",
      created,
    ),
    makeEvent(
      "update",
      t("technicalAudit.lastSave"),
      options.savedDescription ?? t("entityDetail.changesSavedViaApi"),
      "api",
      updated,
    ),
    ...((options.extra?.filter(Boolean) as DetailTimelineEvent[] | undefined) ?? []),
    makeEvent(
      "status",
      t("technicalAudit.currentState"),
      options.stateLabel || t("technicalAudit.statusNotSpecified"),
      "process",
      updated ?? created,
    ),
  ];
}
