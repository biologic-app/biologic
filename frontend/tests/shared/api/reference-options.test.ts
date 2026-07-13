import { describe, expect, test } from "bun:test";
import { formatReferenceOption } from "../../../src/shared/api/reference-options";

describe("reference options", () => {
  test("uses status name as label and status id as submitted value", () => {
    expect(
      formatReferenceOption(
        { id: "status-id", code: "registered", name: "Зарегистрирован" },
        "/sample_statuses",
      ),
    ).toEqual({
      label: "Зарегистрирован",
      value: "status-id",
    });
  });

  test("does not merge status code into the displayed label", () => {
    const option = formatReferenceOption(
      { id: "status-id", code: "draft", name: "Черновик" },
      "/direction_statuses",
    );

    expect(option.label).toBe("Черновик");
    expect(option.label).not.toContain("draft");
  });

  test("keeps default reference labels and id values for non-status dictionaries", () => {
    expect(
      formatReferenceOption(
        { id: "branch-id", code: "BR-01", name: "Филиал №1" },
        "/branches",
      ),
    ).toEqual({
      label: "Филиал №1 (BR-01)",
      value: "branch-id",
    });
  });

  test("does not merge code into the label for sample types", () => {
    const option = formatReferenceOption(
      { id: "sample-type-id", code: "SM-01", name: "Кровь" },
      "/sample_types",
    );

    expect(option.label).toBe("Кровь");
    expect(option.label).not.toContain("SM-01");
  });
});
