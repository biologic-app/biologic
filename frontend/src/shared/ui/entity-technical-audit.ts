import {
  entityDisplayCode,
  makeEvent,
  type DetailTimelineEvent,
} from "@/shared/ui/entity-detail.helpers";

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
      "Запись создана",
      `Код записи: ${entityDisplayCode(row.id)}`,
      "system",
      created,
    ),
    makeEvent(
      "update",
      "Последнее сохранение",
      options.savedDescription ?? "Изменения сохранены через API.",
      "api",
      updated,
    ),
    ...((options.extra?.filter(Boolean) as DetailTimelineEvent[] | undefined) ?? []),
    makeEvent(
      "status",
      "Текущее состояние",
      options.stateLabel || "Статус не указан",
      "process",
      updated ?? created,
    ),
  ];
}
