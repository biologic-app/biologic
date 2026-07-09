import { describe, expect, test } from "bun:test";
import { historyEntryToTechnicalAuditEvent } from "../../../src/shared/ui/technical-audit";

describe("technical audit history", () => {
  test("shows the real recommendation diff from audit history", () => {
    const event = historyEntryToTechnicalAuditEvent({
      id: "history-id",
      action: "research.update",
      actor_name: "api",
      created_at: "2026-06-09T10:00:00Z",
      diff: {
        recommendation: {
          from: "old recommendation",
          to: "new recommendation",
        },
      },
    });

    expect(event).toEqual({
      id: "history-id",
      label: "Исследование обновлено",
      description: "Рекомендация: old recommendation -> new recommendation",
      actor: "api",
      date: "2026-06-09T10:00:00Z",
    });
  });
});
