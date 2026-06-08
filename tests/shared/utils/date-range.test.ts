import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  DATE_RANGE_PRESETS,
  isDateRangePresetSelected,
  selectDateRangePreset,
} from "../../../src/shared/utils/date-range";

const dateRangeFilterSource = readFileSync(
  resolve(import.meta.dir, "../../../src/shared/ui/CrudDateRangeFilter.vue"),
  "utf8",
);

describe("date range presets", () => {
  test("builds predefined date ranges from a fixed current date", () => {
    const currentDate = new Date(Date.UTC(2026, 5, 8));

    expect(selectDateRangePreset(DATE_RANGE_PRESETS[0], currentDate)).toEqual([
      "2026-06-01",
      "2026-06-08",
    ]);
    expect(selectDateRangePreset(DATE_RANGE_PRESETS[3], currentDate)).toEqual([
      "2026-03-08",
      "2026-06-08",
    ]);
  });

  test("detects the selected preset", () => {
    const currentDate = new Date(Date.UTC(2026, 5, 8));

    expect(
      isDateRangePresetSelected(["2026-06-01", "2026-06-08"], DATE_RANGE_PRESETS[0], currentDate),
    ).toBe(true);
    expect(
      isDateRangePresetSelected(["2026-06-02", "2026-06-08"], DATE_RANGE_PRESETS[0], currentDate),
    ).toBe(false);
  });

  test("vertically centers preset actions and keeps labels left aligned", () => {
    expect(dateRangeFilterSource).toContain("sm:w-52");
    expect(dateRangeFilterSource).toContain("sm:justify-center");
    expect(dateRangeFilterSource).toContain("justify-start");
    expect(dateRangeFilterSource).toContain(":ui=\"{ label: 'w-full text-left' }\"");
  });
});
