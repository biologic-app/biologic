import { describe, expect, test } from "bun:test";
import {
  getLastStepperIndex,
  timelineEventsToStepperItems,
} from "../../../src/shared/ui/timeline-stepper";

describe("timeline stepper helpers", () => {
  test("maps audit and business events to Nuxt UI stepper items", () => {
    expect(
      timelineEventsToStepperItems([
        {
          id: "created",
          label: "Создано",
          description: "Запись создана",
          actor: "system",
          date: "2026-06-09T10:00:00Z",
        },
      ]),
    ).toEqual([
      {
        value: "created",
        title: "Создано",
        description: "Запись создана",
        icon: "i-lucide-circle-dot",
        actor: "system",
        date: "2026-06-09T10:00:00Z",
      },
    ]);
  });

  test("uses the last item index as the controlled stepper value", () => {
    expect(getLastStepperIndex([])).toBe(0);
    expect(getLastStepperIndex(["created"])).toBe(0);
    expect(getLastStepperIndex(["created", "registered", "completed"])).toBe(2);
  });
});
